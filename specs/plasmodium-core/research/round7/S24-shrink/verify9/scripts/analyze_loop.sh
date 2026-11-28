#!/bin/bash
# 끝난 실행을 차례로 측정한다 (실행과 나란히). 모든 일이 끝나고 다 측정하면 logs/ANALYZE_DONE
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/verify9; RUNS=$V/../model/runs
while true; do
  for d in $V/logs/*.done; do
    n=$(basename $d .done); [ -f $V/out/run_$n.json ] && continue
    python3 $V/scripts/analyze.py $RUNS/$n >> $V/logs/analyze.log 2>&1 || echo "FAIL $n" >> $V/logs/analyze.log
  done
  if [ -f $V/logs/ALL_DONE ]; then
    left=0; for d in $V/logs/*.done; do n=$(basename $d .done); [ -f $V/out/run_$n.json ] || left=1; done
    [ $left = 0 ] && { date -u +%FT%TZ > $V/logs/ANALYZE_DONE; exit 0; }
  fi
  sleep 30
done
