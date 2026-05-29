#!/usr/bin/env bash
# Convenience launcher from repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT/geometry-editor/start_geometry_editor.sh" "$@"
