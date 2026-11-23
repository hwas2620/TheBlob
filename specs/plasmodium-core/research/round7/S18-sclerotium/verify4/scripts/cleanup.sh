#!/bin/bash
# 디스크가 모자랄 때만 부른다 (job.sh). 내 실행(꼬리표 v4c/v4w, 시드 401~430) 가운데 measure.py 가 이미 잰 것에서, 판정·그림에 쓰지 않는 파일만 지운다.
S18=/home/user/TheBlob/specs/plasmodium-core/research/round7/S18-sclerotium
RUNS=$S18/model/runs; V4=$S18/verify4
echo "$(date -u +%FT%TZ) cleanup"
for d in "$RUNS"/b_*_s4[0-3][0-9]_v4c "$RUNS"/b_*_s4[0-3][0-9]_v4w; do
  [ -d "$d" ] || continue
  n=$(basename "$d"); [ -f "$V4/data/runs/$n.json" ] || continue
  for f in C_edges.npy eage.npy G_edges.npy vein_native.npy Qmean.npy Qgross.npy; do rm -f "${d:?}/${f:?}"; done
  for f in "$d"/state_t*.npz; do [ -e "$f" ] && rm -f "${f:?}"; done
done
