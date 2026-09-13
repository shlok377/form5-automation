#!/usr/bin/env python3
"""
FORM-5 Web Server
Provides REST API and Server-Sent Events (SSE) for the Web UI Dashboard.
Manages:
- CSV file uploads & pre-flight verification
- CSV confirmation & backup
- Parallel pipeline execution (Agent 1 & Agent 2)
- Real-time progress and logging stream
- Live HTML preview & PDF download
"""

import asyncio
import json
import os
import shutil
import sys
import zipfile
from aiohttp import web

# Import validator and pipeline manager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validator import validate_csv_content, validate_csv_file
from pipeline import PipelineManager, build_filled_html
from excel_adapter import convert_xlsx_to_csv, is_excel_file

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_DIR = os.path.dirname(APP_DIR)
ROOT_DIR = os.path.dirname(CORE_DIR)

STATIC_DIR = os.path.join(APP_DIR, "static")
DATA_DIR = os.path.join(CORE_DIR, "data")
TEMP_JSON_DIR = os.path.join(CORE_DIR, "temp_json")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")

# Safe mapping config resolution
MAPPING_CONFIG = os.path.join(CORE_DIR, "config", "mapping_config.json")
if not os.path.exists(MAPPING_CONFIG):
    for candidate in [
        os.path.join(CORE_DIR, "mapping_config.json"),
        os.path.join(APP_DIR, "mapping_config.json"),
        os.path.join(ROOT_DIR, "mapping_config.json")
    ]:
        if os.path.exists(candidate):
            MAPPING_CONFIG = candidate
            break

TEMPLATE_PATH = os.path.join(APP_DIR, "form_template.html")
TEMP_UPLOAD_PATH = os.path.join(DATA_DIR, ".uploaded_pending.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_JSON_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

pipeline_manager = PipelineManager(base_dir=CORE_DIR, root_dir=ROOT_DIR)

async def handle_index(request):
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return web.Response(text="Dashboard UI not found. Please build static/index.html", content_type="text/plain")
    return web.FileResponse(index_path)

async def handle_preflight_upload(request):
    """
    Receives an uploaded CSV, runs validator against mapping_config.json,
    stores temporarily at data/.uploaded_pending.csv, and returns the report.
    """
    reader = await request.multipart()
    field = await reader.next()
    if not field or field.name != "file":
        return web.json_response({"valid": False, "errors": ["No file uploaded with key 'file'."]}, status=400)

    filename = field.filename or "uploaded.csv"
    is_xlsx = is_excel_file(filename)
    is_csv = filename.lower().endswith(".csv")
    if not (is_csv or is_xlsx):
        return web.json_response({"valid": False, "errors": ["Uploaded file must be a .csv or .xlsx file."]}, status=400)

    content_bytes = bytearray()
    while True:
        chunk = await field.read_chunk()
        if not chunk:
            break
        content_bytes.extend(chunk)

    if is_xlsx:
        try:
            csv_text = convert_xlsx_to_csv(bytes(content_bytes))
        except Exception as e:
            return web.json_response({
                "valid": False,
                "errors": [f"Failed to convert Excel (.xlsx) file to CSV: {str(e)}"]
            }, status=400)
    else:
        csv_text = content_bytes.decode("utf-8-sig", errors="replace")

    # Save to pending temp file (as canonical CSV)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TEMP_UPLOAD_PATH, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_text)

    # Validate normalized CSV
    report = validate_csv_content(csv_text, MAPPING_CONFIG)
    report["filename"] = filename
    report["file_size"] = len(content_bytes)
    report["converted_from_xlsx"] = is_xlsx
    
    existing_pdfs = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".pdf") and not f.startswith(".")] if os.path.exists(OUTPUT_DIR) else []
    report["existing_pdf_count"] = len(existing_pdfs)
    return web.json_response(report)

async def handle_confirm_csv(request):
    """
    Commits data/.uploaded_pending.csv to data/data.csv, creating a backup of data.csv if it exists.
    """
    if not os.path.exists(TEMP_UPLOAD_PATH):
        return web.json_response({"success": False, "error": "No pending uploaded CSV found to confirm."}, status=400)

    target_csv = os.path.join(DATA_DIR, "data.csv")
    if os.path.exists(target_csv):
        backup_csv = os.path.join(DATA_DIR, "data.csv.bak")
        shutil.copy2(target_csv, backup_csv)

    shutil.move(TEMP_UPLOAD_PATH, target_csv)
    pipeline_manager.log("New data.csv confirmed and saved successfully.")
    
    return web.json_response({
        "success": True,
        "message": "CSV confirmed and saved to data/data.csv."
    })

