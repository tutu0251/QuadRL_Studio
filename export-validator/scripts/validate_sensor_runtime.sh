#!/usr/bin/env bash
# Validate sensor-editor exports via full training workspace runtime checks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECTS_DIR="${QUADRL_PROJECTS_DIR:-$HOME/quadruped_dev_tool/projects}"
PROJECT="${1:-}"

usage() {
  cat <<'EOF'
Usage: validate_sensor_runtime.sh <project_name>

Runs headless sensor validation through the project's full colcon workspace
(training_readiness.launch.py). Requires a built workspace from workspace-generator.

Environment:
  QUADRL_PROJECTS_DIR   Projects root (default: ~/quadruped_dev_tool/projects)

Example:
  ./export-validator/scripts/validate_sensor_runtime.sh my_robot
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "$PROJECT" ]]; then
  echo "Project name required." >&2
  usage >&2
  exit 1
fi

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
from sensor_runtime import validate_sensor_runtime

exports = Path("${EXPORTS}")
result = validate_sensor_runtime(exports, "${PROJECT}")
print(result.model_dump_json(indent=2))
status = (result.details or {}).get("status", "unknown")
raise SystemExit(0 if result.valid or status == "skipped" else 1)
PY
