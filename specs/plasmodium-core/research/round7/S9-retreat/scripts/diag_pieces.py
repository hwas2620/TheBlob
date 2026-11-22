"""t=2000 떨어진 얇은 조각(두꺼운 칸 없는 젖은 덩어리)의 모양: 조각 수, 칸 수, 평균 두께, 가늘기(둘레 칸 몫: 칸의 몇 %가 마른 이웃을 가졌나).
가늘기가 1에 가까우면 관 조각(한두 칸 폭의 줄), 작으면 넓은 막."""
import os, sys, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref'))
from ref_model import _torus_label
H = os.path.dirname(os.path.abspath(__file__)); RUNS = {'s8': os.path.join(H, '../../../../stage0/ref/runs'), 's9': os.path.join(H, '../model/runs')}
for tag in sys.argv[1:]:
    rows = []
    for s in (181, 182, 183):
        Z = np.load(os.path.join(RUNS[tag[:2]], f'b_long_s{s}_{tag}', 'vs_t2000.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'].astype(float), 0.0); V = h.sum()
        lw = _torus_label(w); thick = w & (h >= 0.3); ht = np.zeros(lw.max() + 1, bool); ht[np.unique(lw[thick])] = True
        nd = sum((~np.roll(np.roll(w, dy, 0), dx, 1)).astype(int) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
        for k in range(1, lw.max() + 1):
            if ht[k]: continue
            m = lw == k; rows.append((m.sum(), h[m].sum() / V, h[m].mean(), (nd[m] > 0).mean()))
    a = np.array(rows); v = a[:, 1]
    print(f'{tag:7s} pieces/run {len(a)/3:.0f}  vol share/run {v.sum()/3:.3f}  cells: median {np.median(a[:,0]):.0f}, vol-weighted mean {np.sum(v*a[:,0])/v.sum():.0f}  '
          f'mean h (vol-w) {np.sum(v*a[:,2])/v.sum():.3f}  rim share (vol-w) {np.sum(v*a[:,3])/v.sum():.2f}  vol in pieces with rim share>0.9: {v[a[:,3]>0.9].sum()/v.sum():.2f}')
