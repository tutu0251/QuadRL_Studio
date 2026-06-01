#!/usr/bin/env bash
# Export validation for ctrl_* exports via export-validator.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
PROJECTS_DIR="${QUADRL_PROJECTS_DIR:-$HOME/quadruped_dev_tool/projects}"
PROJECT_NAME="${1:-}"

usage() {
  cat <<'EOF'
Usage: validate_gazebo_export.sh <project_name>

Validate exported ros2_control files via export-validator (colcon workspace + Gazebo).

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

QUADRL_ROOT="$(cd "$ROOT/.." && pwd)"
# shellcheck source=../../scripts/ensure_venv.sh
source "$QUADRL_ROOT/scripts/ensure_venv.sh"
PYTHON="$QUADRL_PYTHON"

exec "$PYTHON" - <<PY
import json
import sys
from pathlib import Path

sys.path.insert(0, "${BACKEND}")
from validator.runtime_validator import validate_control_export

result = validate_control_export("${PROJECT_NAME}")
status = (result.details or {}).get("status", "unknown")
print(f"Export validation: {status}")
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
