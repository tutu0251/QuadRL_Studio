#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT/rl-trainer-editor/start_rl_trainer_editor.sh" "$@"
