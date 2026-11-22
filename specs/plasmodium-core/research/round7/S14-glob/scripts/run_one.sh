#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S14(오그라듦도 몸 전체 연결로) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S14-glob
REF=$D/model
scn=$1; seed=$2; tag=$3
case "$tag" in
  s14c)  extra="";;                                                                         # 지금 모델 (먹이·이주 확인의 대조)
  s13ib) extra="sup_age=100 dry_edge=1 edge_t=0.3 edge_iso=1 keep_conn=1 ret_h=100";;       # S13 넘김 후보 (먹이·이주 확인용)
  s14g)  extra="sup_age=100 dry_edge=1 edge_t=0.3 edge_iso=1 keep_conn=1 ret_h=100 ret_glob=1";;   # S13 s13ib + 오그라듦도 전체 연결로
  s14g1) extra="sup_age=100 dry_edge=1 edge_t=0.3 edge_iso=1 keep_conn=1 ret_h=1.0 ret_glob=1";;   # 같은 것, 오그라듦 두께 한도 1.0
  s14gn) extra="dry_edge=1 edge_t=0.3 edge_iso=1 keep_conn=1 ret_h=100 ret_glob=1";;               # s14g에서 S7을 뺌 (줄이기 시험)
  s14gd) extra="sup_age=100 keep_conn=1 ret_h=100 ret_glob=1";;                                    # s14g에서 S9 막 규칙(가장자리만 마름, 장력)을 뺌 (줄이기 시험)
  s14k)  extra="keep_conn=1 ret_h=100 ret_glob=1";;                                                # [결승 뒤 진단] s14gd에서 S7을 뺌
  s14s)  extra="sup_age=100";;                                                                     # [결승 뒤 진단] S7만
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
