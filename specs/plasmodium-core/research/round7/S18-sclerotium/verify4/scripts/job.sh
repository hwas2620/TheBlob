#!/bin/bash
# verify4 실행 하나: 모델을 돌리고 바로 measure.py 로 잰다.  usage: job.sh SCN SEED CFG   (CFG = v4c 대조 | v4w 후보)
set -u
SCN=$1; SEED=$2; CFG=$3
S18=/home/user/TheBlob/specs/plasmodium-core/research/round7/S18-sclerotium
V4=$S18/verify4; MODEL=$S18/model
STOPF=/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/verify4_STOP
CAND="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9"
NAME=b_${SCN}_s${SEED}_${CFG}
LOG=$V4/logs/runs/${NAME}.txt
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
[ -f "$STOPF" ] && exit 0
[ -f "$V4/data/runs/${NAME}.json" ] && exit 0
avail=$(df --output=avail -BM /home/user | tail -1 | tr -dc 0-9)
echo "$(date -u +%FT%TZ) start $NAME avail=${avail}M" >> $V4/logs/disk.txt
if [ "$avail" -lt 1400 ]; then
  bash $V4/scripts/cleanup.sh >> $V4/logs/disk.txt 2>&1
  avail=$(df --output=avail -BM /home/user | tail -1 | tr -dc 0-9)
  echo "$(date -u +%FT%TZ) after cleanup avail=${avail}M" >> $V4/logs/disk.txt
fi
if [ "$avail" -lt 1250 ]; then echo "$(date -u +%FT%TZ) STOP avail=${avail}M before $NAME" | tee -a $V4/logs/disk.txt > "$STOPF"; exit 0; fi
cd $MODEL
if [ "$CFG" = v4w ]; then ARGS="$CAND"; else ARGS=""; fi
t0=$(date +%s)
python3 export_ref.py b $SCN $SEED $ARGS tag=$CFG > $LOG 2>&1
echo "exit=$? wall=$(( $(date +%s) - t0 ))s" >> $LOG
python3 $V4/scripts/measure.py $MODEL/runs/$NAME $V4/data/runs/$NAME.json >> $LOG 2>&1
echo "measure_exit=$?" >> $LOG
