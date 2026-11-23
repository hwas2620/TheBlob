#!/usr/bin/env python3
"""verify2 덧붙인 보고 (판정 없음, CRITERIA_CHANGES 2):
  - 앞머리 수: 프레임마다 가장 큰 몸 안의 어린 칸(age < 10) 8-연결 무리 가운데 20칸 이상인 것의 수. "부채꼴 앞머리 하나" 를 보는 값
  - 죽은 실 변형의 짝 통계 (늦은 창)
  - 죽은 실 칸이 몸을 잇는 칸(빼면 몸이 갈라지는 칸)인지: 늦은 창 프레임에서 죽은 실 성분(기본 정의)을 하나씩 빼 보고 몸이 갈라지면 '잇는 실'
-> data/extra.json, logs/extra_out.txt
"""
import glob, json, os, re, sys
import numpy as np
from scipy.stats import wilcoxon
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import measure as Ms
D = os.path.join(HERE, '..', 'data'); RUNS = os.path.normpath(os.path.join(HERE, '..', '..', 'model', 'runs'))
seeds = list(range(311, 327)); name = lambda s, arm: f'b_long_s{s}_' + ('w16c' if arm == 'ctrl' else 'w16gm')
out = dict(); L = []
def say(*a): s = ' '.join(str(x) for x in a); L.append(s); print(s, flush=True)


def per_frame(Z):
    wet = Z['wet'].astype(bool); h = Z['h'].astype(float); age = Z['age'].astype(float); N = wet.shape[0]
    lab, n = Ms.torus_label(wet, 8); vol = np.bincount(lab.ravel(), weights=np.where(wet, h, 0).ravel()); vol[0] = -1; body = lab == int(np.argmax(vol))
    fl, nf = Ms.torus_label(body & (age < 10), 8); sz = np.bincount(fl.ravel())[1:] if nf else np.zeros(0)
    fronts = int((sz >= 20).sum())
    # dead thread components (primary) and whether each one joins the body
    F_ = np.zeros((N, N))
    for k, d in enumerate(Ms.DIRS):
        act = wet & Ms.nb(wet, d); q = np.where(act, Z['Qgross'][k], 0.0); F_ = np.maximum(F_, np.maximum(q, Ms.rev(q, d)))
    Fref = np.median(F_[body & (age >= 20)])
    line = body & ~Ms.in_full_block(wet, 3); ll, nl = Ms.torus_label(line, 8); s2 = np.bincount(ll.ravel()); s2[0] = 0
    dead = line & (s2[ll] >= 4) & (age >= 20) & (F_ < 0.1 * Fref)
    dl, nd = Ms.torus_label(dead, 8); joining = 0; dangling = 0
    for i in range(1, nd + 1):
        m = dl == i; _, nb_ = Ms.torus_label(body & ~m, 8)
        if nb_ >= 2: joining += int(m.sum())
        else: dangling += int(m.sum())
    return fronts, joining, dangling


res = {}
for s in seeds:
    for arm in ('ctrl', 'cand'):
        fs = sorted(glob.glob(os.path.join(RUNS, name(s, arm), 'vs_t*.npz')))
        rows = []
        for f in fs:
            Z = np.load(f); t = float(Z['t'])
            if t < 100: continue
            fr, jo, da = per_frame(Z); rows.append((t, fr, jo, da))
        res[name(s, arm)] = rows
    say('done', s)
out['frames'] = {k: [list(r) for r in v] for k, v in res.items()}


def agg(arm, col, lo, hi):
    return [float(np.mean([r[col] for r in res[name(s, arm)] if lo <= r[0] <= hi])) for s in seeds]


def ps(c, g):
    c = np.array(c); g = np.array(g); d = g - c
    p_less = float(wilcoxon(d, alternative='less').pvalue) if np.any(d) else 1.0
    p_gr = float(wilcoxon(d, alternative='greater').pvalue) if np.any(d) else 1.0
    return dict(ctrl_mean=round(c.mean(), 3), cand_mean=round(g.mean(), 3), p_less=round(p_less, 5), p_greater=round(p_gr, 5), n_lower=int((d < 0).sum()), n_higher=int((d > 0).sum()))


for col, lab in ((1, 'fronts_ge20'), (2, 'dead_joining_cells'), (3, 'dead_dangling_cells')):
    for wn, lo, hi in (('early', 100, 999.9), ('late', 1000, 2000)):
        out[f'{lab}_{wn}'] = ps(agg('ctrl', col, lo, hi), agg('cand', col, lo, hi))
        say(lab, wn, out[f'{lab}_{wn}'])
for wn, lo, hi in (('early', 100, 999.9), ('late', 1000, 2000)):
    for arm in ('ctrl', 'cand'):
        fr = [r[1] for s in seeds for r in res[name(s, arm)] if lo <= r[0] <= hi]
        out[f'fronts_hist_{wn}_{arm}'] = {int(k): int(v) for k, v in zip(*np.unique(fr, return_counts=True))}
        say('front count histogram', wn, arm, out[f'fronts_hist_{wn}_{arm}'])
# dead-thread variants, paired
FR = {json.load(open(f))['run']: json.load(open(f))['frames'] for f in glob.glob(os.path.join(D, 'frames', 'b_long_*.json'))}
for key in ('line=3|F0.03|smin=4', 'line=2|F0.03|smin=4', 'line=2|F0.1|smin=4', 'line=3|F0.3|smin=4', 'line=3|C1|smin=4', 'line=3|C0.5|smin=4'):
    c = [np.mean([x['dead'][key] for x in FR[name(s, 'ctrl')] if x['t'] >= 1000]) for s in seeds]; g = [np.mean([x['dead'][key] for x in FR[name(s, 'cand')] if x['t'] >= 1000]) for s in seeds]
    out[f'dead_{key}'] = ps(c, g); say('dead late', key, out[f'dead_{key}'])
json.dump(out, open(os.path.join(D, 'extra.json'), 'w'), indent=1)
open(os.path.join(HERE, '..', 'logs', 'extra_out.txt'), 'w').write('\n'.join(L) + '\n')
