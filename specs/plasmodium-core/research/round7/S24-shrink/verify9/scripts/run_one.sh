#!/bin/bash
# verify9: 일 하나 (jobs.txt 한 줄 = export_ref.py 인자) 를 한 코어로 돌린다.
# usage: run_one.sh "b SCN SEED [키=값 ...] tag=TAG"
M=/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/model
L=/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/verify9/logs
args="$1"
set -- $args
tag=$(echo "$args" | grep -o 'tag=[^ ]*' | cut -d= -f2)
name="b_$2_s$3_${tag}"
avail=$(df --output=avail -k / | tail -1)
if [ "$avail" -lt 1363149 ]; then echo "SKIP low disk ${avail}k $(date -u +%FT%TZ)" > "$L/$name.skip"; exit 0; fi   # 1.3G 아래면 새로 시작하지 않는다
date -u +%FT%TZ > "$L/$name.start"
cd "$M" && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 export_ref.py $args > "$L/$name.log" 2>&1
echo "$? $(date -u +%FT%TZ)" > "$L/$name.done"
