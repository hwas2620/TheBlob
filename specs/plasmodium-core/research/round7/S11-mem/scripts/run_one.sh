#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표>   — 7차 S11(관 기억) 실행 하나 (numpy, S10-tip/model 복사본을 그대로 쓴다. bridge_mem은 원래 있던 규칙). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S11-mem
REF=/home/user/TheBlob/specs/plasmodium-core/research/round7/S10-tip/model
scn=$1; seed=$2; tag=$3
R="sup_age=100 bridge_break=0.1 dry_edge=1 edge_t=0.3 edge_iso=1 ret_h=0.3"   # S10의 s10r
case "$tag" in
  s11m1) extra="$R bridge_mem=1 bridge_mem_tau=100";;   # + 한때 관 굵기 1 이상이던 다리 칸은 기억이 남은 동안 끊지 않음 (잊는 시간 100)
  s11m3) extra="$R bridge_mem=1 bridge_mem_tau=300";;   # 같은 것, 잊는 시간 300
  s11h)  extra="${R/ret_h=0.3/ret_h=1.0}";;              # 오그라듦 두께 한도 0.3 -> 1.0
  s11mh) extra="${R/ret_h=0.3/ret_h=1.0} bridge_mem=1 bridge_mem_tau=300";;   # 둘 다
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
[ $(df --output=avail -m /home/user | tail -1) -lt 2500 ] && { echo "$name skipped: disk" >> $D/logs/done.txt; exit 3; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
