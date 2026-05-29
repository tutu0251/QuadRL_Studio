#!/usr/bin/env bash
# Stop Geometry Editor dev servers (Vite + uvicorn).
set -euo pipefail

stopped=0

stop_matching() {
  local label=$1
  local pattern=$2
  if pgrep -f "$pattern" >/dev/null 2>&1; then
    pkill -TERM -f "$pattern" 2>/dev/null || true
    sleep 1
    pkill -KILL -f "$pattern" 2>/dev/null || true
    echo "Stopped $label"
    stopped=1
  fi
}

stop_matching "Vite (frontend)" "vite --host"
stop_matching "uvicorn (backend)" "uvicorn main:app"

if [[ $stopped -eq 0 ]]; then
  echo "No geometry editor dev servers were running."
else
  echo "Done. Ports 5173 and 8000 should be free."
fi
