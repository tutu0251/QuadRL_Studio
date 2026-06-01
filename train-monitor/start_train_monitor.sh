#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
"$ROOT/start_backend.sh" &
BACK_PID=$!
trap 'kill $BACK_PID 2>/dev/null' EXIT
sleep 1
"$ROOT/start_frontend.sh"
