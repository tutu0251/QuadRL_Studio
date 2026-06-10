#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi

# Point the UI at the Training Predictor API (start_backend.sh defaults to port 8007).
if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  BACKEND_PORT="${TRAINING_PREDICTOR_PORT:-8007}"
  HOST_FOR_CLIENT="${QUADRL_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
  HOST_FOR_CLIENT="${HOST_FOR_CLIENT:-127.0.0.1}"
  export VITE_API_BASE_URL="http://${HOST_FOR_CLIENT}:${BACKEND_PORT}"
fi

echo "Starting Training Predictor UI on 0.0.0.0:5180 (API: ${VITE_API_BASE_URL})"
exec npm run dev -- --host 0.0.0.0 --port 5180 --strictPort
