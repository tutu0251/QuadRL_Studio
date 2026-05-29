#!/usr/bin/env bash
set -euo pipefail
PE="$(cd "$(dirname "$0")" && pwd)"

BACK_PID=""
FRONT_PID=""

port_busy() {
  ss -tlnH "sport = :$1" 2>/dev/null | grep -q .
}

shutdown() {
  trap - INT TERM EXIT
  [[ -n "${FRONT_PID}" ]] && kill -TERM "$FRONT_PID" 2>/dev/null || true
  [[ -n "${BACK_PID}" ]] && kill -TERM "$BACK_PID" 2>/dev/null || true
  wait "$FRONT_PID" "$BACK_PID" 2>/dev/null || true
}

trap shutdown INT TERM EXIT

if port_busy 8001; then
  echo "ERROR: Port 8001 in use." >&2
  exit 1
fi
if port_busy 5174; then
  echo "ERROR: Port 5174 in use." >&2
  exit 1
fi

"$PE/start_backend.sh" &
BACK_PID=$!
sleep 2
"$PE/start_frontend.sh" &
FRONT_PID=$!

echo ""
echo "Physics Editor running:"
echo "  Backend:  http://0.0.0.0:8001  (API docs: /docs)"
echo "  Frontend: http://0.0.0.0:5174"
echo "  Set physics-editor/frontend/.env: VITE_API_BASE_URL=http://<host>:8001"
echo "  Press Ctrl+C to stop."
echo ""

wait "$BACK_PID" "$FRONT_PID"
