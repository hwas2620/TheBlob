"""S23 둘째 거르기 뒤 진단: 균핵 자리의 가장 작은 넓이(부피 / (h0 × 채움 두께))를 바꿔 보며, 갇히기 직전 장면에서 쉼 두께(방울 모양 포함)를 따로 만든다.
python3 tfill.py   (첫 거르기 long 721~730·slimeall 731~736 의 s23z, 둘째 거르기 long 741~750·slimeall 751~756 의 s23w; 자리 고르기는 갇힘 전이라 둘이 같다)
- fill 5: 지금 (가장 작은 넓이 = V / scl_tgmax)
- fill 3.5, 3.0: 가장 작은 넓이 = V / fill
값: 자리 넓이, V/A, R의 CV·±10% 몫·가장 작은 값·위 한도(5)에 닿은 칸 몫, 그리고 S1과 같은 IoU(자리 대 σ 3 위쪽 칸, 같은 넓이)
"""
import os, sys, json, numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
from sitepick import pick
from tprof import cap, prof
RUNS = os.path.join(HERE, '..', 'model', 'runs')
cases = [('long', s, 's23z') for s in range(721, 731)] + [('slimeall', s, 's23z') for s in range(731, 737)] + [('long', s, 's23w') for s in range(741, 751)] + [('slimeall', s, 's23w') for s in range(751, 757)]
acc = {}
for scn, s, tag in cases:
    d = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}'); m = json.load(open(os.path.join(d, 'metrics.json'))); tf = int(m['t_scl'] // 20 * 20)
    Z = np.load(os.path.join(d, f'vs_t{tf:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); hw = np.where(w, np.maximum(h, 0), 0)
    G5 = gaussian_filter(hw, 5, mode='wrap', truncate=3.0); G3 = gaussian_filter(hw, 3.0, mode='wrap')
    out = []
    for fill in (5.0, 3.5, 3.0):
        T, Vb = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=fill); U = cap(T); R = prof(G5, T, Vb, q=2, capk=1, U=U)
        med = np.median(R); A = int(T.sum()); top = np.zeros(G3.size, bool); top[np.argsort(-G3.ravel(), kind='stable')[:A]] = True; top = top.reshape(G3.shape)
        v = (A, Vb / A, R.std() / R.mean(), float((np.abs(R - med) <= 0.1 * med).mean()), R.min(), float((R >= 4.999).mean()), float((T & top).sum() / (T | top).sum()))
        acc.setdefault(fill, []).append(v); out.append(f"fill {fill}: A {A:4d} V/A {v[1]:.2f} CV {v[2]:.2f} ±10% {v[3]:.2f} Rmin {v[4]:.2f} 위한도 {v[5]:.2f} IoU {v[6]:.2f}")
    print(f"{scn:8s} {s} {tag}  " + '  |  '.join(out))
print()
for fill, L in acc.items():
    a = np.array(L); print(f"fill {fill}: CV 중앙 {np.median(a[:, 2]):.3f} 최소 {a[:, 2].min():.3f}  ±10% 중앙 {np.median(a[:, 3]):.3f}  Rmin 최소 {a[:, 4].min():.2f}  위 한도 칸 몫 최대 {a[:, 5].max():.2f}  IoU 평균 {a[:, 6].mean():.3f}  넓이 CV {a[:, 0].std() / a[:, 0].mean():.3f}")
