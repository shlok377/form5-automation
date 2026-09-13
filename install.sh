#!/usr/bin/env bash
# ==============================================================================
# FORM-5 Medical Examination System - Client Automated Setup Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo ""
echo "================================================================="
echo "   FORM-5 Medical Examination Automation System - Setup"
echo "   Gujarat Factories Rules Statutory Health Reporting"
echo "================================================================="
echo ""

# 1. Detect Operating System & Package Manager
OS_TYPE="$(uname -s)"
echo "[1/6] Detecting environment: ${OS_TYPE}..."

# 2. Check Python 3 (version >= 3.8)
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3 (3.8+) using your system package manager."
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python ${PY_VER}"

# 3. Check / Install Chromium
echo "[2/6] Checking for Chromium or Google Chrome..."
CHROMIUM_FOUND=false
for candidate in chromium chromium-browser google-chrome google-chrome-stable /usr/bin/chromium; do
    if command -v "${candidate}" &> /dev/null || [ -x "${candidate}" ]; then
        echo "Found browser engine: $(command -v "${candidate}" 2>/dev/null || echo "${candidate}")"
        CHROMIUM_FOUND=true
        break
    fi
done

if [ "${CHROMIUM_FOUND}" = false ]; then
    echo "WARNING: Chromium / Google Chrome is not installed."
    echo "Attempting to install Chromium..."
    if command -v apt-get &> /dev/null; then
        echo "Running: sudo apt-get update && sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium"
        sudo apt-get update && (sudo apt-get install -y chromium-browser || sudo apt-get install -y chromium)
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y chromium
    elif command -v yum &> /dev/null; then
        sudo yum install -y chromium
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm chromium
    elif command -v brew &> /dev/null; then
        brew install chromium
    else
        echo "Could not auto-install Chromium. Please install chromium or google-chrome manually."
        exit 1
    fi
fi

# 4. Set up Python Virtual Environment (.venv)
echo "[3/6] Setting up Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv || {
        echo "Warning: python3 -m venv failed. Attempting to install python3-venv..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y python3-venv python3-pip
            python3 -m venv .venv
        else
            echo "Please install python3-venv and re-run this script."
            exit 1
        fi
    }
fi

# 5. Install Dependencies inside .venv
echo "[4/6] Installing required Python packages..."
"${SCRIPT_DIR}/.venv/bin/pip" install --upgrade pip --quiet
"${SCRIPT_DIR}/.venv/bin/pip" install -r requirements.txt --quiet
echo "Dependencies installed successfully."

# 6. Ensure required directories & permissions
echo "[5/6] Ensuring project directories and permissions..."
mkdir -p data temp_json output
chmod +x install.sh run.sh run_pipeline.sh start_dashboard.sh 2>/dev/null || true
chmod +x application/*.py 2>/dev/null || true

# 7. Self-test check
echo "[6/6] Running system pre-flight verification..."
"${SCRIPT_DIR}/.venv/bin/python3" -c "
import aiohttp
from application.generate_pdfs import find_chromium
from application.pipeline import PipelineManager
chrom = find_chromium()
if not chrom:
    print('WARNING: Chromium path not resolved by Python.')
else:
    print(f'Chromium engine verified: {chrom}')
mgr = PipelineManager()
st = mgr.get_status()
print('Pipeline core initialized cleanly.')
"

echo ""
echo "================================================================="
echo "   Installation Completed Successfully!"
echo "================================================================="
echo ""
echo "How to run the system:"
echo ""
echo "  1. Launch the Web Dashboard (Recommended):"
echo "     ./run.sh"
echo "     (or ./start_dashboard.sh 8080)"
echo "     Then open http://localhost:8080 in your browser."
echo ""
echo "  2. Run Batch Generation via Terminal (CLI):"
echo "     ./run.sh --cli"
echo "     (or ./run_pipeline.sh)"
echo ""
echo "  3. Check Pipeline Status:"
echo "     ./run.sh --status"
echo ""
echo "================================================================="
