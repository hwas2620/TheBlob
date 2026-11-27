"""S23 거르기 뒤 진단: 균핵 두께 모양(쉼 두께 R)을 갇히기 직전 장면에서 따로 만들어, 끝 덩이 두께 CV·±10% 몫과 견준다.
python3 tprof.py [꼬리표]   (기본 s23z; 거르기 실행 long 721~730, slimeall 731~736)
변형
- q2: 지금 모델 (R ∝ G5^2)
- q3, q4: 지수만 키움
- s3q2: 두께 모양을 σ 3으로 흐림
- capK: R ∝ G5^2 · (1 + K·u/max u), u는 자리 안에서 -Δu = 1, 자리 밖 u = 0 (얇은 방울이 표면 장력으로 갖는 모양: 가운데가 두껍고 가장자리로 갈수록 얇다)
"""
import os, sys, json, numpy as np
from scipy.ndimage import gaussian_filter
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
from sitepick import pick
from ref_model import _torus_label
RUNS = os.path.join(HERE, '..', '..', 'S23-fix', 'model', 'runs')

def cap(T):
    N = T.shape[0]; idx = -np.ones(T.shape, int); ys, xs = np.nonzero(T); idx[ys, xs] = np.arange(len(ys)); A = lil_matrix((len(ys), len(ys)))
    for k, (y, x) in enumerate(zip(ys, xs)):
        A[k, k] = 4.0
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            j = idx[(y + dy) % N, (x + dx) % N]
            if j >= 0: A[k, j] = -1.0
    u = spsolve(A.tocsr(), np.ones(len(ys))); U = np.zeros(T.shape); U[ys, xs] = u; return U

def prof(G, T, Vb, q=2.0, capk=0.0, U=None, h0=1.0, tmax=5.0):
    w = np.maximum(G[T], 1e-9) ** q
    if capk > 0: w = w * (1.0 + capk * U[T] / U[T].max())
    R = Vb * w / w.sum()
    for _ in range(6): R = np.clip(R * Vb / R.sum(), 0.3 * h0, tmax * h0)
    return R

def st(v):
    med = float(np.median(v)); return float(v.std() / v.mean()), float((np.abs(v - med) <= 0.1 * med).mean()), float(v.min()), float(v.max()), float((v < 0.5).mean())

def main(tag):
    cases = [('long', s) for s in range(721, 731)] + [('slimeall', s) for s in range(731, 737)]
    V = ['q2', 'q3', 'q4', 's3q2', 'cap1', 'cap2']; acc = {k: [] for k in V + ['end']}
    for scn, s in cases:
        d = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}'); m = json.load(open(os.path.join(d, 'metrics.json'))); ts = m['t_scl']; tf = int(ts // 20 * 20)
        Z = np.load(os.path.join(d, f'vs_t{tf:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0)
        T, Vb = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=5.0)
        hw = np.where(w, np.maximum(h, 0), 0); G5 = gaussian_filter(hw, 5, mode='wrap', truncate=3.0); G3 = gaussian_filter(hw, 3, mode='wrap', truncate=3.0); U = cap(T)
        Te = int(m['t_end']) // 20 * 20; Ze = np.load(os.path.join(d, f'vs_t{Te:04d}.npz')); we = Ze['wet'].astype(bool); he = np.where(we, Ze['h'], 0.0)
        lab = _torus_label(we); vol = np.bincount(lab.ravel(), weights=he.ravel()); vol[0] = 0; big = lab == int(np.argmax(vol))
        res = dict(end=st(he[big]), q2=st(prof(G5, T, Vb)), q3=st(prof(G5, T, Vb, q=3)), q4=st(prof(G5, T, Vb, q=4)), s3q2=st(prof(G3, T, Vb)),
                   cap1=st(prof(G5, T, Vb, capk=1, U=U)), cap2=st(prof(G5, T, Vb, capk=2, U=U)))
        for k, v in res.items(): acc[k].append(v)
        print(f"{scn:8s} {s} t_scl {ts:6.1f} 자리 {int(T.sum()):4d} (끝 {int(big.sum()):4d}, 겹침 {float((T & big).sum() / (T | big).sum()):.2f}) V/A {Vb / T.sum():.2f}  " +
              '  '.join(f"{k} {v[0]:.2f}/{v[1]:.2f}/{v[2]:.2f}-{v[3]:.2f}" for k, v in res.items()))
    print('\n변형: CV 중앙값, CV 가장 작은 것, ±10% 몫 중앙값, R 가장 작은 것, h<0.5 몫 가장 큰 것')
    for k, L in acc.items():
        a = np.array(L); print(f"  {k:5s} CV 중앙 {np.median(a[:, 0]):.3f} 최소 {a[:, 0].min():.3f}  ±10% 중앙 {np.median(a[:, 1]):.3f}  가장 얇은 {a[:, 2].min():.2f}  가장 두꺼운 {a[:, 3].max():.2f}  얇은 몫 최대 {a[:, 4].max():.3f}")

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 's23z')
