#!/usr/bin/env bash
set -euo pipefail
CE="$(cd "$(dirname "$0")" && pwd)"
QUADRL_ROOT="$(cd "$CE/.." && pwd)"
# shellcheck source=../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
cd "$CE/backend"
export PYTHONPATH="$CE/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Control Editor API on 0.0.0.0:8002 (DEV — no auth)"
exec "$QUADRL_UVICORN" main:app --host 0.0.0.0 --port 8002
