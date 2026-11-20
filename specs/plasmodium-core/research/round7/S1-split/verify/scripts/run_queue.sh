#!/bin/bash
# 실행 목록을 동시에 P개씩(기본 4) 돌린다: run_queue.sh JOBFILE NAME [P]
#   JOBFILE 의 한 줄 = "SCN SEED TAG [키=값 ...]" (# 로 시작하는 줄과 빈 줄은 건너뛴다)
#   다 끝나면 verify/logs/queue_<NAME>_done 을 만든다
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S1-split/verify
P=${3:-4}
grep -v '^#' "$1" | grep -v '^[[:space:]]*$' | xargs -P $P -L 1 bash $V/scripts/run_one.sh
echo "done $(date -u +%H:%M:%S)" > $V/logs/queue_$2_done
