#!/usr/bin/env bash
# Validate control-editor export via colcon workspace (control_readiness launch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECTS_DIR="${QUADRL_PROJECTS_DIR:-$HOME/quadruped_dev_tool/projects}"
PROJECT="${1:-}"
AUTO_BUILD=1
AUTO_GENERATE=1

usage() {
  cat <<'EOF'
Usage: validate_control_runtime.sh <project_name> [--no-build] [--no-generate]

Runs headless control validation through the project's colcon workspace
(control_readiness.launch.py). Auto-generates/builds the workspace when missing
unless --no-build or --no-generate is passed.

Environment:
  QUADRL_PROJECTS_DIR   Projects root (default: ~/quadruped_dev_tool/projects)

Example:
  ./export-validator/scripts/validate_control_runtime.sh my_robot
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --no-build)
      AUTO_BUILD=0
      shift
      ;;
    --no-generate)
      AUTO_GENERATE=0
      shift
      ;;
    *)
      if [[ -z "$PROJECT" ]]; then
        PROJECT="$1"
      fi
      shift
      ;;
  esac
done

PROJECT="${PROJECT:-my_robot}"
EXPORTS="${PROJECTS_DIR}/${PROJECT}/exports"

if [[ ! -d "$EXPORTS" ]]; then
  echo "Exports directory not found: $EXPORTS" >&2
  exit 1
fi

export PYTHONPATH="${ROOT}/backend:${PYTHONPATH:-}"
python3 - <<PY
from pathlib import Path
import sys

sys.path.insert(0, "${ROOT}/backend")
from control_runtime import validate_control_runtime

exports = Path("${EXPORTS}")
result = validate_control_runtime(
    exports,
    "${PROJECT}",
    auto_build=bool(${AUTO_BUILD}),
    auto_generate=bool(${AUTO_GENERATE}),
)
print(result.model_dump_json(indent=2))
status = (result.details or {}).get("status", "unknown")
raise SystemExit(0 if result.valid or status == "skipped" else 1)
PY
