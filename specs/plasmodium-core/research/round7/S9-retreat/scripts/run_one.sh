#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S9(막이 가장자리부터 물러남) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S9-retreat
REF=$D/model
scn=$1; seed=$2; tag=$3
B="sup_age=100 bridge_break=0.1"                          # S8의 s8k1: S7 후보 + 가는 이음까지 지킴
case "$tag" in
  s9c)   extra="";;                                       # 지금 모델 그대로 (관문 B 설정)
  s9b)   extra="$B";;                                     # 바탕 (= s8k1)
  s9e)   extra="$B dry_edge=1";;                          # + 가장자리만 마름
  s9t)   extra="$B edge_t=0.3";;                          # + 가장자리 장력 0.3
  s9et)  extra="$B dry_edge=1 edge_t=0.3";;               # + 둘 다
  s9et6) extra="$B dry_edge=1 edge_t=0.6";;               # + 둘 다, 장력 0.6
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
