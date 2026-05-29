#!/usr/bin/env bash
set -euo pipefail
PE="$(cd "$(dirname "$0")" && pwd)"
cd "$PE/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
export PYTHONPATH="$PE/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Physics Editor API on 0.0.0.0:8001 (DEV — no auth)"
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001
