#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PORT="${1:-8080}"
echo "=== Starting FORM-5 Web Dashboard Server on http://localhost:${PORT} ==="
python3 application/server.py "${PORT}"
