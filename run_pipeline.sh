#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "=== Running FORM-5 Medical Examination Parallel Pipeline ==="
python3 application/pipeline.py --workers 8 "$@"
