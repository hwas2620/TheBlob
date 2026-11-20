#!/bin/bash
# 탐색 실행 하나: run_explore.sh <시나리오> <시드> <꼬리표> [키=값 ...]  (꼬리표는 탐색용만 받는다)
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S3-thin/verify
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
scn=$1; seed=$2; tag=$3; shift 3
case "$tag" in vthAv|vcdv|vthAdiag|vcdvT7|vthAvT7) ;; *) echo "bad tag $tag"; exit 2;; esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
[ -f $REF/runs/$name/metrics.json ] && { echo "skip $name"; exit 0; }
cd $REF; t0=$(date +%s)
python3 export_ref.py b $scn $seed "$@" tag=$tag > $V/logs/$name.log 2>&1
echo "$name rc=$? wall=$(( $(date +%s) - t0 ))s end=$(date -u +%H:%M:%S)" >> $V/logs/done_explore.txt
