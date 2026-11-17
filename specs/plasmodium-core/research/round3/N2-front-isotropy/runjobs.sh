#!/bin/bash
# usage: ./runjobs.sh JOBFILE [P]  (lines: NAME<TAB>JSON) ; P parallel processes, 1 thread each
cd "$(dirname "$0")"
export NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs
grep -v '^#' "$1" | grep -v '^$' | tr '\t' '\n' | xargs -d '\n' -n 2 -P ${2:-2} sh -c 'python3 n2.py "$0" "$1" > logs/"$0".log 2>&1; tail -1 logs/"$0".log | cut -c1-300'
echo "DONE $1" >> done.txt
