#!/bin/bash
# 실행 하나: run_job.sh SCN SEED TAG   (jobs.txt 한 줄). 시간·디스크 지킴을 거친 뒤 export_ref.py b 를 돌린다
set -u
SCN=$1; SEED=$2; TAG=$3
V6=$(cd "$(dirname "$0")/.." && pwd); MODEL=$(cd "$V6/../model" && pwd)
LOG=$V6/data/joblog.tsv; NAME=b_${SCN}_s${SEED}_${TAG}
CAND="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9 scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50 ret_tipfree=1 sup_ramp=100 scl_star=1 scl_freeze=1 scl_rstep=10 scl_Hramp=200 tip_home=1 tri_rnd=1 mg_deep=1"
EXTRA=""
[ "$SCN" = "slimeall" ] && EXTRA="T=800"
SET=""
[ "$TAG" = "v6g" ] && SET="$CAND"
now=$(date -u +%s)
if [ -f "$V6/logs/deadline" ] && [ "$now" -gt "$(cat $V6/logs/deadline)" ]; then
  printf "%s\t%s\tSKIP_TIME\t%s\t-\t-\n" "$NAME" "$(date -u +%FT%TZ)" "-" >> $LOG; exit 0; fi
avail=$(df --output=avail -k /home/user | tail -1)
if [ "$avail" -lt 1363149 ]; then
  printf "%s\t%s\tSKIP_DISK\t%s\t-\t-\n" "$NAME" "$(date -u +%FT%TZ)" "$avail" >> $LOG; exit 0; fi
start=$(date -u +%FT%TZ)
cd "$MODEL" && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 export_ref.py b "$SCN" "$SEED" $SET $EXTRA tag=$TAG > "$V6/logs/$NAME.log" 2>&1
rc=$?
printf "%s\t%s\tDONE\t%s\t%s\t%s\n" "$NAME" "$start" "$rc" "$(date -u +%FT%TZ)" "$(( $(date -u +%s) - now ))" >> $LOG
