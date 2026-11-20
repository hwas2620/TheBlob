#!/bin/bash
# 대기열: 4개씩 나란히. run_queue.sh jobs.txt
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S3-thin/verify
cat "$1" | xargs -P 4 -L 1 bash $V/scripts/run_one.sh
echo "queue done $(date -u +%H:%M:%S)" >> $V/logs/done.txt
