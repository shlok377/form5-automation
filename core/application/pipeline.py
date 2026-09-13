#!/usr/bin/env python3
"""
FORM-5 Resilient Parallel Pipeline
Coordinates:
- Agent 1: ExtractorAgent (Reads CSV, transforms data, writes atomic JSONs to temp_json/)
- Agent 2: PdfManagerAgent (Consumes JSONs from queue, renders via Chromium, writes atomic PDFs to output/)
Includes full crash recovery, idempotency, row-level error isolation, and live event callbacks.
"""

import csv
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# Ensure application directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_json import (
    sanitize_filename,
    get_value_from_row,
    evaluate_section_f,
    build_employee_json,
)
from generate_pdfs import find_chromium, build_filled_html
from excel_adapter import convert_xlsx_to_csv, is_excel_file


class PipelineManager:
    """
    Orchestrates Agent 1 and Agent 2 in a parallel producer-consumer queue.
    """
    def __init__(self, base_dir=None, root_dir=None):
        app_dir = os.path.dirname(os.path.abspath(__file__))
        core_dir = os.path.dirname(app_dir)
        default_root = os.path.dirname(core_dir)

        self.root_dir = root_dir or default_root
        self.core_dir = base_dir or core_dir
        self.base_dir = self.core_dir  # for backward-compatibility

        self.data_csv = os.path.join(self.core_dir, "data", "data.csv")

        # Safe mapping config resolution
        for candidate in [
            os.path.join(self.core_dir, "config", "mapping_config.json"),
            os.path.join(self.core_dir, "mapping_config.json"),
            os.path.join(app_dir, "mapping_config.json"),
            os.path.join(self.root_dir, "mapping_config.json"),
        ]:
            if os.path.exists(candidate):
                self.mapping_config = candidate
                break
        else:
            self.mapping_config = os.path.join(self.core_dir, "config", "mapping_config.json")

        self.temp_json_dir = os.path.join(self.core_dir, "temp_json")
        self.output_dir = os.path.join(self.root_dir, "output")
        self.template_path = os.path.join(app_dir, "form_template.html")
        self.failed_log_path = os.path.join(self.temp_json_dir, "failed_records.json")
        
        os.makedirs(self.temp_json_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.data_csv), exist_ok=True)
        
        self.chromium_path = find_chromium()
        self.lock = threading.RLock()
        self.listeners = []
        self.work_queue = queue.Queue()
        self.stop_requested = False
        
        # State
        self.state = "idle"  # idle, running, completed, stopped, error
        self.total_records = 0
        self.json_generated = 0
        self.json_skipped = 0
        self.pdf_generated = 0
        self.pdf_skipped = 0
        self.failed_records = []
        self.recent_logs = []
        self._load_existing_failures()

    def _load_existing_failures(self):
        if os.path.exists(self.failed_log_path):
            try:
                with open(self.failed_log_path, "r", encoding="utf-8") as f:
                    self.failed_records = json.load(f)
            except Exception:
                self.failed_records = []

    def _save_failures(self):
        try:
            tmp_path = self.failed_log_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.failed_records, f, indent=2)
            os.replace(tmp_path, self.failed_log_path)
        except Exception as e:
            self.log(f"Failed to save error log: {e}", level="error")

    def add_listener(self, callback):
        with self.lock:
            self.listeners.append(callback)

    def remove_listener(self, callback):
        with self.lock:
            if callback in self.listeners:
                self.listeners.remove(callback)

    def log(self, message, level="info"):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message
        }
        with self.lock:
            self.recent_logs.append(entry)
            if len(self.recent_logs) > 150:
                self.recent_logs.pop(0)
            callbacks = list(self.listeners)
        
        for cb in callbacks:
            try:
                cb({"type": "log", "data": entry})
            except Exception:
                pass

    def emit_progress(self):
        payload = self.get_status()
        with self.lock:
            callbacks = list(self.listeners)
        for cb in callbacks:
            try:
                cb({"type": "progress", "data": payload})
            except Exception:
                pass

    def get_status(self):
        with self.lock:
            existing_pdfs = len([f for f in os.listdir(self.output_dir) if f.endswith(".pdf") and not f.startswith(".")]) if os.path.exists(self.output_dir) else 0
            return {
                "state": self.state,
                "total_records": self.total_records,
                "json_generated": self.json_generated,
                "json_skipped": self.json_skipped,
                "json_total_ready": self.json_generated + self.json_skipped,
                "pdf_generated": self.pdf_generated,
                "pdf_skipped": self.pdf_skipped,
                "pdf_total_ready": self.pdf_generated + self.pdf_skipped,
                "existing_pdf_count": existing_pdfs,
                "failed_count": len(self.failed_records),
                "failed_records": list(self.failed_records),
                "recent_logs": list(self.recent_logs[-30:])
            }

    def reset(self):
        """
        Cleans up generated batch outputs (PDFs, ZIPs, and intermediate JSON cache).
        GUARANTEED NEVER to delete mapping_config.json, code files, or .gitkeep.
        """
        PROTECTED_NAMES = {"mapping_config.json", ".gitkeep"}

        with self.lock:
            # 1. Purge only generated PDFs, ZIPs, and tmp files in output_dir
            if os.path.exists(self.output_dir):
                for fname in os.listdir(self.output_dir):
                    if fname in PROTECTED_NAMES:
                        continue
                    if fname.endswith((".pdf", ".zip", ".tmp")) or fname.startswith(".all_reports"):
                        try:
                            os.remove(os.path.join(self.output_dir, fname))
                        except Exception as e:
                            self.log(f"Warning removing {fname}: {e}", level="warn")

            # 2. Purge only generated employee JSON files and tmp files in temp_json_dir
            if os.path.exists(self.temp_json_dir):
                for fname in os.listdir(self.temp_json_dir):
                    if fname in PROTECTED_NAMES or fname == "mapping_config.json":
                        continue
                    if fname.endswith((".json", ".tmp")):
                        try:
                            os.remove(os.path.join(self.temp_json_dir, fname))
                        except Exception as e:
                            self.log(f"Warning removing {fname}: {e}", level="warn")

            # 3. Reset in-memory tracking state
            self.state = "idle"
            self.total_records = 0
            self.json_generated = 0
            self.json_skipped = 0
            self.pdf_generated = 0
            self.pdf_skipped = 0
            self.failed_records = []
            self.recent_logs = []
            while not self.work_queue.empty():
                try:
                    self.work_queue.get_nowait()
                except Exception:
                    break
            self.stop_requested = False

            # 4. Notify listeners of clean state
            self.emit_progress()
            return True

    def start(self, force=False, num_workers=2):
        with self.lock:
            if self.state == "running":
                return False, "Pipeline is already running."
            self.state = "running"
            self.stop_requested = False
            self.json_generated = 0
            self.json_skipped = 0
            self.pdf_generated = 0
            self.pdf_skipped = 0
            # Clear previous failures if forcing, otherwise keep
            if force:
                self.failed_records = []
                self._save_failures()

        num_workers = max(1, min(3, int(num_workers)))
        threading.Thread(target=self._run_pipeline, args=(force, num_workers), daemon=True).start()
        return True, "Pipeline started."

    def stop(self):
        with self.lock:
            if self.state != "running":
                return False, "Pipeline is not running."
            self.stop_requested = True
            self.state = "stopping"
        self.log("Pipeline stop requested by user.", level="warn")
        self.emit_progress()
        return True, "Stop requested."

    def _run_pipeline(self, force, num_workers):
        num_workers = max(1, min(3, int(num_workers)))
        self.log(f"Starting pipeline (force={force}, workers={num_workers})...")
        
        if not os.path.exists(self.data_csv):
            xlsx_alt = os.path.join(self.base_dir, "data", "data.xlsx")
            if os.path.exists(xlsx_alt):
                self.log(f"Detected {xlsx_alt}. Auto-converting to CSV...")
                try:
                    convert_xlsx_to_csv(xlsx_alt, self.data_csv)
                    self.log(f"Successfully converted Excel to {self.data_csv}")
                except Exception as e:
                    self.log(f"Failed to convert Excel to CSV: {e}", level="error")
                    with self.lock:
                        self.state = "error"
                    self.emit_progress()
                    return
            else:
                self.log(f"Error: Data file not found at {self.data_csv} (nor data.xlsx)", level="error")
                with self.lock:
                    self.state = "error"
                self.emit_progress()
                return

        if not self.chromium_path:
            self.log("Error: Chromium browser not found.", level="error")
            with self.lock:
                self.state = "error"
            self.emit_progress()
            return

        with open(self.mapping_config, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        with open(self.template_path, "r", encoding="utf-8") as f:
            template_str = f.read()

        with open(self.data_csv, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            try:
                next(reader) # Category header
                next(reader) # Column name header
            except StopIteration:
                self.log("Error: CSV has invalid headers.", level="error")
                with self.lock:
                    self.state = "error"
                self.emit_progress()
                return
            rows = list(reader)

        with self.lock:
            self.total_records = len(rows)

        self.log(f"Loaded {self.total_records} employee records from CSV.")
        self.emit_progress()

        # Clear queue
        while not self.work_queue.empty():
            try:
                self.work_queue.get_nowait()
            except queue.Empty:
                break

        # Start Agent 2 (PDF Workers) with staggered thread initialization
        worker_threads = []
        for worker_id in range(num_workers):
            t = threading.Thread(
                target=self._pdf_worker_loop,
                args=(worker_id, template_str, force),
                daemon=True
            )
            t.start()
            worker_threads.append(t)
            time.sleep(0.15)

        # Run Agent 1 (JSON Extractor)
        self._extractor_producer_loop(rows, mapping, force)

        # Signal PDF workers to finish
        for _ in range(num_workers):
            self.work_queue.put(None)

        # Wait for workers to finish
        for t in worker_threads:
            t.join()

        with self.lock:
            if self.stop_requested:
                self.state = "stopped"
                self.log("Pipeline execution stopped.", level="warn")
            else:
                self.state = "completed"
                self.log(
                    f"Pipeline completed! JSONs: {self.json_generated + self.json_skipped}/{self.total_records}, "
                    f"PDFs: {self.pdf_generated + self.pdf_skipped}/{self.total_records}, "
                    f"Errors: {len(self.failed_records)}"
                )

        self.emit_progress()

    def _extractor_producer_loop(self, rows, mapping, force):
        """Agent 1: Row extraction & atomic JSON generation in batches of 5 with 2s pause"""
        BATCH_SIZE = 5
        PAUSE_SECONDS = 2.0

        for i, row in enumerate(rows, start=1):
            if self.stop_requested:
                break

            # Natural queue backpressure: pause if queue has >= 10 items until Agent 2 catches up
            while self.work_queue.qsize() >= 10 and not self.stop_requested:
                time.sleep(0.2)

            if self.stop_requested:
                break

            idx_str = f"{i:04d}"
            code = row[0].strip() if len(row) > 0 else "UNKNOWN"
            name = row[2].strip() if len(row) > 2 else f"Employee_{idx_str}"
            json_filename = f"{idx_str}_{sanitize_filename(name)}_{sanitize_filename(code)}.json"
            final_json_path = os.path.join(self.temp_json_dir, json_filename)

            # Check idempotency: does valid JSON already exist?
            already_done = False
            if not force and os.path.exists(final_json_path) and os.path.getsize(final_json_path) > 10:
                try:
                    with open(final_json_path, "r", encoding="utf-8") as jf:
                        json.load(jf)
                    already_done = True
                except Exception:
                    already_done = False

            if already_done:
                with self.lock:
                    self.json_skipped += 1
                self.work_queue.put(final_json_path)
            else:
                # Generate JSON with row-level error isolation
                try:
                    if not any(cell.strip() for cell in row):
                        raise ValueError(f"Row {i} is completely empty.")
                    if len(row) < 3 or (not row[0].strip() and not row[2].strip()):
                        raise ValueError(f"Row {i} is missing both Employee Code and Employee Name.")

                    _, emp_data = build_employee_json(row, i, mapping)
                    
                    # Atomic write: write to .tmp then replace
                    tmp_path = os.path.join(self.temp_json_dir, f".{json_filename}.tmp")
                    with open(tmp_path, "w", encoding="utf-8") as out:
                        json.dump(emp_data, out, indent=2, ensure_ascii=False)
                    os.replace(tmp_path, final_json_path)

                    with self.lock:
                        self.json_generated += 1
                        if any(f.get("code") == code for f in self.failed_records):
                            self.failed_records = [f for f in self.failed_records if f.get("code") != code]
                            self._save_failures()

                    self.work_queue.put(final_json_path)

                except Exception as e:
                    err_msg = f"Row {i} ({code} - {name}): {str(e)}"
                    self.log(f"[Agent 1 Error] {err_msg}", level="error")
                    with self.lock:
                        self.failed_records = [f for f in self.failed_records if f.get("code") != code]
                        self.failed_records.append({
                            "row": i,
                            "code": code,
                            "name": name,
                            "stage": "json_extraction",
                            "error": str(e),
                            "time": time.strftime("%H:%M:%S")
                        })
                        self._save_failures()

            # Pacing & Progress emission: pause 2s every 5 records to allow Agent 2 steady throughput
            total_ready = self.json_generated + self.json_skipped
            if i % BATCH_SIZE == 0 and i < len(rows):
                self.log(f"[Agent 1] Extracted {total_ready}/{self.total_records} records. Pausing {int(PAUSE_SECONDS)}s...")
                self.emit_progress()
                # Responsive pause in 0.1s slices so stop requests are handled immediately
                for _ in range(int(PAUSE_SECONDS / 0.1)):
                    if self.stop_requested:
                        break
                    time.sleep(0.1)
            elif i == len(rows):
                self.log(f"[Agent 1] Completed extracting all {total_ready}/{self.total_records} records.")
                self.emit_progress()

    def _pdf_worker_loop(self, worker_id, template_str, force):
        """Agent 2: Consumer worker rendering PDFs via headless Chromium"""
        while True:
            item = self.work_queue.get()
            if item is None or self.stop_requested:
                self.work_queue.task_done()
                break

            json_path = item
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    emp_data = json.load(f)

                name = emp_data.get("employee_name", "Employee")
                pdf_filename = f"{sanitize_filename(name)}.pdf"
                final_pdf_path = os.path.join(self.output_dir, pdf_filename)

                # Check idempotency: does valid PDF already exist?
                if not force and os.path.exists(final_pdf_path) and os.path.getsize(final_pdf_path) > 10000:
                    with self.lock:
                        self.pdf_skipped += 1
                        code = emp_data.get("employee_code")
                        if any(f.get("code") == code for f in self.failed_records):
                            self.failed_records = [f for f in self.failed_records if f.get("code") != code]
                            self._save_failures()
                    continue

                filled_html = build_filled_html(template_str, emp_data)
                
                # Render to temporary file first (atomic generation)
                with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as tmp_html:
                    tmp_html.write(filled_html)
                    tmp_html_path = tmp_html.name

                tmp_pdf_path = os.path.join(self.output_dir, f".{pdf_filename}.tmp")

                # Worker launch jitter to prevent simultaneous CPU spikes across threads
                time.sleep(0.1 * (worker_id + 1))

                cmd = [
                    self.chromium_path,
                    "--headless",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-software-rasterizer",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-default-apps",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--no-first-run",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={tmp_pdf_path}",
                    tmp_html_path
                ]
                
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                
                # Atomic rename
                os.replace(tmp_pdf_path, final_pdf_path)
                
                if os.path.exists(tmp_html_path):
                    os.remove(tmp_html_path)

                with self.lock:
                    self.pdf_generated += 1

                total_pdf = self.pdf_generated + self.pdf_skipped
                if total_pdf % 5 == 0 or total_pdf == self.total_records:
                    self.log(f"[Agent 2] Rendered {total_pdf}/{self.total_records} PDFs.")
                    self.emit_progress()

            except Exception as e:
                code = emp_data.get("employee_code", "UNKNOWN") if 'emp_data' in locals() else "UNKNOWN"
                name = emp_data.get("employee_name", os.path.basename(json_path)) if 'emp_data' in locals() else os.path.basename(json_path)
                err_msg = f"PDF render error for {name} ({code}): {str(e)}"
                self.log(f"[Agent 2 Error] {err_msg}", level="error")
                
                with self.lock:
                    self.failed_records = [f for f in self.failed_records if f.get("code") != code]
                    self.failed_records.append({
                        "code": code,
                        "name": name,
                        "stage": "pdf_render",
                        "error": str(e),
                        "time": time.strftime("%H:%M:%S")
                    })
                    self._save_failures()
                self.emit_progress()

            finally:
                self.work_queue.task_done()

    def get_records_overview(self):
        """Returns the full list of employees with their JSON & PDF status."""
        records = []
        if not os.path.exists(self.data_csv):
            return records

        with open(self.mapping_config, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        with open(self.data_csv, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            try:
                next(reader)
                next(reader)
            except StopIteration:
                return records
            
            for i, row in enumerate(reader, start=1):
                idx_str = f"{i:04d}"
                code = row[0].strip() if len(row) > 0 else "UNKNOWN"
                name = row[2].strip() if len(row) > 2 else f"Employee_{idx_str}"
                age = row[3].strip() if len(row) > 3 else ""
                designation = row[10].strip() if len(row) > 10 else ""
                
                json_filename = f"{idx_str}_{sanitize_filename(name)}_{sanitize_filename(code)}.json"
                json_path = os.path.join(self.temp_json_dir, json_filename)
                pdf_filename = f"{sanitize_filename(name)}.pdf"
                pdf_path = os.path.join(self.output_dir, pdf_filename)
                
                has_json = os.path.exists(json_path) and os.path.getsize(json_path) > 10
                has_pdf = os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 10000
                
                # Check error
                err = next((f for f in self.failed_records if f.get("code") == code), None)

                records.append({
                    "row": i,
                    "code": code,
                    "name": name,
                    "age": age,
                    "designation": designation,
                    "json_file": json_filename if has_json else None,
                    "pdf_file": pdf_filename if has_pdf else None,
                    "has_json": has_json,
                    "has_pdf": has_pdf,
                    "error": err["error"] if err else None
                })
        return records

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FORM-5 Resilient Parallel Pipeline (JSON Extraction + PDF Generation)")
    parser.add_argument("--workers", type=int, default=2, help="Number of PDF worker threads (default: 2, max: 3)")
    parser.add_argument("--force", action="store_true", help="Force re-generation of all JSONs and PDFs")
    parser.add_argument("--status", action="store_true", help="Print pipeline status and exit")
    args = parser.parse_args()

    mgr = PipelineManager()
    if args.status:
        print(json.dumps(mgr.get_status(), indent=2))
        sys.exit(0)

    print(f"=== FORM-5 Parallel Pipeline ===")
    print(f"Workers: {args.workers} | Force: {args.force}")

    def console_listener(evt):
        if evt.get("type") == "log":
            d = evt.get("data", {})
            lvl = d.get("level", "info").upper()
            msg = d.get("message", "")
            t = d.get("time", "")
            print(f"[{t}] [{lvl}] {msg}")

    mgr.add_listener(console_listener)
    success, msg = mgr.start(force=args.force, num_workers=args.workers)
    if not success:
        print(f"Failed to start pipeline: {msg}", file=sys.stderr)
        sys.exit(1)

    while True:
        time.sleep(0.5)
        st = mgr.get_status()
        if st["state"] in ["completed", "stopped", "error"]:
            break

    print("\n=== Final Pipeline Summary ===")
    final_st = mgr.get_status()
    print(f"Status: {final_st['state']}")
    print(f"Total Records: {final_st['total_records']}")
    print(f"JSONs: Ready={final_st['json_total_ready']} (New={final_st['json_generated']}, Skipped={final_st['json_skipped']})")
    print(f"PDFs:  Ready={final_st['pdf_total_ready']} (New={final_st['pdf_generated']}, Skipped={final_st['pdf_skipped']})")
    print(f"Failed: {final_st['failed_count']}")
    if final_st['failed_records']:
        for rec in final_st['failed_records']:
            print(f"  - Error: {rec}")

