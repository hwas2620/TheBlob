#!/bin/bash
# 주 세션이 이어서 하는 검증 실행 (새 시드 12, 큰 격자 시드 2). 프로세스 2개 병렬.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
run() { local n=$1; shift; local T0=$(date +%s); python3 n1v.py "$n" "$1" > "log_$n.txt" 2>&1; echo "$n $(( $(date +%s) - T0 ))s" >> timing2.txt; }
(
run v_s12_exact '{"seed":12}'
run v_s12_mg2 '{"seed":12,"solver":"mg","ncyc":2,"vh_every":1}'
run v_s12_mg1 '{"seed":12,"solver":"mg","ncyc":1,"vh_every":1}'
run v_s12_e9asis '{"seed":12,"solver":"mg","ncyc":2,"mg_mass":"scaled"}'
run v_s12_mg3 '{"seed":12,"solver":"mg","ncyc":3,"vh_every":1}'
) &
(
run v_s12_mg2x '{"seed":12,"solver":"mg","ncyc":2,"extrap":0.5,"vh_every":1}'
run v_s11_mg2x '{"seed":11,"solver":"mg","ncyc":2,"extrap":0.5,"vh_every":1}'
run v_384_s2_mg2 '{"seed":2,"N":384,"R_init":24,"solver":"mg","ncyc":2,"check_every":20}'
run v_384_s2_mg2x '{"seed":2,"N":384,"R_init":24,"solver":"mg","ncyc":2,"extrap":0.5,"check_every":20}'
) &
wait
echo BATCH2_DONE >> timing2.txt
