#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S7 거르기 실행 하나 (numpy). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S7-merge
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
scn=$1; seed=$2; tag=$3
case "$tag" in
  s6c)   extra="ncyc=3";;                     # 거르기 대조 (S6과 같음)
  s7c)   extra="";;                           # 결승 대조: 지금 모델 그대로 (관문 B 설정, 2사이클)
  s7k)   extra="sup_age=100";;                # 결승 후보: 지금 모델 + 흐름으로 정하는 부채 경쟁
  s7b20)  extra="ncyc=3 sup_age=20";;         # 2차: 경계 흐름으로 잰 규칙, 보통
  s7b100) extra="ncyc=3 sup_age=100";;        # 2차: 같은 규칙, 세게
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1000 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
