#!/usr/bin/env bash
# Start all QuadRL Studio subprojects plus headless Gazebo on this machine.
#
# Usage:
#   ./start_all_headless.sh
#   ./start_all_headless.sh my_robot
#   ./start_all_headless.sh --physics my_robot
#   QUADRL_HOST=<ip_or_dns> ./start_all_headless.sh
#
# Extra arguments are passed to spawn_gazebo_gui.sh (with --headless always set).
# Open UIs from your browser at http://<host>:5173–5179 (see printed URLs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

BACKENDS=(
  "$ROOT/geometry-editor/start_backend.sh"
  "$ROOT/physics-editor/start_backend.sh"
  "$ROOT/control-editor/start_backend.sh"
  "$ROOT/sensor-editor/start_backend.sh"
  "$ROOT/ppo-planner/start_backend.sh"
  "$ROOT/rl-trainer-editor/start_backend.sh"
  "$ROOT/train-monitor/start_backend.sh"
  "$ROOT/training-predictor/start_backend.sh"
)

FRONTENDS=(
  "$ROOT/geometry-editor/start_frontend.sh"
  "$ROOT/physics-editor/start_frontend.sh"
  "$ROOT/control-editor/start_frontend.sh"
  "$ROOT/sensor-editor/start_frontend.sh"
  "$ROOT/ppo-planner/start_frontend.sh"
  "$ROOT/rl-trainer-editor/start_frontend.sh"
  "$ROOT/train-monitor/start_frontend.sh"
)

PIDS=()

training_ip() {
  local ip
  ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  echo "${ip:-127.0.0.1}"
}

shutdown() {
  trap - INT TERM EXIT
  if [[ ${#PIDS[@]} -gt 0 ]]; then
    kill -TERM "${PIDS[@]}" 2>/dev/null || true
    sleep 0.5
    kill -KILL "${PIDS[@]}" 2>/dev/null || true
  fi
  "$ROOT/stop_all_editors.sh" >/dev/null 2>&1 || true
}
trap shutdown INT TERM EXIT

echo "Stopping any stale QuadRL Studio dev servers..."
"$ROOT/stop_all_editors.sh" || true
echo ""

export QUADRL_HOST="${QUADRL_HOST:-$(training_ip)}"
echo "Using QUADRL_HOST=${QUADRL_HOST}"
echo ""

echo "Starting headless Gazebo (spawn_gazebo_gui.sh --headless)..."
bash "$ROOT/spawn_gazebo_gui.sh" --headless "$@" >/tmp/spawn_gazebo.headless.log 2>&1 &
PIDS+=("$!")

echo "Starting backends..."
for cmd in "${BACKENDS[@]}"; do
  bash "$cmd" >/tmp/"$(basename "$(dirname "$cmd")")".backend.log 2>&1 &
  PIDS+=("$!")
done

sleep 2

echo "Starting frontends..."
for cmd in "${FRONTENDS[@]}"; do
  bash "$cmd" >/tmp/"$(basename "$(dirname "$cmd")")".frontend.log 2>&1 &
  PIDS+=("$!")
done

cat <<EOF

All subprojects launching in the background (headless Gazebo sim included).

Open from your browser:
  Geometry Editor:   http://${QUADRL_HOST}:5173
  Physics Editor:    http://${QUADRL_HOST}:5174
  Control Editor:    http://${QUADRL_HOST}:5175
  Sensor Editor:     http://${QUADRL_HOST}:5176
  PPO Planner:       http://${QUADRL_HOST}:5177
  RL Trainer Editor: http://${QUADRL_HOST}:5178
  Train Monitor:     http://${QUADRL_HOST}:5179

API docs:
  Geometry:   http://${QUADRL_HOST}:8000/docs
  Physics:    http://${QUADRL_HOST}:8001/docs
  Control:    http://${QUADRL_HOST}:8002/docs
  Sensor:     http://${QUADRL_HOST}:8003/docs
  PPO:        http://${QUADRL_HOST}:8004/docs
  RL Trainer: http://${QUADRL_HOST}:8005/docs
  Monitor:    http://${QUADRL_HOST}:8006/docs

Gazebo (headless, no DISPLAY required):
  Log: /tmp/spawn_gazebo.headless.log
  Spawn log: /tmp/spawn_gazebo_gui_last.log

Editor logs:
  /tmp/geometry-editor.backend.log, /tmp/geometry-editor.frontend.log, etc.

Press Ctrl+C here to stop everything.
EOF

wait
