#!/usr/bin/env bash
set -euo pipefail
SE="$(cd "$(dirname "$0")" && pwd)"
QUADRL_ROOT="$(cd "$SE/.." && pwd)"
# shellcheck source=../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
cd "$SE/backend"
export PYTHONPATH="$SE/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Sensor Editor API on 0.0.0.0:8003 (DEV — no auth)"
exec "$QUADRL_UVICORN" main:app --host 0.0.0.0 --port 8003
