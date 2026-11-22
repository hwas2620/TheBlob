#!/usr/bin/env python3
"""[S7 독립 검증] 작성자 결승 실행(s7c/s7k, long 141~150)에 내 지표(큰 두꺼운 덩어리 둘 이상 1c, 큰 엽 둘 이상 2a)를 적용한다 (판정 아님, 측정 치우침 확인용)."""
import json, os
import numpy as np
import vlong
from vcommon import rundir, VER
R = {}
for s in range(141, 151):
    for tag in ('s7c', 's7k'):
        o = vlong.measure(rundir('long', s, tag)); r = [x for x in o['rows'] if x['t'] >= 100]
        R[f's{s}_{tag}'] = dict(nbig2=float(np.mean([x['nbig'] >= 2 for x in r])), lobe2=float(np.mean([x['nlobe'] >= 2 for x in r])), fan2=float(np.mean([x['nfan'] >= 2 for x in r])),
                                split=float(np.mean([x['out'] >= 0.1 for x in r])), lobe2_given_nbig1=float(np.mean([x['nlobe'] >= 2 for x in r if x['nbig'] <= 1])) if any(x['nbig'] <= 1 for x in r) else None)
    print(s, R[f's{s}_s7c'], R[f's{s}_s7k'], flush=True)
for tag in ('s7c', 's7k'):
    print(tag, {k: round(float(np.mean([R[f's{s}_{tag}'][k] for s in range(141, 151)])), 3) for k in ('nbig2', 'lobe2', 'fan2', 'split')})
json.dump(R, open(os.path.join(VER, 'data', 'author_long_lobes.json'), 'w'), indent=1)
