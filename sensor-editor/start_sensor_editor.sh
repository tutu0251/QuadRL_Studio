#!/usr/bin/env bash
set -euo pipefail
SE="$(cd "$(dirname "$0")" && pwd)"

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

if port_busy 8003; then
  echo "ERROR: Port 8003 in use." >&2
  exit 1
fi
if port_busy 5176; then
  echo "ERROR: Port 5176 in use." >&2
  exit 1
fi

"$SE/start_backend.sh" &
BACK_PID=$!
sleep 2
"$SE/start_frontend.sh" &
FRONT_PID=$!

echo ""
echo "Sensor Editor running:"
echo "  Backend:  http://0.0.0.0:8003  (API docs: /docs)"
echo "  Frontend: http://0.0.0.0:5176"
echo "  Set sensor-editor/frontend/.env: VITE_API_BASE_URL=http://<host>:8003"
echo "  Press Ctrl+C to stop."
echo ""

wait "$BACK_PID" "$FRONT_PID"
