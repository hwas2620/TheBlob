#!/bin/bash
# 큰 격자: 통합 모델 + 멀티그리드(2사이클 + 외삽 0.5) + 고친 젖음 판정, 구배 방향 27도. 2개 병렬.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
FIX='"wet_rho":0.92,"curv":"gauss","curv_sigma":2.0'
MG='"solver":"mg","ncyc":2,"extrap":0.5,"check_every":50,"food_angle":27,"nsnap":5'
run() { python3 n1g.py "$1" "$2" > "log_$1.txt" 2>&1; echo "$1 done $(date -u +%H:%M:%S)" >> timingG.txt; }
(
run G768_fix_s1 "{\"seed\":1,\"N\":768,\"R_init\":48,\"T\":800,$MG,$FIX}"
run G768_base_s1 "{\"seed\":1,\"N\":768,\"R_init\":48,\"T\":800,$MG}"
) &
(
run G512_fix_s1 "{\"seed\":1,\"N\":512,\"R_init\":32,\"T\":700,$MG,$FIX}"
run G768_fix_s2 "{\"seed\":2,\"N\":768,\"R_init\":48,\"T\":800,$MG,$FIX}"
) &
wait; echo BATCHG_DONE >> timingG.txt
