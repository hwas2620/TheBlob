#!/bin/bash
# verify9: jobs.txt 의 일을 4 개씩 나란히 (위에서부터: 긴 일 먼저). 끝나면 logs/ALL_DONE 을 쓴다.
S=/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/verify9/scripts
L=/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/verify9/logs
date -u +%FT%TZ > "$L/ALL_START"
xargs -P 4 -d '\n' -n 1 bash "$S/run_one.sh" < "$S/jobs.txt"
date -u +%FT%TZ > "$L/ALL_DONE"
