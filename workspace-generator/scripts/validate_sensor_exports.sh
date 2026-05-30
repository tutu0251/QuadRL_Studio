#!/usr/bin/env bash
# Validate sensor-editor RL exports (URDF, bridge, observations) without building workspace.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/scripts/_run_cli.sh" validate-exports "$@"
