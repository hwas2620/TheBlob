#!/usr/bin/env python3
"""[verify5] 닿는 시각의 지연(base 대비 %). usage: delay.py ROOT seeds 변형 ...  (Ym: 목표 원반, Y3: 먹이별·마지막 먹이, 먹이가 떨어진 시각)"""
import json, sys, os, numpy as np
ROOT = sys.argv[1]; seeds = [int(x) for x in sys.argv[2].split(',')]
M = lambda r: json.load(open(os.path.join(ROOT, 'runs', r, 'metrics.json'))) if os.path.exists(os.path.join(ROOT, 'runs', r, 'metrics.json')) else None
for v in sys.argv[3:]:
    ss = [s for s in seeds if M(f'Ym_{v}_s{s}') and M(f'Ym_base_s{s}')]
    if ss:
        d = np.array([100 * (M(f'Ym_{v}_s{s}')['t_touch'][0] / M(f'Ym_base_s{s}')['t_touch'][0] - 1) for s in ss])
        dc = np.array([100 * (M(f'Ym_{v}_s{s}')['t_cover'][0] / M(f'Ym_base_s{s}')['t_cover'][0] - 1) if (M(f'Ym_{v}_s{s}')['t_cover'][0] and M(f'Ym_base_s{s}')['t_cover'][0]) else np.nan for s in ss])
        print(f"Ym {v:9s} n={len(ss)} 닿는 시각 지연 % 범위 {d.min():+.1f}~{d.max():+.1f} 중앙 {np.median(d):+.1f} 평균 {d.mean():+.1f} (늦은 시드 {int((d > 0).sum())}/{len(d)}) | 원반 절반 덮는 시각 지연 % 중앙 {np.nanmedian(dc):+.1f} 범위 {np.nanmin(dc):+.1f}~{np.nanmax(dc):+.1f}")
    ss = [s for s in seeds if M(f'Y3_{v}_s{s}') and M(f'Y3_base_s{s}')]
    if ss:
        a = np.array([M(f'Y3_{v}_s{s}')['t_touch'] for s in ss], float); b = np.array([M(f'Y3_base_s{s}')['t_touch'] for s in ss], float)
        d = 100 * (a / b - 1); dl = 100 * (a.max(1) / b.max(1) - 1)
        ea = np.array([[x if x is not None else np.nan for x in M(f'Y3_{v}_s{s}')['t_exh']] for s in ss], float); eb = np.array([[x if x is not None else np.nan for x in M(f'Y3_base_s{s}')['t_exh']] for s in ss], float)
        print(f"Y3 {v:9s} n={len(ss)} 먹이별 닿는 시각 지연 % 중앙 (20°/140°/260°) {np.median(d[:,0]):+.1f}/{np.median(d[:,1]):+.1f}/{np.median(d[:,2]):+.1f}, 최대 {d[:,0].max():+.1f}/{d[:,1].max():+.1f}/{d[:,2].max():+.1f} | 마지막 먹이 지연 % 중앙 {np.median(dl):+.1f} 범위 {dl.min():+.1f}~{dl.max():+.1f} | 닿는 시각 평균 {a.mean(0).round(1).tolist()} (base {b.mean(0).round(1).tolist()}) | 먹이 떨어진 시각 평균 {np.nanmean(ea,0).round(0).tolist()} (base {np.nanmean(eb,0).round(0).tolist()})")
