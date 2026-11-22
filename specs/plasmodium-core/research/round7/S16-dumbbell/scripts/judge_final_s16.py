#!/usr/bin/env python3
"""[7차 S16] 결승 판정. 기준은 ../CRITERIA.md (결승 실행 전에 커밋, sha256은 ../criteria_sha256.txt).
usage: judge_final_s16.py [후보=s16gh]   (대조 s16c = 지금 모델, 같은 모델 복사본)"""
import json, os, sys, glob
import numpy as np
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
from shape import nbig, tlab
from diag4 import linemask
from ref_model import rev, DIRS
cand = sys.argv[1] if len(sys.argv) > 1 else 's16gh'; C = 's16c'
SEEDS = dict(long=range(261, 271), food4=range(261, 271), food3=range(261, 265), mig=range(261, 265), asym3=(261, 262))

def rd(scn, s, tag): return os.path.join(RUNS, f'b_{scn}_s{s}_{tag}')
def met(scn, s, tag): return json.load(open(os.path.join(rd(scn, s, tag), 'metrics.json')))
def node_C(Cs):
    Cn = np.zeros(Cs.shape[1:])
    for k, d in enumerate(DIRS): Cn = np.maximum(Cn, np.maximum(Cs[k], rev(Cs[k], d)))
    return Cn
def lumps(w, h):     # 한 칸 깎은 뒤 몸 부피 5% 이상 조각 수 (S15 결승의 끝 덩이 수와 같은 뜻)
    # 토러스: 가장자리에 걸친 칸도 바르게 깎이도록 한 칸 감싸서 깎는다
    big = np.pad(w, 1, mode='wrap'); e = ndimage.binary_erosion(big, np.ones((3, 3), bool))[1:-1, 1:-1]
    lab, n = tlab(e)
    if n == 0: return 0
    v = np.bincount(lab.ravel(), weights=np.where(e, h, 0.0).ravel())[1:]
    return int((v >= 0.05 * h[w].sum()).sum())

def long_stats(s, tag):
    b6 = []; out = []; thin = []; lmain = []; llive = []; ldead = []; endl = []; endthick = []
    for f in sorted(glob.glob(os.path.join(rd('long', s, tag), 'vs_t*.npz'))):
        Z = np.load(f); t = float(Z['t']); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0)
        if t >= 100: b6.append(nbig(h, w, 0.6) >= 2)
        lab, n = tlab(w)
        vol = np.bincount(lab.ravel(), weights=h.ravel())[1:] if n else np.zeros(1)
        if t >= 1600:
            out.append(1.0 - vol.max() / max(vol.sum(), 1e-12)); thin.append(int((w & (h < 0.3)).sum()))
        if (1000 <= t <= 1500 or t >= 1800) and n:
            Lm = linemask(lab == np.argmax(vol) + 1); Cn = node_C(Z['C'])
            if t <= 1500:
                lmain.append(int(Lm.sum())); llive.append(int((Lm & (Cn >= 9.0)).sum())); ldead.append(int((Lm & (Cn < 9.0)).sum()))
            else:
                endl.append(lumps(w, h)); endthick.append(float(h[Lm & (Cn < 9.0) & (h >= 0.3)].sum() / h[w].sum()))
    wE = np.load(os.path.join(rd('long', s, tag), 'wet.npy')).astype(bool)
    return dict(big2_06=float(np.mean(b6)), out_late=float(np.mean(out)), thin_late=float(np.mean(thin)), line_end=int(linemask(wE).sum()),
                line_main=float(np.mean(lmain)), line_live=float(np.mean(llive)), line_dead=float(np.mean(ldead)), area_end=int(wE.sum()),
                lumps_1800=float(np.mean(endl)), deadthick_1800=float(np.mean(endthick)))

def verdict(conf, refu): return '확인' if conf and not refu else ('반박' if refu else '판정 못 함')
lines = []; V = {}
L = {tag: [long_stats(s, tag) for s in SEEDS['long']] for tag in (C, cand)}
def mean(tag, k): return float(np.mean([r[k] for r in L[tag]]))
for k in ('big2_06', 'out_late', 'thin_late', 'line_end', 'line_main', 'line_live', 'line_dead', 'area_end', 'lumps_1800', 'deadthick_1800'):
    lines.append(f'  long {k}: 대조 {mean(C, k):.3f}  후보 {mean(cand, k):.3f}   후보 시드별 {[round(r[k], 3) for r in L[cand]]}')
