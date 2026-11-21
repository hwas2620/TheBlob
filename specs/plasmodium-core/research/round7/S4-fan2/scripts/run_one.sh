#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표 vs4c|vs4k>   — 7차 S4 실행 하나 (numpy). 이미 있으면 건너뛴다
D=/home/user/TheBlob/specs/plasmodium-core/research/round7/S4-fan2
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
scn=$1; seed=$2; tag=$3
case "$tag" in vs4c) extra="";; vs4k) extra="fan_comp=1 fan_gain=3 fan_slow=0.5 fan_food=4 fan_scent=0.01";; *) echo "bad tag"; exit 2;; esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && exit 0
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed $extra tag=$tag > $D/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s" >> $D/logs/done.txt
