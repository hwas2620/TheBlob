#!/bin/bash
# usage: ./runjobs.sh JOBFILE   (lines: NAME<TAB>JSON) ; at most 2 processes, 2 threads each
cd "$(dirname "$0")"
export NUMBA_NUM_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
mkdir -p logs
grep -v '^#' "$1" | grep -v '^$' | tr '\t' '\n' | xargs -d '\n' -n 2 -P 2 sh -c 'python3 n3.py "$0" "$1" > logs/"$0".log 2>&1; tail -3 logs/"$0".log | cut -c1-400'
