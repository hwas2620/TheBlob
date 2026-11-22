#!/usr/bin/env python3
"""[S7 독립 검증] long 20쌍의 시간 평균 곡선 그림: 얇은 칸 수, 찌꺼기 몫, 몸 밖 몫, 큰 두꺼운 덩어리 둘 이상 / 큰 부채 둘 이상인 실행의 몫."""
import json, os
import numpy as np
from vcommon import VER
from vfig import lineplot, FIG
D = os.path.join(VER, 'data', 'long')
def series(tag, key, f=lambda x: x):
    M = []
    for s in range(151, 171):
        p = os.path.join(D, f'b_long_s{s}_{tag}.json')
        if os.path.exists(p): M.append([f(r[key]) for r in json.load(open(p))['rows']])
    return np.array(M, float)
t = [r['t'] for r in json.load(open(os.path.join(D, 'b_long_s151_v7c.json')))['rows']]
C = (40, 90, 230); K = (220, 30, 30)
for key, lab, f, yl in (('thin', 'thin wet cells (h<0.3), mean of 20 runs', lambda x: x, None), ('debris', 'debris volume share (pieces <5% each), mean', lambda x: x, None),
                        ('out', 'volume share outside largest wet piece, mean', lambda x: x, None), ('nbig', 'share of runs with >=2 big thick parts', lambda x: float(x >= 2), (0, 1)),
                        ('nfan', 'share of runs with >=2 big fans (2a-prime)', lambda x: float(x >= 2), (0, 1))):
    c = series('v7c', key, f); k = series('v7k', key, f)
    lineplot(os.path.join(FIG, f'time_{key}.png'), [('control v7c (n=%d)' % len(c), t, c.mean(0), C), ('candidate v7k (n=%d)' % len(k), t, k.mean(0), K)], ylim=yl, title=lab)
