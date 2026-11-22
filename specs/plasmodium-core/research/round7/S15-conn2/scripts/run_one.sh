#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S15(찢어짐 틈 막기 + 먹이 놓침) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S15-conn2
REF=$D/model
scn=$1; seed=$2; tag=$3
case "$tag" in
  s15c)  extra="";;                                                     # 지금 모델
  s15d)  extra="sup_age=100 keep_conn=2 ret_h=100 ret_glob=1";;         # S14 결승 후보 s14gd + 찢어짐 틈 막기 (마르는 칸 덩어리 단위 판단)
  s15k)  extra="keep_conn=2 ret_h=100 ret_glob=1";;                     # s15d에서 S7(흐름 경쟁)을 뺌
  s15dc) extra="sup_age=100 sup_cap=2 keep_conn=2 ret_h=100 ret_glob=1";;   # s15d에서 S7의 늙는 배율을 3배까지로 묶음
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
