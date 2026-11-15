#!/bin/bash
# A1·A2 긴 실행을 차례로 돌린다 (소프트웨어 렌더러 기준 192² 약 10분, 384² 약 40분씩). 먼저 npm run build.
cd "$(dirname "$0")/../../.."
R=specs/plasmodium-core/stage0/run_stage0.cjs; L=specs/plasmodium-core/stage0/results; mkdir -p $L
run() { node $R "$1" "$2" 14400 > "$L/$1.log" 2>&1; }
(
run a12_N192_s1_c2 "test=a12&N=192&seed=1&cyc=2&steps=10000"
run a12_N192_s2_c2 "test=a12&N=192&seed=2&cyc=2&steps=10000"
run a12_N192_s1_c3 "test=a12&N=192&seed=1&cyc=3&steps=10000"
run a12_N192_s1_c2_tri "test=a12&N=192&seed=1&cyc=2&steps=10000&tri=1"
) &
(
run a12_N384_s1_c2 "test=a12&N=384&seed=1&cyc=2&steps=10000"
run a12_N384_s2_c2 "test=a12&N=384&seed=2&cyc=2&steps=10000"
) &
wait; echo ALL_DONE > $L/a12_done.txt
