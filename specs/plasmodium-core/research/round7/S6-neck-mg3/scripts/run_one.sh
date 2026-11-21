#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S6 실행 하나 (numpy). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S6-neck-mg3
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
scn=$1; seed=$2; tag=$3
case "$tag" in
  s6c)   extra="ncyc=3";;                                  # 대조: 지금 모델 (GB) + 압력 풀이 3사이클
  s6nk)  extra="ncyc=3 neck_keep=1 curv_gain=16";;         # 이음 지키기 + 표면 장력 두 배 (S5의 s5nkcv) + 3사이클
  s6nk8) extra="ncyc=3 neck_keep=1";;                      # 이음 지키기만 (표면 장력은 지금 값 8) + 3사이클
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
