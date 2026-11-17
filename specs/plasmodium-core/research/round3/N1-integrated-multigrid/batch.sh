#!/bin/bash
# usage: batch.sh name1 'json1' name2 'json2' ...   (runs 2 at a time)
cd "$(dirname "$0")"; export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMBA_NUM_THREADS=2 MKL_NUM_THREADS=2
while [ $# -gt 0 ]; do
  python3 n1.py "$1" "$2" > "log_$1.txt" 2>&1 &
  if [ $# -gt 2 ]; then python3 n1.py "$3" "$4" > "log_$3.txt" 2>&1 & shift 2; fi
  shift 2; wait
done
echo BATCH_DONE
