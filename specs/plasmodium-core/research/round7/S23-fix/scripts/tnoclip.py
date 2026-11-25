"""S23 셋째 거르기 뒤 진단: 가장 작은 넓이(V/3.5)에 걸린 덩이는 넓이가 공식 값(385칸)으로 같아진다.
'잘리지 않게 넓히기': 문턱으로 고른 자리에서 쉼 두께(G5² · 방울 모양)를 만들어, 가장 두꺼운 칸이 위 한도(5 h0)를 넘으면 그만큼 자리를 넓혀(같은 흐름 순서로) 다시 만든다.
넓이가 덩이 모양(가운데와 평균의 비)에 따라 정해지므로 실행마다 다르다.
python3 tnoclip.py   (첫·둘째·셋째 거르기의 long·slimeall 덩이 48개)
"""
import os, sys, json, numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
from sitepick import pick
from tprof import cap
RUNS = os.path.join(HERE, '..', 'model', 'runs')

def raw(G5, T, Vb):
    U = cap(T); w = np.maximum(G5[T], 1e-9) ** 2 * (1.0 + U[T] / U[T].max()); return Vb * w / w.sum()

def clipR(R, Vb, tmax=5.0):
    for _ in range(6): R = np.clip(R * Vb / R.sum(), 0.3, tmax)
    return R

def noclip(h, w, G5, tmax=5.0, slack=1.0):
    T, Vb = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=tmax); it = 0
    while True:
        R = raw(G5, T, Vb); mx = R.max(); A = int(T.sum())
        if mx <= tmax * slack or it >= 12: break
        A2 = int(np.ceil(A * min(mx / tmax, 1.5))) + 1; T2, _ = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=Vb / A2)
        if T2.sum() <= A: break
        T = T2; it += 1
    return T, Vb, clipR(R, Vb, tmax), it

cases = [('long', s, 's23z') for s in range(721, 731)] + [('slimeall', s, 's23z') for s in range(731, 737)] + [('long', s, 's23w') for s in range(741, 751)] + [('slimeall', s, 's23w') for s in range(751, 757)] + [('long', s, 's23v') for s in range(781, 791)] + [('slimeall', s, 's23v') for s in range(791, 797)]
acc = {'fill3.5': [], 'noclip': []}
for scn, s, tag in cases:
    d = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}'); m = json.load(open(os.path.join(d, 'metrics.json'))); tf = int(m['t_scl'] // 20 * 20)
    Z = np.load(os.path.join(d, f'vs_t{tf:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); hw = np.where(w, np.maximum(h, 0), 0)
    G5 = gaussian_filter(hw, 5, mode='wrap', truncate=3.0); G3 = gaussian_filter(hw, 3.0, mode='wrap')
    T1, Vb = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=3.5); R1 = clipR(raw(G5, T1, Vb), Vb)
    T2, _, R2, it = noclip(h, w, G5)
    row = []
    for k, T, R in (('fill3.5', T1, R1), ('noclip', T2, R2)):
        A = int(T.sum()); med = np.median(R); top = np.zeros(G3.size, bool); top[np.argsort(-G3.ravel(), kind='stable')[:A]] = True; top = top.reshape(G3.shape)
        v = (A, Vb / A, R.std() / R.mean(), float((np.abs(R - med) <= 0.1 * med).mean()), float((R >= 4.999).mean()), float((T & top).sum() / (T | top).sum()), scn)
        acc[k].append(v); row.append(f"{k}: A {A:4d} V/A {v[1]:.2f} CV {v[2]:.2f} ±10% {v[3]:.2f} 잘린 {v[4]:.2f} IoU {v[5]:.2f}")
    print(f"{scn:8s} {s} {tag}  " + '  |  '.join(row) + f"  (넓힘 {it}번)")
print()
for k, L in acc.items():
    a = np.array([x[:6] for x in L], float); lo = np.array([x[0] for x in L if x[6] == 'long'], float)
    vals, cnt = np.unique(a[:, 0], return_counts=True)
    print(f"{k}: CV 중앙 {np.median(a[:, 2]):.3f} 최소 {a[:, 2].min():.3f}  ±10% 중앙 {np.median(a[:, 3]):.3f}  잘린 칸 몫 최대 {a[:, 4].max():.2f}  IoU 평균 {a[:, 5].mean():.3f}  넓이 CV {a[:, 0].std() / a[:, 0].mean():.3f}  long 넓이 CV {lo.std() / lo.mean():.3f}  같은 넓이가 가장 많은 수 {cnt.max()} (넓이 {int(vals[np.argmax(cnt)])})")
