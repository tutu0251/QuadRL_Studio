#!/usr/bin/env bash
# Generate workspace, build, and validate full RL training readiness.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${1:-}"

usage() {
  cat <<'EOF'
Usage: setup_robot.sh <project_name> [validate options]

Generate colcon workspace from QuadRL exports, build, and validate training readiness.

Examples:
  ./workspace-generator/scripts/setup_robot.sh my_robot
  ./workspace-generator/scripts/setup_robot.sh my_robot --static-only
  ./workspace-generator/scripts/setup_robot.sh my_robot --skip-runtime
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

shift || true
"$ROOT/scripts/generate_workspace.sh" "$PROJECT"
"$ROOT/scripts/build_workspace.sh" "$PROJECT"
exec "$ROOT/scripts/validate_training_readiness.sh" "$PROJECT" "$@"
