# FORM-5 Statutory Medical Examination Automation System
### Annual Health Record Automation — Under Gujarat Factories Rules (Rule 68-T & 68-U, Form No. 5)

An enterprise-grade, high-throughput system that transforms health examination CSV records into statutory 4-page print-ready FORM-5 medical documents with automated clinical pathology evaluations, 100% full-width header banner logos, and zero layout overflow.

---

## 🚀 Quick Start (1-Minute Setup)

### 1. Install Everything with One Script
On the target machine (Ubuntu, Debian, Fedora, Arch, or macOS), run:
```bash
./install.sh
```
This automated script will:
- Check for Python 3.8+ and package managers.
- Check and automatically install Chromium browser if missing.
- Create an isolated Python virtual environment (`.venv`).
- Install all required dependencies (`aiohttp`).
- Set permissions and verify system health.

---

## 🖥️ How to Run the System

### Option A: Interactive Web Dashboard (Recommended)
```bash
./run.sh
```
Open **http://localhost:8080** in any browser.

**Features in Web Dashboard**:
- **Drag & Drop CSV Upload**: Immediate pre-flight validation of column count, headers, and mapping indices.
- **One-Click Run on Existing Data**: Process `data/data.csv` instantly.
- **Two-Agent Live Monitoring**: Real-time pastel donut charts and status indicators via Server-Sent Events (SSE).
- **Live Logs Drawer**: Inspect real-time worker logs directly from the browser.
- **Interactive Records Browser**: Search employee records, open instant HTML previews, and download individual PDFs.
- **Batch ZIP Export**: Download all generated PDFs in one click via **"Download All (.ZIP)"**.

### Option B: High-Speed CLI Batch Generation
To generate PDFs for all employees directly from the terminal:
```bash
./run.sh --cli
```
*Tip: To force re-generation of all records from scratch:*
```bash
./run.sh --cli --force
```

### Option C: Check Current Pipeline Status
```bash
./run.sh --status
```

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

## 🔒 Confidentiality & Publishing to GitHub

### Should you publish this project to GitHub?
**YES, but it MUST be a PRIVATE repository.**

Publishing to a private GitHub repository is the cleanest and most professional way to deliver software to your client. It provides:
1. **One-command installation**: The client simply runs `git clone <repo_url>` followed by `./install.sh`.
2. **Easy updates**: Whenever changes or adjustments are made, the client runs `git pull` without breaking local data.
3. **Issue tracking**: Both teams can track change requests and mapping adjustments.

### ⚠️ Critical Medical Privacy Warning:
Employee medical records, pathology results, names, and contact details are sensitive Personal Health Information (PHI).
- **Never publish to a PUBLIC repository.**
- The included `.gitignore` is pre-configured to **strictly exclude**:
  - `data/*.csv`, `data/*.xlsx`
  - `temp_json/*.json`
  - `output/*.pdf`, `output/*.zip`
  - `temp.pdf`, `temp2.pdf`
- Only code, templates, and scripts will be committed to git.

### Step-by-Step: Pushing to a Private GitHub Repo
```bash
# 1. Initialize git (if not already done)
git init

# 2. Add files (protected by .gitignore)
git add .

# 3. Commit the clean codebase
git commit -m "Initial commit: FORM-5 Statutory Medical Examination Automation System"

# 4. Create a PRIVATE repo on GitHub and link it:
git remote add origin git@github.com:YOUR_ORGANIZATION/form5-automation.git
git branch -M main
git push -u origin main
```

On your client's machine:
```bash
git clone git@github.com:YOUR_ORGANIZATION/form5-automation.git
cd form5-automation
./install.sh
./run.sh
```

---

## 🛠️ Statutory Compliance & Layout Standards

- **Gujarat Factories Rules 1963**: Form No. 5 under Rule 68-T and Rule 68-U.
- **Strict 4-Page Guarantee**: Form sections are isolated using CSS paged media page breaks (`@page { margin: 0; }`).
- **Section F Clinical Reasoning**:
  - Total WBC and 5-part Differential counts formatted as `WBC=/↑/↓ (N / L / M / E / B)`.
  - Urine routine examination indicators: `P= S= B= PC= RBC= EC= C= B=`.
  - Reference ranges printed directly in the Parameter column.
- **Section J Statutory Rules**:
  - Separate report notices for Item 1 and Item 2 (`As Per Attached Reports`).
  - Section J(f) Vertigo/Dizziness table left blank for safety officer completion.