lower = sum(1 for a, b in zip(L[C], L[cand]) if b['big2_06'] < a['big2_06'])
V['F1'] = verdict(mean(cand, 'big2_06') <= 0.5 * mean(C, 'big2_06') and lower >= 7, mean(cand, 'big2_06') >= mean(C, 'big2_06'))
lines.append(f"F1 아령 {mean(cand, 'big2_06'):.3f} / {mean(C, 'big2_06'):.3f}, 후보가 낮은 시드 {lower}/10 → {V['F1']}")
for key, k, conf_x, ref_x, name in (('F2', 'out_late', 0.5, 1.0, '늦은 몸 밖 부피'), ('F3', 'thin_late', 1.0, 1.3, '늦은 얇은 칸'),
                                    ('F4', 'line_end', 1.0, 1.3, '끝 줄 칸'), ('F5', 'line_dead', 1.0, 1.3, '몸 안 죽은 실')):
    a, b = mean(C, k), mean(cand, k)
    V[key] = verdict(b <= conf_x * a, (b >= a) if key == 'F2' else (b > ref_x * a))
    lines.append(f'{key} {name} {b:.3f} / {a:.3f} → {V[key]}')

# G3 mig 4쌍
good = 0
for s in SEEDS['mig']:
    a, b = met('mig', s, C), met('mig', s, cand); r = b['disp'] / a['disp']; q = b['area_end'] / a['area_end']; good += (r >= 0.8 and q <= 1.2)
    lines.append(f'  mig s{s}: 이동 {r:.2f}배, 끝 넓이 {q:.2f}배')
V['G3'] = verdict(good >= 3, good <= 1); lines.append(f"G3 mig 이동 ≥ 0.8배·넓이 ≤ 1.2배인 쌍 {good}/4 → {V['G3']}")
# G4 food3 4쌍 + asym3 2쌍
late4 = []
for scn in ('food3', 'asym3'):
    for s in SEEDS[scn]:
        a, b = met(scn, s, C)['t_touch'], met(scn, s, cand)['t_touch']
        late4 += [(scn, s, i + 1) for i in range(len(a)) if a[i] is not None and (b[i] is None or b[i] > a[i] + 50)]
V['G4'] = verdict(len(late4) <= 1, len(late4) >= 3); lines.append(f"G4 food3·asym3 늦음 {len(late4)} {late4} → {V['G4']}")
# G5 food4 10쌍 (40 먹이쌍)
allr = {C: 0, cand: 0}; late = []; early = []; dall = []; perfood = [[] for _ in range(4)]
for s in SEEDS['food4']:
    a, b = met('food4', s, C)['t_touch'], met('food4', s, cand)['t_touch']
    allr[C] += all(x is not None for x in a); allr[cand] += all(x is not None for x in b)
    for i in range(4):
        if a[i] is not None and (b[i] is None or b[i] > a[i] + 50): late.append((s, i + 1, a[i], b[i]))
        if b[i] is not None and (a[i] is None or a[i] > b[i] + 50): early.append((s, i + 1, a[i], b[i]))
        if a[i] is not None and b[i] is not None: perfood[i].append(round(b[i] - a[i], 1))
    dall.append(round(max(x if x is not None else 700.0 for x in b) - max(x if x is not None else 700.0 for x in a), 1))
    lines.append(f'  food4 s{s}: 대조 {a}  후보 {b}')
med = float(np.median(dall))
V['G5'] = verdict(allr[cand] >= allr[C] - 1 and len(late) <= len(early) + 2 and med <= 20.0, allr[cand] <= allr[C] - 3 or len(late) >= len(early) + 5)
lines.append(f"G5 food4 모두 닿음 {allr[cand]} / {allr[C]}, 늦음 {len(late)} {late}, 이름 {len(early)}, 마지막 먹이 차이 중앙 {med:+.1f} {dall} → {V['G5']}")
lines.append(f'  (관문 아님) 먹이별 평균 차이 (둘 다 닿은 쌍): {[round(float(np.mean(p)), 1) if p else None for p in perfood]}')
# G6 건강 (후보 30 실행)
bad = []; n_runs = 0
for scn, ss in SEEDS.items():
    for s in ss:
        b = met(scn, s, cand); n = tlab(np.load(os.path.join(rd(scn, s, cand), 'wet.npy')).astype(bool))[1]; n_runs += 1
        if not (b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and b['V_crumb'] / b['V0'] < 0.01 and n == 1 and b.get('stop', '') in ('', None)):
            bad.append(f'{scn}{s}: 음수 {b["neg_end_cellsteps"]} 부피오차 {b["mass_err_max"]:.1e} 버린 {b["V_crumb"] / b["V0"]:.1e} 조각 {n} stop {b.get("stop")}')
V['G6'] = '확인' if not bad else '반박'; lines.append(f"G6 건강 (후보 {n_runs} 실행) 어긴 실행 {bad} → {V['G6']}")

go = all(V[k] == '확인' for k in ('F1', 'F2', 'F3', 'F4', 'F5', 'G6')) and all(V[k] != '반박' for k in ('G3', 'G4', 'G5'))
print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('독립 검증으로 간다' if go else '독립 검증으로 가지 않는다') + f'  {V}')
os.makedirs(os.path.join(HERE, '..', 'summaries'), exist_ok=True)
json.dump(dict(cand=cand, verdicts=V, go=go, long=L, food4=dict(late=late, early=early, dall=dall, allr=allr), g4_late=late4),
          open(os.path.join(HERE, '..', 'summaries', 'judge_final.json'), 'w'), indent=1, default=float)
