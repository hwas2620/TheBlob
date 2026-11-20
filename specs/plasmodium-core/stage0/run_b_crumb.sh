#!/bin/bash
# 계획 C: 외톨이 셀 말리기를 켠 뒤 관문 B 의 먹이 시나리오만 GPU 와 numpy 로 다시 돈다 (이름 꼬리 _cd).
# GPU 는 관문 B 시나리오의 기본(crumbDry 켬), numpy 는 export_ref.py 의 GB(crumb_dry=1).
# 판정: python3 judge_b_crumb.py  (나머지 시나리오는 기존 기록을 그대로 쓴다)
cd "$(dirname "$0")/../../.."
D=specs/plasmodium-core/stage0; R=$D/run_stage0.cjs; L=$D/results; mkdir -p $L/b
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
run() {   # GPU: run <시나리오> <시드>
  local name="b_$1_s$2_cd"
  rm -rf "$D/dumps/$name"
  node $R "$name" "test=b&scn=$1&seed=$2&dump=1&name=$name" 10800 > "$L/$name.log" 2>&1 || echo "(러너가 실패로 끝났다)" >> "$L/$name.log"
  python3 $D/metrics/gpu2run.py "$D/dumps/$name" >> "$L/$name.log" 2>&1 && python3 $D/metrics/bmet.py "$D/runs_gpu/$name" --out $L/b >> "$L/$name.log" 2>&1
}
ref() {   # numpy: ref <시나리오> <시드>
  (cd $D/ref && python3 export_ref.py b $1 $2 tag=cd > logs/b_$1_$2_cd.log 2>&1) && python3 $D/metrics/bmet.py "$D/ref/runs/b_$1_s$2_cd" --out $L/b >> "$D/ref/logs/b_$1_$2_cd.log" 2>&1
}
( for s in 1 2 3 4 5 6; do run food3 $s; done; for s in 1 2 3; do run asym3 $s; done ) &
( for s in 1 2 3; do run food4 $s; done; for s in 1 2 3; do run food3_256 $s; done ) &
( for s in 1 2 3; do ref food4 $s; done; for s in 1 2 3; do ref asym3 $s; done ) &
( for s in 1 2 3 4 5 6; do ref food3 $s; done; for s in 1 2 3; do ref food3_256 $s; done ) &
wait; echo ALL_DONE > $L/b_crumb_done.txt
