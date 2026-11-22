#!/usr/bin/env python3
"""[7차 S11] 관 기억 거르기 판정. 기준은 ../SCREEN.md (실행 전에 커밋).
기준 실행: s8c·s8k는 S8의 것(stage0/ref/runs), s9eti는 S9의 것(S9-retreat/model/runs). 모두 같은 코드다. 지표 정의는 S8 screen_s8.py와 같고, t=2000 조각 수(pieces_end)를 더했다."""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'stage0'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S4-fan2', 'scripts')); from judge_s4 import long_stats
sys.path.insert(0, os.path.join(STAGE0, 'ref')); from ref_model import _torus_label
S8SUM = os.path.join(HERE, '..', '..', 'S8-film', 'summaries'); REF = os.path.join(STAGE0, 'ref', 'runs')
K = ['split_frac', 'nbig2', 'piece_max', 'det_late', 'thin_late', 'out_late', 'area_end', 'pieces_end', 'V_crumb', 'neg_end', 'mass_err']


# film(): S8 screen_s8.py에서 그대로 옮김
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


MODEL_RUNS = os.path.join(HERE, '..', '..', 'S10-tip', 'model', 'runs'); S10SUM = os.path.join(HERE, '..', '..', 'S10-tip', 'summaries'); S9RUNS = os.path.join(HERE, '..', '..', 'S9-retreat', 'model', 'runs'); S9SUM = os.path.join(HERE, '..', '..', 'S9-retreat', 'summaries'); SUM = os.path.join(HERE, '..', 'summaries')
SEEDS = [181, 182, 183]


def stats(tag, s):
    if tag.startswith('s8'): rd = os.path.join(REF, f'b_long_s{s}_{tag}'); f = os.path.join(S8SUM, f'long_s{s}_{tag}.json')
    elif tag.startswith('s9'): rd = os.path.join(S9RUNS, f'b_long_s{s}_{tag}'); f = os.path.join(S9SUM, f'long_s{s}_{tag}.json')
    elif tag.startswith('s10'): rd = os.path.join(MODEL_RUNS, f'b_long_s{s}_{tag}'); f = os.path.join(S10SUM, f'long_s{s}_{tag}.json')
    else: rd = os.path.join(MODEL_RUNS, f'b_long_s{s}_{tag}'); f = os.path.join(SUM, f'long_s{s}_{tag}.json')
    if not os.path.exists(os.path.join(rd, 'metrics.json')): return None
    if not os.path.exists(f):
        m = json.load(open(os.path.join(rd, 'metrics.json'))); r = long_stats(rd); r.update(film(rd))
        r.update(area_end=m['area_end'], neg_end=m['neg_end_cellsteps'], mass_err=m['mass_err_max'], V_crumb=m['V_crumb'] / m['V0'])
        json.dump(r, open(f, 'w'))
    r = json.load(open(f))
    if 'pieces_end' not in r:      # [S10] t=2000: 가장 큰 젖은 덩어리 밖 조각 수
        Z = np.load(os.path.join(rd, 'vs_t2000.npz')); w = Z['wet'].astype(bool); r['pieces_end'] = int(_torus_label(w).max()) - 1
        json.dump(r, open(f, 'w'))
    return r


M = {}
TAGS = ['s11m1', 's11m3', 's11h', 's11mh']
for tag in ['s8c', 's10r'] + TAGS:
    rs = [stats(tag, s) for s in SEEDS]
    if any(r is None for r in rs): print(tag, '빠짐', [s for s, r in zip(SEEDS, rs) if r is None]); continue
    M[tag] = {k: float(np.mean([r[k] for r in rs])) for k in K}; M[tag]['neg_end'] = int(sum(r['neg_end'] for r in rs)); M[tag]['mass_err'] = max(r['mass_err'] for r in rs); M[tag]['V_crumb'] = max(r['V_crumb'] for r in rs)
    print(f'{tag:6s} ' + ' '.join(f'{k}={M[tag][k]:.3g}' for k in K))
    for s, r in zip(SEEDS, rs): print(f'   s{s} ' + ' '.join(f'{k}={r[k]:.3g}' for k in K[:8]))
print()
c = M.get('s8c')
for tag in TAGS:
    if tag not in M or c is None: continue
    x = M[tag]
    c1 = x['out_late'] <= 0.5 * c['out_late']; c2 = x['thin_late'] <= c['thin_late']
    c3 = x['split_frac'] <= 0.5 * c['split_frac'] and x['nbig2'] <= 0.5 * c['nbig2']; c4 = x['neg_end'] == 0 and x['mass_err'] < 1e-10 and x['V_crumb'] < 0.01
    print(f'{tag} (기준 s8c): 1 몸 밖 부피 절반 이하 {c1} ({x["out_late"]:.3f} vs {c["out_late"]:.3f}) | 2 얇은 칸 지금 이하 {c2} ({x["thin_late"]:.0f} vs {c["thin_late"]:.0f}) '
          f'| 3 갈라짐 절반 이하 {c3} ({x["split_frac"]:.3f}/{x["nbig2"]:.3f} vs {c["split_frac"]:.3f}/{c["nbig2"]:.3f}) | 4 음수·부피·버린 부피 {c4} (음수 {x["neg_end"]}, 버린 부피 최대 {x["V_crumb"]:.2g}) → {"넘김" if c1 and c2 and c3 and c4 else "탈락"}'
          f'  [관문 아님: 끝 넓이 {x["area_end"] / c["area_end"]:.2f}배, 끝 조각 수 {x["pieces_end"]:.0f} (지금 {c["pieces_end"]:.0f})]')
print('\nmig 181 (관문 아님)')
for tag in TAGS:
    f = os.path.join(MODEL_RUNS, f'b_mig_s181_{tag}', 'metrics.json')
    if not os.path.exists(f): print(f'  {tag} 빠짐'); continue
    m = json.load(open(f)); print(f'  {tag:6s} disp={m["disp"]} path_len={m["path_len"]} area_end={m["area_end"]} neg_end={m["neg_end_cellsteps"]} ret={m["ret_cellsteps"]}')
print('  (S10: s10r disp=82.51 path_len=92.44 area_end=2953; S9: s9c disp=74.99 area_end=3095)')
