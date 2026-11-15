#!/bin/bash
# 큰 격자 3: 몸 전체 수축파(파장을 격자에 비례)를 넣으면 안쪽 정맥이 남고 몸이 한쪽으로 쏠리는가.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
FIX='"wet_rho":0.92,"curv":"gauss","curv_sigma":2.0'
MG='"solver":"mg","ncyc":2,"extrap":0.5,"check_every":50,"food_angle":27,"nsnap":5'
run() { python3 n1g.py "$1" "$2" > "log_$1.txt" 2>&1; echo "$1 done $(date -u +%H:%M:%S)" >> timingG.txt; }
run G512_fix_wave267_s1 "{\"seed\":1,\"N\":512,\"R_init\":32,\"T\":700,\"wave_lambda\":267,\"wave_Trot\":80,$MG,$FIX}" &
run G512_fix_wave133_s1 "{\"seed\":1,\"N\":512,\"R_init\":32,\"T\":700,\"wave_lambda\":133,\"wave_Trot\":80,$MG,$FIX}" &
run G384_fix_wave200_s1 "{\"seed\":1,\"N\":384,\"R_init\":24,\"T\":600,\"wave_lambda\":200,\"wave_Trot\":80,$MG,$FIX}" &
wait; echo BATCHG3_DONE >> timingG.txt
