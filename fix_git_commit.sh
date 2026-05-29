#!/usr/bin/env bash
# Fix common git commit blockers for QuadRL Studio.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

DRY_RUN=0
DO_COMMIT=0
COMMIT_MSG=""

usage() {
  cat <<'EOF'
Usage: ./fix_git_commit.sh [OPTIONS]

Fix common issues that block "git commit" in this repo, then show status.

Options:
  --dry-run           Print fixes without changing anything
  --commit "MESSAGE"  Apply fixes, then run git commit with MESSAGE
  -h, --help          Show this help

Common fixes:
  - Stale .git/index.lock
  - Accidentally staged secrets (.env, keys)
  - Staged build artifacts (node_modules, .venv, dist, __pycache__)
  - Staged files that match .gitignore
  - Missing git user.name / user.email (prints setup instructions)

Does NOT modify git config. Set identity yourself:

  git config --global user.name "Your Name"
  git config --global user.email "you@example.com"

Examples:
  ./fix_git_commit.sh
  ./fix_git_commit.sh --commit "Reorganize geometry editor into subfolder"
EOF
}

log() { echo "==> $*"; }
warn() { echo "WARN: $*" >&2; }

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --commit)
      DO_COMMIT=1
      COMMIT_MSG="${2:-}"
      if [[ -z "$COMMIT_MSG" ]]; then
        echo "ERROR: --commit requires a message." >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "ERROR: Not inside a git repository." >&2
  exit 1
fi

if [[ -d .git/rebase-merge || -d .git/rebase-apply || -f .git/MERGE_HEAD || -f .git/CHERRY_PICK_HEAD ]]; then
  echo "ERROR: A merge, rebase, or cherry-pick is in progress. Finish or abort it first." >&2
  exit 1
fi

# --- 1. Git identity (cannot auto-fix per repo policy) ---
NAME="$(git config user.name 2>/dev/null || true)"
EMAIL="$(git config user.email 2>/dev/null || true)"
if [[ -z "$NAME" || -z "$EMAIL" ]]; then
  echo "ERROR: Git author identity is not configured." >&2
  echo "" >&2
  echo "Run (use your real name and email):" >&2
  echo '  git config --global user.name "Your Name"' >&2
  echo '  git config --global user.email "you@example.com"' >&2
  echo "" >&2
  echo "Or set only for this repo by omitting --global." >&2
  exit 1
fi

# --- 2. Stale index lock ---
if [[ -f .git/index.lock ]]; then
  if pgrep -af '[g]it (commit|add|merge|rebase|checkout|restore|reset)' >/dev/null 2>&1; then
    warn ".git/index.lock exists while another git command may be running; not removing."
  else
    log "Removing stale .git/index.lock"
    run rm -f .git/index.lock
  fi
fi

# --- 3. Unstage files that must never be committed ---
should_unstage() {
  local f=$1
  [[ "$f" == .env || "$f" == */.env || "$f" == */.env.local ]] && return 0
  [[ "$f" == *".env.example" ]] && return 1
  [[ "$f" == *node_modules* || "$f" == */.venv/* || "$f" == */.venv ]] && return 0
  [[ "$f" == */__pycache__/* || "$f" == *.pyc ]] && return 0
  [[ "$f" == */dist/* || "$f" == *.tsbuildinfo ]] && return 0
  [[ "$f" == *credentials.json || "$f" == *.pem || "$f" == *.key ]] && return 0
  [[ "$f" == */id_rsa || "$f" == */id_ed25519 ]] && return 0
  git check-ignore -q "$f" 2>/dev/null
}

unstage_path() {
  local path=$1
  log "Unstaging: $path"
  run git restore --staged -- "$path" 2>/dev/null || run git reset HEAD -- "$path" 2>/dev/null || true
}

unstage_bad_staged_files() {
  while IFS= read -r staged; do
    [[ -z "$staged" ]] && continue
    if should_unstage "$staged"; then
      unstage_path "$staged"
    fi
  done < <(git diff --cached --name-only 2>/dev/null || true)
}

if ! git diff --cached --quiet 2>/dev/null; then
  unstage_bad_staged_files
fi

# --- 4. Stage project files (respects .gitignore) ---
log "Staging tracked changes and new project files"
run git add -A
run git add -u

# Re-unstage secrets/artifacts if add -A picked them up
unstage_bad_staged_files

# --- 5. Summary ---
echo ""
if git diff --cached --quiet 2>/dev/null; then
  echo "Nothing staged to commit."
  echo ""
  git status --short
  echo ""
  if git status --porcelain | grep -q .; then
    echo "You have unstaged changes. Review with: git status"
  else
    echo "Working tree is clean."
  fi
  exit 0
fi

echo "Staged for commit:"
git diff --cached --stat
echo ""
git status --short
echo ""

if [[ $DO_COMMIT -eq 1 ]]; then
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[dry-run] git commit -m $(printf '%q' "$COMMIT_MSG")"
    exit 0
  fi
  log "Committing..."
  git commit -m "$COMMIT_MSG"
  echo ""
  git log -1 --oneline
  git status --short
else
  echo "Ready to commit. Example:"
  echo '  git commit -m "Your message here"'
  echo ""
  echo "Or run:"
  echo "  ./fix_git_commit.sh --commit \"Your message here\""
fi
