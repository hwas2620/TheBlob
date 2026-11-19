#!/bin/bash
# 관문 B 의 GPU 실행 전부. 먼저 npm run build (또는 STAGE0_DIST 로 빌드 폴더 지정).
# 실행마다: 헤드리스 페이지가 시나리오를 돌리며 상태 덤프를 보낸다(dumps/) → 변환기가 numpy 실행과 같은 꼴로 바꾼다(runs_gpu/) → 채점(results/b/gpu_<실행>.json)
# numpy 쪽은 ref/run_b_ref.sh 로 돌리고 같은 채점기를 쓴다:  python3 metrics/bmet.py ref/runs/b_* --out results/b
# 판정은 python3 judge_b.py. 이 컨테이너의 소프트웨어 렌더러 기준으로 192² 한 실행이 1~4분, 지속 실행이 15분쯤, 3개씩 나란히 돌려 모두 1시간쯤이다.
cd "$(dirname "$0")/../../.."
D=specs/plasmodium-core/stage0; R=$D/run_stage0.cjs; L=$D/results; mkdir -p $L/b
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
# run <시나리오> <시드> [쿼리에 더할 것] [이름 꼬리]
run() {
  local name="b_$1_s$2${4:+_$4}"
  node $R "$name" "test=b&scn=$1&seed=$2&dump=1&name=$name${3:+&$3}" 10800 > "$L/$name.log" 2>&1
  python3 $D/metrics/gpu2run.py "$D/dumps/$name" >> "$L/$name.log" 2>&1 && python3 $D/metrics/bmet.py "$D/runs_gpu/$name" --out $L/b >> "$L/$name.log" 2>&1
}
(
  for s in 1 2 3 4 5; do run mig $s; done                    # 굶은 이주 (B1~B4)
  for s in 1 2 3 4 5 6; do run food3 $s; done                # 대칭 먹이 셋 (B5)
  for s in 1 2 3; do run slimehalf $s; run slimeall $s; done # 점액 (B6)
  run long 1                                                 # 지속 (B7)
) &
(
  for d in dir0 dir13 dir27 dir34 dir45; do run $d 1; run $d 2; done   # 방향별 도달 시각 (B2)
  for s in 1 2 3; do run asym3 $s; done                      # 비대칭 먹이 셋 (B5 참고)
  for s in 1 2 3; do run food4 $s; done                      # 긴 배치 먹이 넷 (B5)
  run long 2
) &
(
  for s in 1 2 3; do run mig256 $s; run food3_256 $s; done   # 게임 격자 후보 256² (무늬 주기 128)
  run mig 1 "N=384&check=100" N384; run mig 2 "N=384&check=100" N384   # 384² 확인
  run food3 1 "N=384&check=100" N384
  run mig2x 1 "check=100"; run mig2x 2 "check=100"           # 몸 길이 2배 (B4 의 위상 지연)
  run food3 1 "gate=0" g0; run food3 2 "gate=0" g0           # 90% 조건을 끈 길 (코드 경로 확인)
) &
wait; echo ALL_DONE > $L/b_done.txt
