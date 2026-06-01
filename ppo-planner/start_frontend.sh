#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi

if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  HOST_FOR_CLIENT="${QUADRL_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
  HOST_FOR_CLIENT="${HOST_FOR_CLIENT:-127.0.0.1}"
  export VITE_API_BASE_URL="http://${HOST_FOR_CLIENT}:8004"
fi

echo "Starting PPO Planner UI on 0.0.0.0:5177"
exec npm run dev -- --host 0.0.0.0 --port 5177 --strictPort
