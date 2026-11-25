"""S23: 갇히기 직전 장면에서 균핵 자리 고르기를 따로 재현해, 넓게 흐리는 폭(scl_tgs2)과 틈 메우기(scl_hole=4)에 따라 자리가 어떻게 바뀌는지 본다 (모델 코드와 같은 순서)."""
import os, sys, json, numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
from ref_model import _flood_top, _torus_label, nb, RING
def pick(h, w, s1=5, s2=0, hole=0, frac=0.7, tmin=1.2, tmax=5.0, h0=1.0):
    hw = np.where(w, np.maximum(h, 0), 0); G = gaussian_filter(hw, s1, mode='wrap', truncate=3.0); Gs = gaussian_filter(hw, s2, mode='wrap', truncate=3.0) if s2 > 0 else G
    lw = _torus_label(w); vol = np.bincount(lw.ravel(), weights=hw.ravel()); vol[0] = 0; b = int(np.argmax(vol)); bm = lw == b; Vb = float(hw[bm].sum()); fm = bm
    if hole >= 4:
        cl = bm.copy()
        for _ in range(2):
            d = cl.copy()
            for dd in RING: d |= nb(cl, dd)
            cl = d
        for _ in range(2):
            e = cl.copy()
            for dd in RING: e &= nb(cl, dd)
            cl = e
        cl |= bm; lo = _torus_label(~cl); so = np.bincount(lo.ravel()); so[0] = 0; fm = ~((lo > 0) & (lo == int(np.argmax(so))))
    T = _flood_top(Gs, fm, int(min(fm.sum(), Vb / (h0 * tmin))), thr=frac * float(Gs[bm].max()), amin=int(Vb / (h0 * tmax)) + 1)
    if hole >= 3:
        lo = _torus_label(~T); so = np.bincount(lo.ravel()); so[0] = 0; T = T | ((lo > 0) & (lo != int(np.argmax(so))))
    return T, Vb
if __name__ == '__main__':
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    R22 = os.path.join(HERE, '..', '..', 'S22-form', 'model', 'runs')
    cases = [('long', 641, 's22y'), ('long', 642, 's22y'), ('long', 645, 's22y'), ('slimeall', 652, 's22y'), ('slimeall', 655, 's22y'), ('slimeall', 686, 'v7y'), ('slimeall', 688, 'v7y'), ('slimeall', 684, 'v7y')]
    confs = [('s22y', dict()), ('hole4', dict(hole=4)), ('s2=10 hole4', dict(s2=10, hole=4)), ('s2=15 hole4', dict(s2=15, hole=4)), ('s2=10 hole4 f.6', dict(s2=10, hole=4, frac=0.6))]
    fig, ax = plt.subplots(len(cases), len(confs), figsize=(2.6 * len(confs), 2.6 * len(cases)))
    for i, (scn, s, tag) in enumerate(cases):
        d = os.path.join(R22, f'b_{scn}_s{s}_{tag}'); m = json.load(open(os.path.join(d, 'metrics.json'))); ts = m['t_scl']; tf = int(ts // 20 * 20)
        Z = np.load(os.path.join(d, f'vs_t{tf:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); N = w.shape[0]
        ys, xs = np.nonzero(w); cy = int(np.angle(np.exp(2j * np.pi * ys / N).mean()) * N / (2 * np.pi)) % N; cx = int(np.angle(np.exp(2j * np.pi * xs / N).mean()) * N / (2 * np.pi)) % N
        for j, (nm, kw) in enumerate(confs):
            T, Vb = pick(h, w, **kw); sh = lambda a: np.roll(a, (N // 2 - cy, N // 2 - cx), (0, 1))[N // 2 - 45:N // 2 + 45, N // 2 - 45:N // 2 + 45]
            a = ax[i, j]; a.imshow(sh(np.where(w, h, np.nan)), cmap='Greys', vmin=0, vmax=3, origin='lower'); a.contour(sh(T.astype(float)), [0.5], colors='r', linewidths=0.8)
            a.set_title(f'{scn} {s} {nm}\nA {int(T.sum())} V/A {Vb / max(T.sum(), 1):.2f}', fontsize=7); a.axis('off')
            print(scn, s, nm, int(T.sum()), round(Vb / max(T.sum(), 1), 2))
    plt.tight_layout(); plt.savefig(os.path.join(HERE, '..', 'fig', 'sitepick.png'), dpi=60)
