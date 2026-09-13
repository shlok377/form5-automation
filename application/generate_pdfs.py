#!/usr/bin/env python3
"""
FORM-5 Batch PDF Generator
Reads structured employee JSON files from temp_json/ and renders them into
the FORM-5 HTML template (application/form_template.html), then generates
individual 4-page print-ready PDFs into output/ using headless Chromium.

Naming convention: <employee_name>.pdf (default) or 0001_<employee_name>_<empcode>.pdf (--full-name)
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

def sanitize_filename(name):
    name = re.sub(r'[^\w\s-]', '', str(name)).strip()
    return re.sub(r'[-\s]+', '_', name)

def find_chromium():
    # 1. Search PATH
    for candidate in [
        "chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
        "chrome", "chrome.exe", "msedge", "msedge.exe"
    ]:
        path = shutil.which(candidate)
        if path:
            return path

    # 2. Windows specific standard locations
    if sys.platform == "win32":
        win_candidates = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for c in win_candidates:
            if os.path.exists(c):
                return c

    # 3. macOS specific standard locations
    if sys.platform == "darwin":
        mac_candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        ]
        for c in mac_candidates:
            if os.path.exists(c):
                return c

    # 4. Linux specific standard locations
    linux_candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium"
    ]
    for c in linux_candidates:
        if os.path.exists(c):
            return c

    return None

def build_filled_html(template_str, emp_data):
    """
    Injects employee data into form_template.html and ensures all data-key
    attributes are populated cleanly on document load.
    """
    script = f"""
    <script>
      (function() {{
        const empData = {json.dumps(emp_data, ensure_ascii=False)};
        
        function getVal(obj, path) {{
          return path.split('.').reduce((prev, curr) => prev ? prev[curr] : undefined, obj);
        }}
        
        document.querySelectorAll("[data-key]").forEach(cell => {{
          const key = cell.getAttribute("data-key");
          const val = getVal(empData, key);
          if (val !== undefined && val !== null && val !== "") {{
            cell.textContent = val;
          }} else {{
            if (key === "demographics.esi_scheme" || key === "demographics.other_scheme") {{
              cell.textContent = "Yes / No";
            }} else if (key === "medical_fitness_test.item1_report" || key === "medical_fitness_test.item2_report") {{
              cell.textContent = "As Per Attached Reports";
            }} else if (key === "physical.exam_date" || key === "signature_date") {{
              cell.innerHTML = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;";
            }}
          }}
        }});
        
        const toolbar = document.querySelector(".preview-toolbar");
        if (toolbar) toolbar.style.display = "none";
      }})();
    </script>
    """
    return template_str.replace("</body>", script + "</body>")

def convert_json_to_pdf(json_path, template_str, output_dir, chromium_path, use_full_name=False):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    idx_str = data.get("employee_index", "0000")
    name = data.get("employee_name", f"Employee_{idx_str}")
    code = data.get("employee_code", "")

    if use_full_name:
        out_name = f"{idx_str}_{sanitize_filename(name)}_{sanitize_filename(code)}.pdf"
    else:
        out_name = f"{sanitize_filename(name)}.pdf"

    out_pdf_path = os.path.join(output_dir, out_name)
    filled_html = build_filled_html(template_str, data)

    # Write temporary HTML and render via headless Chromium
    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as tmp:
        tmp.write(filled_html)
        tmp_html_path = tmp.name

    try:
        cmd = [
            chromium_path,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-pdf-header-footer",
            f"--print-to-pdf={out_pdf_path}",
            tmp_html_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return out_pdf_path, None
    except subprocess.CalledProcessError as e:
        return None, f"Error rendering {json_path}: {e.stderr.decode('utf-8', errors='ignore')}"
    finally:
        if os.path.exists(tmp_html_path):
            os.remove(tmp_html_path)

def main():
    parser = argparse.ArgumentParser(description="Generate FORM-5 PDFs from temp_json/ employee data.")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent workers (default: 4)")
    parser.add_argument("--full-name", action="store_true", help="Name files as 0001_name_code.pdf instead of name.pdf")
    parser.add_argument("--single", type=str, default=None, help="Process a specific JSON filename or employee index")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_dir = os.path.join(base_dir, "temp_json")
    output_dir = os.path.join(base_dir, "output")
    template_path = os.path.join(base_dir, "application", "form_template.html")

    chromium_path = find_chromium()
    if not chromium_path:
        print("Error: Chromium browser executable not found. Please install chromium.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    os.makedirs(output_dir, exist_ok=True)

    json_files = sorted([
        os.path.join(json_dir, f) for f in os.listdir(json_dir) 
        if f.endswith(".json") and f[0].isdigit()
    ])
    if not json_files:
        print(f"No JSON files found in {json_dir}. Run generate_json.py first.", file=sys.stderr)
        sys.exit(1)

    if args.single:
        json_files = [f for f in json_files if args.single in os.path.basename(f)]
        if not json_files:
            print(f"No matching file found for filter: {args.single}", file=sys.stderr)
            sys.exit(1)

    print(f"Found {len(json_files)} employee records to generate into {output_dir}")
    print(f"Using Chromium: {chromium_path} with {args.workers} workers.")

    success_count = 0
    errors = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_file = {
            executor.submit(convert_json_to_pdf, jf, template_str, output_dir, chromium_path, args.full_name): jf
            for jf in json_files
        }
        for i, future in enumerate(concurrent.futures.as_completed(future_to_file), start=1):
            jf = future_to_file[future]
            try:
                pdf_path, err = future.result()
                if err:
                    errors.append((jf, err))
                else:
                    success_count += 1
            except Exception as e:
                errors.append((jf, str(e)))

            if i % 25 == 0 or i == len(json_files):
                print(f"Progress: {i}/{len(json_files)} PDFs generated...")

    print("\n--- Summary ---")
    print(f"Successfully generated: {success_count}/{len(json_files)} PDFs in {output_dir}")
    if errors:
        print(f"Encountered {len(errors)} errors:")
        for jf, err in errors[:5]:
            print(f"  {os.path.basename(jf)}: {err}")
    else:
        print("All PDFs successfully created with 0 errors!")

if __name__ == "__main__":
    main()
