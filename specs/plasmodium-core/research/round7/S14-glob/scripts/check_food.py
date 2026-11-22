#!/usr/bin/env python3
"""[7차 S14] 먹이·이주 확인 판정. 기준은 ../CHECK.md (확인 실행 전에 커밋).
usage: check_food.py <후보 꼬리표>   (대조는 s14c = 지금 모델, 같은 모델 복사본)"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label
cand = sys.argv[1]; C = 's14c'
def met(scn, s, tag):
    f = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}', 'metrics.json')
    return json.load(open(f)) if os.path.exists(f) else None
def ncomp(scn, s, tag):
    w = np.load(os.path.join(RUNS, f'b_{scn}_s{s}_{tag}', 'wet.npy')).astype(bool); return int(_torus_label(w).max())
ok = True; health = []
late = 0; lines = []
for s in (181, 182):
    a, b = met('food3', s, C), met('food3', s, cand)
    for k, (ta, tb) in enumerate(zip(a['t_touch'], b['t_touch'])):
        if ta is not None and (tb is None or tb > ta + 50): late += 1
    lines.append(f'  food3 s{s}: 대조 {a["t_touch"]} 후보 {b["t_touch"]}')
c1 = late <= 1; lines.append(f'1 food3 늦음·못 닿음 {late} (≤ 1) → {c1}')
na = nb = 0
for s in (181, 182):
    a, b = met('food4', s, C), met('food4', s, cand)
    na += sum(t is not None for t in a['t_touch']); nb += sum(t is not None for t in b['t_touch'])
    lines.append(f'  food4 s{s}: 대조 {a["t_touch"]} 후보 {b["t_touch"]}')
c2 = nb >= na - 1; lines.append(f'2 food4 닿은 먹이 수 대조 {na} 후보 {nb} (≥ 대조 − 1) → {c2}')
c3 = True
for s in (181, 182):
    a, b = met('mig', s, C), met('mig', s, cand)
    r = b['disp'] / a['disp']; q = b['area_end'] / a['area_end']; c3 &= (r >= 0.8) and (q <= 1.2)
    lines.append(f'  mig s{s}: 이동 대조 {a["disp"]} 후보 {b["disp"]} ({r:.2f}배), 끝 넓이 {a["area_end"]} → {b["area_end"]} ({q:.2f}배)')
lines.append(f'3 mig 이동 ≥ 0.8배, 끝 넓이 ≤ 1.2배 (두 시드 모두) → {c3}')
c4 = True
for scn in ('food3', 'food4', 'mig'):
    for s in (181, 182):
        b = met(scn, s, cand); n = ncomp(scn, s, cand)
        good = b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and b['V_crumb'] / b['V0'] < 0.01 and n == 1
        c4 &= good; health.append(f'{scn}{s}: 음수 {b["neg_end_cellsteps"]} 부피오차 {b["mass_err_max"]:.1e} 버린 {b["V_crumb"] / b["V0"]:.1e} 덩어리 {n}')
lines.append('4 음수 0, 부피 오차 < 1e-10, 버린 부피 < 0.01, 끝 젖은 덩어리 1 (후보 6 실행) → ' + str(c4)); lines += ['  ' + x for x in health]
print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('넘김' if c1 and c2 and c3 and c4 else '탈락'))
