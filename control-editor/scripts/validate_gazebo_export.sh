#!/usr/bin/env bash
# Headless Gazebo validation for exported ctrl_*_ros2_control.urdf
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
PROJECTS_DIR="${QUADRL_PROJECTS_DIR:-$HOME/quadruped_dev_tool/projects}"
PROJECT_NAME="${1:-}"

usage() {
  cat <<'EOF'
Usage: validate_gazebo_export.sh <project_name>

Spawn the exported ros2_control URDF in headless Gazebo Fortress and verify
gz_ros2_control loads. Uses the Control Editor backend validator.

Environment:
  QUADRL_PROJECTS_DIR   Projects root (default: ~/quadruped_dev_tool/projects)

Example:
  ./control-editor/scripts/validate_gazebo_export.sh my_robot
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "$PROJECT_NAME" ]]; then
  echo "Project name required." >&2
  usage >&2
  exit 1
fi

URDF="$PROJECTS_DIR/$PROJECT_NAME/exports/ctrl_${PROJECT_NAME}_ros2_control.urdf"
if [[ ! -f "$URDF" ]]; then
  echo "Export URDF not found: $URDF" >&2
  echo "Run Export ros2_control in the Control Editor first." >&2
  exit 1
fi

PYTHON="${BACKEND}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

exec "$PYTHON" - <<PY
import json
import sys
from pathlib import Path

sys.path.insert(0, "${BACKEND}")
from validator.gazebo_validator import validate_gazebo_export

urdf = Path("${URDF}")
result = validate_gazebo_export(urdf, "${PROJECT_NAME}")
status = (result.details or {}).get("status", "unknown")
print(f"Gazebo validation: {status}")
if result.warnings:
    for w in result.warnings:
        print(f"  [warning] {w.message}")
if result.errors:
    for e in result.errors:
        print(f"  [error] {e.message}")
if result.details:
    print(json.dumps(result.details, indent=2))
sys.exit(0 if result.valid or status == "skipped" else 1)
PY
