#!/bin/bash
# 큰 격자 2: 나이 수축 시간을 몸 크기에 비례시키면(tau_a = 50 * N/192) 정맥이 몸 안쪽까지 남는가. batchG 가 끝난 뒤 2개 병렬.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
while ! grep -q BATCHG_DONE timingG.txt 2>/dev/null; do python3 -c "import time; time.sleep(5)"; done
FIX='"wet_rho":0.92,"curv":"gauss","curv_sigma":2.0'
MG='"solver":"mg","ncyc":2,"extrap":0.5,"check_every":50,"food_angle":27,"nsnap":5'
run() { python3 n1g.py "$1" "$2" > "log_$1.txt" 2>&1; echo "$1 done $(date -u +%H:%M:%S)" >> timingG.txt; }
(
run G512_fix_tau133_s1 "{\"seed\":1,\"N\":512,\"R_init\":32,\"T\":700,\"tau_a\":133,$MG,$FIX}"
run G384_fix_tau100_s1 "{\"seed\":1,\"N\":384,\"R_init\":24,\"T\":600,\"tau_a\":100,$MG,$FIX}"
) &
(
run G512_fix_tau133_s2 "{\"seed\":2,\"N\":512,\"R_init\":32,\"T\":700,\"tau_a\":133,$MG,$FIX}"
run G384_fix_s1 "{\"seed\":1,\"N\":384,\"R_init\":24,\"T\":600,$MG,$FIX}"
) &
wait; echo BATCHG2_DONE >> timingG.txt
