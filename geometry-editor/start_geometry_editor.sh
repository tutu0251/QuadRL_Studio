#!/usr/bin/env bash
set -euo pipefail
GE="$(cd "$(dirname "$0")" && pwd)"

BACK_PID=""
FRONT_PID=""

port_busy() {
  ss -tlnH "sport = :$1" 2>/dev/null | grep -q .
}

shutdown() {
  trap - INT TERM EXIT
  if [[ -n "${FRONT_PID}" ]] && kill -0 "$FRONT_PID" 2>/dev/null; then
    kill -TERM "$FRONT_PID" 2>/dev/null || true
    pkill -TERM -P "$FRONT_PID" 2>/dev/null || true
  fi
  if [[ -n "${BACK_PID}" ]] && kill -0 "$BACK_PID" 2>/dev/null; then
    kill -TERM "$BACK_PID" 2>/dev/null || true
  fi
  wait "$FRONT_PID" "$BACK_PID" 2>/dev/null || true
}

trap shutdown INT TERM EXIT

if port_busy 8000; then
  echo "ERROR: Port 8000 is already in use. Stop stale backends first:" >&2
  echo "  pkill -f 'uvicorn main:app'" >&2
  exit 1
fi
if port_busy 5173; then
  echo "ERROR: Port 5173 is already in use. Stop stale Vite first:" >&2
  echo "  pkill -f 'vite --host'" >&2
  exit 1
fi

"$GE/start_backend.sh" &
BACK_PID=$!
sleep 2
"$GE/start_frontend.sh" &
FRONT_PID=$!

echo ""
echo "Geometry Editor v2 running:"
echo "  Backend:  http://0.0.0.0:8000  (API docs: /docs)"
echo "  Frontend: http://0.0.0.0:5173"
echo "  From your PC browser: http://2.24.99.148:5173"
echo "  Set geometry-editor/frontend/.env: VITE_API_BASE_URL=http://2.24.99.148:8000"
echo "  Press Ctrl+C to stop (both services)."
echo ""

wait "$BACK_PID" "$FRONT_PID"
