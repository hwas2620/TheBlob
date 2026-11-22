#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S12(몸이 찢어지지 않음) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S12-conn
REF=$D/model
scn=$1; seed=$2; tag=$3
F="bridge_break=0.1 dry_edge=1 edge_t=0.3 edge_iso=1"     # S9 막 규칙 (가는 이음 지킴, 가장자리만 마름, 방향 안 타는 장력 0.3)
case "$tag" in
  s12h) extra="sup_age=100 $F ret_h=1.0 keep_conn=1";;   # S11의 s11h + 찢어지지 않음
  s12r) extra="sup_age=100 $F ret_h=0.3 keep_conn=1";;   # S10의 s10r + 찢어지지 않음
  s12n) extra="$F ret_h=1.0 keep_conn=1";;               # s12h에서 S7만 뺌
  s12g) extra="keep_conn=1";;                            # 지금 모델 + 찢어지지 않음만
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
