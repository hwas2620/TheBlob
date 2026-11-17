#!/usr/bin/env python3
"""이주 실행 요약(먹이는 멀리 있는 유인원 하나, 저장소·섭취 없음). usage: summm.py RUN [RUN ...]. 창 = t>=200."""
import json, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
print('run                         이동  닿음   정맥최대성분(중앙/최소)  정맥∪시트  간선  순환  끝점/분기  몸조각  몸최대부피  hmin    진폭(시트)')
for r in sys.argv[1:]:
    f = os.path.join(HERE, 'runs', r, 'metrics.json')
    if not os.path.exists(f): print(r, '(없음)'); continue
    m = json.load(open(f)); gs = [g for g in m['gseries'] if g['t'] >= 200]
    if not gs: print(r, '창 없음'); continue
    lg = [g['vein']['largest'] for g in gs]; ws = [g['vein'].get('largest_ws') or 0 for g in gs]
    med = lambda x: float(np.median(x))
    print(f"{r:26s} {m['disp']:5.1f}  {str(m['t_touch']):8s} {med(lg):.2f} / {min(lg):.2f}            {med(ws):.2f}     {med([g['vein']['edges'] for g in gs]):5.0f} {med([g['vein']['cycles'] for g in gs]):4.0f}   {med([g['vein']['end_per_junc'] for g in gs]):.2f}      {gs[-1]['body']['comps']:4d}   {min(g['body']['largest_vol'] for g in gs):.3f}     {m['h_min_seen']:+.3f}  {m['hamp'].get('sheet_rel')}")
