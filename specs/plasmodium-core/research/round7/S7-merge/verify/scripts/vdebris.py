#!/usr/bin/env python3
"""[S7 독립 검증] 찌꺼기(가장 큰 젖은 덩어리 밖의, 하나하나 몸의 5% 미만인 조각)의 나이와 늙음 시계 (판정 아님).
usage: vdebris.py  -> data/debris.json
t = 1000, 1500, 2000 에서: 찌꺼기 부피 몫, 조각 수, 찌꺼기 칸의 sage 중앙과 age 중앙(본체와 견줌), 찌꺼기 칸의 평균 두께, 찌꺼기 칸 가운데 sage > age + 20 인 몫
(sage 가 age 보다 크게 앞서면 그 칸은 규칙이나 다른 이유로 빨리 늙은 것이다. 보통 칸은 sage = age; 먹이 위에서는 sage < age)."""
import json, os
import numpy as np
from vcommon import load, _torus_label, comp_vols, rundir, VER
R = {}
for s in range(151, 171):
    for tag in ('v7c', 'v7k'):
        rd = rundir('long', s, tag)
        if not os.path.exists(os.path.join(rd, 'metrics.json')): continue
        for t in (1000, 1500, 2000):
            S = load(os.path.join(rd, f'vs_t{t:04d}.npz')); wet, h, age, sage = S['wet'], S['h'], S['age'], S['sage']; V = h.sum()
            lw = _torus_label(wet); v = comp_vols(lw, h); main = int(np.argmax(v))
            small = np.zeros(v.size, bool); small[1:] = v[1:] < 0.05 * V; small[main] = False
            d = small[lw] & wet; m = (lw == main) & wet
            R[f's{s}_{tag}_t{t}'] = dict(debris=float(h[d].sum() / V), npieces=int(small.sum()), sage_debris=float(np.median(sage[d])) if d.any() else None,
                                         sage_main=float(np.median(sage[m])), age_debris=float(np.median(age[d])) if d.any() else None, age_main=float(np.median(age[m])),
                                         h_debris=float(h[d].mean()) if d.any() else None, fast_aged=float(((sage - age) > 20)[d].mean()) if d.any() else None,
                                         fast_aged_main=float(((sage - age) > 20)[m].mean()))
json.dump(R, open(os.path.join(VER, 'data', 'debris.json'), 'w'), indent=1)
for tag in ('v7c', 'v7k'):
    for t in (1000, 1500, 2000):
        X = [v for k, v in R.items() if f'_{tag}_t{t}' in k]
        f = lambda key: float(np.nanmedian([x[key] if x[key] is not None else np.nan for x in X]))
        print(tag, t, 'n', len(X), {k: round(f(k), 3) for k in ('debris', 'npieces', 'sage_debris', 'age_debris', 'h_debris', 'fast_aged', 'sage_main', 'age_main', 'fast_aged_main')})
