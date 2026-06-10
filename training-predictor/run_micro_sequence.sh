#!/usr/bin/env bash
# Real single-stage micro-run for sequential per-stage tuning (§14 verification).
#
# Launches a REAL sequential study (mock_objective=false) with the smallest sensible budget:
# 2 stages, 1 trial each, a tiny per-stage timestep budget — just enough to validate the full
# pipeline end-to-end: stage 0 trains from scratch → checkpoint captured/promoted → stage 1
# resumes from it (--resume + --start-stage) → objective read from TensorBoard → per-stage best.
#
# Prereqs: Training Predictor API (:8007) and Train Monitor (:8006) running, the project's
# workspace built, and Gazebo able to launch headless. Trains on CPU if no GPU (slow).
#
# Usage:
#   ./run_micro_sequence.sh [PROJECT] [STAGES] [TRIALS_PER_STAGE] [TIMESTEPS_PER_STAGE]
#   ./run_micro_sequence.sh my_robot 2 1 4000
set -euo pipefail

API="${TRAINING_PREDICTOR_URL:-http://127.0.0.1:8007}"
PROJECT="${1:-my_robot}"
STAGES="${2:-2}"
TRIALS="${3:-1}"
TIMESTEPS="${4:-4000}"
TIMEOUT="${TRIAL_TIMEOUT:-900}"

echo "Micro-run: project=$PROJECT  stages=1..$STAGES  trials/stage=$TRIALS  timesteps/stage=$TIMESTEPS"
echo "API=$API  (REAL training via Train Monitor :8006)"

body=$(cat <<JSON
{"project":"$PROJECT","mode":"sequential_stage","mock_objective":false,
 "max_stages":$STAGES,"trials_per_stage":$TRIALS,"timesteps_per_stage":$TIMESTEPS,
 "advisor_every_n":99,"gazebo_headless":true,"trial_timeout":$TIMEOUT}
JSON
)

resp=$(curl -s -X POST "$API/api/tuning/start" -H 'Content-Type: application/json' -d "$body")
echo "start -> $resp"
tid=$(echo "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin).get('task_id',''))")
[ -n "$tid" ] || { echo "Failed to start."; exit 1; }

echo "Streaming status + logs for task $tid (Ctrl+C to stop watching; the run keeps going)…"
echo "  Stop the run with: curl -X POST $API/api/tuning/$tid/stop"
echo "  Apply the result with: curl -X POST $API/api/tuning/$tid/apply"
echo

last=""
while true; do
  st=$(curl -s "$API/api/tuning/$tid/status")
  line=$(echo "$st" | python3 -c "
import sys,json
d=json.load(sys.stdin)
stages=' | '.join(f\"{s['stage_index']}:{s['stage_name']}={s['status']}({s['n_completed']})\" for s in d.get('stages',[]))
print(f\"{d['status']}  stage={d.get('current_stage_index')}  [{stages}]\")
")
  [ "$line" != "$last" ] && echo "  $line" && last="$line"
  echo "$line" | grep -qE '^(complete|stopped|error)' && break
  sleep 3
done

echo
echo "Final per-stage results:"
curl -s "$API/api/tuning/$tid/status" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('  status:', d['status'], '| error:', d.get('error'))
for s in d.get('stages',[]):
    print(f\"   stage {s['stage_index']} {s['stage_name']}: {s['status']}  best={s['best_value']}  seed={bool(s.get('seed_checkpoint'))}\")
"
echo "Task id: $tid"
