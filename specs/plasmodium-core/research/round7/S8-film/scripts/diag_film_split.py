"""t=1600의 얇은 칸을 '두꺼운 몸과 같은 젖은 덩어리에 붙은 것'과 '떨어진 조각(두꺼운 칸 없는 젖은 덩어리)'으로 나눠, 각각 +200 시간 뒤 남은 부피를 잰다."""
import os, sys, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref'))
from ref_model import _torus_label
RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref/runs'))
def ld(run, t):
    Z = np.load(os.path.join(RUNS, run, f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); return w, np.where(w, Z['h'].astype(float), 0.0)
for tag in ['s7c', 's7k']:
    out = []
    for s in range(141, 151):
        run = f'b_long_s{s}_{tag}'; w, h = ld(run, 1600); thin = w & (h < 0.3); thick = w & (h >= 0.3); V = h.sum()
        lw = _torus_label(w); ht = np.zeros(lw.max() + 1, bool); ht[np.unique(lw[thick])] = True; ht[0] = False
        att = thin & ht[lw]; det = thin & ~ht[lw]
        w2, h2 = ld(run, 1800); w3, h3 = ld(run, 2000)
        out.append([h[att].sum() / V, h[det].sum() / V, h2[att].sum() / max(h[att].sum(), 1e-9), h2[det].sum() / max(h[det].sum(), 1e-9), h3[det].sum() / max(h[det].sum(), 1e-9)])
    o = np.array(out)
    print(tag, 'share of body: attached thin %.3f detached thin %.3f | left after 200: attached %.2f detached %.2f | detached after 400: %.2f' % tuple(o.mean(0)))
    print('   detached share per seed', o[:, 1].round(3), ' left@400', o[:, 4].round(2))
