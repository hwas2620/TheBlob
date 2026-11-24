#!/bin/bash
# verify5: jobs.txt 의 실행을 4개씩 나란히. 터미널과 떨어뜨려 띄운다:
#   setsid nohup bash run_all.sh > /dev/null 2>&1 & disown
D=$(cd "$(dirname "$0")" && pwd)
xargs -P 4 -L 1 bash "$D/run_one.sh" < "$D/jobs.txt"
echo "$(date -u +%FT%TZ) ALLDONE" >> "$D/../logs/progress.txt"
