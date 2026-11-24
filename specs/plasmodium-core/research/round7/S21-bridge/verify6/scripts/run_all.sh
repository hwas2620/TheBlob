#!/bin/bash
# 일 목록 전체: 코어 4 개. 첫 실행 시작 뒤 100 분이 지나면 새 실행을 시작하지 않는다
V6=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p $V6/logs $V6/data
echo $(( $(date -u +%s) + 6000 )) > $V6/logs/deadline
date -u +%FT%TZ > $V6/data/first_start_utc.txt
grep -v '^#' $V6/jobs.txt | grep -v '^\s*$' | xargs -P 4 -L 1 $V6/scripts/run_job.sh
date -u +%FT%TZ > $V6/data/all_done_utc.txt
