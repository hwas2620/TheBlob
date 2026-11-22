#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S10(끝 오그라듦) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S10-tip
REF=$D/model
scn=$1; seed=$2; tag=$3
B="sup_age=100 bridge_break=0.1 dry_edge=1 edge_t=0.3 edge_iso=1"   # S9의 s9eti (S7 + 가는 이음 지킴 + 가장자리만 마름 + 방향 안 타는 장력 0.3)
F="bridge_break=0.1 dry_edge=1 edge_t=0.3 edge_iso=1"                 # 같은 것에서 S7만 뺌
case "$tag" in
  s10a) extra="$B ret_h=0.3 bridge_h=0.05";;              # + 끝 오그라듦 + 빌 때까지 다리 지킴
  s10b) extra="$B ret_h=0.3 bridge_h=0.05 sup_cap=4";;    # + 같은 것 + S7 늙는 배율 한도 5배
  s10r) extra="$B ret_h=0.3";;                            # + 끝 오그라듦만
  s10n) extra="$F ret_h=0.3 bridge_h=0.05";;              # S7 없이 막·관 규칙만
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
