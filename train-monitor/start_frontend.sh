#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
echo "Starting Train Monitor UI on 0.0.0.0:5179"

# Train Monitor defaults to window.location.hostname:8006, but allow override for
# non-standard networking setups.
if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  HOST_FOR_CLIENT="${QUADRL_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
  HOST_FOR_CLIENT="${HOST_FOR_CLIENT:-127.0.0.1}"
  export VITE_API_BASE_URL="http://${HOST_FOR_CLIENT}:8006"
fi

exec npm run dev -- --host 0.0.0.0 --port 5179 --strictPort
