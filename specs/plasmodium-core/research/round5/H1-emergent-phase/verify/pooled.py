#!/usr/bin/env python3
"""[verify5] 작성자 시드 12개(21~26, 31~36) + 내 시드 6개(41~46)를 합친 집계와 짝지은 비교."""
import json, os, numpy as np
from scipy.stats import wilcoxon
SA = [21, 22, 23, 24, 25, 26, 31, 32, 33, 34, 35, 36]; SV = [41, 42, 43, 44, 45, 46]
def S(test, v, s):
    if s in SA: return json.load(open(f'../summ/{test}_{ {"tri": "tri96d"}.get(v, v) }_s{s}.json'.replace(' ', '')))
    return json.load(open(f'summ/{test}_{v}_s{s}.json'))
def M(test, v, s):
    if s in SA: return json.load(open(f'../runs/{test}_{ {"tri": "tri96d"}.get(v, v) }_s{s}/metrics.json'.replace(' ', '')))
    return json.load(open(f'runs/{test}_{v}_s{s}/metrics.json'))
ALL = SA + SV
print('=== 18 시드 합계 (작성자 12 + 새 시드 6)')
for v in ('base', 'wave', 'tri'):
    ym = [S('Ym', v, s) for s in ALL]; y3 = [S('Y3', v, s) for s in ALL]
    v4 = np.array([o['vein4_largest_med'] for o in ym])
    same = [x for o in y3 for x in o['same4'].values()]; pc = [x for o in y3 for x in o['pathminC_med'].values()]
    thick = [x >= 5 * o['vein_medC_med'] for o in y3 for x in o['pathminC_med'].values()]
    bd = [o['body_largest_vol_min'] for o in y3]; hm = [o['m_h_min_seen'] for o in y3]
    runs_ok = sum(all(x >= 0.9 for x in o['same4'].values()) and all(x >= 5 * o['vein_medC_med'] for x in o['pathminC_med'].values()) and o['body_largest_vol_min'] >= 0.9 for o in y3)
    print(f"{v:5s} Ym 정맥최대 {v4.min():.2f}~{v4.max():.2f} 중앙 {np.median(v4):.3f}, >=0.8: {int((v4 >= 0.8).sum())}/18, >=0.85: {int((v4 >= 0.85).sum())}/18 | Y3 같은 성분>=0.9: {sum(x >= 0.9 for x in same)}/54, 굵은 쌍 {sum(thick)}/54, 경로 최소 C {min(pc):.0f}~{max(pc):.0f} (중앙 {np.median(pc):.0f}), 몸<0.9: {sum(b < 0.9 for b in bd)}/18, 스텝 안 최소 두께<-0.1: {sum(h < -0.1 for h in hm)}/18 (최소 {min(hm):.3f}), 세 기준을 모두 통과한 실행 {runs_ok}/18")
def rep(name, a, b, ratio=False):
    a = np.array(a, float); b = np.array(b, float); d = np.log(a / b) if ratio else a - b
    print(f"  {name:28s} 차 평균 {d.mean():+.3f}" + (f" (비 {np.exp(d.mean()):.2f})" if ratio else '') + f" | 앞이 큰 경우 {int((d > 0).sum())}/{len(d)} | Wilcoxon p={wilcoxon(d).pvalue:.4f}")
for va, vb in (('tri', 'wave'), ('tri', 'base'), ('wave', 'base')):
    print(f'--- {va} − {vb} (18 시드 짝)')
    A = [S('Ym', va, s) for s in ALL]; B = [S('Ym', vb, s) for s in ALL]
    for k in ('vein4_largest_med', 'vein30_largest_med', 'cycles4_med', 'disp_track'): rep('Ym ' + k, [o[k] for o in A], [o[k] for o in B])
    rep('Ym 닿는 시각', [M('Ym', va, s)['t_touch'][0] for s in ALL], [M('Ym', vb, s)['t_touch'][0] for s in ALL])
    ta = np.array([M('Ym', va, s)['t_touch'][0] for s in ALL]); tb = np.array([M('Ym', vb, s)['t_touch'][0] for s in ALL]); pct = 100 * (ta / tb - 1)
    print(f"  Ym 닿는 시각 지연 %: 범위 {pct.min():+.1f}~{pct.max():+.1f}, 중앙 {np.median(pct):+.1f}")
    A = [S('Y3', va, s) for s in ALL]; B = [S('Y3', vb, s) for s in ALL]
    rep('Y3 경로 최소 C (쌍별)', [max(x, 0.05) for o in A for x in o['pathminC_med'].values()], [max(x, 0.05) for o in B for x in o['pathminC_med'].values()], ratio=True)
    rep('Y3 경로 최소 C (실행 최소)', [max(min(o['pathminC_med'].values()), 0.05) for o in A], [max(min(o['pathminC_med'].values()), 0.05) for o in B], ratio=True)
    rep('Y3 vein30_largest_med', [o['vein30_largest_med'] for o in A], [o['vein30_largest_med'] for o in B])
    rep('Y3 cycles4_med', [o['cycles4_med'] for o in A], [o['cycles4_med'] for o in B])
    tA = np.array([M('Y3', va, s)['t_touch'] for s in ALL], float); tB = np.array([M('Y3', vb, s)['t_touch'] for s in ALL], float); d = 100 * (tA / tB - 1); dl = 100 * (tA.max(1) / tB.max(1) - 1)
    print(f"  Y3 먹이별 닿는 시각 지연 % 중앙 {np.median(d[:,0]):+.1f}/{np.median(d[:,1]):+.1f}/{np.median(d[:,2]):+.1f} (최대 {d[:,0].max():+.1f}/{d[:,1].max():+.1f}/{d[:,2].max():+.1f}) | 마지막 먹이 지연 % 중앙 {np.median(dl):+.1f} (범위 {dl.min():+.1f}~{dl.max():+.1f})")
