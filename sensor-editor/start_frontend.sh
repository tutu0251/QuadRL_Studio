#!/usr/bin/env bash
set -euo pipefail
SE="$(cd "$(dirname "$0")" && pwd)"
cd "$SE/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
exec npm run dev
