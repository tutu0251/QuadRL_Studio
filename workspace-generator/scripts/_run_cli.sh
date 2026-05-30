#!/usr/bin/env bash
# Bootstrap venv and run workspace-generator CLI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
VENV="$BACKEND/.venv"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r "$ROOT/requirements.txt"
fi

export PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV/bin/python" "$BACKEND/cli.py" "$@"
