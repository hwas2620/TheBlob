#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S16(아령: 찢어지지 않음이 남긴 실) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S16-dumbbell
REF=$D/model
scn=$1; seed=$2; tag=$3
K="sup_age=100 sup_cap=2 keep_conn=2 ret_h=100 ret_glob=1"            # S15 후보 s15dc
case "$tag" in
  s16c)  extra="";;                       # 지금 모델
  s16k)  extra="$K";;                     # S15 후보 그대로
  s16h)  extra="$K sup_h=0.6";;           # S7이 굵은 덩이를 h >= 0.6으로 본다 (관 두께 상한 0.5 위: 실은 굵다에 들지 않는다)
  s16k0) extra="keep_conn=2 ret_h=100 ret_glob=1";;   # S7 없이 찢어지지 않음 + 오그라듦만 (S15의 s15k)
  s16hc) extra="sup_age=100 sup_cap=1 keep_conn=2 ret_h=100 ret_glob=1 sup_h=0.6";;   # s16h에서 S7의 늙는 배율을 2배까지로 (경쟁을 약하게)
  s16hr) extra="sup_age=100 sup_cap=2 keep_conn=3 ret_h=100 ret_glob=1 sup_h=0.6";;   # s16h + 고리 풀기 (keep_conn=3)
  s16kr) extra="sup_age=100 sup_cap=2 keep_conn=3 ret_h=100 ret_glob=1";;              # S15 후보 + 고리 풀기
  s16k0r) extra="keep_conn=3 ret_h=100 ret_glob=1";;                                  # S7 없이 + 고리 풀기
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
