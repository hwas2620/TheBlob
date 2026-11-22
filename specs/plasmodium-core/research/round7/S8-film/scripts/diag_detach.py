"""t=2000에 남은 떨어진 얇은 조각(두꺼운 칸 없는 젖은 덩어리)이 언제, 어떤 모습으로 몸에서 떨어졌는지 거꾸로 따라간다.
조각마다: 떨어진 시각(그 칸들이 두꺼운 칸 있는 덩어리에 마지막으로 속했던 저장 다음), 떨어지기 직전 그 칸들의 평균 두께,
떨어질 때 조각 부피 대비 t=2000 부피, 떨어진 뒤 두꺼운 칸(h>=0.3)이 있었는지."""
import os, sys, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref'))
from ref_model import _torus_label
RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref/runs'))
TS = list(range(20, 2001, 20))
def ld(run, t):
    Z = np.load(os.path.join(RUNS, run, f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); return w, np.where(w, Z['h'].astype(float), 0.0)
def one(run):
    st = {t: ld(run, t) for t in TS}
    w, h = st[2000]; V = h.sum(); lw = _torus_label(w); thick = w & (h >= 0.3)
    ht = np.zeros(lw.max() + 1, bool); ht[np.unique(lw[thick])] = True; ht[0] = False
    rows = []
    for k in range(1, lw.max() + 1):
        if ht[k]: continue
        m = lw == k; vk = h[m].sum()
        if vk < 1e-3 * V: continue
        tdet = None; hpre = np.nan; vpre = np.nan; thick_after = False
        for t in reversed(TS[:-1]):
            wt, hh = st[t]; l = _torus_label(wt); mm = m & wt
            if not mm.any(): tdet = t; break
            labs = np.unique(l[mm]); tk = wt & (hh >= 0.3)
            att = any(tk[l == q].any() for q in labs if q > 0)
            if att:
                tdet = t + 20; hpre = float(hh[mm].mean()); vpre = float(hh[mm].sum()); break
            if (hh[mm] >= 0.3).any(): thick_after = True
        rows.append((vk / V, tdet, hpre, vk / vpre if vpre == vpre else np.nan, thick_after))
    return rows
for tag in sys.argv[1:]:
    allr = []
    for s in (181, 182, 183):
        r = one(f'b_long_s{s}_{tag}'); allr += r
    a = np.array([[x[0], x[1] if x[1] else np.nan, x[2], x[3], float(x[4])] for x in allr])
    if not len(a): print(tag, 'no pieces'); continue
    wsum = a[:, 0].sum()
    print(f'{tag}: pieces {len(a)} (3 runs), detached vol share sum/3 = {wsum/3:.3f}')
    print(f'   detach time (vol-weighted mean) {np.nansum(a[:,0]*a[:,1])/wsum:.0f}; share detached after t>=1000: {a[a[:,1]>=1000,0].sum()/wsum:.2f}')
    print(f'   mean h of those cells just before detaching (vol-weighted) {np.nansum(a[:,0]*a[:,2])/wsum:.3f}; share that had h>=0.3 cells after detaching: {a[a[:,4]>0,0].sum()/wsum:.2f}')
    print(f'   volume at t=2000 / volume of same cells just before detach (vol-weighted) {np.nansum(a[:,0]*a[:,3])/wsum:.2f}')
    for x in sorted(allr, key=lambda x: -x[0])[:6]: print('     piece', np.round(x[0], 4), 'tdet', x[1], 'h_pre', np.round(x[2], 3), 'v2000/vpre', np.round(x[3], 2), 'thick_after', x[4])
