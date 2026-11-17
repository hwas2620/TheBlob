#!/usr/bin/env python3
"""먹이가 여럿일 때: 모든 쌍의 연결 요약. usage: summ3.py RUN [RUN ...]
창 = 모든 먹이에 닿은 뒤 20 시간단위부터 첫 먹이가 떨어질 때까지(없으면 끝까지)."""
import json, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for r in sys.argv[1:]:
    f = os.path.join(HERE, 'runs', r, 'metrics.json')
    if not os.path.exists(f): print(r, '(없음)'); continue
    m = json.load(open(f)); gs = m['gseries']; tt = m['t_touch']
    if any(v is None for v in tt): print(r, 'touch', tt, '모든 먹이에 닿지 못함'); continue
    ex = [v for v in (m.get('t_exh') or []) if v is not None]; t1 = min(ex) if ex else 1e9
    post = [g for g in gs if g['t'] >= max(tt) + 20 and g['t'] <= t1]
    if not post: print(r, '창 없음'); continue
    keys = sorted(post[0].get('path', {}))
    line = []
    for k in keys:
        P = [g['path'][k] for g in post]
        same = np.mean([bool(p.get('same_vein_comp')) for p in P])
        ratio = [((p.get('C_min') or 0) / max(g['vein']['C_p90'], 1e-9)) if p.get('connected') else 0.0 for g, p in zip(post, P)]
        cmin = [p.get('C_min') or 0 for p in P]
        line.append(f'{k}: 같은성분 {same:.2f}, minC/p90 중앙 {np.median(ratio):.2f}, Cmin 중앙 {np.median(cmin):.0f}')
    bv = [g['body']['largest_vol'] for g in post]; lg = [g['vein']['largest'] for g in post]
    print(f"{r:20s} 닿은 시각 {tt} 창 {post[0]['t']:.0f}-{post[-1]['t']:.0f} (n={len(post)}) | " + ' | '.join(line) + f" | 몸 최대성분 부피 최소 {min(bv):.3f} | 정맥 최대성분 중앙 {np.median(lg):.2f} | hmin {m['h_min_seen']:.3f} 음수 {m.get('neg_cellsteps')} | 간선 중앙 {np.median([g['vein']['edges'] for g in post]):.0f} 순환 {np.median([g['vein']['cycles'] for g in post]):.0f}")
