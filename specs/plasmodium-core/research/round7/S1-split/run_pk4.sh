#!/bin/bash
# 묶음 4 (bridge_mem=50 + sat_k=0.4 + sat_scent=0.5 + crumb_dry=1) 로 관문 B 의 판정에 쓰는 실행 전부 (먼 먹이 넷 시드 1~3 과 가까운 먹이 셋 시드 4 는 이미 돌렸다)
cd /home/user/TheBlob/specs/plasmodium-core/stage0/ref
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
LOG=/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/pkg_logs
O="bridge_mem=50 sat_k=0.4 sat_scent=0.5 crumb_dry=1"
r() { python3 export_ref.py b "$@" $O tag=pk4 > "$LOG/pk4all_$(echo "$@" | tr ' ' '_').log" 2>&1; }
rn() { python3 export_ref.py b "$1" "$2" N=384 $O tag=N384pk4 > "$LOG/pk4all_$1_$2_N384.log" 2>&1; }
( for s in 1 2 3 5 6; do r food3 $s; done; for s in 1 2 3; do r asym3 $s; done; r long 1 ) &
( for s in 1 2 3 4 5; do r mig $s; done; for s in 1 2 3; do r slimehalf $s; r slimeall $s; done; r long 2 ) &
( for d in dir0 dir13 dir27 dir34 dir45; do r $d 1; r $d 2; done; for s in 1 2 3; do r mig256 $s; done; r mig2x 1; r mig2x 2 ) &
( for s in 1 2 3; do r food3_256 $s; done; rn food3 1; rn mig 1; rn mig 2 ) &
wait
echo done > $LOG/pk4all_done.txt
