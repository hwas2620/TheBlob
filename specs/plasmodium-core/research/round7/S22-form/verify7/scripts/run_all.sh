#!/bin/bash
# verify7: 일 목록 전체를 코어 4개로 (오래 걸리는 것부터 적혀 있다)
S=$(cd "$(dirname "$0")" && pwd); V=$(dirname "$S")
echo -e "ALL\tSTART\t$(date -u +%FT%TZ)" >> "$V/logs/times.tsv"
grep -v '^\s*$' "$V/jobs.txt" | xargs -P 4 -L 1 bash "$S/run_one.sh"
echo -e "ALL\tEND\t$(date -u +%FT%TZ)" >> "$V/logs/times.tsv"
