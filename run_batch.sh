#!/bin/bash
# Run N independent drift runs (default 10), two at a time, then score them.
# Usage: ./run_batch.sh [N] [rounds]   Needs: pip install -r requirements.txt, claude CLI signed in.
cd "$(dirname "$0")"
N=${1:-10}; ROUNDS=${2:-20}; PY=${PYTHON:-python3}
export LINTEGRITY_TRANSLATE_MODEL=${LINTEGRITY_TRANSLATE_MODEL:-claude-opus-5-5}
mkdir -p results
one() {  # one run; on a crash, resume once from its partial logs
  [ -f "results/batch-$1/results.json" ] && return 0   # already finished
  "$PY" -u lintegrity/handoff_drift.py "$ROUNDS" --run "batch-$1" --resume > "results/batch-$1.log" 2>&1 ||
    "$PY" -u lintegrity/handoff_drift.py "$ROUNDS" --run "batch-$1" --resume >> "results/batch-$1.log" 2>&1
}
for i in $(seq 1 "$N"); do
  one "$i" &
  (( i % 2 == 0 )) && wait
done
wait
"$PY" lintegrity/score_batch.py
