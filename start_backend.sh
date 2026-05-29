#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Geometry Editor API v2 on 0.0.0.0:8000 (DEV — no auth)"
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
