"""이음 지키기가 남긴 관이 물질을 나르는지: 저장 상태마다 '두꺼운 몸(h>=0.3)의 큰 덩어리 둘 사이 얇은 칸'의 흐름(Qgross)과 관 굵기를 몸 평균과 비교.
python3 neck_flow.py RUN_DIR [...]"""
import os, sys, glob, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref'))
from ref_model import _torus_label
ALL = [(1, 0), (0, 1), (1, 1), (1, -1), (-1, 0), (0, -1), (-1, -1), (-1, 1)]
nb = lambda a, d: np.roll(a, (-d[1], -d[0]), (0, 1))
def geo(src, wet):
    N = wet.shape[0]; dist = np.where(src, 0.0, np.inf); fr = src.copy(); seen = src.copy(); it = 0
    while fr.any() and it < N:
        it += 1; m = np.zeros_like(wet)
        for d in ALL: m |= nb(fr, d)
        fr = m & wet & ~seen; dist[fr] = it; seen |= fr
    return dist
for rd in sys.argv[1:]:
    rows = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); Qg = np.max(Z['Qgross'].astype(float), axis=0); Cn = np.max(Z['C'].astype(float), axis=0)
        th = wet & (h >= 0.3); lt = _torus_label(th); nt = int(lt.max())
        if nt < 2: continue
        vt = np.bincount(lt.ravel(), weights=np.where(th, h, 0).ravel()); vt[0] = 0; big = [k for k in np.argsort(vt)[::-1] if vt[k] >= 0.1 * h[wet].sum()]
        if len(big) < 2: continue
        s = geo(lt == big[0], wet) + geo(lt == big[1], wet)
        if not np.isfinite(s[wet]).any(): continue
        neck = wet & (s <= s[wet].min() + 1) & ~th
        if neck.sum() < 2: continue
        rows.append((float(Z['t']), int(neck.sum()), np.median(h[neck]), np.median(Cn[neck]), np.median(Qg[neck]), np.median(Qg[wet])))
    if not rows: print(os.path.basename(rd), '이음 없음'); continue
    R = np.array(rows)
    print(f"{os.path.basename(rd)}: 이음이 있던 저장 상태 {len(R)}개 | 이음 칸 {np.median(R[:,1]):.0f} | 두께 {np.median(R[:,2]):.2f} | 관 C {np.median(R[:,3]):.1f} | 흐름 이음 {np.median(R[:,4]):.3f} 몸 {np.median(R[:,5]):.3f} (비 {np.median(R[:,4]/R[:,5]):.1f})")
