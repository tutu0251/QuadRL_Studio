#!/usr/bin/env bash
set -euo pipefail
CE="$(cd "$(dirname "$0")" && pwd)"
cd "$CE/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
exec npm run dev
