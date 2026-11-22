#!/usr/bin/env python3
"""[7차 S16] 셋째 거르기 판정. 기준은 ../SCREEN3.md (실행 전에 커밋, sha256은 ../screen3_sha256.txt).
아령·막·죽은 실·끝 줄은 S16 독립 검증자의 측정 코드(../verify/scripts/vlib.py)를 그대로 쓴다.
usage: screen3_s16.py [후보=s16gm]   (대조 s16c = 지금 모델, 같은 모델 복사본)"""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'verify', 'scripts'))
import vlib
cand = sys.argv[1] if len(sys.argv) > 1 else 's16gm'; C = 's16c'
LONG = range(291, 301); FOOD4 = range(291, 297); FOOD3 = (291, 292); MIG = range(291, 295)

def rd(scn, s, tag): return os.path.join(RUNS, f'b_{scn}_s{s}_{tag}')
def met(scn, s, tag): return json.load(open(os.path.join(rd(scn, s, tag), 'metrics.json')))

def long_stats(s, tag):
    d2 = []; d2l = []; out = []; cell = {'film': [], 'dead': [], 'endline': []}
    for f in sorted(glob.glob(os.path.join(rd('long', s, tag), 'vs_t*.npz'))):
        Z = np.load(f); S = {k: Z[k] for k in Z.files}; t = float(S['t'])
        if t < 200: continue
        w = S['wet'].astype(bool); h = S['h'].astype(float)
        lab, n = vlib.torus_label(w)
        x = vlib.dumbbell(w, h, lab_w=lab)['D2']; d2.append(x)
        if t >= 1000: d2l.append(x)
        vol = np.bincount(lab.ravel(), weights=np.where(w, h, 0.0).ravel())[1:]
        if t >= 1500:
            main = lab == np.argmax(vol) + 1
            S2 = dict(S); S2['wet'] = main; S2['h'] = np.where(main, h, 0.0); c = vlib.late_cells(S2)
            for k in cell: cell[k].append(c[k])
        if t >= 1600: out.append(1.0 - vol.max() / max(vol.sum(), 1e-12))
    return dict(fD2=float(np.mean(d2)), fD2_late=float(np.mean(d2l)), out_late=float(np.mean(out)), **{k: float(np.mean(v)) for k, v in cell.items()})

L = {tag: [long_stats(s, tag) for s in LONG] for tag in (C, cand)}
def mean(tag, k): return float(np.mean([r[k] for r in L[tag]]))
lines = []; ok = {}
def cond(key, text, val):
    ok[key] = bool(val); lines.append(f'{key} {text} → {"넘음" if val else "못 넘음"}')
for k in ('fD2', 'fD2_late', 'out_late', 'film', 'dead', 'endline'):
    lines.append(f'  long {k}: 대조 {mean(C, k):.3f} {[round(r[k], 3) for r in L[C]]}\n            후보 {mean(cand, k):.3f} {[round(r[k], 3) for r in L[cand]]}')
low = sum(1 for a, b in zip(L[C], L[cand]) if b['fD2'] < a['fD2'])
cond('D1', f'실 아령 비율(t 200~2000) ≤ 0.8배 그리고 후보가 낮은 시드 ≥ 7/10: {mean(cand, "fD2"):.3f} / {mean(C, "fD2"):.3f}, {low}/10',
     mean(cand, 'fD2') <= 0.8 * mean(C, 'fD2') and low >= 7)
