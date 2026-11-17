#!/bin/bash
# 조대 레벨을 일찍 끊어도 되는지 (시드 12, 2사이클, 매 스텝 유량 오차). 기준: 전체 계층 0.105
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
run() { python3 n1v.py "$1" "$2" > "log_$1.txt" 2>&1; echo "$1 done" >> timing3.txt; }
run v_s12_mg2_nmin12 '{"seed":12,"solver":"mg","ncyc":2,"vh_every":1,"nmin":12,"nc":4}' &
run v_s12_mg2_nmin24 '{"seed":12,"solver":"mg","ncyc":2,"vh_every":1,"nmin":24,"nc":4}' &
run v_s12_mg2_nmin48 '{"seed":12,"solver":"mg","ncyc":2,"vh_every":1,"nmin":48,"nc":4}' &
run v_s12_mg2_nmin24_nc8 '{"seed":12,"solver":"mg","ncyc":2,"vh_every":1,"nmin":24,"nc":8}' &
wait; echo BATCH3_DONE >> timing3.txt
