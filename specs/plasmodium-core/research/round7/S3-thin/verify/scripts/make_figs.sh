#!/bin/bash
# 미리 정한 그림 (CRITERIA.md 의 C6). 줄마다 대조 → 후보 순서.
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S3-thin/verify
R=/home/user/TheBlob/specs/plasmodium-core/stage0/ref/runs
D="python3 $V/scripts/draw.py"
ctl() { [ -d $R/b_$1_s$2_vcd ] && echo $R/b_$1_s$2_vcd || echo $R/b_$1_s$2_vcdv; }
pairs() { scn=$1; shift; for s in "$@"; do echo -n "$(ctl $scn $s) $R/b_${scn}_s${s}_vthAv "; done; }
case "$1" in
  asym3)
    $D ends $V/fig/asym3_t300_a.png 300 $(pairs asym3 23 31 32 33 34 35 36 37) --cols 4
    $D ends $V/fig/asym3_t300_b.png 300 $(pairs asym3 38 39 40 41 42 43 44) --cols 4
    $D ends $V/fig/asym3_t480_a.png 480 $(pairs asym3 23 31 32 33 34 35 36 37) --cols 4
    $D ends $V/fig/asym3_t480_b.png 480 $(pairs asym3 38 39 40 41 42 43 44) --cols 4 ;;
  mig)
    $D times $V/fig/mig_t300_t400.png 300,400 $(pairs mig 31 32 33 34) ;;
  food3_256)
    $D times $V/fig/food3_256_t380_t480.png 380,480 $(pairs food3_256 21 22 23) ;;
  food3)
    $D ends $V/fig/food3_t480.png 480 $(pairs food3 25 26 31 32 33 34) --cols 4 ;;
esac
