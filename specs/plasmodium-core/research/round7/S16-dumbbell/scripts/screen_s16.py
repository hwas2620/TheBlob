#!/usr/bin/env python3
"""[7차 S16] 거르기 판정. 기준은 ../SCREEN.md (거르기 실행 전에 커밋).
usage: screen_s16.py [후보 꼬리표=s16g]   (대조는 s16c = 지금 모델, 같은 모델 복사본)"""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, HERE)
from shape import nbig, tlab
from diag4 import linemask
cand = sys.argv[1] if len(sys.argv) > 1 else 's16g'; C = 's16c'
LONG = (241, 242, 243); FOOD4 = range(241, 247); SMALL = (241, 242)

def rd(scn, s, tag): return os.path.join(RUNS, f'b_{scn}_s{s}_{tag}')
def met(scn, s, tag): return json.load(open(os.path.join(rd(scn, s, tag), 'metrics.json')))

def long_stats(s, tag):
    b6 = []; out = []; thin = []; lmain = []
    for f in sorted(glob.glob(os.path.join(rd('long', s, tag), 'vs_t*.npz'))):
        Z = np.load(f); t = float(Z['t']); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0)
        if t >= 100: b6.append(nbig(h, w, 0.6) >= 2)
        lab, n = tlab(w)
        vol = np.bincount(lab.ravel(), weights=h.ravel())[1:] if n else np.zeros(1)
        if t >= 1600:
            out.append(1.0 - vol.max() / max(vol.sum(), 1e-12)); thin.append(int((w & (h < 0.3)).sum()))
        if 1000 <= t <= 1500 and n: lmain.append(int(linemask(lab == np.argmax(vol) + 1).sum()))
    wE = np.load(os.path.join(rd('long', s, tag), 'wet.npy')).astype(bool)
    return dict(big2_06=float(np.mean(b6)), out_late=float(np.mean(out)), thin_late=float(np.mean(thin)),
                line_end=int(linemask(wE).sum()), line_main=float(np.mean(lmain)), area_end=int(wE.sum()))

L = {tag: [long_stats(s, tag) for s in LONG] for tag in (C, cand)}
def mean(tag, k): return float(np.mean([r[k] for r in L[tag]]))
lines = []; ok = {}
def cond(key, text, val):
    ok[key] = bool(val); lines.append(f'{key} {text} → {"넘음" if val else "못 넘음"}')
for k in ('big2_06', 'out_late', 'thin_late', 'line_end', 'line_main', 'area_end'):
    lines.append(f'  long {k}: 대조 {mean(C, k):.3f} {[round(r[k], 3) for r in L[C]]}  후보 {mean(cand, k):.3f} {[round(r[k], 3) for r in L[cand]]}')
cond('L1', f'아령(큰 굵은 덩이 둘 이상, h≥0.6) ≤ 0.5배: {mean(cand, "big2_06"):.3f} / {mean(C, "big2_06"):.3f}', mean(cand, 'big2_06') <= 0.5 * mean(C, 'big2_06'))
cond('L2', f'늦은 몸 밖 부피 ≤ 0.5배: {mean(cand, "out_late"):.4f} / {mean(C, "out_late"):.4f}', mean(cand, 'out_late') <= 0.5 * mean(C, 'out_late'))
cond('L3', f'늦은 얇은 칸 ≤ 1배: {mean(cand, "thin_late"):.0f} / {mean(C, "thin_late"):.0f}', mean(cand, 'thin_late') <= mean(C, 'thin_late'))
cond('L4', f'끝 줄 칸 ≤ 1배: {mean(cand, "line_end"):.0f} / {mean(C, "line_end"):.0f}', mean(cand, 'line_end') <= mean(C, 'line_end'))
cond('L5', f'몸 안 줄 칸(t 1000~1500) ≤ 1.2배: {mean(cand, "line_main"):.0f} / {mean(C, "line_main"):.0f}', mean(cand, 'line_main') <= 1.2 * mean(C, 'line_main'))

allr = {C: 0, cand: 0}; late = []; dall = []
for s in FOOD4:
    a, b = met('food4', s, C)['t_touch'], met('food4', s, cand)['t_touch']
    allr[C] += all(x is not None for x in a); allr[cand] += all(x is not None for x in b)
    for i in range(4):
        if a[i] is not None and (b[i] is None or b[i] > a[i] + 50): late.append((s, i + 1, a[i], b[i]))
    ta = max(x if x is not None else 700.0 for x in a); tb = max(x if x is not None else 700.0 for x in b); dall.append(round(tb - ta, 1))
    lines.append(f'  food4 s{s}: 대조 {a}  후보 {b}')
cond('F1', f'food4 모두 닿음 ≥ 대조: {allr[cand]} / {allr[C]}', allr[cand] >= allr[C])
cond('F2', f'food4 늦음 ≤ 1 (24쌍): {len(late)} {late}', len(late) <= 1)
cond('F3', f'food4 마지막 먹이 시각 차이 중앙 ≤ +20: {float(np.median(dall)):+.1f} {dall}', float(np.median(dall)) <= 20.0)

late3 = 0
for s in SMALL:
    a, b = met('food3', s, C)['t_touch'], met('food3', s, cand)['t_touch']
    late3 += sum(1 for i in range(3) if a[i] is not None and (b[i] is None or b[i] > a[i] + 50))
    lines.append(f'  food3 s{s}: 대조 {a}  후보 {b}')
cond('F4', f'food3 늦음 ≤ 1 (6쌍): {late3}', late3 <= 1)
m_ok = True
for s in SMALL:
    a, b = met('mig', s, C), met('mig', s, cand); r = b['disp'] / a['disp']; q = b['area_end'] / a['area_end']
    m_ok &= (r >= 0.8) and (q <= 1.2)
    lines.append(f'  mig s{s}: 이동 {a["disp"]} → {b["disp"]} ({r:.2f}배), 끝 넓이 {a["area_end"]} → {b["area_end"]} ({q:.2f}배)')
cond('M1', 'mig 이동 ≥ 0.8배, 끝 넓이 ≤ 1.2배 (두 시드 모두)', m_ok)

h_ok = True; bad = []
runs = [('long', s) for s in LONG] + [('food4', s) for s in FOOD4] + [(x, s) for x in ('food3', 'mig') for s in SMALL]
for scn, s in runs:
    b = met(scn, s, cand); n = tlab(np.load(os.path.join(rd(scn, s, cand), 'wet.npy')).astype(bool))[1]
    g = b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and b['V_crumb'] / b['V0'] < 0.01 and n == 1 and b.get('stop', '') in ('', None)
    h_ok &= g
    if not g: bad.append(f'{scn}{s}: 음수 {b["neg_end_cellsteps"]} 부피오차 {b["mass_err_max"]:.1e} 버린 {b["V_crumb"] / b["V0"]:.1e} 덩어리 {n} stop {b.get("stop")}')
cond('H1', f'건강 (후보 {len(runs)} 실행: 음수 0, 부피 오차 < 1e-10, 버린 부피 < 0.01, 끝 젖은 덩어리 1) {bad}', h_ok)

print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('넘김' if all(ok.values()) else '탈락 (' + ', '.join(k for k, v in ok.items() if not v) + ')'))
json.dump(dict(cand=cand, ok=ok, long={t: L[t] for t in L}, food4_late=late, food4_dall=dall, food3_late=late3),
          open(os.path.join(HERE, '..', 'screen.json'), 'w'), indent=1, default=float)
