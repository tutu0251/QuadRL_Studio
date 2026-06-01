#!/usr/bin/env bash
set -euo pipefail
PP="$(cd "$(dirname "$0")" && pwd)"
QUADRL_ROOT="$(cd "$PP/.." && pwd)"
# shellcheck source=../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
cd "$PP/backend"
export PYTHONPATH="$PP/backend${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting PPO Planner API on 0.0.0.0:8004 (DEV — no auth)"
exec "$QUADRL_UVICORN" main:app --host 0.0.0.0 --port 8004
