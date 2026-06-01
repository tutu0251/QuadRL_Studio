#!/usr/bin/env bash
set -euo pipefail
GE="$(cd "$(dirname "$0")" && pwd)"
QUADRL_ROOT="$(cd "$GE/.." && pwd)"
# shellcheck source=../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
cd "$GE/backend"
export PYTHONPATH="$GE/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Geometry Editor API v2 on 0.0.0.0:8000 (DEV — no auth)"
exec "$QUADRL_UVICORN" main:app --host 0.0.0.0 --port 8000
