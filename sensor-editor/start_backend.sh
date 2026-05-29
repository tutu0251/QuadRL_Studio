#!/usr/bin/env bash
set -euo pipefail
SE="$(cd "$(dirname "$0")" && pwd)"
cd "$SE/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
export PYTHONPATH="$SE/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Sensor Editor API on 0.0.0.0:8003 (DEV — no auth)"
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8003
