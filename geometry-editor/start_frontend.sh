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
exec npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
