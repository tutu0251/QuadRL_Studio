#!/usr/bin/env bash
# Restart QuadRL Studio editor servers after a short delay.
# Usage: restart_services.sh [all|editor-id] [delay_seconds]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCOPE="${1:-all}"
DELAY="${2:-2}"

sleep "$DELAY"

if [[ "$SCOPE" == "all" ]]; then
  "$ROOT/stop_all_editors.sh" || true
  exec bash "$ROOT/scripts/start_all_background.sh"
fi

declare -A BACKEND_PORTS=(
  [geometry-editor]=8000
  [physics-editor]=8001
  [control-editor]=8002
  [sensor-editor]=8003
  [ppo-planner]=8004
  [rl-trainer-editor]=8005
  [train-monitor]=8006
)
declare -A FRONTEND_PORTS=(
  [geometry-editor]=5173
  [physics-editor]=5174
  [control-editor]=5175
  [sensor-editor]=5176
  [ppo-planner]=5177
  [rl-trainer-editor]=5178
  [train-monitor]=5179
)

if [[ -z "${BACKEND_PORTS[$SCOPE]+x}" ]]; then
  echo "Unknown scope: $SCOPE" >&2
  exit 1
fi

kill_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti :"$port" 2>/dev/null | xargs -r kill -TERM 2>/dev/null || true
    sleep 0.5
    lsof -ti :"$port" 2>/dev/null | xargs -r kill -KILL 2>/dev/null || true
  fi
}

kill_port "${BACKEND_PORTS[$SCOPE]}"
kill_port "${FRONTEND_PORTS[$SCOPE]}"

export QUADRL_HOST="${QUADRL_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}' || echo 127.0.0.1)}"
bash "$ROOT/$SCOPE/start_backend.sh" >"/tmp/$SCOPE.backend.log" 2>&1 &
sleep 1
bash "$ROOT/$SCOPE/start_frontend.sh" >"/tmp/$SCOPE.frontend.log" 2>&1 &

echo "[quadrl] Restarted $SCOPE"
