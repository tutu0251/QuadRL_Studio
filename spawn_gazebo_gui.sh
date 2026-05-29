#!/usr/bin/env bash
# Launch Gazebo Fortress (Ignition) and spawn a robot exported from QuadRL Studio.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

PROJECTS_DIR="${QUADRL_PROJECTS_DIR:-$HOME/quadruped_dev_tool/projects}"
PROJECT_NAME="${QUADRL_PROJECT:-my_robot}"
WORLD_SDF="${GZ_WORLD:-/usr/share/ignition/ignition-gazebo6/worlds/empty.sdf}"
WORLD_NAME="${GZ_WORLD_NAME:-empty}"
SPAWN_Z="${GZ_SPAWN_Z:-0}"
SPAWN_TIMEOUT="${GZ_SPAWN_TIMEOUT:-30}"
HEADLESS=0
USE_PHYSICS=0

SDF_PATH=""
MODEL_NAME=""
DO_SPAWN=1
POSITIONAL_SET=0

usage() {
  cat <<'EOF'
Usage: ./spawn_gazebo_gui.sh [OPTIONS] [project_name]

Launch Gazebo Sim (Fortress) and spawn the robot SDF from a QuadRL Studio project.

By default this opens the Gazebo GUI (requires DISPLAY / desktop or ssh -X).

Arguments:
  project_name          Project folder under ~/quadruped_dev_tool/projects (default: my_robot)

Options:
  --sdf PATH            Use this SDF file instead of project exports/geo_<name>.sdf
  --name NAME           Spawned model name (default: project name or SDF basename)
  --world PATH          World SDF (default: ignition empty.sdf)
  --world-name NAME     World name for spawn service (default: empty)
  --z METERS            Spawn height (default: 0; models are exported with feet at z=0)
  --headless            Server only (no GUI). Use on SSH without X11 forwarding.
  --no-spawn            Start Gazebo only; do not spawn a robot
  --physics             Use exports/phy_<name>.sdf (physics editor) instead of geo_
  -h, --help            Show this help

Environment:
  QUADRL_PROJECTS_DIR, QUADRL_PROJECT, GZ_WORLD, GZ_WORLD_NAME, GZ_SPAWN_Z, GZ_SPAWN_TIMEOUT

Examples:
  ./spawn_gazebo_gui.sh
  ./spawn_gazebo_gui.sh my_robot
  ssh -X gazebo@host './spawn_gazebo_gui.sh'    # GUI over SSH
  ./spawn_gazebo_gui.sh --headless              # no display needed
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --sdf) SDF_PATH="${2:?--sdf requires a path}"; shift 2 ;;
    --name) MODEL_NAME="${2:?--name requires a value}"; shift 2 ;;
    --world) WORLD_SDF="${2:?--world requires a path}"; shift 2 ;;
    --world-name) WORLD_NAME="${2:?--world-name requires a value}"; shift 2 ;;
    --z) SPAWN_Z="${2:?--z requires a value}"; shift 2 ;;
    --headless) HEADLESS=1; shift ;;
    --no-spawn) DO_SPAWN=0; shift ;;
    --physics) USE_PHYSICS=1; shift ;;
    -*) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    *)
      if [[ "$POSITIONAL_SET" -eq 1 ]]; then
        echo "Unexpected argument: $1" >&2
        exit 1
      fi
      PROJECT_NAME="$1"
      POSITIONAL_SET=1
      shift
      ;;
  esac
done

if [[ -z "$SDF_PATH" ]]; then
  if [[ "$USE_PHYSICS" -eq 1 ]]; then
    SDF_PATH="$PROJECTS_DIR/$PROJECT_NAME/exports/phy_${PROJECT_NAME}.sdf"
  else
    SDF_PATH="$PROJECTS_DIR/$PROJECT_NAME/exports/geo_${PROJECT_NAME}.sdf"
  fi
fi
SDF_PATH="$(readlink -f "$SDF_PATH" 2>/dev/null || realpath "$SDF_PATH")"

if [[ "$DO_SPAWN" -eq 1 && ! -f "$SDF_PATH" ]]; then
  echo "Robot SDF not found: $SDF_PATH" >&2
  echo "Export from the geometry/physics editor (Export SDF) or pass --sdf PATH." >&2
  exit 1
