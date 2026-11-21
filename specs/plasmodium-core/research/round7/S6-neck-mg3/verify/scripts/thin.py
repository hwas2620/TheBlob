#!/usr/bin/env python3
"""thin.py RUN_DIR — 디스크가 모자라 long 이외 실행의 vs_t*.npz 를 100 시간 간격(과 마지막)만 남기고 지운다.
채점(verify/data/bmet_<run>.json, x_<run>.json)이 먼저 저장돼 있어야 한다. 이 검증이 만든 실행(_vc, _vnk)에만 쓴다."""
import sys, os, glob, re
V = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S6-neck-mg3/verify'
for rd in sys.argv[1:]:
    run = os.path.basename(rd.rstrip('/'))
    assert re.match(r'b_(food4|food3|asym3|mig)_s\d+_(vc|vnk)$', run), run
    assert os.path.exists(os.path.join(V, 'data', f'bmet_{run}.json')) and os.path.exists(os.path.join(V, 'data', f'x_{run}.json')), run
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))); gone = []
    for f in fs[:-1]:
        t = int(re.search(r'vs_t(\d+)\.npz', f).group(1))
        if t % 100 != 0: os.remove(f); gone.append(t)
    print(run, 'removed', len(gone), 'kept', len(fs) - len(gone), flush=True)
