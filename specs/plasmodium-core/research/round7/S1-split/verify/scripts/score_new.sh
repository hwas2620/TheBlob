#!/bin/bash
# 끝난 내 실행(시드 21 이상, 꼬리표 있음) 가운데 아직 채점하지 않은 것을 채점한다.
#   채점기(stage0/metrics/bmet.py) 그대로 → verify/summaries/numpy_<실행>.json
#   추가 지표(scripts/extra_metrics.py)       → verify/summaries/extra_<실행>.json
# 끝나지 않은 폴더(metrics.json 없음)는 넘기지 않는다(채점기가 죽는다).
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S1-split/verify
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
cd $REF
for d in runs/b_*_s2[1-9]_* runs/b_*_s[3-9][0-9]_*; do
  [ -f "$d/metrics.json" ] || continue
  n=$(basename $d)
  if [ ! -f "$V/summaries/numpy_$n.json" ]; then
    python3 ../metrics/bmet.py $d --out $V/summaries > $V/logs/score_$n.log 2>&1 || echo "bmet 실패: $n" | tee -a $V/logs/done.txt
  fi
  if [ ! -f "$V/summaries/extra_$n.json" ]; then
    python3 $V/scripts/extra_metrics.py $d --out $V/summaries >> $V/logs/score_$n.log 2>&1 || echo "extra 실패: $n" | tee -a $V/logs/done.txt
  fi
done
ls $V/summaries | grep -c '^numpy_' | xargs echo "채점된 실행 수:"
