#!/bin/bash
# 계획 D: 얇은 칸 줄임(규칙 3 의 s_e)을 켠 뒤 관문 B 를 모두 GPU 와 numpy 로 다시 돈다 (이름 꼬리 _th).
# GPU 는 관문 B 시나리오의 기본(thinH = PLASM.THIN_H), numpy 는 export_ref.py 의 GB(thin_h=0.15). 둘 다 외톨이 셀 말리기도 켠다.
# 먼저 npm run build. 판정: python3 judge_b_thin.py  (규칙 이전 기록은 꼬리 없는 이름, 계획 C 의 재실행은 _cd 로 남아 있다)
cd "$(dirname "$0")/../../.."
D=specs/plasmodium-core/stage0; R=$D/run_stage0.cjs; L=$D/results; mkdir -p $L/b $D/ref/logs
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
run() {   # GPU: run <시나리오> <시드> [쿼리에 더할 것] [이름 꼬리]
  local name="b_$1_s$2${4:+_$4}_th"
  [ -f "$L/b/gpu_$name.json" ] && return 0   # 이미 채점된 실행은 건너뛴다 (다시 돌려도 빠진 것만 돈다)
  rm -rf "$D/dumps/$name" "$D/runs_gpu/$name"
  node $R "$name" "test=b&scn=$1&seed=$2&dump=1&name=$name${3:+&$3}" 10800 > "$L/$name.log" 2>&1 || echo "(러너가 실패로 끝났다)" >> "$L/$name.log"
  python3 $D/metrics/gpu2run.py "$D/dumps/$name" >> "$L/$name.log" 2>&1 && python3 $D/metrics/bmet.py "$D/runs_gpu/$name" --out $L/b >> "$L/$name.log" 2>&1
}
ref() {   # numpy: ref <시나리오> <시드> [키=값 …] [꼬리=이름]
  local scn=$1 seed=$2; shift 2; local tag=th extra=()
  for a in "$@"; do case $a in tail=*) tag="${a#tail=}_th";; *) extra+=("$a");; esac; done
  local name="b_${scn}_s${seed}_$tag"
  [ -f "$L/b/numpy_$name.json" ] && return 0
  rm -rf "$D/ref/runs/$name"
  (cd $D/ref && python3 export_ref.py b $scn $seed "${extra[@]}" tag=$tag > logs/$name.log 2>&1) && python3 $D/metrics/bmet.py "$D/ref/runs/$name" --out $L/b >> "$D/ref/logs/$name.log" 2>&1
}
gpu_main() {
  ( for s in 1 2 3 4 5; do run mig $s; done; for s in 1 2 3 4 5 6; do run food3 $s; done; for s in 1 2 3; do run slimehalf $s; run slimeall $s; done ) &
  ( for d in dir0 dir13 dir27 dir34 dir45; do run $d 1; run $d 2; done; for s in 1 2 3; do run asym3 $s; done; for s in 1 2 3; do run food4 $s; done ) &
  ( for s in 1 2 3; do run mig256 $s; run food3_256 $s; done; run mig 1 "N=384&check=100" N384; run mig 2 "N=384&check=100" N384; run food3 1 "N=384&check=100" N384
    run mig2x 1 "check=100"; run mig2x 2 "check=100"; run food3 1 "gate=0" g0; run food3 2 "gate=0" g0 ) &
  wait
  ( run long 1; run long 4; for s in 6 7 8; do run mig $s; done ) &
  ( run long 2; run long 5; for s in 9 10 11; do run mig $s; done ) &
  ( run long 3; for s in 12 13 14 15; do run mig $s; done ) &
  wait
}
ref_main() {
  ( for s in 1 2 3 4 5; do ref mig $s; done; for s in 1 2 3 4 5 6; do ref food3 $s; done; for s in 1 2 3; do ref slimehalf $s; ref slimeall $s; done; ref long 1 ) &
  ( for d in dir0 dir13 dir27 dir34 dir45; do ref $d 1; ref $d 2; done; for s in 1 2 3; do ref asym3 $s; done; for s in 1 2 3; do ref food4 $s; done; ref long 2 ) &
  wait
  ( for s in 1 2 3; do ref mig256 $s; ref food3_256 $s; done; ref mig 1 N=384 tail=N384; ref mig 2 N=384 tail=N384; ref food3 1 N=384 tail=N384
    ref mig2x 1; ref mig2x 2; ref food3 1 res_gate=0 tail=g0; ref food3 2 res_gate=0 tail=g0 ) &
  ( for s in 6 7 8 9 10 11 12 13 14 15; do ref mig $s; done; ref long 3; ref long 4; ref long 5 ) &
  wait
}
gpu_main > $L/b_thin_gpu.txt 2>&1 &
ref_main > $L/b_thin_ref.txt 2>&1 &
wait; echo ALL_DONE > $L/b_thin_done.txt
