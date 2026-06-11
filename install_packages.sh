#!/usr/bin/env bash
# Install every dependency QuadRL Studio needs — system packages, ROS 2 Humble
# + Gazebo Fortress, the repo-root Python venv (all backends + training + tools,
# including stable-baselines3 / gymnasium / tensorboard), and node_modules for
# every frontend. Does NOT launch anything (use start_all.sh for that).
#
# Usage:
#   ./install_packages.sh              # full install (system + ROS/Gazebo + python + node)
#   ./install_packages.sh --no-ros     # skip ROS 2 + Gazebo (Python/Node only)
#   ./install_packages.sh --no-system  # skip apt + ROS/Gazebo (no sudo / non-Debian)
#   QUADRL_DEV=1 ./install_packages.sh # also install requirements-dev.txt
#
# ROS 2 Humble + Gazebo Fortress target Ubuntu 22.04 (jammy) and are large —
# use --no-ros if they are already installed or you only need Python/Node.
# Re-runnable: skips work that is already done.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

INSTALL_SYSTEM=1
INSTALL_ROS=1
for arg in "$@"; do
  case "$arg" in
    --no-system) INSTALL_SYSTEM=0; INSTALL_ROS=0 ;;
    --no-ros)    INSTALL_ROS=0 ;;
    -h|--help)   sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# --- 1. System dependencies (Debian/Ubuntu) -------------------------------
if [[ "$INSTALL_SYSTEM" -eq 1 ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    SUDO=""
    [[ $EUID -ne 0 ]] && SUDO="sudo"

    log "Installing system packages (python3, venv, pip, git, curl)"
    $SUDO apt-get update -y
    $SUDO apt-get install -y python3 python3-venv python3-pip git curl ca-certificates

    # Node 20.x — only install if missing or older than v18.
    NODE_MAJOR="$(node --version 2>/dev/null | sed 's/v\([0-9]*\).*/\1/' || echo 0)"
    if [[ "${NODE_MAJOR:-0}" -lt 18 ]]; then
      log "Installing Node.js 20.x via NodeSource"
      curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash -
      $SUDO apt-get install -y nodejs
    else
      log "Node.js already present: $(node --version)"
    fi
  else
    log "WARNING: apt-get not found — install python3/python3-venv/pip and Node 20 manually, then re-run with --no-system."
  fi
else
  log "Skipping system packages (--no-system)"
fi

# --- 2. ROS 2 Humble + Gazebo Fortress ------------------------------------
if [[ "$INSTALL_ROS" -eq 1 ]]; then
  if [[ -x "$ROOT/install_ros2_gazebo.sh" ]]; then
    log "Installing ROS 2 Humble + Gazebo Fortress (via install_ros2_gazebo.sh)"
    "$ROOT/install_ros2_gazebo.sh"
  else
    log "WARNING: install_ros2_gazebo.sh not found/executable — skipping ROS/Gazebo."
  fi
else
  log "Skipping ROS 2 + Gazebo (--no-ros / --no-system)"
fi

# --- 3. Python virtual environment (all backends + training + tools) ------
log "Building Python venv (.venv) and installing all requirements"
./scripts/ensure_venv.sh

# --- 4. Frontend node_modules for every editor ----------------------------
log "Installing frontend dependencies for all editors"
for d in "$ROOT"/*/frontend; do
  [[ -f "$d/package.json" ]] || continue
  if [[ -d "$d/node_modules" ]]; then
    echo "  skip (already installed): $d"
  else
    echo "  npm install: $d"
    ( cd "$d" && npm install )
  fi
done

log "All packages installed. Run ./start_all.sh to launch."
