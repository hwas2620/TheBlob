#!/bin/bash
# [verify] usage: ./runjobs.sh JOBFILE [P]   (lines: NAME<TAB>JSON)
cd "$(dirname "$0")"
export NUMBA_NUM_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs
date +%s > logs/$(basename "$1").start
grep -v '^#' "$1" | grep -v '^$' | tr '\t' '\n' | xargs -d '\n' -n 2 -P ${2:-3} sh -c 'python3 f1.py "$0" "$1" > logs/"$0".log 2>&1; tail -2 logs/"$0".log | cut -c1-400'
date +%s > logs/$(basename "$1").end
echo "DONE $1" >> done.txt
