#!/bin/bash
# verify7: 내 실행 폴더(꼬리표 v7c, v7y, v7cm, v7ym)를 모두 재고(코어 4개), mgdump 실행을 짝 비교하고, 판정한다
S=$(cd "$(dirname "$0")" && pwd); V=$(dirname "$S"); M=$(cd "$V/../model" && pwd)
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
ls -d "$M"/runs/b_*_v7c "$M"/runs/b_*_v7y "$M"/runs/b_*_v7cm "$M"/runs/b_*_v7ym 2>/dev/null | xargs -P 4 -n 1 python3 "$S/measure_run.py"
python3 "$S/replay.py" "$V/data/replay.json" $(ls -d "$M"/runs/b_*_v7cm "$M"/runs/b_*_v7ym 2>/dev/null)
python3 "$S/judge.py"
