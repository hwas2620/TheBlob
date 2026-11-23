#!/bin/bash
# usage: run_one.sh SCENARIO SEED ARM     ARM = ctrl | cand | dense
set -u
SCN=$1; SEED=$2; ARM=$3
HERE=$(cd "$(dirname "$0")" && pwd)
MODEL=$(cd "$HERE/../../model" && pwd)
LOGD="$HERE/../logs/runs"; mkdir -p "$LOGD"
CAND="keep_conn=3 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05"
case $ARM in
  ctrl)  ARGS="tag=w16c" ;;
  cand)  ARGS="$CAND tag=w16gm" ;;
  dense) ARGS="$CAND gm_every=0.2 vsave=0 tag=w16gm_dense" ;;
  *) echo "bad arm $ARM"; exit 1 ;;
esac
cd "$MODEL"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
T0=$(date +%s)
python3 export_ref.py b "$SCN" "$SEED" $ARGS > "$LOGD/${SCN}_s${SEED}_${ARM}.log" 2>&1
RC=$?
echo "$SCN $SEED $ARM rc=$RC sec=$(( $(date +%s) - T0 ))" >> "$LOGD/finished.txt"
