#!/usr/bin/env bash
set -euo pipefail
PE="$(cd "$(dirname "$0")" && pwd)"
cd "$PE/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
echo "Starting Physics Editor UI on 0.0.0.0:5174"
exec npm run dev -- --host 0.0.0.0 --port 5174
