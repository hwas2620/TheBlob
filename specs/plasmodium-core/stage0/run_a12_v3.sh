#!/bin/bash
# "두 번 스무딩" 변형(variant=3)의 A1·A2 긴 실행. run_a12_variants.sh 가 끝난 뒤에 돈다.
cd "$(dirname "$0")/../../.."
R=specs/plasmodium-core/stage0/run_stage0.cjs; L=specs/plasmodium-core/stage0/results; mkdir -p $L
until [ -f $L/a12_variants_done.txt ]; do sleep 20; done
run() { node $R "$1" "$2" 14400 > "$L/$1.log" 2>&1; }
run a12_N192_s1_c2_v3 "test=a12&N=192&seed=1&cyc=2&steps=10000&variant=3"
run a12_N384_s1_c2_v3 "test=a12&N=384&seed=1&cyc=2&steps=10000&variant=3"
run a12_N768_s1_c2_v3 "test=a12&N=768&seed=1&cyc=2&steps=10000&variant=3&check=200"
echo ALL_DONE > $L/a12_v3_done.txt
