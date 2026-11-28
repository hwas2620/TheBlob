#!/bin/bash
# 돌고 있는 실행이 끝나면 jobs_d7all.txt 를 코어 4개로 돌린다
cd /home/user/TheBlob/specs/plasmodium-core/research/round7/S25-site
while pgrep -f 'python3 export_re[f]' > /dev/null; do sleep 10; done
cat scripts/jobs_d7all.txt | xargs -P 4 -L 1 bash scripts/run_one.sh
echo ALL_DONE > logs/all_done_d7.txt
