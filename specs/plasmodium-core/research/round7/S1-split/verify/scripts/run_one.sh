#!/bin/bash
# 실행 하나: run_one.sh SCN SEED TAG [키=값 ...]
#   → stage0/ref/runs/b_<SCN>_s<SEED>_<TAG>/ , 로그는 verify/logs/b_<SCN>_s<SEED>_<TAG>.log
# 이미 끝난 실행(metrics.json 이 있음)은 건너뛴다. 기존 폴더를 덮어쓰지 않도록 시드 21 이상과 꼬리표가 있는 이름만 받는다.
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S1-split/verify
scn=$1; seed=$2; tag=$3; shift 3
name=b_${scn}_s${seed}_${tag}
if [ -z "$tag" ] || [ "$seed" -lt 21 ]; then echo "refuse $name (시드 21 이상과 꼬리표가 필요)" >> $V/logs/done.txt; exit 1; fi
if [ -f "$REF/runs/$name/metrics.json" ]; then echo "$name skip (already done)" >> $V/logs/done.txt; exit 0; fi
cd $REF
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
start=$(date +%s)
python3 export_ref.py b $scn $seed "$@" tag=$tag > $V/logs/$name.log 2>&1
rc=$?
end=$(date +%s)
echo "$name rc=$rc wall=$((end-start))s end=$(date -u +%H:%M:%S) opts=[$*]" >> $V/logs/done.txt
exit 0
