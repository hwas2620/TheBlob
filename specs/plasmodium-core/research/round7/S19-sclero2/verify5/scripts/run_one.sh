#!/bin/bash
# verify5: 실행 하나 (모델 → 측정 → 필요 없는 저장 상태 지우기). usage: run_one.sh SCN SEED ARM   (ARM: c = 대조 v5c, y = 후보 v5y)
# 이미 끝난 것(metrics.json 과 측정 JSON 이 있음)은 건너뛴다. 끝나지 않은 실행 폴더(metrics.json 없음)는 지우고 다시 돈다(실행은 결정적).
set -u
SCN=${1:?}; SEED=${2:?}; ARM=${3:?}
S19=/home/user/TheBlob/specs/plasmodium-core/research/round7/S19-sclero2
M=$S19/model; V=$S19/verify5
CAND="keep_conn=4 fis_min=0.10 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2 hang_C=20 scl_f=0.02 scl_H=3 scl_age=5 scl_C=20 scl_disc=1 scl_thin=0 sup_scent=2 scl_dlim=1 scl_bk=2 scl_shmin=1e-9 scl_stay=1 scl_rundry=1 dlim_all=1 scl_notube=1 t_eat0=50"
case "$ARM" in
  y) EXTRA="$CAND"; TAG=v5y ;;
  c) EXTRA=""; TAG=v5c ;;
  *) echo "bad arm $ARM"; exit 2 ;;
esac
NAME=b_${SCN}_s${SEED}_${TAG}
RD=$M/runs/$NAME
OUTJ=$V/data/runs/$NAME.json
mkdir -p "$V/logs/runs" "$V/data/runs"
LOG=$V/logs/runs/$NAME.log
if [ -f "$RD/metrics.json" ] && [ -f "$OUTJ" ]; then exit 0; fi
AV=$(df --output=avail -B1M /home/user | tail -1 | tr -d ' ')
if [ "$AV" -lt 1300 ]; then echo "$(date -u +%FT%TZ) LOWDISK ${AV}M skip $NAME" >> "$V/logs/lowdisk.txt"; exit 1; fi
if [ -d "$RD" ] && [ ! -f "$RD/metrics.json" ]; then rm -rf -- "${RD:?}"; fi
cd "$M" || exit 3
if [ ! -f "$RD/metrics.json" ]; then
  echo "$(date -u +%FT%TZ) start $NAME" >> "$V/logs/progress.txt"
  env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 export_ref.py b "$SCN" "$SEED" $EXTRA tag=$TAG > "$LOG" 2>&1
  [ -f "$RD/metrics.json" ] || { echo "$(date -u +%FT%TZ) FAIL $NAME" >> "$V/logs/progress.txt"; exit 4; }
fi
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python3 "$V/scripts/measure.py" "$RD" "$OUTJ" >> "$LOG" 2>&1 || { echo "$(date -u +%FT%TZ) MEASUREFAIL $NAME" >> "$V/logs/progress.txt"; exit 5; }
# 쓰지 않는 저장 상태: 상태 묶음(state_t*.npz), 고정 잡음(G_edges.npy), 간선 나이(eage.npy)
for f in "$RD"/state_t*.npz; do [ -e "$f" ] && rm -f -- "${f:?}"; done
for f in G_edges.npy eage.npy; do rm -f -- "${RD:?}/${f:?}"; done
echo "$(date -u +%FT%TZ) done $NAME $(du -sm "$RD" | cut -f1)M avail=$(df --output=avail -B1M /home/user | tail -1 | tr -d ' ')M" >> "$V/logs/progress.txt"
