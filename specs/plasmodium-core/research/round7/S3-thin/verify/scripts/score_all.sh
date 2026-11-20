#!/bin/bash
# 끝난 판정 실행(대조·후보)을 모두 채점한다: bmet.py → summaries/numpy_<실행>.json, extra_metrics.py → summaries/extra_<실행>.json
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S3-thin/verify
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
dirs=$(python3 - <<'PY'
import json
c=json.load(open('/home/user/TheBlob/specs/plasmodium-core/research/round7/S3-thin/verify/scripts/criteria.json'))
for scn,d in c['seeds'].items():
    for s in d['seeds']:
        for tag in ('vthAv', 'vcd' if s in d['existing_vcd'] else 'vcdv'):
            print(f'b_{scn}_s{s}_{tag}')
print('b_asym3_s23_vcdv')
PY
)
todo=()
for n in $dirs; do
  [ -f $REF/runs/$n/metrics.json ] || continue
  [ -f $V/summaries/numpy_$n.json ] && [ -f $V/summaries/extra_$n.json ] && continue
  todo+=($REF/runs/$n)
done
echo "to score: ${#todo[@]}"
[ ${#todo[@]} -eq 0 ] && exit 0
printf '%s\n' "${todo[@]}" | xargs -P ${P:-2} -I{} sh -c "python3 /home/user/TheBlob/specs/plasmodium-core/stage0/metrics/bmet.py {} --out $V/summaries > /dev/null 2>> $V/logs/score_err.txt; python3 $V/scripts/extra_metrics.py {} --out $V/summaries >> $V/logs/score_extra.txt 2>> $V/logs/score_err.txt"
