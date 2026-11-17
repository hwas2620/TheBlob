#!/usr/bin/env python3
"""[verify5] 같은 시드에서 두 변형의 짝지은 비교. usage: pair.py ROOT seeds VA VB   (VA − VB)"""
import json, sys, os, numpy as np
from scipy.stats import wilcoxon
ROOT = sys.argv[1]; seeds = [int(x) for x in sys.argv[2].split(',')]; va, vb = sys.argv[3], sys.argv[4]
S = lambda r: json.load(open(os.path.join(ROOT, 'summ', r + '.json'))) if os.path.exists(os.path.join(ROOT, 'summ', r + '.json')) else None
M = lambda r: json.load(open(os.path.join(ROOT, 'runs', r, 'metrics.json')))
def rep(name, a, b, fmt='%+.3f', ratio=False):
    a = np.array(a, float); b = np.array(b, float); d = np.log(a / b) if ratio else a - b
    try: p = wilcoxon(d).pvalue
    except Exception: p = float('nan')
    extra = f" 비(기하평균) {np.exp(d.mean()):.2f}" if ratio else ''
    print(f"  {name:24s} {va} 중앙 {np.median(a):.3g} / {vb} 중앙 {np.median(b):.3g} | 차 평균 {fmt % d.mean()}{extra} | {va}>{vb}: {int((d > 0).sum())}/{len(d)} | Wilcoxon p={p:.3f}")
ss = [s for s in seeds if S(f'Ym_{va}_s{s}') and S(f'Ym_{vb}_s{s}')]
if ss:
    A = [S(f'Ym_{va}_s{s}') for s in ss]; B = [S(f'Ym_{vb}_s{s}') for s in ss]
    print(f'Ym: {va} − {vb}, 시드 {ss}')
    for k in ('vein4_largest_med', 'vein4_largest_min', 'vein10_largest_med', 'vein30_largest_med', 'cycles4_med', 'disp_track', 'vein4_E_med', 'vein30_E_med', 'area_end'): rep(k, [x[k] for x in A], [x[k] for x in B])
    rep('t_touch', [M(f'Ym_{va}_s{s}')['t_touch'][0] for s in ss], [M(f'Ym_{vb}_s{s}')['t_touch'][0] for s in ss])
ss = [s for s in seeds if S(f'Y3_{va}_s{s}') and S(f'Y3_{vb}_s{s}')]
if ss:
    A = [S(f'Y3_{va}_s{s}') for s in ss]; B = [S(f'Y3_{vb}_s{s}') for s in ss]
    print(f'Y3: {va} − {vb}, 시드 {ss}')
    rep('경로 최소 C (쌍별)', [max(x, 0.05) for o in A for x in o['pathminC_med'].values()], [max(x, 0.05) for o in B for x in o['pathminC_med'].values()], ratio=True)
    rep('경로 최소 C (실행 최소)', [max(min(o['pathminC_med'].values()), 0.05) for o in A], [max(min(o['pathminC_med'].values()), 0.05) for o in B], ratio=True)
    rep('병목 C 중앙 (쌍별)', [max(x, 0.05) for o in A for x in o['bottleneck_med'].values()], [max(x, 0.05) for o in B for x in o['bottleneck_med'].values()], ratio=True)
    rep('병목 C 창 최소 (쌍별)', [max(x, 0.05) for o in A for x in o['bottleneck_min'].values()], [max(x, 0.05) for o in B for x in o['bottleneck_min'].values()], ratio=True)
    for k in ('vein4_largest_med', 'vein30_largest_med', 'vein_medC_med', 'body_largest_vol_min', 'cycles4_med', 'm_h_min_seen'): rep(k, [x[k] for x in A], [x[k] for x in B])
