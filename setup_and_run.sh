#!/usr/bin/env bash
# One-shot: prepare a fresh machine and run all of QuadRL Studio.
#
# Installs system deps (python3 + venv + pip, Node 20, git), builds the repo-root
# .venv, installs every frontend's node_modules, then launches all backends and
# frontends via start_all.sh.
#
# Usage:
#   ./setup_and_run.sh                       # full setup + run (foreground)
#   QUADRL_HOST=<ip_or_dns> ./setup_and_run.sh   # override the host shown in URLs
#   ./setup_and_run.sh --headless [args...]  # also start headless Gazebo
#   ./setup_and_run.sh --setup-only          # prepare everything, do not launch
#
# Re-runnable: skips work that is already done.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

HEADLESS=0
SETUP_ONLY=0
PASS_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --headless)   HEADLESS=1 ;;
    --setup-only) SETUP_ONLY=1 ;;
    *)            PASS_ARGS+=("$arg") ;;
  esac
done

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

# --- 1. System dependencies (Debian/Ubuntu) -------------------------------
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
  log "WARNING: apt-get not found — install python3/python3-venv/pip and Node 20 manually."
fi

# --- 2. Make all helper scripts executable --------------------------------
log "Marking scripts executable"
chmod +x ./*.sh ./scripts/*.sh ./*/start_*.sh ./*/scripts/*.sh 2>/dev/null || true

# --- 3. Python virtual environment ----------------------------------------
log "Building Python venv (.venv) and installing requirements"
./scripts/ensure_venv.sh

# --- 4. Frontend node_modules ---------------------------------------------
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


###
# --- 5. Launch ------------------------------------------------------------
#if [[ "$SETUP_ONLY" -eq 1 ]]; then
#  log "Setup complete. Skipping launch (--setup-only)."
#  exit 0
#fi
#
#if [[ "$HEADLESS" -eq 1 ]]; then
#  log "Launching everything (headless Gazebo included)"
#  exec ./start_all_headless.sh "${PASS_ARGS[@]}"
#else
#  log "Launching all backends and frontends"
#  exec ./start_all.sh "${PASS_ARGS[@]}"
#fi