fi

if [[ ! -f "$WORLD_SDF" ]]; then
  echo "World SDF not found: $WORLD_SDF" >&2
  exit 1
fi

if [[ -z "$MODEL_NAME" ]]; then
  if [[ -n "${PROJECT_NAME:-}" && "$SDF_PATH" == *"/$PROJECT_NAME/"* ]]; then
    MODEL_NAME="$PROJECT_NAME"
  else
    MODEL_NAME="$(basename "$SDF_PATH" .sdf)"
  fi
fi

if [[ "$HEADLESS" -eq 0 && -z "${DISPLAY:-}" ]]; then
  cat >&2 <<'EOF'
ERROR: DISPLAY is not set — Gazebo GUI cannot start.

You are probably on plain SSH (no X11). Options:
  1. GUI over SSH:  ssh -X gazebo@<host>   then run this script again
  2. Desktop/VNC on the server, then run from that session
  3. No window:     ./spawn_gazebo_gui.sh --headless
EOF
  exit 1
fi

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo "ROS 2 Humble not found at /opt/ros/humble/setup.bash" >&2
  exit 1
fi
set +u
# shellcheck source=/dev/null
source /opt/ros/humble/setup.bash
set -u

if ! command -v ign >/dev/null 2>&1; then
  echo "Gazebo Fortress CLI 'ign' not found. Install ignition-fortress." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${GZ_PID:-}" ]] && kill -0 "$GZ_PID" 2>/dev/null; then
    kill "$GZ_PID" 2>/dev/null || true
    wait "$GZ_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

wait_for_sim() {
  local service="/world/${WORLD_NAME}/create"
  local deadline=$((SECONDS + SPAWN_TIMEOUT))
  while (( SECONDS < deadline )); do
    if ign service -s "$service" --info 2>/dev/null | grep -q EntityFactory; then
      return 0
    fi
    if ! kill -0 "$GZ_PID" 2>/dev/null; then
      echo "Gazebo exited before the simulation was ready." >&2
      return 1
    fi
    sleep 1
  done
  echo "Timed out waiting for $service (${SPAWN_TIMEOUT}s)." >&2
  return 1
}

if [[ "$HEADLESS" -eq 1 ]]; then
  echo "Starting Gazebo server (headless, world: $WORLD_SDF)"
  ign gazebo -s "$WORLD_SDF" &
else
  echo "Starting Gazebo GUI (world: $WORLD_SDF)"
  ign gazebo "$WORLD_SDF" &
fi
GZ_PID=$!

spawn_robot() {
  local create_pkg="ros_gz_sim"
  if ! ros2 pkg prefix "$create_pkg" &>/dev/null; then
    create_pkg="ros_ign_gazebo"
  fi
  echo "Spawning '$MODEL_NAME' from $SDF_PATH (z=$SPAWN_Z)"
  if ! ros2 run "$create_pkg" create \
    -world "$WORLD_NAME" \
    -file "$SDF_PATH" \
    -name "$MODEL_NAME" \
    -z "$SPAWN_Z" \
    -allow_renaming true 2>&1 | tee /tmp/spawn_gazebo_gui_last.log; then
    return 1
  fi
  if grep -q '\[ERROR\]' /tmp/spawn_gazebo_gui_last.log 2>/dev/null; then
    return 1
  fi
  return 0
}

if [[ "$DO_SPAWN" -eq 1 ]]; then
  echo "Waiting for simulation..."
  wait_for_sim
  if ! spawn_robot; then
    echo "" >&2
    echo "Spawn failed. If the log mentions missing visual name=, re-export SDF from the geometry editor." >&2
    exit 1
  fi
  echo ""
  if [[ "$HEADLESS" -eq 1 ]]; then
    echo "Robot spawned (headless). Press Ctrl+C to stop the simulation."
  else
    echo "Robot spawned. Close the Gazebo window or press Ctrl+C here to exit."
  fi
else
  if [[ "$HEADLESS" -eq 1 ]]; then
    echo "Gazebo server running (--no-spawn). Press Ctrl+C to exit."
  else
    echo "Gazebo running (--no-spawn). Close the window or press Ctrl+C to exit."
  fi
fi

wait "$GZ_PID"
