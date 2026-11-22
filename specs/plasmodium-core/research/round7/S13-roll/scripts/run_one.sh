#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S13(실 끝 점 되감기) 실행 하나 (numpy, 이 폴더의 모델 복사본 model/). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S13-roll
REF=$D/model
scn=$1; seed=$2; tag=$3
H="sup_age=100 dry_edge=1 edge_t=0.3 edge_iso=1 keep_conn=1"    # S12 s12h에서 ret_h, bridge_break만 뺀 것
case "$tag" in
  s13t)  extra="$H bridge_break=0.1 ret_h=1.0 ret_tip=1";;   # 실 끝 칸은 두께 한도 없이 오그라듦
  s13i)  extra="$H bridge_break=0.1 ret_h=100";;             # 모든 오그라듦에 두께 한도 없음
  s13tb) extra="$H bridge_break=1.0 ret_h=1.0 ret_tip=1";;   # s13t + 다리 지키기 문턱을 원래 값으로
  s13ib) extra="$H bridge_break=1.0 ret_h=100";;             # s13i + 같은 것
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
