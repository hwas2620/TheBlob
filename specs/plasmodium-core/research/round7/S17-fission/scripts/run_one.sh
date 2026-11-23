#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S17(갈라짐 허용 + 부스러기 막기) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S17-fission
REF=$D/model
scn=$1; seed=$2; tag=$3
G="sup_age=100 sup_cap=2 keep_conn=3 ret_h=100 ret_glob=1 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1"   # S16 둘째 후보 s16gm + 음수 고침
case "$tag" in
  s17c)  extra="";;                                   # 지금 모델
  s17g)  extra="$G";;                                 # S16 후보 + 음수 고침 (찢어지지 않음)
  s17f)  extra="${G/keep_conn=3/keep_conn=4} fis_min=0.15";;   # 갈라짐 허용: 닿은 조각이 모두 몸 부피 15% 이상이면 끊어지게 둔다
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1200 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
