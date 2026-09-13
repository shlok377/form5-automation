
## 🚀 Quick Start (1-Minute Setup)

### Windows (Zero Prerequisites Required)
1. **Double-click `install.bat`**
   - Automatically detects or installs Python 3.11 (via `winget` or direct silent download from python.org).
   - Uses pre-installed **Microsoft Edge** or **Google Chrome** natively.
   - Sets up the `.venv` virtual environment and installs required dependencies.
2. **Double-click `run.bat`**
   - Automatically starts the server on `http://localhost:8080` and opens your default browser.

### Linux / macOS
1. **Run `./install.sh`**
   - Detects system package manager, verifies Chromium/Chrome, and configures `.venv`.
2. **Run `./run.sh`**
   - Launches the dashboard on `http://localhost:8080`.

---

## 🖥️ How to Run the System

### Option A: Interactive Web Dashboard (Recommended)
- **Windows**: Double-click `run.bat`
- **Linux/macOS**: `./run.sh`

Open **http://localhost:8080** in any browser.

**Features in Web Dashboard**:
- **Drag & Drop Excel (.xlsx) & CSV Upload**: Automatic in-memory conversion of Excel spreadsheets into clean, normalized CSVs with instant pre-flight validation.
- **One-Click Run on Existing Data**: Process `data/data.csv` (or `data/data.xlsx`) instantly.
- **Two-Agent Live Monitoring**: Real-time pastel donut charts and status indicators via Server-Sent Events (SSE).
- **Live Logs Drawer**: Inspect real-time worker logs directly from the browser.
- **Interactive Records Browser**: Search employee records, open instant HTML previews, and download individual PDFs.
- **Batch ZIP Export**: Download all generated PDFs in one click via **"Download All (.ZIP)"**.

### Option B: High-Speed CLI Batch Generation
- **Windows**: `run.bat --cli`
- **Linux/macOS**: `./run.sh --cli`

*Tip: To force re-generation of all records from scratch:*
- **Windows**: `run.bat --cli --force`
- **Linux/macOS**: `./run.sh --cli --force`

### Option C: Check Current Pipeline Status
- **Windows**: `run.bat --status`
- **Linux/macOS**: `./run.sh --status`

---

## 📂 Project Structure

```text
├── install.sh                  # Automated system installer & dependency manager
├── run.sh                      # Master executable launcher (Web Dashboard or CLI)
├── run_pipeline.sh             # Shortcut to launch parallel batch pipeline
├── start_dashboard.sh          # Shortcut to launch web dashboard server
├── requirements.txt            # Python dependencies (aiohttp)
├── mapping_config.json         # Master CSV-to-form column mapping schema
├── .gitignore                  # Strict security filter preventing medical data leaks
│
├── application/
│   ├── generate_json.py        # Agent 1: Data extraction & Section F clinical evaluation
│   ├── generate_pdfs.py        # Agent 2: Headless Chromium 4-page PDF renderer
│   ├── pipeline.py             # Resilient parallel producer-consumer queue orchestrator
│   ├── validator.py            # Pre-flight CSV validator and structure checker
│   ├── server.py               # Asynchronous REST & Server-Sent Events (SSE) server
│   ├── form_template.html      # 4-page statutory FORM-5 print template
│   ├── mapping_ui.html         # Visual interactive mapping calibration tool
│   ├── logo.png                # Edge-to-edge header banner logo
│   └── static/
│       └── index.html          # Web Dashboard UI
│
├── data/
│   └── data.csv                # Active input employee health examination dataset
├── temp_json/                  # Intermediate structured JSON records
└── output/                     # Final 4-page print-ready employee PDFs
```

---
