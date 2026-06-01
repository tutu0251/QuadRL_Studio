#!/usr/bin/env bash
set -euo pipefail
PE="$(cd "$(dirname "$0")" && pwd)"
QUADRL_ROOT="$(cd "$PE/.." && pwd)"
# shellcheck source=../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
cd "$PE/backend"
export PYTHONPATH="$PE/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Physics Editor API on 0.0.0.0:8001 (DEV — no auth)"
exec "$QUADRL_UVICORN" main:app --host 0.0.0.0 --port 8001
