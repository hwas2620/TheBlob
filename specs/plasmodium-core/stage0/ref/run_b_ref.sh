#!/bin/bash
# 관문 B 의 numpy 기준 실행 전부 (3개씩 나란히). 로그는 logs/ 에, 상태는 runs/b_<시나리오>_s<시드>[_이름]/ 에 남는다.
# 192² 한 실행이 1~3분(지속 실행은 약 10분, 384² 는 약 10분)이다. 채점은 ../metrics/bmet.py.
cd "$(dirname "$0")"; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p logs
r() { python3 export_ref.py b "$@" > "logs/b_$(echo "$@" | tr ' ' '_').log" 2>&1; }
(
  for s in 1 2 3 4 5; do r mig $s; done            # 굶은 이주 (B1~B4)
  for s in 1 2 3 4 5 6; do r food3 $s; done        # 대칭 먹이 셋 (B5)
  for s in 1 2 3; do r slimehalf $s; r slimeall $s; done   # 점액 (B6)
  r long 1                                         # 지속 (B7)
) &
(
  for d in dir0 dir13 dir27 dir34 dir45; do r $d 1; r $d 2; done   # 방향별 도달 시각 (B2)
  for s in 1 2 3; do r asym3 $s; done              # 비대칭 먹이 셋 (B5 참고)
  for s in 1 2 3; do r food4 $s; done              # 긴 배치 먹이 넷 (B5)
  r long 2
) &
(
  for s in 1 2 3; do r mig256 $s; r food3_256 $s; done   # 게임 격자 후보 256² (무늬 주기 128)
  r mig 1 N=384 tag=N384; r mig 2 N=384 tag=N384   # 384² 확인
  r food3 1 N=384 tag=N384
  r mig2x 1; r mig2x 2                             # 몸 길이 2배 (B4 의 위상 지연)
  r food3 1 res_gate=0 tag=g0; r food3 2 res_gate=0 tag=g0   # 90% 조건을 끈 길 (GPU 의 같은 실행과 견준다)
) &
wait
# 덧붙임 (판정에는 쓰지 않는다): 굶은 이주의 시드를 15개까지 늘려 GPU − numpy 의 짝 차이를 본다
( for s in 6 7 8 9; do r mig $s; done ) &
( for s in 10 11 12; do r mig $s; done ) &
( for s in 13 14 15; do r mig $s; done ) &
wait; echo ALL_DONE > logs/b_done.txt
