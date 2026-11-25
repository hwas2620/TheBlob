#!/bin/bash
# verify7: 끝난 실행을 그때그때 잰다 (times.tsv 의 END 를 따라간다). 모든 일이 끝나면(ALL END) 멈춘다
S=$(cd "$(dirname "$0")" && pwd); V=$(dirname "$S"); M=$(cd "$V/../model" && pwd)
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
done_list="$V/logs/measured.txt"; touch "$done_list"
while true; do
  for n in $(awk -F'\t' '$2=="END" && $1!="ALL" {print $1}' "$V/logs/times.tsv"); do
    grep -qx "$n" "$done_list" && continue
    python3 "$S/measure_run.py" "$M/runs/$n" >> "$V/logs/measure.log" 2>&1 && python3 "$S/measure_extra.py" "$M/runs/$n" >> "$V/logs/measure.log" 2>&1 && echo "$n" >> "$done_list"
  done
  grep -q "^ALL	END" "$V/logs/times.tsv" && [ $(wc -l < "$done_list") -ge $(awk -F'\t' '$2=="END" && $1!="ALL"' "$V/logs/times.tsv" | wc -l) ] && break
  sleep 20
done
echo FOLLOW_DONE >> "$V/logs/measure.log"
