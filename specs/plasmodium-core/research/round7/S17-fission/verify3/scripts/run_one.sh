#!/usr/bin/env bash
# 실행 하나: run_one.sh SCN SEED ARM   (ARM = x17c | x17fs)
# 모델 폴더에서 export_ref.py b 를 코어 하나로 돌린다. 표준 출력은 scratch 로그 폴더(RUNLOG)로 보낸다.
set -u
SCN=$1; SEED=$2; ARM=$3
M=/home/user/TheBlob/specs/plasmodium-core/research/round7/S17-fission/model
RUNLOG=${RUNLOG:-/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/runlogs}
mkdir -p "$RUNLOG"
CAND="keep_conn=4 fis_min=0.03 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2"
if [ "$ARM" = "x17fs" ]; then EXTRA="$CAND"; elif [ "$ARM" = "x17c" ]; then EXTRA=""; else echo "bad arm $ARM"; exit 2; fi
cd "$M" || exit 2
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
s=$(date +%s)
python3 export_ref.py b "$SCN" "$SEED" $EXTRA tag=$ARM > "$RUNLOG/b_${SCN}_s${SEED}_${ARM}.out" 2>&1
rc=$?
echo "$SCN $SEED $ARM rc=$rc sec=$(( $(date +%s) - s ))" >> "$RUNLOG/finished.txt"
