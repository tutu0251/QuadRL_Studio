#!/usr/bin/env bash
# Bootstrap venv and run workspace-generator CLI.
set -euo pipefail

WG="$(cd "$(dirname "$0")/.." && pwd)"
QUADRL_ROOT="$(cd "$WG/.." && pwd)"
BACKEND="$WG/backend"
# shellcheck source=../../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"

export PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
exec "$QUADRL_PYTHON" "$BACKEND/cli.py" "$@"
