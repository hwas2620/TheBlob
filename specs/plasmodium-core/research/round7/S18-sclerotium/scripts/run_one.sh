#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S18(균핵 + 매달린 조각 되돌리기) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S18-sclerotium
REF=$D/model
scn=$1; seed=$2; tag=$3
F="keep_conn=4 fis_min=0.03 ret_h=100 ret_glob=1 sup_age=100 sup_cap=2 sup_h=0.6 sup_fed=50 ret_fed=50 hang_age=4 sup_min=0.05 neg_fill_global=1 sup_size=2"   # S17 후보 s17fs
case "$tag" in
  s18c)  extra="";;                                                     # 지금 모델
  s18f)  extra="$F";;                                                   # S17 후보 그대로
  s18s)  extra="$F scl_f=0.02";;                                        # + 균핵 (갇히면 뻗기를 멈추고 한 덩어리로)
  s18a)  extra="${F/fis_min=0.03/fis_min=0.10} hang_C=20 scl_f=0.02";;   # + 갈라짐 문턱 10%, 지켜진 실 전도도 20, 균핵
  s18b)  extra="${F/fis_min=0.03/fis_min=0.10} hang_C=20 scl_f=0.02 scl_H=3 scl_age=5";;   # s18a + 균핵 핵(늙지 않고 쉬는 두께 3배) + 나머지 5배 빨리 늙음
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 1200 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
