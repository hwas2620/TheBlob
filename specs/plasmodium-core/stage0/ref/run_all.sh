#!/bin/bash
# 기준 자료를 순서대로 만든다 (2개씩 병렬). 로그는 logs/ 에.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs
r() { python3 export_ref.py "$@" > "logs/$(echo "$@" | tr ' ' '_').log" 2>&1; }
( r dumps192; r a12 192 1 mg; r a12 192 2 mg; r a12 384 1 mg ) &
( r a12 192 1 exact; r a12 192 2 exact; r dumps384; r a12 384 2 mg ) &
wait; echo ALL_DONE > logs/done.txt
