#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>  — S7 독립 검증 실행 하나 (numpy). 이미 있으면 건너뛴다
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S7-merge/verify
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
scn=$1; seed=$2; tag=$3
case "$tag" in
  v7c)  extra="";;                         # 대조: 관문 B 설정 그대로
  v7k)  extra="sup_age=100";;              # 후보
  v7cf) extra="gm_every=4";;               # 진단: 대조, 4 시간마다 저장
  v7kf) extra="sup_age=100 gm_every=4";;   # 진단: 후보, 4 시간마다 저장
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $V/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $V/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s $(date -u +%H:%M:%S)" >> $V/logs/done.txt
