#!/bin/bash
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
T0=$(date +%s)
python3 n1v.py v_s11_exact '{"seed":11,"ckpt_steps":[1000,2000,3000]}' > log_v_s11_exact.txt 2>&1; echo "s11_exact $(( $(date +%s) - T0 ))s" >> timing.txt
T1=$(date +%s)
python3 n1v.py v_s11_mg2 '{"seed":11,"solver":"mg","ncyc":2,"vh_every":1,"ckpt_steps":[1000,2000,3000]}' > log_v_s11_mg2.txt 2>&1; echo "s11_mg2 $(( $(date +%s) - T1 ))s" >> timing.txt
echo BATCH1_DONE >> timing.txt
