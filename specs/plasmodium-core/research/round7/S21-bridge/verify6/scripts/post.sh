#!/bin/bash
# 실행·측정이 끝난 뒤: 균핵 부피 모임(바꿈 2) → 판정 → 그림 → 풀이 맞비교(판정 아님)
V6=$(cd "$(dirname "$0")/.." && pwd); RUNS=$(cd "$V6/../model/runs" && pwd)
python3 $V6/scripts/scl_mass.py $(ls -d $RUNS/b_slimeall_s5[2-9]*_v6g $RUNS/b_long_s5[2-9]*_v6g 2>/dev/null)
python3 $V6/scripts/judge.py
python3 $V6/scripts/figs.py
F=""
for sd in 521 523 525; do for t in 0200 1000 1800 2000; do F="$F $RUNS/b_long_s${sd}_v6g/vs_t$t.npz"; done; done
for sd in 561 563; do for t in 0300 0700; do F="$F $RUNS/b_food4_s${sd}_v6g/vs_t$t.npz"; done; done
for sd in 571 573; do for t in 0400 0800; do F="$F $RUNS/b_slimeall_s${sd}_v6g/vs_t$t.npz"; done; done
for sd in 531 533; do for t in 0200 0400; do F="$F $RUNS/b_mig_s${sd}_v6g/vs_t$t.npz"; done; done
ls $F > /dev/null 2>&1; python3 $V6/scripts/mg_ab.py $V6/data/mg_ab.json $(for f in $F; do [ -f $f ] && echo $f; done) > /dev/null
