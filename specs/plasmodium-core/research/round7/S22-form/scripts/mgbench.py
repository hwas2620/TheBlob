"""S22 풀이 시험: 저장한 풀이 입력(mgdump)에서 멀티그리드 구성마다 유량 오차를 직접 풀이와 견준다.
python3 mgbench.py out.json dump1.npz dump2.npz ...
- warm: 실행과 같이 p0(웜스타트)에서 ncyc=2 → 유량 오차 (모델의 mg_err 와 같은 정의)
- cold: 0에서 출발해 사이클 1,2,4,10,40 의 상대 유량 오차 (40 > 10 이면 수렴하지 않음)
"""
import sys, os, json, time
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'model'))
import mgt
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
nb = lambda a, d: np.roll(a, (-d[1], -d[0]), (0, 1))
CONF = {   # 이름: (층 1·2·3+ 과보정, om, nu)
    'old':      ([1.5, 1.5, 1.5], 0.8, 2),
    'deep':     ([1.5, 1.0, 1.0], 0.8, 2),
    'c15_125':  ([1.5, 1.25, 1.0], 0.8, 2),
    'c16_12':   ([1.6, 1.2, 1.0], 0.8, 2),
    'c18':      ([1.8, 1.0, 1.0], 0.8, 2),
    'c17_11':   ([1.7, 1.1, 1.0], 0.8, 2),
    'c15_13':   ([1.5, 1.3, 1.0], 0.8, 2),
    'c14_12_11': ([1.4, 1.2, 1.1], 0.8, 2),
    'deep_om9': ([1.5, 1.0, 1.0], 0.9, 2),
    'deep_nu3': ([1.5, 1.0, 1.0], 0.8, 3),
}

def pcg(W, M, S, p0, sc, k, om=0.8, nu=2, sd=False):
    """V 사이클(과보정 sc)을 앞풀이로 쓰는 켤레기울기 k 번 (sd=True 면 가장 가파른 내림: 방향을 잇지 않는다). 사이클 수 = k"""
    N = p0.shape[0]; mg = mgt.MGT(N, scales=sc, om=om, nu=nu)
    for kk in range(4): mg.W[0][kk][...] = W[kk]
    mg.M[0][...] = M; mg.build(); D = mg.D[0]; Wl = mg.W[0]
    Z0 = np.zeros((N, N)); R = np.zeros((N, N))
    def A(x): mgt.k_resid(x, Wl, Z0, D, R); return -R.copy()
    def B(r):
        mg.S[0][...] = r; mg.p[0][...] = 0.0; mg.vcycle(0, nu, nu, 4, om); return mg.p[0].copy()
    act = D > 0; p = np.where(act, p0, 0.0); r = np.where(act, S, 0.0) - A(p); z = B(r); d = z.copy(); rz = float((r * z).sum())
    for i in range(k):
        q = A(d); dq = float((d * q).sum())
        if dq <= 0: break
        a = rz / dq; p = p + a * d; r = r - a * q
        if i == k - 1: break
        z = B(r); rz2 = float((r * z).sum()); beta = 0.0 if sd else rz2 / rz; d = z + beta * d; rz = rz2
    return p

PCG = {'pcg_old': ([1.5, 1.5, 1.5], False), 'pcg_deep': ([1.5, 1.0, 1.0], False), 'sd_old': ([1.5, 1.5, 1.5], True), 'pcg_2': ([2.0, 2.0, 2.0], False)}

def load(f):
    Z = np.load(f)
    if 'M' in Z.files: return np.array(Z['W']), Z['wet'].astype(bool), np.array(Z['M']), np.array(Z['S']), np.array(Z['p0']), float(Z['t'])
    wet = Z['wet'].astype(bool); kap = float(Z['kap']); dt = float(Z['dt'])      # dbg499 덤프 (S21 진단 5)
    return np.array(Z['W']), wet, np.where(wet, 1.0 / (kap * dt), 0.0), np.where(wet, (Z['h'] - Z['hstar']) / dt, 0.0), np.array(Z['p0']), float(Z['t'])

def exact(W, M, S, wet):
    N = wet.shape[0]; idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n); r = []; c = []; v = []
    for k, d in enumerate(DIRS):
        m = W[k] > 0; a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]; r += [a, b, a, b]; c += [b, a, a, b]; v += [-w, -w, w, w]
    ar = np.arange(n); r.append(ar); c.append(ar); v.append(M[wet])
    A = sp.coo_matrix((np.concatenate(v), (np.concatenate(r), np.concatenate(c))), shape=(n, n)).tocsc()
    pe = np.zeros((N, N)); pe[wet] = spl.splu(A, permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0.0, options=dict(SymmetricMode=True)).solve(S[wet]); return pe

def ferr(W, pa, pe):
    num = den = 0.0
    for k, d in enumerate(DIRS):
        qa = W[k] * (pa - nb(pa, d)); qe = W[k] * (pe - nb(pe, d)); num += float(((qa - qe) ** 2).sum()); den += float((qe ** 2).sum())
    return (num / max(den, 1e-300)) ** 0.5

if __name__ == '__main__':
    out = sys.argv[1]; files = sys.argv[2:]; cold_every = int(os.environ.get('COLD_EVERY', '4'))
    res = []
    for i, f in enumerate(files):
        W, wet, M, S, p0, t = load(f); N = wet.shape[0]; pe = exact(W, M, S, wet)
        row = dict(f=f, t=t, wet=int(wet.sum()), warm={}, cold={})
        for name, (sc, om, nu) in CONF.items():
            mg = mgt.MGT(N, scales=sc, om=om, nu=nu)
            row['warm'][name] = ferr(W, mg.solve(W, M, S, p0, ncyc=2), pe)
            if i % cold_every == 0 or 'dbg499' in f:
                p = np.zeros((N, N)); e = {}
                for c in range(1, 41):
                    p = mg.solve(W, M, S, p, ncyc=1)
                    if c in (1, 2, 4, 10, 40): e[c] = ferr(W, p, pe) if np.isfinite(p).all() else 1e30
                row['cold'][name] = e
        for name, (sc, sd) in PCG.items():
            row['warm'][name] = ferr(W, pcg(W, M, S, p0, sc, 2, sd=sd), pe)
            if i % cold_every == 0 or 'dbg499' in f:
                e = {}
                for c in (1, 2, 4, 10, 40):
                    pp = pcg(W, M, S, np.zeros((N, N)), sc, c, sd=sd); e[c] = ferr(W, pp, pe) if np.isfinite(pp).all() else 1e30
                row['cold'][name] = e
        res.append(row)
        if i % 20 == 0: print(i, len(files), f, {k: round(v, 3) for k, v in row['warm'].items()}, flush=True)
    json.dump(res, open(out, 'w'))
