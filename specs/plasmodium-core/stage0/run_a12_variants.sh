#!/bin/bash
# 변형(합친 패스, 몸 주변만)과 큰 격자의 A1·A2 긴 실행을 차례로 돌린다. 먼저 npm run build (또는 STAGE0_DIST 로 빌드 폴더 지정).
# "몸 주변만" 변형은 소프트웨어 렌더러에서도 빨라서 512²·768² 를 10000스텝까지 돌린다. 기준형은 느려서 2000스텝만.
cd "$(dirname "$0")/../../.."
R=specs/plasmodium-core/stage0/run_stage0.cjs; L=specs/plasmodium-core/stage0/results; mkdir -p $L
run() { node $R "$1" "$2" 14400 > "$L/$1.log" 2>&1; }
run a12_N192_s1_c2_v1 "test=a12&N=192&seed=1&cyc=2&steps=10000&variant=1"
run a12_N192_s1_c2_v2 "test=a12&N=192&seed=1&cyc=2&steps=10000&variant=2"
run a12_N384_s1_c2_v2 "test=a12&N=384&seed=1&cyc=2&steps=10000&variant=2"
run a12_N384_s2_c2_v2 "test=a12&N=384&seed=2&cyc=2&steps=10000&variant=2"
run a12_N512_s1_c2_v2 "test=a12&N=512&seed=1&cyc=2&steps=10000&variant=2&check=100"
run a12_N768_s1_c2_v2 "test=a12&N=768&seed=1&cyc=2&steps=10000&variant=2&check=200"
run a12_N512_s1_c2_v0 "test=a12&N=512&seed=1&cyc=2&steps=2000&check=100"
run a12_N768_s1_c2_v0 "test=a12&N=768&seed=1&cyc=2&steps=2000&check=200"
echo ALL_DONE > $L/a12_variants_done.txt
