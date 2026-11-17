#!/bin/bash
# A1·A2 긴 실행 전부. 먼저 npm run build (또는 STAGE0_DIST 로 빌드 폴더 지정).
# 결과는 results/<이름>.json, 판정은 python3 judge_a12.py.
# 이 컨테이너의 소프트웨어 렌더러 기준으로 기준형은 192² 약 13분, 384² 약 55분이 걸리고 "몸 주변만" 변형은 격자와 거의 무관하게 10~15분이다.
# 실제로는 아래 묶음들을 2~3개씩 나란히 돌렸다. variant 번호는 src/stage0/tests.ts 의 VARIANTS.
cd "$(dirname "$0")/../../.."
R=specs/plasmodium-core/stage0/run_stage0.cjs; L=specs/plasmodium-core/stage0/results; mkdir -p $L
run() { node $R "$1" "$2" 14400 > "$L/$1.log" 2>&1; }

# 기준형 (A1·A2 의 판정 대상)
run a12_N192_s1_c2 "test=a12&N=192&seed=1&cyc=2&steps=10000"
run a12_N192_s2_c2 "test=a12&N=192&seed=2&cyc=2&steps=10000"
run a12_N384_s1_c2 "test=a12&N=384&seed=1&cyc=2&steps=10000"
run a12_N192_s1_c3 "test=a12&N=192&seed=1&cyc=3&steps=10000"   # 3사이클 (기록)

# 변형이 기준형과 같은 궤적을 내는지 (192² 와 384² 의 시드 1)
# sync=1 은 몸의 경계 상자를 그 자리에서 읽는다. 이 시험 루프에서는 그래야 가위 사각형이 좁게 유지된다(tests.ts 의 syncBounds 설명).
run a12_N192_s1_c2_v1 "test=a12&N=192&seed=1&cyc=2&steps=10000&variant=1"
run a12_N192_s1_c2_v2async "test=a12&N=192&seed=1&cyc=2&steps=10000&variant=2"
run a12_N192_s1_c2_v2 "test=a12&N=192&seed=1&cyc=2&steps=10000&variant=2&sync=1"
run a12_N192_s1_c2_v3 "test=a12&N=192&seed=1&cyc=2&steps=10000&variant=3&sync=1"
run a12_N384_s1_c2_v2 "test=a12&N=384&seed=1&cyc=2&steps=10000&variant=2&sync=1"
run a12_N384_s1_c2_v3 "test=a12&N=384&seed=1&cyc=2&steps=10000&variant=3&sync=1"

# 384² 시드 2 와 큰 격자는 "몸 주변만" 변형으로 (기준형은 여기서 너무 느리다. 큰 격자의 기준형은 300스텝만)
run a12_N384_s2_c2_v2 "test=a12&N=384&seed=2&cyc=2&steps=10000&variant=2&sync=1"
run a12_N192_s3_c2_v2 "test=a12&N=192&seed=3&cyc=2&steps=10000&variant=2&sync=1"   # 판정 뒤에 더한 새 시드
run a12_N512_s1_c2_v2 "test=a12&N=512&seed=1&cyc=2&steps=10000&variant=2&sync=1&check=100"
run a12_N768_s1_c2_v2 "test=a12&N=768&seed=1&cyc=2&steps=10000&variant=2&sync=1&check=200"
run a12_N768_s1_c2_v3 "test=a12&N=768&seed=1&cyc=2&steps=10000&variant=3&sync=1&check=200"
run a12_N512_s1_c2_v0 "test=a12&N=512&seed=1&cyc=2&steps=300&check=100"
run a12_N768_s1_c2_v0 "test=a12&N=768&seed=1&cyc=2&steps=300&check=100"

# 삼각 격자 무늬를 켠 실행 (견줄 numpy 기준이 없어 기록만)
run a12_N192_s1_c2_tri_v2 "test=a12&N=192&seed=1&cyc=2&steps=10000&tri=1&variant=2&sync=1"
run a12_N384_s1_c2_tri_v2 "test=a12&N=384&seed=1&cyc=2&steps=10000&tri=1&variant=2&sync=1"
# 속도 후보 설정 (dt 0.2 + 맥동 주기 8). numpy 기준은 export_ref.py a12 <N> <시드> <mg|exact> 400 dt=0.2 period=8 osc_sub=8 tag=dt2p8
run a12_N192_s1_c2_v2_dt2p8 "test=a12&N=192&seed=1&cyc=2&steps=2000&variant=2&sync=1&dt=0.2&period=8&sub=8&tag=dt2p8"
run a12_N192_s2_c2_v2_dt2p8 "test=a12&N=192&seed=2&cyc=2&steps=2000&variant=2&sync=1&dt=0.2&period=8&sub=8&tag=dt2p8"
run a12_N384_s1_c2_v2_dt2p8 "test=a12&N=384&seed=1&cyc=2&steps=2000&variant=2&sync=1&dt=0.2&period=8&sub=8&tag=dt2p8"
run a12_N384_s1_c2_v3_dt2p8 "test=a12&N=384&seed=1&cyc=2&steps=2000&variant=3&sync=1&dt=0.2&period=8&sub=8&tag=dt2p8"

# 코드 검토 뒤의 빌드로 다시 돌려 앞의 결과와 같은지 본 것
run a12_N384_s1_c2_v3_final "test=a12&N=384&seed=1&cyc=2&steps=10000&variant=3&sync=1"
echo ALL_DONE > $L/a12_done.txt
