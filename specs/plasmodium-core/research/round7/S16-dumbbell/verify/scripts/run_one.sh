#!/bin/bash
# usage: run_one.sh SCN SEED TAG     (TAG = v16c | v16gh | v16ghd)
# 모델 폴더에서 export_ref.py b 를 돌린다. 로그는 verify/logs/runs/ 에, 끝난 줄은 status.txt 에.
V=$(cd "$(dirname "$0")/.." && pwd); M="$V/../model"
SCN=$1; SEED=$2; TAG=$3
CAND="keep_conn=3 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4"
case "$TAG" in
  v16c)   EXTRA="" ;;
  v16gh)  EXTRA="$CAND" ;;
  v16ghd) EXTRA="$CAND gm_every=0.1 vsave=0" ;;
  *) echo "bad tag $TAG"; exit 2 ;;
esac
cd "$M" || exit 2
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
t0=$(date +%s)
python3 export_ref.py b "$SCN" "$SEED" $EXTRA tag="$TAG" > "$V/logs/runs/b_${SCN}_s${SEED}_${TAG}.log" 2>&1
rc=$?
echo "$rc $SCN $SEED $TAG $(( $(date +%s) - t0 ))s $(df -BM --output=avail / | tail -1)" >> "$V/logs/runs/status.txt"
