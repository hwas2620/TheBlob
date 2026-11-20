#!/usr/bin/env python3
"""[S3 검증, 탐색] "굵은 관이 한 칸 너비 가닥을 지남": 저장 시각마다 노드 전도도 Cn > CMIN 이고 젖은 8이웃이 2개 이하인 젖은 셀 수 (첫 판: Cn>100 이고 h<0.15 — 모든 실행에서 0 이라 바꿨다). 판정에 쓰지 않는다.
usage: vein_thin.py RUN_DIR ... → 실행마다 (먹는 동안 창의 합, 최대, 창 밖 합)"""
import glob, json, os, sys
import numpy as np
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
CMIN = float(os.environ.get('CMIN', 300))
def count(rd):
    m = json.load(open(os.path.join(rd, 'metrics.json'))); tt = m['t_touch']; te = [x for x in m['t_exh'] if x is not None]
    w0 = max(tt) + 20 if all(x is not None for x in tt) else 1e9; w1 = min(te) if te else 1e9; inw = []; allc = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); C = Z['C']; h = Z['h']; wet = Z['wet'].astype(bool); Cn = np.zeros_like(h)
        for k, d in enumerate(DIRS): Cn = np.maximum(Cn, np.maximum(C[k], np.roll(C[k], (d[1], d[0]), (0, 1))))
        nw = sum(np.roll(wet, (-dy, -dx), (0, 1)).astype(int) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)); n = int((wet & (Cn > CMIN) & (nw <= 2)).sum()); allc.append(n)
        if w0 <= float(Z['t']) <= w1: inw.append(n)
    return sum(inw), max(allc), sum(allc)
for rd in sys.argv[1:]:
    print(os.path.basename(rd), *count(rd))
