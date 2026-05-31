#!/usr/bin/env bash
# Validate control-editor export via colcon workspace (control_readiness launch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECTS_DIR="${QUADRL_PROJECTS_DIR:-$HOME/quadruped_dev_tool/projects}"
PROJECT="${1:-}"
AUTO_BUILD=1
AUTO_GENERATE=1
QUIET=0

usage() {
  cat <<'EOF'
Usage: validate_control_runtime.sh <project_name> [--no-build] [--no-generate] [--quiet]

Runs headless control validation through the project's colcon workspace
(control_readiness.launch.py). Auto-generates/builds the workspace when missing
unless --no-build or --no-generate is passed.

Progress lines are printed to stdout during execution (timestamps + stage updates).
Use --quiet to suppress progress and only print the final JSON result.

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
    --quiet|-q)
      QUIET=1
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
from cli_progress import cli_log, log_stage
from control_runtime import validate_control_runtime

quiet = bool(${QUIET})
log = cli_log("control") if not quiet else None
if log:
    log_stage(log, f"control runtime validation — ${PROJECT}")
    log(f"exports: ${EXPORTS}")

exports = Path("${EXPORTS}")
result = validate_control_runtime(
    exports,
    "${PROJECT}",
    auto_build=bool(${AUTO_BUILD}),
    auto_generate=bool(${AUTO_GENERATE}),
    on_log=log,
)
if log:
    status = (result.details or {}).get("status", "unknown")
    duration = (result.details or {}).get("durationS")
    extra = f" in {duration}s" if duration is not None else ""
    log(f"finished: {status}{extra}")
    print("", flush=True)
print(result.model_dump_json(indent=2))
status = (result.details or {}).get("status", "unknown")
raise SystemExit(0 if result.valid or status == "skipped" else 1)
PY
