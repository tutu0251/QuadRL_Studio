#!/usr/bin/env bash
# Start all QuadRL Studio editors in the background (for systemd / unattended boot).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

training_ip() {
  local ip
  ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  echo "${ip:-127.0.0.1}"
}

export QUADRL_HOST="${QUADRL_HOST:-$(training_ip)}"

echo "[quadrl] Stopping stale servers..."
"$ROOT/stop_all_editors.sh" || true

echo "[quadrl] Starting backends..."
for editor in geometry-editor physics-editor control-editor sensor-editor ppo-planner rl-trainer-editor train-monitor; do
  bash "$ROOT/$editor/start_backend.sh" >"/tmp/$editor.backend.log" 2>&1 &
done

sleep 2

echo "[quadrl] Starting frontends..."
for editor in geometry-editor physics-editor control-editor sensor-editor ppo-planner rl-trainer-editor train-monitor; do
  bash "$ROOT/$editor/start_frontend.sh" >"/tmp/$editor.frontend.log" 2>&1 &
done

echo "[quadrl] All editors launched (QUADRL_HOST=${QUADRL_HOST})"
