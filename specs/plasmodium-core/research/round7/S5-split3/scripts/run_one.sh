#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S5 실행 하나 (numpy). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S5-split3
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
scn=$1; seed=$2; tag=$3
case "$tag" in
  s5c)  extra="";;                                                   # 대조: 지금 모델 (GB)
  s5up) extra="fan_comp=1 fan_gain=3 fan_slow=0.5 fan_up=0.001";;   # 앞머리 경쟁, 냄새 오르막 앞머리는 면제
  s5cv) extra="curv_gain=16";;                                       # 표면 장력 두 배
  s5b)  extra="beta=0.1";;                                           # 관 벽 두께 두 배
  s5rd) extra="rate_down=0.01";;                                     # 관이 가늘어지는 빠르기 1/5
  s5w)  extra="wall_tau=300";;                                       # 관 벽이 굵기를 기억 (300 시간)
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
