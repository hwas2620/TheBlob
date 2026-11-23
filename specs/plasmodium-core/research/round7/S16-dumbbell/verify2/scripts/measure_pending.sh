#!/bin/bash
# measure finished long runs that have no frames json yet (nice, one process)
cd "$(dirname "$0")/.."
R=../model/runs
grep '^long' logs/runs/finished.txt | while read scn seed arm rest; do
  [ "$arm" = dense ] && continue
  tag=$([ "$arm" = ctrl ] && echo w16c || echo w16gm)
  n=b_long_s${seed}_${tag}
  [ -f data/frames/$n.json ] || nice -n 10 python3 scripts/measure.py $R/$n
done
