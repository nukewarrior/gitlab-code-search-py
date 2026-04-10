#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x ".venv/bin/python" ]]; then
  echo "ERROR: .venv/bin/python not found. Please create .venv first."
  exit 1
fi

PYINSTALLER_CONFIG_DIR=.pyinstaller .venv/bin/pyinstaller \
  --clean \
  --onefile \
  --name gcs \
  gcs_main.py

echo
echo "Build done: dist/gcs"
