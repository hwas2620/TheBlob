#!/usr/bin/env python3
"""[verify] 먹는 동안 창의 모든 표본×쌍에서 경로 최소 C 와 병목 C 의 분포(풀이별 비교용). usage: tube.py RUN ... ; 실험자 실행은 exp:RUN (gseries 의 C_min)"""
import json, os, sys, numpy as np, vmet
for a in sys.argv[1:]:
    if a.startswith('exp:'):
        r = a[4:]; m = json.load(open(f'../runs/{r}/metrics.json')); tt = m['t_touch']; ex = [v for v in m['t_exh'] if v is not None]
        W = [g for g in m['gseries'] if max(tt) + 20 <= g['t'] <= min(ex)]
        v = np.array([[(g['path'][k].get('C_min') or 0) for k in sorted(g['path'])] for g in W]); b = None
    else:
        r = a; o = vmet.summarise(f'runs/{r}', 'food', verbose=True); t0, t1, _ = o['window']
        W = [x for x in o['rows'] if t0 <= x['t'] <= t1 + 1e-6]
        v = np.array([[(x['pairs'][k]['path'] or {}).get('minC', 0.0) for k in sorted(x['pairs'])] for x in W]); b = np.array([[x['pairs'][k]['bottleneck'] for k in sorted(x['pairs'])] for x in W])
    f = lambda z: f"q25 {np.percentile(z,25):.0f} 중앙 {np.median(z):.0f} q75 {np.percentile(z,75):.0f} 로그평균 {np.exp(np.log(np.maximum(z,1e-3)).mean()):.0f}"
    late = v[len(v)//2:]
    print(f"{a:28s} 표본 {v.shape[0]}×{v.shape[1]} | 경로 최소 C: {f(v.ravel())} | 쌍별 중앙 {[int(x) for x in np.median(v,0)]} | 창 뒷절반 중앙 {np.median(late):.0f}" + (f" | 병목 C: {f(b.ravel())}" if b is not None else ''))
