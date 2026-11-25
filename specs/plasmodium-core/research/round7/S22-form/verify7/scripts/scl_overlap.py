#!/usr/bin/env python3
"""verify7 보충 (CRITERIA_CHANGES.md 2절): 주장 7(c) 위치를 넓이에 매이지 않는 값으로 다시 본다.
갇힘 장면의 두께를 sigma=4 로 흐린 값 G 에서, 끝 덩이와 같은 넓이만큼 G 가 큰 셀(갇힘 장면 몸 안)을 '짙던 곳'으로 하고,
끝 덩이가 그 자리와 겹치는 몫(overlap)과 아무 데나 놓였을 때의 기대값(끝 넓이 / 갇힘 장면 넓이)을 비교한다.
usage: scl_overlap.py -> data/scl_overlap.json"""
import json, os, sys, glob
import numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.normpath(os.path.join(HERE, '..')); RUNS = os.path.normpath(os.path.join(V, '..', 'model', 'runs'))
J = json.load(open(os.path.join(V, 'judge_out.json'))); out = []
for x in J['claim7']['runs']:
    r = json.load(open(os.path.join(V, 'data', x['name'] + '.json'))); tt = int(round(r['scl']['t_trap_frame'])); tE = int(round(r['scl']['t_end_frame']))
    Z0 = np.load(os.path.join(RUNS, x['name'], f'vs_t{tt:04d}.npz')); w0 = Z0['wet'].astype(bool); h0 = np.where(w0, np.maximum(Z0['h'], 0), 0)
    wE = np.load(os.path.join(RUNS, x['name'], f'vs_t{tE:04d}.npz'))['wet'].astype(bool)
    G = gaussian_filter(h0, 4, mode='wrap', truncate=3.0); A = int(wE.sum()); k = min(A, int(w0.sum()))
    thr = np.sort(G[w0])[::-1][k - 1]; top = w0 & (G >= thr)
    ov = float((top & wE).sum() / A); rnd = float(A / w0.sum())
    out.append(dict(name=x['name'], overlap=ov, random=rnd, margin=ov - rnd, ok=bool(ov >= rnd + 0.15)))
    print(x['name'], 'overlap %.2f random %.2f' % (ov, rnd))
json.dump(out, open(os.path.join(V, 'data', 'scl_overlap.json'), 'w'), indent=1)
