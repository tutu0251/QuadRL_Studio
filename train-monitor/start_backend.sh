#!/usr/bin/env bash
set -euo pipefail
TM="$(cd "$(dirname "$0")" && pwd)"
QUADRL_ROOT="$(cd "$TM/.." && pwd)"
# shellcheck source=../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
cd "$TM/backend"
export PYTHONPATH="$TM/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Train Monitor API on 0.0.0.0:8006 (DEV — no auth)"
exec "$QUADRL_UVICORN" main:app --host 0.0.0.0 --port 8006
