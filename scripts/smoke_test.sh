#!/usr/bin/env bash
# End-to-end API smoke test for Geometry Editor v2
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"

# Start uvicorn in background
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8765 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
sleep 2

BASE="http://127.0.0.1:8765"
PROJECT="smoke_test_$$"

echo "== Health =="
curl -sf "$BASE/api/health" | grep -q '"version":"2.0.0"'

echo "== Create project =="
curl -sf -X POST "$BASE/api/projects" -H 'Content-Type: application/json' -d "{\"name\":\"$PROJECT\"}" | grep -q base_link

echo "== Insert quadruped template =="
curl -sf -X POST "$BASE/api/projects/$PROJECT/templates" \
  -H 'Content-Type: application/json' -d '{"template_id":"mini_dog"}' | grep -q fl_hip

echo "== Validate =="
TASK=$(curl -sf -X POST "$BASE/api/projects/$PROJECT/validate" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
sleep 1
curl -sf "$BASE/api/tasks/$TASK" | grep -q completed

echo "== Export both =="
TASK=$(curl -sf -X POST "$BASE/api/projects/$PROJECT/export/both" | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
sleep 1
RESULT=$(curl -sf "$BASE/api/tasks/$TASK")
echo "$RESULT" | grep -q completed

URDF="$HOME/quadruped_dev_tool/projects/$PROJECT/exports/$PROJECT.urdf"
SDF="$HOME/quadruped_dev_tool/projects/$PROJECT/exports/$PROJECT.sdf"
test -f "$URDF"
test -f "$SDF"
grep -q '<robot' "$URDF"
grep -q '<sdf' "$SDF"
grep -qE "name=['\"].*_visual" "$SDF"
grep -qE '<box size=' "$URDF"

if command -v check_urdf >/dev/null 2>&1; then
  check_urdf "$URDF" >/dev/null
fi
if command -v ign >/dev/null 2>&1; then
  ign sdf -k "$SDF" >/dev/null
fi

echo "== Measure =="
LINK=$(curl -sf "$BASE/api/projects/$PROJECT/model" | python3 -c "import sys,json; m=json.load(sys.stdin); print(m['links'][0]['id'])")
curl -sf -X POST "$BASE/api/projects/$PROJECT/measure/height" \
  -H 'Content-Type: application/json' -d "{\"link_id\":\"$LINK\"}" | grep -q '"tool":"height"'

echo ""
echo "Smoke test PASSED"
echo "  URDF: $URDF"
echo "  SDF:  $SDF"
