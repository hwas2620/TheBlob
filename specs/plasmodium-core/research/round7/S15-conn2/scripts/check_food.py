#!/usr/bin/env python3
"""[7차 S15] 먹이·이주 확인 판정. 기준은 ../CHECK.md (확인 실행 전에 커밋).
usage: check_food.py <후보 꼬리표>   (대조는 s15c = 지금 모델, 같은 모델 복사본). S14 check_food.py에서 food4 부분을 뺐다(거르기 조건 5가 봄)."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label
cand = sys.argv[1]; C = 's15c'; SEEDS = (221, 222)
def met(scn, s, tag):
    f = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}', 'metrics.json')
    return json.load(open(f)) if os.path.exists(f) else None
def ncomp(scn, s, tag):
    w = np.load(os.path.join(RUNS, f'b_{scn}_s{s}_{tag}', 'wet.npy')).astype(bool); return int(_torus_label(w).max())
health = []; late = 0; lines = []
for s in SEEDS:
    a, b = met('food3', s, C), met('food3', s, cand)
    for k, (ta, tb) in enumerate(zip(a['t_touch'], b['t_touch'])):
        if ta is not None and (tb is None or tb > ta + 50): late += 1
    lines.append(f'  food3 s{s}: 대조 {a["t_touch"]} 후보 {b["t_touch"]} (통과 {a.get("pass")} → {b.get("pass")})')
c1 = late <= 1; lines.append(f'1 food3 늦음·못 닿음 {late} (≤ 1) → {c1}')
c2 = True
for s in SEEDS:
    a, b = met('mig', s, C), met('mig', s, cand)
    r = b['disp'] / a['disp']; q = b['area_end'] / a['area_end']; c2 &= (r >= 0.8) and (q <= 1.2)
    lines.append(f'  mig s{s}: 이동 대조 {a["disp"]} 후보 {b["disp"]} ({r:.2f}배), 끝 넓이 {a["area_end"]} → {b["area_end"]} ({q:.2f}배)')
lines.append(f'2 mig 이동 ≥ 0.8배, 끝 넓이 ≤ 1.2배 (두 시드 모두) → {c2}')
c3 = True
for scn in ('food3', 'mig'):
    for s in SEEDS:
        b = met(scn, s, cand); n = ncomp(scn, s, cand)
        good = b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and b['V_crumb'] / b['V0'] < 0.01 and n == 1
        c3 &= good; health.append(f'{scn}{s}: 음수 {b["neg_end_cellsteps"]} 부피오차 {b["mass_err_max"]:.1e} 버린 {b["V_crumb"] / b["V0"]:.1e} 덩어리 {n}')
lines.append('3 음수 0, 부피 오차 < 1e-10, 버린 부피 < 0.01, 끝 젖은 덩어리 1 (후보 4 실행) → ' + str(c3)); lines += ['  ' + x for x in health]
print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('넘김' if c1 and c2 and c3 else '탈락'))
