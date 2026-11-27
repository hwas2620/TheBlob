"""[S24 진단 5] 자리 고리 넓히기(scl_tggrow): 갇히기 직전 장면에서 자리 넓이만 다시 만든다 (S23 결승 s23v long 761~770·slimeall 771~776, long 787)."""
import os, sys, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from sitepick import pick
RUNS = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model/runs'
A0 = []; A1 = []
for scn, s in [('long', s) for s in range(761, 771)] + [('slimeall', s) for s in range(771, 777)] + [('long', 787)]:
    d = os.path.join(RUNS, f'b_{scn}_s{s}_s23v'); m = json.load(open(os.path.join(d, 'metrics.json'))); ts = m['t_scl']
    if ts is None: continue
    Z = np.load(os.path.join(d, f'vs_t{int(ts // 20 * 20):04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0)
    T0, Vb = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=3.5); T1, _ = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=3.5, grow=1)
    Tt, _ = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=1e9)
    A0.append(int(T0.sum())); A1.append(int(T1.sum()))
    print(f"{scn:8s} {s} V {Vb:6.0f} 문턱만 {int(Tt.sum()):4d}  지금 {int(T0.sum()):4d}  고리 {int(T1.sum()):4d} (V/A {Vb / T1.sum():.2f}, 지금과 IoU {float((T0 & T1).sum() / (T0 | T1).sum()):.2f})")
A0 = np.array(A0); A1 = np.array(A1)
print(f"넓이 CV 지금 {A0.std() / A0.mean():.3f}, 고리 {A1.std() / A1.mean():.3f}; 같은 넓이 최다 지금 {np.bincount(A0).max()}, 고리 {np.bincount(A1).max()}")
