#!/usr/bin/env bash
# ==============================================================================
# FORM-5 Master Launcher (Linux / macOS)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${CORE_DIR}/.." && pwd)"

# Determine Python binary (core/.venv preferred)
if [ -x "${CORE_DIR}/.venv/bin/python3" ]; then
    PYTHON_BIN="${CORE_DIR}/.venv/bin/python3"
elif [ -x "${ROOT_DIR}/.venv/bin/python3" ]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python3"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
else
    echo "Error: Python 3 not found. Please run ./core/scripts/install.sh first."
    exit 1
fi

cd "${CORE_DIR}"

if [ "$1" = "--cli" ] || [ "$1" = "-c" ] || [ "$1" = "--batch" ]; then
    shift
    echo "Starting FORM-5 Batch Generation Pipeline via CLI..."
    exec "${PYTHON_BIN}" application/pipeline.py --workers 2 "$@"
elif [ "$1" = "--status" ] || [ "$1" = "-s" ]; then
    exec "${PYTHON_BIN}" application/pipeline.py --status
elif [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: ./core/scripts/run.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  (no args)           Start the Web Dashboard server on http://localhost:8080"
    echo "  --cli, -c           Run the parallel batch PDF pipeline via CLI"
    echo "  --status, -s        Display current pipeline execution status"
    echo "  PORT                Start the Web Dashboard on a specific port (e.g. ./run.sh 9000)"
    echo "  --help, -h          Show this help message"
    exit 0
else
    PORT="${1:-8080}"
    exec "${PYTHON_BIN}" application/server.py "${PORT}"
fi
