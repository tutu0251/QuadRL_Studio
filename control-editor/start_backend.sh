#!/usr/bin/env bash
set -euo pipefail
CE="$(cd "$(dirname "$0")" && pwd)"
cd "$CE/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
export PYTHONPATH="$CE/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Control Editor API on 0.0.0.0:8002 (DEV — no auth)"
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8002
