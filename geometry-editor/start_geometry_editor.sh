#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
trap 'kill 0' EXIT INT TERM

"$ROOT/start_backend.sh" &
BACK_PID=$!
sleep 2
"$ROOT/start_frontend.sh" &
FRONT_PID=$!

echo ""
echo "Geometry Editor v2 running:"
echo "  Backend:  http://0.0.0.0:8000  (API docs: /docs)"
echo "  Frontend: http://0.0.0.0:5173"
echo "  From your PC browser: http://2.24.99.148:5173"
echo "  Set apps/geometry-editor/.env: VITE_API_BASE_URL=http://2.24.99.148:8000"
echo ""

wait $BACK_PID $FRONT_PID
