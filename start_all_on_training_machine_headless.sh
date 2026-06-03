#!/usr/bin/env bash
# Back-compat alias for start_all_headless.sh (editors + headless Gazebo).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT/start_all_headless.sh" "$@"
