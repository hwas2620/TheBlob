#!/bin/bash
# usage: par2.sh cmdfile   (one shell command per line, at most 2 at a time, single-threaded numerics to avoid oversubscription)
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
n=0
while IFS= read -r line; do
  case "$line" in ''|'#'*) continue;; esac
  bash -c "$line" &
  n=$((n+1)); if [ $n -ge 2 ]; then wait -n; n=$((n-1)); fi
done < "$1"
wait
echo PAR2_DONE
