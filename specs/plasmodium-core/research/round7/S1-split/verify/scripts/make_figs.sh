#!/bin/bash
# 그림 묶음: make_figs.sh WHAT   (WHAT = near | food4 | long | mig | extra)
# 윗줄 = 지금 규칙(v0), 아랫줄 = 후보(vpk). 색은 draw.py 머리말.
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S1-split/verify
D="python3 $V/scripts/draw.py"
cd $REF
rs() { local scn=$1 tag=$2; shift 2; for s in "$@"; do printf 'runs/b_%s_s%s_%s ' $scn $s $tag; done; }
case "$1" in
near)
  $D ends $V/fig/food3_t380.png 380 $(rs food3 v0 21 22 23 24 25 26) $(rs food3 vpk 21 22 23 24 25 26) --px 1 --cols 6
  $D ends $V/fig/food3_t480.png 480 $(rs food3 v0 21 22 23 24 25 26) $(rs food3 vpk 21 22 23 24 25 26) --px 1 --cols 6
  $D ends $V/fig/asym3_t380.png 380 $(rs asym3 v0 21 22 23) $(rs asym3 vpk 21 22 23) --px 2 --cols 3
  $D ends $V/fig/asym3_t480.png 480 $(rs asym3 v0 21 22 23) $(rs asym3 vpk 21 22 23) --px 2 --cols 3
  $D ends $V/fig/food3_256_t380.png 380 $(rs food3_256 v0 21 22 23) $(rs food3_256 vpk 21 22 23) --px 1 --cols 3
  $D ends $V/fig/food3_256_t480.png 480 $(rs food3_256 v0 21 22 23) $(rs food3_256 vpk 21 22 23) --px 1 --cols 3
  ;;
food4)
  for s in 21 22 23 24 25 26; do $D times $V/fig/food4_s${s}_times.png 300,420,540,620,700 runs/b_food4_s${s}_v0 runs/b_food4_s${s}_vpk --px 1; done
  $D ends $V/fig/food4_t700.png 700 $(rs food4 v0 21 22 23 24 25 26) $(rs food4 vpk 21 22 23 24 25 26) --px 1 --cols 6
  ;;
long)
  for s in 21 22 23; do $D times $V/fig/long_s${s}_times.png 800,1100,1300,1500,1700,2000 runs/b_long_s${s}_v0 runs/b_long_s${s}_vpk --px 1; done
  $D ends $V/fig/long_t2000.png 2000 $(rs long v0 21 22 23) $(rs long vpk 21 22 23) --px 2 --cols 3
  ;;
mig)
  $D ends $V/fig/mig_t400.png 400 $(rs mig v0 21 22 23 24) $(rs mig vpk 21 22 23 24) --px 2 --cols 4
  ;;
extra)
  $D times $V/fig/long_T4000_s21.png 2000,3000,4000 runs/b_long_s21_v0T4 runs/b_long_s21_v0T4st runs/b_long_s21_vpkT4st --px 1
  $D times $V/fig/long_T4000st_vpk.png 2600,3200,4000 runs/b_long_s21_vpkT4st runs/b_long_s22_vpkT4st --px 2
  $D ends $V/fig/long_decomp_t2000.png 2000 $(rs long vbm 21 22 23) runs/b_long_s21_vsat runs/b_long_s22_vsat --px 2 --cols 3
  $D ends $V/fig/mig256_t400.png 400 $(rs mig256 v0 21 22 23) $(rs mig256 vpk 21 22 23) --px 1 --cols 3
  ;;
*) echo "usage: make_figs.sh near|food4|long|mig|extra";;
esac
