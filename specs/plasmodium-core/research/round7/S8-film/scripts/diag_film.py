"""얇은 막(h < 0.3인 젖은 칸) 진단. 이미 돌린 S7 결승 long 실행(s7c, s7k)의 저장 상태를 읽는다.
python3 diag_film.py [TAG ...]"""
import os, sys, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref'))
from ref_model import _torus_label
RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref/runs'))
tags = sys.argv[1:] or ['s7c', 's7k']; TS = [1600, 1700, 1800, 1900, 2000]
def load(run, t):
    Z = np.load(os.path.join(RUNS, run, f'vs_t{t:04d}.npz')); wet = Z['wet'].astype(bool)
    return wet, np.where(wet, Z['h'].astype(float), 0.0), Z['sage'].astype(float), Z['age'].astype(float), Z['C'].astype(float).max(0), Z['Qgross'].astype(float).max(0)
for tag in tags:
    rows = []
    for s in range(141, 151):
        run = f'b_long_s{s}_{tag}'; r = {}
        wet, h, sage, age, C, Qg = load(run, 1600); thin = wet & (h < 0.3); thick = wet & (h >= 0.3)
        V = h.sum(); r['n_thin'] = int(thin.sum()); r['v_thin'] = h[thin].sum() / V
        lw = _torus_label(wet); has_thick = np.zeros(lw.max() + 1, bool); has_thick[np.unique(lw[thick])] = True
        att = thin & has_thick[lw]; r['att'] = att.sum() / max(thin.sum(), 1)          # 두꺼운 몸과 같은 젖은 덩어리에 붙은 몫
        r['sage_thin'] = np.median(sage[thin]); r['sage_thick'] = np.median(sage[thick])
        hs = np.exp(-sage / 50.0); r['hs_thin'] = np.median(hs[thin])                       # 관 몫을 뺀 쉬는 두께(늙음만)
        r['C_thin'] = np.median(C[thin]); r['C_thin_gt1'] = (C[thin] > 1).mean(); r['Qg_thin'] = np.median(Qg[thin])
        r['h_thin'] = np.median(h[thin])
        surv = []
        for t in TS[1:]:
            w2, h2, *_ = load(run, t); surv.append(round(float((w2 & thin).sum() / max(thin.sum(), 1)), 2))
        r['surv'] = surv
        vt = []
        for t in TS:
            w2, h2, *_ = load(run, t); th2 = w2 & (h2 < 0.3); vt.append(int(th2.sum()))
        r['n_thin_t'] = vt; rows.append((s, r))
    print(f'== {tag}')
    for s, r in rows:
        print(s, ' '.join(f'{k}={v:.3g}' if isinstance(v, float) else f'{k}={v}' for k, v in r.items()))
    keys = ['n_thin', 'v_thin', 'att', 'sage_thin', 'sage_thick', 'hs_thin', 'C_thin', 'C_thin_gt1', 'Qg_thin', 'h_thin']
    print('median', ' '.join(f'{k}={np.median([r[k] for _, r in rows]):.3g}' for k in keys))
    print('surv mean', np.round(np.mean([r['surv'] for _, r in rows], 0), 2))
