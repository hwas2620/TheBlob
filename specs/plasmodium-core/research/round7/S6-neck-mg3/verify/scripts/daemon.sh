#!/bin/bash
# 끝난 실행을 채점하고(vextract.py), THIN_ENABLED 가 있으면 long 이외 실행을 솎는다(thin.py). 배치가 끝나면 한 번 더 돌고 멈춘다.
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S6-neck-mg3/verify
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
last=0
while true; do
  [ -f $V/logs/all_done.txt ] && last=1
  for name in $(grep ' END ' $V/logs/done.txt | awk '{print $1}'); do
    if [ ! -f $V/data/x_$name.json ] || [ ! -f $V/data/bmet_$name.json ]; then
      python3 $V/scripts/vextract.py $REF/runs/$name >> $V/logs/extract.log 2>&1 || echo "$name EXTRACT_FAIL $(date -u +%FT%TZ)" >> $V/logs/extract.log
    fi
    if [ -f $V/THIN_ENABLED ] && [ -f $V/data/x_$name.json ] && [ -f $V/data/bmet_$name.json ] && [[ $name != b_long_* ]] && [ ! -f $V/data/thinned_$name ]; then
      python3 $V/scripts/thin.py $REF/runs/$name >> $V/logs/thin.log 2>&1 && touch $V/data/thinned_$name
    fi
  done
  [ $last = 1 ] && break
  sleep 30
done
echo DAEMON_DONE > $V/logs/daemon_done.txt
