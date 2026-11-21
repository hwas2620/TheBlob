#!/bin/bash
# run_one.sh <시나리오> <시드> <꼬리표 vc|vnk>  — 독립 검증 실행 하나 (numpy 기준 모델, 코드는 고치지 않고 그대로 부른다)
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S6-neck-mg3/verify
REF=/home/user/TheBlob/specs/plasmodium-core/stage0/ref
scn=$1; seed=$2; tag=$3
case "$tag" in
  vc)  extra="ncyc=3";;                 # 대조: 관문 B 설정 + 압력 풀이 3사이클
  vnk) extra="ncyc=3 neck_keep=1";;     # 후보: 대조 + 이음 지키기
  *) echo "bad tag $tag"; exit 2;;
esac
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1
name=b_${scn}_s${seed}_${tag}
if [ -f $REF/runs/$name/metrics.json ]; then echo "$name EXISTS" >> $V/logs/done.txt; exit 0; fi
av=$(df --output=avail -m /home/user | tail -1)
if [ "$av" -lt 1500 ]; then echo "$name SKIPPED disk avail=${av}MB $(date -u +%FT%TZ)" >> $V/logs/done.txt; exit 0; fi
cd $REF; t0=$(date +%s); echo "$name START $(date -u +%FT%TZ) avail=${av}MB" >> $V/logs/done.txt
python3 export_ref.py b $scn $seed $extra tag=$tag > $V/logs/$name.log 2>&1
rc=$?
echo "$name END rc=$rc wall=$(( $(date +%s) - t0 ))s $(date -u +%FT%TZ)" >> $V/logs/done.txt
exit 0
