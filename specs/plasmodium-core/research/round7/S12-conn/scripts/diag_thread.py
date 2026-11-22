"""t=2000 실 칸(h < 0.3이면서 다리 칸)의 두께·관 굵기, 그리고 큰 두꺼운 덩어리 밖에 있는 두꺼운 칸(점)의 수와 부피."""
import os, sys, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '../model'))
from ref_model import _torus_label, RING, nb
for tag in sys.argv[1:]:
    for s in (181, 182, 183):
        Z = np.load(os.path.join(H, f'../model/runs/b_long_s{s}_{tag}/vs_t2000.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'].astype(float), 0.0); C = Z['C'].astype(float)
        Cn = np.zeros_like(h)
        for k, d in enumerate([(1, 0), (0, 1), (1, 1), (1, -1)]): Cn = np.maximum(Cn, np.maximum(C[k], nb(C[k], (-d[0], -d[1]))))
        xb = [~nb(w, d) for d in RING]; Nc = np.zeros(w.shape, np.int8)
        for q in (0, 2, 4, 6): Nc += xb[q].astype(np.int8) - (xb[q] & xb[q + 1] & xb[(q + 2) % 8]).astype(np.int8)
        th = w & (h < 0.3) & (Nc > 1); thick = w & (h >= 0.3); lt = _torus_label(thick); vt = np.bincount(lt.ravel(), weights=h.ravel()); vt[0] = 0
        small = (vt > 0) & (vt < 0.01 * h.sum()); dots = small[lt] & thick
        print(f'{tag} s{s}: thread cells {th.sum()}, h median {np.median(h[th]):.3f} (q90 {np.quantile(h[th], .9):.3f}), share h<0.05 {(h[th] < 0.05).mean():.2f}, Cn median {np.median(Cn[th]):.3f}, share Cn>=0.1 {(Cn[th] >= 0.1).mean():.2f} | '
              f'thread vol {h[th].sum() / h.sum():.4f} | dots: {int(small.sum())} pieces, vol {h[dots].sum() / h.sum():.4f}')
