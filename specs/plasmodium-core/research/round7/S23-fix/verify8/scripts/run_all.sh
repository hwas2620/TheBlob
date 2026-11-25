#!/bin/bash
# verify8 전체 실행: 일 목록을 4코어로 (xargs -P 4). 끝나면 logs/ALL_DONE
M=/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model
V=/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/verify8
mkdir -p $V/logs $V/data
cd $M && NUMBA_NUM_THREADS=1 python3 -c "import numpy as np, mgt; m = mgt.MGT(16); z = np.zeros((16, 16)); m.solve([np.ones((16, 16))] * 4, np.ones((16, 16)), z, z)"   # numba 캐시를 먼저 한 번 만든다
echo "$(date -u +%FT%TZ) ALL_START" >> $V/jobs_log.txt
grep -vE '^\s*(#|$)' $V/scripts/jobs.txt | xargs -P 4 -L 1 bash $V/scripts/worker.sh
echo "$(date -u +%FT%TZ) ALL_END" >> $V/jobs_log.txt
touch $V/logs/ALL_DONE
