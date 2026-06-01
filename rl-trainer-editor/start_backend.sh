#!/usr/bin/env bash
set -euo pipefail
RL="$(cd "$(dirname "$0")" && pwd)"
QUADRL_ROOT="$(cd "$RL/.." && pwd)"
# shellcheck source=../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
cd "$RL/backend"
export PYTHONPATH="$RL/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting RL Trainer Editor API on 0.0.0.0:8005 (DEV — no auth)"
exec "$QUADRL_UVICORN" main:app --host 0.0.0.0 --port 8005
