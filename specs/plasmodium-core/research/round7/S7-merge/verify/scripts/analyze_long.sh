#!/bin/bash
# 끝난 long 실행 가운데 아직 재지 않은 것을 잰다
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S7-merge/verify; R=/home/user/TheBlob/specs/plasmodium-core/stage0/ref/runs
cd $V/scripts
for s in $(seq 151 170); do for tag in v7c v7k; do
  rd=$R/b_long_s${s}_${tag}
  [ -f $rd/metrics.json ] && [ ! -f $V/data/long/b_long_s${s}_${tag}.json ] && python3 vlong.py $rd
done; done
