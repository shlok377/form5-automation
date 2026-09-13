#!/usr/bin/env bash
# ==============================================================================
# FORM-5 Medical Examination System - Linux / macOS Setup Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${CORE_DIR}/.." && pwd)"

cd "${CORE_DIR}"

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

# 4. Set up Python Virtual Environment (core/.venv)
echo "[3/6] Setting up Python virtual environment (core/.venv)..."
if [ ! -d "${CORE_DIR}/.venv" ]; then
    python3 -m venv "${CORE_DIR}/.venv" || {
        echo "Warning: python3 -m venv failed. Attempting to install python3-venv..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y python3-venv python3-pip
            python3 -m venv "${CORE_DIR}/.venv"
        else
            echo "Please install python3-venv and re-run this script."
            exit 1
        fi
    }
fi

# 5. Install Dependencies inside .venv
echo "[4/6] Installing required Python packages..."
"${CORE_DIR}/.venv/bin/pip" install --upgrade pip --quiet
"${CORE_DIR}/.venv/bin/pip" install -r "${CORE_DIR}/requirements.txt" --quiet
echo "Dependencies installed successfully."

# 6. Ensure required directories & permissions
echo "[5/6] Ensuring project directories and permissions..."
mkdir -p "${CORE_DIR}/data" "${CORE_DIR}/temp_json" "${ROOT_DIR}/output"
chmod +x "${CORE_DIR}/scripts/"*.sh 2>/dev/null || true
chmod +x "${CORE_DIR}/application/"*.py 2>/dev/null || true

# 7. Self-test check
echo "[6/6] Running system pre-flight verification..."
PYTHONPATH="${CORE_DIR}/application" "${CORE_DIR}/.venv/bin/python3" -c "
import aiohttp
import openpyxl
from generate_pdfs import find_chromium
from pipeline import PipelineManager
chrom = find_chromium()
if not chrom:
    print('WARNING: Chromium path not resolved by Python.')
else:
    print(f'Chromium engine verified: {chrom}')
mgr = PipelineManager(base_dir='${CORE_DIR}', root_dir='${ROOT_DIR}')
st = mgr.get_status()
print('Pipeline core initialized cleanly.')
"

echo ""
echo "---------------------------------------------------------------"
echo "  Installation Complete!"
echo "---------------------------------------------------------------"
echo ""
echo "  HOW TO LAUNCH:"
echo ""
echo "  Linux / macOS:"
echo "     ./core/scripts/run.sh"
echo ""
echo "  Windows (Client):"
echo "     Double-click \"2_START.bat\" in the project folder."
echo "---------------------------------------------------------------"
echo ""
