#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/train-monitor" && pwd)"
exec "$ROOT/start_train_monitor.sh"
