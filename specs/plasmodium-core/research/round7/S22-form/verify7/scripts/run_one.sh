#!/bin/bash
# verify7 실행 하나: run_one.sh 시나리오 시드 꼬리표 [추가 키=값 …]
# 꼬리표가 v7y 로 시작하면 후보 설정(cand_args.txt) 전체를 붙인다. v7c 로 시작하면 아무것도 붙이지 않는다(대조)
# 추가 키=값: T=800 (slimeall), mgdump=k (주장 9 짝 비교용 실행만. 동역학을 바꾸지 않고 풀이 입력을 저장만 한다)
S=$(cd "$(dirname "$0")" && pwd); V=$(dirname "$S"); M=$(cd "$V/../model" && pwd)
scn=$1; seed=$2; tag=$3; shift 3
name="b_${scn}_s${seed}_${tag}"
free_kb=$(df -k --output=avail "$M" | tail -1)
if [ "$free_kb" -lt 1363148 ]; then echo -e "$name\tSKIPPED_DISK\t$(date -u +%FT%TZ)\t$free_kb" >> "$V/logs/times.tsv"; exit 0; fi
extra=""
case "$tag" in v7y*) extra=$(cat "$S/cand_args.txt");; v7c*) extra="";; *) echo "bad tag $tag"; exit 1;; esac
t0=$(date -u +%FT%TZ)
echo -e "$name\tSTART\t$t0" >> "$V/logs/times.tsv"
cd "$M" && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 export_ref.py b "$scn" "$seed" "$@" $extra tag="$tag" > "$V/logs/$name.log" 2>&1
rc=$?
echo -e "$name\tEND\t$(date -u +%FT%TZ)\trc=$rc" >> "$V/logs/times.tsv"
