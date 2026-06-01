#!/usr/bin/env bash
set -euo pipefail
CE="$(cd "$(dirname "$0")" && pwd)"
cd "$CE/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi

# If you're accessing the UI from another machine, the browser must call the API
# via a training-machine reachable hostname/IP (not 127.0.0.1).
if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  HOST_FOR_CLIENT="${QUADRL_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
  HOST_FOR_CLIENT="${HOST_FOR_CLIENT:-127.0.0.1}"
  export VITE_API_BASE_URL="http://${HOST_FOR_CLIENT}:8002"
fi

echo "Starting Control Editor UI on 0.0.0.0:5175"
exec npm run dev -- --host 0.0.0.0 --port 5175 --strictPort