async def handle_pipeline_start(request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    force = bool(data.get("force", False))
    workers = int(data.get("workers", 2))
    workers = max(1, min(3, workers))

    success, msg = pipeline_manager.start(force=force, num_workers=workers)
    return web.json_response({"success": success, "message": msg})

async def handle_pipeline_stop(request):
    success, msg = pipeline_manager.stop()
    return web.json_response({"success": success, "message": msg})

async def handle_pipeline_status(request):
    return web.json_response(pipeline_manager.get_status())

async def handle_records_list(request):
    records = pipeline_manager.get_records_overview()
    return web.json_response({
        "total": len(records),
        "records": records
    })

async def handle_preview_html(request):
    json_filename = request.match_info.get("filename", "")
    json_path = os.path.join(TEMP_JSON_DIR, json_filename)
    if not os.path.exists(json_path):
        return web.Response(text="Employee JSON file not found.", status=404)

    with open(json_path, "r", encoding="utf-8") as f:
        emp_data = json.load(f)

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_str = f.read()

    filled_html = build_filled_html(template_str, emp_data)
    return web.Response(text=filled_html, content_type="text/html")

async def handle_download_pdf(request):
    pdf_filename = request.match_info.get("filename", "")
    pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        return web.Response(text="PDF not found.", status=404)

    return web.FileResponse(pdf_path, headers={
        "Content-Disposition": f'inline; filename="{pdf_filename}"'
    })

async def handle_download_all_zip(request):
    """Packages all generated output/*.pdf files into a ZIP archive and streams it."""
    if not os.path.exists(OUTPUT_DIR):
        return web.Response(text="Output directory not found.", status=404)

    pdf_files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".pdf") and not f.startswith(".")])
    if not pdf_files:
        return web.Response(text="No generated PDFs found to download.", status=404)

    zip_path = os.path.join(OUTPUT_DIR, ".all_reports_bundle.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf_name in pdf_files:
            p_path = os.path.join(OUTPUT_DIR, pdf_name)
            zf.write(p_path, arcname=pdf_name)

    return web.FileResponse(zip_path, headers={
        "Content-Disposition": 'attachment; filename="FORM-5_Batch_Reports.zip"'
    })

async def handle_sse_events(request):
    """Server-Sent Events streaming endpoint for live progress and logs."""
    response = web.StreamResponse(
        status=200,
        reason='OK',
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )
    await response.prepare(request)

    event_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def listener(event):
        try:
            loop.call_soon_threadsafe(event_queue.put_nowait, event)
        except Exception:
            pass

    pipeline_manager.add_listener(listener)

    try:
        # Push initial status
        init_status = pipeline_manager.get_status()
        await response.write(f"data: {json.dumps({'type': 'init', 'data': init_status})}\n\n".encode('utf-8'))

        while True:
            event = await event_queue.get()
            payload = f"data: {json.dumps(event)}\n\n"
            await response.write(payload.encode('utf-8'))
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        pipeline_manager.remove_listener(listener)

async def handle_workspace_reset(request):
    """
    Purges current batch outputs and resets pipeline to clean state.
    Guaranteed never to touch configuration files or .gitkeep.
    """
    success = pipeline_manager.reset()
    if os.path.exists(TEMP_UPLOAD_PATH):
        try:
            os.remove(TEMP_UPLOAD_PATH)
        except Exception:
            pass
    return web.json_response({
        "success": success,
        "message": "Workspace reset successfully."
    })

def create_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/upload-preflight", handle_preflight_upload)
    app.router.add_post("/api/confirm-csv", handle_confirm_csv)
    app.router.add_post("/api/pipeline/start", handle_pipeline_start)
    app.router.add_post("/api/pipeline/stop", handle_pipeline_stop)
    app.router.add_get("/api/pipeline/status", handle_pipeline_status)
    app.router.add_get("/api/pipeline/events", handle_sse_events)
    app.router.add_get("/api/records", handle_records_list)
    app.router.add_get("/api/preview/{filename}", handle_preview_html)
    app.router.add_get("/api/pdf/{filename}", handle_download_pdf)
    app.router.add_get("/api/download-all", handle_download_all_zip)
    app.router.add_post("/api/workspace/reset", handle_workspace_reset)
    app.router.add_static("/static", STATIC_DIR)
    return app

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    
    url = f"http://localhost:{port}"
    print("\n" + "─" * 63)
    print("  FORM-5 Dashboard is Live & Ready")
    print("─" * 63)
    print("")
    print("  ➜ Hold Ctrl and click to open in browser:")
    print(f"    {url}")
    print("")
    print("  (Press Ctrl+C in this terminal to stop the server)")
    print("─" * 63 + "\n")

    app = create_app()
    web.run_app(app, host="127.0.0.1", port=port, print=None)

