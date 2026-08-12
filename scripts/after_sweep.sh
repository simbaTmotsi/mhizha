#!/usr/bin/env bash
# BUILD TIME. Overnight chain: wait for the lm-eval sweep, then build the composite and
# execute the pre-registered cluster rule, then run O-13. Nothing here needs anyone awake.
#
# ORDER IS LOAD-BEARING (COMPETITION.md section 9g)
# -------------------------------------------------
#   1. sweep finishes
#   2. composite + tie cluster           <- completes before any qualitative work
#   3. if cluster > 3: re-run tied candidates at a higher limit, re-form the cluster
#      (this is PRE-REGISTERED in section 9f-pre, so it needs no judgement at 3am)
#   4. O-13 attribution reps             <- after the composite, never delaying it
#
# Everything is SERIAL. Step 4 measures run-to-run variance, so anything running beside it
# would corrupt exactly the quantity it exists to measure. Step 3 would do the same.
#
# Nothing here is latency-bearing: it is all llama-bench and lm-eval on a shared VPS.
# The three-arm qualitative pass is deliberately NOT chained, because it must run on the
# O-12 physical machine (section 9g).

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

LOG="${LOG:-/tmp/after_sweep.log}"
CLUSTER_RERUN_LIMIT="${CLUSTER_RERUN_LIMIT:-150}"
O13_REPS="${O13_REPS:-6}"
O13_CANDIDATE="${O13_CANDIDATE:-qwen3.5-0.8b-q4_k_m}"

say() { echo "[$(date -u +%H:%M:%SZ)] $*" | tee -a "$LOG"; }

say "waiting for the lm-eval sweep to finish"
while pgrep -f "lmeval_mix.py --candidates all" > /dev/null 2>&1; do sleep 60; done
while docker ps --format '{{.Image}}' | grep -q adtc; do sleep 30; done
sleep 20
say "sweep finished"

# ---- step 2: composite ------------------------------------------------------------
say "building composite"
python3 scripts/composite.py --auto >> "$LOG" 2>&1
COMPOSITE_RC=$?
if [[ $COMPOSITE_RC -ne 0 ]]; then
  say "composite FAILED (exit $COMPOSITE_RC). Stopping: the cluster rule needs a table."
  exit 1
fi

latest_composite() { ls -td runs/*_composite 2>/dev/null | head -1; }
CDIR="$(latest_composite)"
CLUSTER=$(python3 -c "
import json,sys
d=json.load(open('$CDIR/composite.json'))
print(len(d['finalists']))
" 2>/dev/null || echo 0)
say "composite built: $CDIR, tie cluster = $CLUSTER"

# ---- step 3: pre-registered cluster rule -------------------------------------------
if [[ "$CLUSTER" -gt 3 ]]; then
  TIED=$(python3 -c "
import json
d=json.load(open('$CDIR/composite.json'))
print(','.join(d['finalists']))
")
  say "cluster > 3: re-running TIED candidates only at limit $CLUSTER_RERUN_LIMIT (pre-registered, section 9f-pre)"
  say "  tied: $TIED"
  python3 scripts/lmeval_mix.py --candidates "$TIED" \
      --limit "$CLUSTER_RERUN_LIMIT" --image adtc-profiler:latest \
      --tag "cluster-rerun" >> "$LOG" 2>&1
  RERUN_RC=$?
  if [[ $RERUN_RC -eq 0 ]]; then
    say "re-run complete, re-forming the cluster"
    python3 scripts/composite.py --auto >> "$LOG" 2>&1
    CDIR="$(latest_composite)"
    CLUSTER=$(python3 -c "
import json
d=json.load(open('$CDIR/composite.json'))
print(len(d['finalists']))
" 2>/dev/null || echo "$CLUSTER")
    say "re-formed: $CDIR, tie cluster = $CLUSTER"
  else
    say "cluster re-run FAILED (exit $RERUN_RC). Keeping the limit-50 cluster."
  fi
else
  say "cluster <= 3: no re-run needed, straight to the three-arm pass (on O-12 hardware)"
fi

# ---- step 4: O-13, strictly after the composite -------------------------------------
say "starting O-13 attribution: $O13_REPS reps, warmup 1, candidate $O13_CANDIDATE"
python3 scripts/bench_screened.py --candidates "$O13_CANDIDATE" \
    --reps "$O13_REPS" --warmup 1 --max-steal 1.0 --tag o13 >> "$LOG" 2>&1
say "O-13 complete"

# ---- summary ------------------------------------------------------------------------
say "chain finished. Figures now available:"
python3 scripts/report_figures.py >> "$LOG" 2>&1
say "  composite : $CDIR"
say "  cluster   : $CLUSTER"
say "  next      : three-arm pass on the O-12 physical machine (NOT run here)"
