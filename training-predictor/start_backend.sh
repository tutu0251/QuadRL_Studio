#!/usr/bin/env bash
# Start the Training Predictor API (Optuna + Claude parameter tuning).
# Uses a dedicated venv so the heavier deps (optuna/anthropic/tensorboard) stay isolated
# from the editor root venv.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$HERE/backend"
VENV="$BACKEND/.venv"
PORT="${TRAINING_PREDICTOR_PORT:-8007}"

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -r "$BACKEND/requirements.txt"

# Load ANTHROPIC_API_KEY (and any other secrets) from repo-root .env if present.
ENV_FILE="$(cd "$HERE/.." && pwd)/.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a; # shellcheck disable=SC1090
  source "$ENV_FILE"; set +a
fi

# Let the Claude advisor work WITHOUT an API key. The advisor's claude_cli backend
# shells out to the Claude Code CLI, which is authenticated by your Claude Code
# (Max/Pro) login — no ANTHROPIC_API_KEY required. The CLI usually isn't on the
# backend's PATH, so resolve it here and export QUADRL_CLAUDE_CLI for find_claude_cli().
if [[ -z "${QUADRL_CLAUDE_CLI:-}" ]]; then
  CLI=""
  for c in "${CLAUDE_CODE_EXECPATH:-}" "$(command -v claude 2>/dev/null || true)" "$HOME/.claude/local/claude"; do
    if [[ -n "$c" && -x "$c" ]]; then CLI="$c"; break; fi
  done
  # Fall back to the VS Code / Cursor extension's bundled binary (newest version).
  if [[ -z "$CLI" ]]; then
    CLI="$(ls -1 \
      "$HOME"/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude \
      "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude \
      "$HOME"/.cursor-server/extensions/anthropic.claude-code-*/resources/native-binary/claude \
      2>/dev/null | sort -V | tail -1 || true)"
  fi
  if [[ -n "$CLI" && -x "$CLI" ]]; then export QUADRL_CLAUDE_CLI="$CLI"; fi
fi

cd "$BACKEND"
export PYTHONPATH="$BACKEND${PYTHONPATH:+:$PYTHONPATH}"
echo "Starting Training Predictor API on 0.0.0.0:$PORT (DEV — no auth)"
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "  advisor: Claude via API key"
elif [[ -n "${QUADRL_CLAUDE_CLI:-}" ]]; then
  echo "  advisor: Claude via CLI (${QUADRL_CLAUDE_CLI}) — no API key needed"
else
  echo "  advisor: disabled (no ANTHROPIC_API_KEY and no Claude CLI found)"
fi
exec "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port "$PORT"
