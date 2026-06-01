#!/usr/bin/env bash
# Stop all QuadRL Studio editor dev servers (backends + frontends).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Backend (uvicorn) and frontend (Vite) ports per editor.
declare -A BACKEND_PORTS=(
  [8000]="Geometry Editor backend"
  [8001]="Physics Editor backend"
  [8002]="Control Editor backend"
  [8003]="Sensor Editor backend"
  [8004]="PPO Planner backend"
  [8005]="RL Trainer Editor backend"
  [8006]="Train Monitor backend"
)
declare -A FRONTEND_PORTS=(
  [5173]="Geometry Editor frontend"
  [5174]="Physics Editor frontend"
  [5175]="Control Editor frontend"
  [5176]="Sensor Editor frontend"
  [5177]="PPO Planner frontend"
  [5178]="RL Trainer Editor frontend"
  [5179]="Train Monitor frontend"
)

stopped=0

pids_on_port() {
  local port=$1
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
  elif command -v fuser >/dev/null 2>&1; then
    pids=$(fuser "$port"/tcp 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' || true)
  elif command -v ss >/dev/null 2>&1; then
    pids=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' || true)
  fi

  echo "$pids"
}

kill_pids() {
  local signal=$1
  shift
  local pid

  for pid in "$@"; do
    [[ -n "$pid" ]] || continue
    kill "-$signal" "$pid" 2>/dev/null || true
  done
}

stop_port() {
  local port=$1
  local label=$2
  local pids
  pids=$(pids_on_port "$port")

  if [[ -z "$pids" ]]; then
    return 0
  fi

  # shellcheck disable=SC2206
  kill_pids TERM $pids
  sleep 0.5

  pids=$(pids_on_port "$port")
  if [[ -n "$pids" ]]; then
    # shellcheck disable=SC2206
    kill_pids KILL $pids
  fi

  echo "Stopped $label (port $port)"
  stopped=1
}

stop_launchers() {
  local patterns=(
    "$ROOT/geometry-editor/start_geometry_editor.sh"
    "$ROOT/physics-editor/start_physics_editor.sh"
    "$ROOT/control-editor/start_control_editor.sh"
    "$ROOT/sensor-editor/start_sensor_editor.sh"
    "$ROOT/ppo-planner/start_ppo_planner.sh"
    "$ROOT/rl-trainer-editor/start_rl_trainer_editor.sh"
    "$ROOT/start_geometry_editor.sh"
    "$ROOT/start_physics_editor.sh"
    "$ROOT/start_control_editor.sh"
    "$ROOT/start_sensor_editor.sh"
    "$ROOT/start_ppo_planner.sh"
    "$ROOT/start_rl_trainer_editor.sh"
  )

  local pattern
  for pattern in "${patterns[@]}"; do
    if pgrep -f "$pattern" >/dev/null 2>&1; then
      pkill -TERM -f "$pattern" 2>/dev/null || true
      sleep 0.5
      pkill -KILL -f "$pattern" 2>/dev/null || true
      echo "Stopped launcher: $(basename "$pattern")"
      stopped=1
    fi
  done
}

echo "Stopping QuadRL Studio dev servers..."

stop_launchers

for port in "${!BACKEND_PORTS[@]}"; do
  stop_port "$port" "${BACKEND_PORTS[$port]}"
done

for port in "${!FRONTEND_PORTS[@]}"; do
  stop_port "$port" "${FRONTEND_PORTS[$port]}"
done

if [[ $stopped -eq 0 ]]; then
  echo "No editor dev servers were running."
else
  echo "Done. Backend ports 8000-8006 and frontend ports 5173-5179 should be free."
fi
