# FORM-5 Medical Examination Automation System
### Statutory Health Reporting under Gujarat Factories Rules (Form No. 5, Rule 68-T & 102)

---

## 🚀 Quick Start for Clients (Windows)

Zero configuration or prior programming setup required. Everything runs out-of-the-box.

1. **Step 1: Run Setup**
   - Double-click **`1_SETUP.bat`**.
   - Automatically configures the isolated environment, dependencies, and places a **FORM-5 Medical Automation** shortcut on your Desktop.

2. **Step 2: Launch Dashboard**
   - Double-click **`2_START.bat`** (or use your Desktop shortcut).
   - The Web Dashboard opens automatically in your browser at **http://localhost:8080**.

3. **Step 3: Generate PDFs**
   - Drag and drop your `.xlsx` or `.csv` spreadsheet onto the dashboard.
   - Click **Start Pipeline**.
   - When finished, click **Download All (.ZIP)** or find your completed PDFs ready in the **`output/`** folder.

---

## 🖥️ Usage Options

### Option A: Interactive Web Dashboard (Recommended)
- **Windows**: Double-click `2_START.bat`
- **Linux / macOS**: `./core/scripts/run.sh`

**Dashboard Capabilities:**
- **Drag & Drop Excel (.xlsx) & CSV Upload**: Automatic in-memory conversion with instant validation.
- **Two-Agent Live Monitoring**: Real-time progress donuts and status counters via Server-Sent Events (SSE).
- **Interactive Records Browser**: Search employee records, open instant HTML previews, and download individual PDFs.
- **Batch ZIP Export**: Download all generated PDFs in one package via **"Download All (.ZIP)"**.
- **Minimalist Completion Modal**: Notifies you when 100% of PDFs are verified and ready.

### Option B: Headless CLI Batch Generation
- **Windows**: `2_START.bat --cli`
- **Linux / macOS**: `./core/scripts/run.sh --cli`

*To force regeneration of all records:*
- **Windows**: `2_START.bat --cli --force`
- **Linux / macOS**: `./core/scripts/run.sh --cli --force`

### Option C: Queue Status Check
- **Windows**: `2_START.bat --status`
- **Linux / macOS**: `./core/scripts/run.sh --status`

---

## 📂 Project Organization

Clean **"Single Door"** architecture separating user controls from internal machinery:

```text
form5-automation/
├── 📄 1_SETUP.bat              # Step 1: One-click setup & Desktop shortcut creation
├── 📄 2_START.bat              # Step 2: Double-click launcher (starts Web Dashboard)
├── 📂 output/                  # Final 4-page print-ready employee PDFs saved here
├── 📄 README.md                # System documentation
│
└── 📂 core/                    # Engine internals (isolated from accidental edits)
    ├── application/            # Server, pipeline orchestrator, PDF & JSON agents, UI
    ├── config/                 # mapping_config.json (Column mapping schema)
    ├── data/                   # Internal working storage
    ├── temp_json/              # Intermediate clinical JSON records
    ├── scripts/                # Linux / macOS setup and launcher scripts
    ├── docs_local/             # Form reference scans
    └── requirements.txt        # Python dependency list
```

---

## 🔒 Confidentiality & Security
- All processing executes **100% locally** on the host machine.
- No employee medical data or identifiable health information leaves the local computer or connects to external cloud servers.
