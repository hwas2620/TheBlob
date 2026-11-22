#!/usr/bin/env python3
"""[7차 S8] 얇은 막 거르기 판정. 기준은 ../SCREEN.md (실행 전에 커밋).
usage: screen_s8.py [--seeds 181,182,183]"""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'stage0')); REF = os.path.join(STAGE0, 'ref', 'runs'); SUM = os.path.join(HERE, '..', 'summaries')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S4-fan2', 'scripts')); from judge_s4 import long_stats
sys.path.insert(0, os.path.join(STAGE0, 'ref')); from ref_model import _torus_label
a = sys.argv[1:]; SEEDS = [int(x) for x in a[a.index('--seeds') + 1].split(',')] if '--seeds' in a else [181, 182, 183]
REFTAG = dict(s8k3='s8k', s8k1='s8k', s8c3='s8c', s8k='s8c')


def film(rd):
    """t >= 100 저장 상태: 큰 덩어리 둘 이상(nbig2), 조각 하나 최대(piece_max). t >= 1600: 얇은 칸 수(thin_late),
    떨어진 얇은 조각(두꺼운 칸이 하나도 없는 젖은 덩어리)의 부피 몫(det_late), 가장 큰 젖은 덩어리 밖 부피 몫 합(out_late)."""
    nb2 = []; thin = []; det = []; outl = []; piece = 0.0
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); t = float(Z['t'])
        if t < 100: continue
        wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); V = h.sum(); thick = wet & (h >= 0.3)
        lt = _torus_label(thick); vt = np.bincount(lt.ravel(), weights=h.ravel()); vt[0] = 0; nb2.append(int((vt >= 0.1 * V).sum() >= 2))
        lw = _torus_label(wet); vw = np.bincount(lw.ravel(), weights=h.ravel()); vw[0] = 0; srt = np.sort(vw[1:])[::-1]
        if len(srt) > 1: piece = max(piece, float(srt[1] / V))
        if t >= 1600:
            thin.append(int((wet & (h < 0.3)).sum())); ht = np.zeros(len(vw), bool); ht[np.unique(lw[thick])] = True; ht[0] = True
            det.append(float(vw[~ht].sum() / V)); outl.append(float(1 - srt[0] / V))
    return dict(nbig2=float(np.mean(nb2)), piece_max=piece, thin_late=float(np.mean(thin)), det_late=float(np.mean(det)), out_late=float(np.mean(outl)))


def stats(tag, s):
    rd = os.path.join(REF, f'b_long_s{s}_{tag}'); f = os.path.join(SUM, f'long_s{s}_{tag}.json')
    if not os.path.exists(os.path.join(rd, 'metrics.json')): return None
    if not os.path.exists(f):
        m = json.load(open(os.path.join(rd, 'metrics.json'))); r = long_stats(rd); r.update(film(rd))
        r.update(area_end=m['area_end'], neg_end=m['neg_end_cellsteps'], mass_err=m['mass_err_max'], V_crumb=m['V_crumb'] / m['V0'])
        json.dump(r, open(f, 'w'))
    return json.load(open(f))


K = ['split_frac', 'nbig2', 'piece_max', 'det_late', 'thin_late', 'out_late', 'area_end', 'V_crumb', 'neg_end', 'mass_err']
M = {}
for tag in ['s8c', 's8k', 's8k3', 's8k1', 's8c3']:
    rs = [stats(tag, s) for s in SEEDS]
    if any(r is None for r in rs): print(tag, '빠짐'); continue
    M[tag] = {k: float(np.mean([r[k] for r in rs])) for k in K}; M[tag]['neg_end'] = int(sum(r['neg_end'] for r in rs)); M[tag]['mass_err'] = max(r['mass_err'] for r in rs)
    print(f'{tag:5s} ' + ' '.join(f'{k}={M[tag][k]:.3g}' for k in K))
    for s, r in zip(SEEDS, rs): print(f'   s{s} ' + ' '.join(f'{k}={r[k]:.3g}' for k in K[:7]))
print()
for tag, rt in REFTAG.items():
    if tag == 's8k' or tag not in M or rt not in M: continue
    x, y = M[tag], M[rt]
    c1 = x['det_late'] <= 0.5 * y['det_late']; c2 = x['thin_late'] <= 0.85 * y['thin_late']
    c3 = x['split_frac'] <= y['split_frac'] + 0.03 and x['nbig2'] <= y['nbig2'] + 0.03; c4 = x['neg_end'] == 0 and x['mass_err'] < 1e-10
    print(f'{tag} (기준 {rt}): 1 떨어진 얇은 조각 절반 이하 {c1} ({x["det_late"]:.3f} vs {y["det_late"]:.3f}) | 2 얇은 칸 0.85배 이하 {c2} ({x["thin_late"]:.0f} vs {y["thin_late"]:.0f}) '
          f'| 3 갈라짐 나빠지지 않음 {c3} | 4 음수·부피 {c4} → {"넘김" if c1 and c2 and c3 and c4 else "탈락"}')