cond('D2', f'늦은 실 아령 비율(t 1000~2000) ≤ 1배: {mean(cand, "fD2_late"):.3f} / {mean(C, "fD2_late"):.3f}', mean(cand, 'fD2_late') <= mean(C, 'fD2_late'))
cond('L1', f'늦은 몸 밖 부피 ≤ 0.5배: {mean(cand, "out_late"):.4f} / {mean(C, "out_late"):.4f}', mean(cand, 'out_late') <= 0.5 * mean(C, 'out_late'))
cond('L2', f'가장 큰 몸 안 막(t 1500~2000) ≤ 1배: {mean(cand, "film"):.0f} / {mean(C, "film"):.0f}', mean(cand, 'film') <= mean(C, 'film'))
cond('L3', f'가장 큰 몸 안 죽은 실 ≤ 1배: {mean(cand, "dead"):.0f} / {mean(C, "dead"):.0f}', mean(cand, 'dead') <= mean(C, 'dead'))
cond('L4', f'가장 큰 몸 안 끝 줄(가지 끝) ≤ 1.2배: {mean(cand, "endline"):.0f} / {mean(C, "endline"):.0f}', mean(cand, 'endline') <= 1.2 * mean(C, 'endline'))

allr = {C: 0, cand: 0}; late = []; early = []; dall = []
for s in FOOD4:
    a, b = met('food4', s, C)['t_touch'], met('food4', s, cand)['t_touch']
    allr[C] += all(x is not None for x in a); allr[cand] += all(x is not None for x in b)
    for i in range(4):
        if a[i] is not None and (b[i] is None or b[i] > a[i] + 50): late.append((s, i + 1, a[i], b[i]))
        if b[i] is not None and (a[i] is None or a[i] > b[i] + 50): early.append((s, i + 1, a[i], b[i]))
    dall.append(round(max(x if x is not None else 700.0 for x in b) - max(x if x is not None else 700.0 for x in a), 1))
    lines.append(f'  food4 s{s}: 대조 {a}  후보 {b}')
cond('F1', f'food4 모두 닿음 ≥ 대조 − 1, 늦음 ≤ 이름 + 2, 마지막 먹이 차이 중앙 ≤ +20: {allr[cand]} / {allr[C]}, 늦음 {len(late)} {late}, 이름 {len(early)}, 중앙 {float(np.median(dall)):+.1f} {dall}',
     allr[cand] >= allr[C] - 1 and len(late) <= len(early) + 2 and float(np.median(dall)) <= 20.0)
late3 = 0
for s in FOOD3:
    a, b = met('food3', s, C)['t_touch'], met('food3', s, cand)['t_touch']
    late3 += sum(1 for i in range(3) if a[i] is not None and (b[i] is None or b[i] > a[i] + 50))
cond('F2', f'food3 늦음 ≤ 1 (6쌍): {late3}', late3 <= 1)
good = 0
for s in MIG:
    a, b = met('mig', s, C), met('mig', s, cand); r = b['disp'] / a['disp']; q = b['area_end'] / a['area_end']; good += (r >= 0.8 and q <= 1.2)
    lines.append(f'  mig s{s}: 이동 {r:.2f}배, 끝 넓이 {q:.2f}배')
cond('M1', f'mig 이동 ≥ 0.8배·넓이 ≤ 1.2배인 쌍 ≥ 3/4: {good}/4', good >= 3)
bad = []; nr = 0
for scn, ss in (('long', LONG), ('food4', FOOD4), ('food3', FOOD3), ('mig', MIG)):
    for s in ss:
        b = met(scn, s, cand); n = vlib.torus_label(np.load(os.path.join(rd(scn, s, cand), 'wet.npy')).astype(bool))[1]; nr += 1
        if not (b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and b['V_crumb'] / b['V0'] < 0.01 and n == 1 and b.get('stop', '') in ('', None)):
            bad.append(f'{scn}{s}')
cond('H1', f'건강 (후보 {nr} 실행) 어긴 실행 {bad}', not bad)

print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('넘김' if all(ok.values()) else '탈락 (' + ', '.join(k for k, v in ok.items() if not v) + ')'))
json.dump(dict(cand=cand, ok=ok, long=L, food4=dict(late=late, early=early, dall=dall, allr=allr), food3_late=late3, mig_good=good),
          open(os.path.join(HERE, '..', 'screen3.json'), 'w'), indent=1, default=float)
