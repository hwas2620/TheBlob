#!/usr/bin/env python3
"""[7차 S16] 둘째 결승(`s16gm`) 판정. 기준은 ../CRITERIA2.md (실행 전에 커밋, sha256은 ../criteria2_sha256.txt). screen3_s16.py에서 시드, asym3, 확인/반박 판정, 끝 구간 기록만 더했다.
아령·막·죽은 실·끝 줄은 S16 독립 검증자의 측정 코드(../verify/scripts/vlib.py)를 그대로 쓴다.
usage: judge_final2_s16.py [후보=s16gm]   (대조 s16c = 지금 모델, 같은 모델 복사본)"""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'verify', 'scripts'))
import vlib
cand = sys.argv[1] if len(sys.argv) > 1 else 's16gm'; C = 's16c'
LONG = range(301, 311); FOOD4 = range(301, 311); FOOD3 = range(301, 305); ASYM3 = (301, 302); MIG = range(301, 305)
from scipy import ndimage
def lumps(w, h):     # 끝 구간 덩이 수 (관문 아님): 한 칸 깎은 뒤 몸 부피 5% 이상 조각 수
    e = ndimage.binary_erosion(np.pad(w, 1, mode='wrap'), np.ones((3, 3), bool))[1:-1, 1:-1]
    lab, n = vlib.torus_label(e)
    if n == 0: return 0
    v = np.bincount(lab.ravel(), weights=np.where(e, h, 0.0).ravel())[1:]
    return int((v >= 0.05 * h[w].sum()).sum())

def rd(scn, s, tag): return os.path.join(RUNS, f'b_{scn}_s{s}_{tag}')
def met(scn, s, tag): return json.load(open(os.path.join(rd(scn, s, tag), 'metrics.json')))

def long_stats(s, tag):
    d2 = []; d2l = []; out = []; cell = {'film': [], 'dead': [], 'endline': []}; lmp = []
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
        if t >= 1800: lmp.append(lumps(w, np.where(w, h, 0.0)))
    return dict(fD2=float(np.mean(d2)), fD2_late=float(np.mean(d2l)), out_late=float(np.mean(out)), lumps_1800=float(np.mean(lmp)), **{k: float(np.mean(v)) for k, v in cell.items()})

L = {tag: [long_stats(s, tag) for s in LONG] for tag in (C, cand)}
def mean(tag, k): return float(np.mean([r[k] for r in L[tag]]))
lines = []; ok = {}
def cond(key, text, conf, refu):
    v = '확인' if conf and not refu else ('반박' if refu else '판정 못 함'); ok[key] = v; lines.append(f'{key} {text} → {v}')
for k in ('fD2', 'fD2_late', 'out_late', 'film', 'dead', 'endline', 'lumps_1800'):
    lines.append(f'  long {k}: 대조 {mean(C, k):.3f} {[round(r[k], 3) for r in L[C]]}\n            후보 {mean(cand, k):.3f} {[round(r[k], 3) for r in L[cand]]}')
low = sum(1 for a, b in zip(L[C], L[cand]) if b['fD2'] < a['fD2'])
cond('D1', f'실 아령 비율(t 200~2000) ≤ 0.8배 그리고 후보가 낮은 시드 ≥ 7/10: {mean(cand, "fD2"):.3f} / {mean(C, "fD2"):.3f}, {low}/10',
     mean(cand, 'fD2') <= 0.8 * mean(C, 'fD2') and low >= 7, mean(cand, 'fD2') >= mean(C, 'fD2'))
cond('D2', f'늦은 실 아령 비율(t 1000~2000) ≤ 1배: {mean(cand, "fD2_late"):.3f} / {mean(C, "fD2_late"):.3f}', mean(cand, 'fD2_late') <= mean(C, 'fD2_late'), mean(cand, 'fD2_late') > 1.3 * mean(C, 'fD2_late'))
cond('L1', f'늦은 몸 밖 부피 ≤ 0.5배: {mean(cand, "out_late"):.4f} / {mean(C, "out_late"):.4f}', mean(cand, 'out_late') <= 0.5 * mean(C, 'out_late'), mean(cand, 'out_late') >= mean(C, 'out_late'))
cond('L2', f'가장 큰 몸 안 막(t 1500~2000) ≤ 1배: {mean(cand, "film"):.0f} / {mean(C, "film"):.0f}', mean(cand, 'film') <= mean(C, 'film'), mean(cand, 'film') > 1.3 * mean(C, 'film'))
cond('L3', f'가장 큰 몸 안 죽은 실 ≤ 1배: {mean(cand, "dead"):.0f} / {mean(C, "dead"):.0f}', mean(cand, 'dead') <= mean(C, 'dead'), mean(cand, 'dead') > 1.3 * mean(C, 'dead'))
cond('L4', f'가장 큰 몸 안 끝 줄(가지 끝) ≤ 1.2배: {mean(cand, "endline"):.0f} / {mean(C, "endline"):.0f}', mean(cand, 'endline') <= 1.2 * mean(C, 'endline'), mean(cand, 'endline') > 1.5 * mean(C, 'endline'))

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
     allr[cand] >= allr[C] - 1 and len(late) <= len(early) + 2 and float(np.median(dall)) <= 20.0, allr[cand] <= allr[C] - 3 or len(late) >= len(early) + 5)
late3 = 0
for scn_, s in [('food3', x) for x in FOOD3] + [('asym3', x) for x in ASYM3]:
    a, b = met(scn_, s, C)['t_touch'], met(scn_, s, cand)['t_touch']
    late3 += sum(1 for i in range(3) if a[i] is not None and (b[i] is None or b[i] > a[i] + 50))
cond('F2', f'food3·asym3 늦음 (18쌍): {late3}', late3 <= 1, late3 >= 3)
good = 0
for s in MIG:
    a, b = met('mig', s, C), met('mig', s, cand); r = b['disp'] / a['disp']; q = b['area_end'] / a['area_end']; good += (r >= 0.8 and q <= 1.2)
    lines.append(f'  mig s{s}: 이동 {r:.2f}배, 끝 넓이 {q:.2f}배')
cond('M1', f'mig 이동 ≥ 0.8배·넓이 ≤ 1.2배인 쌍: {good}/4', good >= 3, good <= 1)
bad = []; nr = 0
for scn, ss in (('long', LONG), ('food4', FOOD4), ('food3', FOOD3), ('asym3', ASYM3), ('mig', MIG)):
    for s in ss:
        b = met(scn, s, cand); n = vlib.torus_label(np.load(os.path.join(rd(scn, s, cand), 'wet.npy')).astype(bool))[1]; nr += 1
        if not (b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and b['V_crumb'] / b['V0'] < 0.01 and n == 1 and b.get('stop', '') in ('', None)):
            bad.append(f'{scn}{s}')
cond('H1', f'건강 (후보 {nr} 실행) 어긴 실행 {bad}', not bad, bool(bad))

go = all(ok[k] == '확인' for k in ('D1', 'D2', 'L1', 'L2', 'L3', 'L4', 'H1')) and all(ok[k] != '반박' for k in ('F1', 'F2', 'M1'))
print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('독립 검증으로 간다' if go else '독립 검증으로 가지 않는다') + f'  {ok}')
os.makedirs(os.path.join(HERE, '..', 'summaries'), exist_ok=True)
json.dump(dict(cand=cand, ok=ok, go=go, long=L, food4=dict(late=late, early=early, dall=dall, allr=allr), food3_late=late3, mig_good=good),
          open(os.path.join(HERE, '..', 'summaries', 'judge_final2.json'), 'w'), indent=1, default=float)
