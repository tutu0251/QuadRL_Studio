#!/usr/bin/env bash
# Start the Training Predictor API (Optuna + Claude parameter tuning).
# Uses a dedicated venv so the heavier deps (optuna/anthropic/tensorboard) stay isolated
# from the editor root venv.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$HERE/backend"
VENV="$BACKEND/.venv"
PORT="${TRAINING_PREDICTOR_PORT:-8007}"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -r "$BACKEND/requirements.txt"

# Load ANTHROPIC_API_KEY (and any other secrets) from repo-root .env if present.
ENV_FILE="$(cd "$HERE/.." && pwd)/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a; # shellcheck disable=SC1090
  source "$ENV_FILE"; set +a
fi

cd "$BACKEND"
export PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Training Predictor API on 0.0.0.0:$PORT (DEV — no auth)"
echo "  advisor: $([[ -n "${ANTHROPIC_API_KEY:-}" ]] && echo 'Claude ready' || echo 'disabled (set ANTHROPIC_API_KEY for Claude advice)')"
exec "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port "$PORT"
