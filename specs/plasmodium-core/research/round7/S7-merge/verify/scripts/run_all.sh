#!/bin/bash
# run_all.sh JOBFILE — 3개씩 나란히
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S7-merge/verify
xargs -P 3 -L 1 $V/scripts/run_one.sh < $1
echo "ALL DONE $(date -u +%H:%M:%S)" >> $V/logs/done.txt
