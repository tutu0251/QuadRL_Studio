#!/usr/bin/env bash
# Create or refresh the repo-root .venv and export interpreter paths.
# Source from other scripts: source "$(dirname "$0")/../scripts/ensure_venv.sh"
# Or: QUADRL_ROOT=/path/to/QuadRL_Studio source scripts/ensure_venv.sh
set -euo pipefail

_ensure_venv_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUADRL_ROOT="${QUADRL_ROOT:-$(cd "$_ensure_venv_dir/.." && pwd)}"
VENV="$QUADRL_ROOT/.venv"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi

REQ="$QUADRL_ROOT/requirements.txt"
if [[ "${QUADRL_DEV:-}" == "1" ]] && [[ -f "$QUADRL_ROOT/requirements-dev.txt" ]]; then
  "$VENV/bin/pip" install -q -r "$REQ" -r "$QUADRL_ROOT/requirements-dev.txt"
else
  "$VENV/bin/pip" install -q -r "$REQ"
fi

export QUADRL_ROOT
export QUADRL_PYTHON="$VENV/bin/python"
export QUADRL_UVICORN="$VENV/bin/uvicorn"
export QUADRL_PIP="$VENV/bin/pip"
