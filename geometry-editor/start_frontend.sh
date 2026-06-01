#!/usr/bin/env bash
set -euo pipefail
GE="$(cd "$(dirname "$0")" && pwd)"
cd "$GE/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp .env.example .env
  echo "Created geometry-editor/frontend/.env — set VITE_API_BASE_URL to your Ubuntu IP for LAN access."
fi
echo "Starting Geometry Editor UI v2 on 0.0.0.0:5173"

if [[ -z "${VITE_API_BASE_URL:-}" ]]; then
  HOST_FOR_CLIENT="${QUADRL_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
  HOST_FOR_CLIENT="${HOST_FOR_CLIENT:-127.0.0.1}"
  export VITE_API_BASE_URL="http://${HOST_FOR_CLIENT}:8000"
fi

exec npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
