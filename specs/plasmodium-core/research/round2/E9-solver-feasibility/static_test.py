#!/usr/bin/env python3
"""static (frozen conductance) convergence test on a real E1 tree state.
usage: static_test.py runs/NAME/edges_K.npz [r=1e-3] [out.json]
cold start p=0; flux error = ||Q - Q*|| / ||Q*|| vs number of passes / cycles."""
import sys, json, time, numpy as np
import scipy.sparse as sp, scipy.sparse.linalg as spl
import e9
from e9 import MG, k_jac_n, k_hb_n, k_gs4_n, k_resid

def load(path, r=1e-3):
    z = np.load(path); C = z['C'].astype(float); G = z['G'].astype(float); wet = z['wet']; S = z['S'].astype(float)
    N = wet.shape[0]; dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]
    nb = lambda a, d: np.roll(a, (-d[1], -d[0]), (0, 1))
    W = [(wet & nb(wet, d)) * G[k] * (C[k] + r) / np.hypot(*d) for k, d in enumerate(dirs)]
    S = S.copy(); S[wet] -= S[wet].sum() / wet.sum()
    return N, dirs, nb, W, S, wet

def exact(N, dirs, nb, W, S, wet):
    idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n); rows = []; cols = []; vals = []
    for k, d in enumerate(dirs):
        m = W[k] > 0; a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
        rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
    A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc() + sp.identity(n, format='csc') * 1e-10
    sol = spl.spsolve(A, S[wet], permc_spec='MMD_AT_PLUS_A'); pp = np.zeros((N, N)); pp[wet] = sol - sol.mean(); return pp

def main():
    path = sys.argv[1]; r = float(sys.argv[2]) if len(sys.argv) > 2 else 1e-3
    N, dirs, nb, W, S, wet = load(path, r)
    pe = exact(N, dirs, nb, W, S, wet); Qe = [W[k] * (pe - nb(pe, dirs[k])) for k in range(4)]; den = np.sqrt(sum((q ** 2).sum() for q in Qe))
    def ferr(pp):
        p = pp[1:-1, 1:-1]
        return float(np.sqrt(sum(((W[k] * (p - nb(p, dirs[k])) - Qe[k]) ** 2).sum() for k in range(4))) / den)
    Wp = np.zeros((4, N + 2, N + 2)); Sp = np.zeros((N + 2, N + 2)); Sp[1:-1, 1:-1] = S
    for k in range(4): Wp[k, 1:-1, 1:-1] = W[k]
    allw = np.concatenate([w[w > 0] for w in W]); res = dict(path=path, N=N, r=r, area=int(wet.sum()), w_min=float(allw.min()), w_max=float(allw.max()),
                                                           w_p50=float(np.median(allw)), w_p99=float(np.percentile(allw, 99)))
    print(json.dumps(res))
    P = dict(e9.DEF)
    # --- Jacobi / heavy ball / GS: cumulative passes ---
    marks = [10, 30, 100, 300, 1000, 3000, 10000]
    def sweep_curve(fn):
        out = {}; done = 0
        for m in marks:
            fn(m - done); done = m; out[m] = round(ferr(mg.p[0]), 4)
        return out
    mg = MG(N, 4, np.float64, 2.0); mg.build(Wp); T = mg.T[0]
    mg.p[0][...] = 0; res['jac_w0.8'] = sweep_curve(lambda n: k_jac_n(mg.p[0], Wp, Sp, mg.D[0], 0.8, n, T)); print('jac', res['jac_w0.8'], flush=True)
    for beta in (0.9, 0.97, 0.99, 0.997):
        mg.p[0][...] = 0; pm = np.zeros_like(Sp); om = 0.9 * (1 + beta) / 2 * 1.0
        res[f'hb_b{beta}'] = sweep_curve(lambda n: k_hb_n(mg.p[0], pm, Wp, Sp, mg.D[0], om, beta, n, T)); print('hb', beta, 'om', round(om, 3), res[f'hb_b{beta}'], flush=True)
    mg.p[0][...] = 0; done = 0; o = {}
    for m in marks[:-1]:
        k_gs4_n(mg.p[0], Wp, Sp, mg.D[0], 1.0, m - done); done = m; o[m] = round(ferr(mg.p[0]), 4)
    res['gs4_sweeps(x4 passes)'] = o; print('gs4', o, flush=True)
    # --- MG V-cycles ---
    for scale in (1.0, 1.5, 2.0):
        for (n1, n2, om) in ((2, 2, 0.8), (1, 1, 0.8), (3, 3, 0.8)):
            if scale != 1.5 and (n1, n2) != (2, 2): continue
            mg = MG(N, 4, np.float64, scale); mg.build(Wp); mg.S[0][...] = Sp; mg.p[0][...] = 0
            P.update(nu1=n1, nu2=n2, mg_omega=om); o = {}; c = 0
            for m in (1, 2, 3, 5, 10, 20, 40):
                while c < m: mg.vcycle(0, P); c += 1
                e = ferr(mg.p[0]); o[m] = round(e, 4) if np.isfinite(e) and e < 1e6 else 'DIVERGED'
                if o[m] == 'DIVERGED': break
            res[f'mg_s{scale}_V{n1}{n2}'] = o; print(f'mg scale {scale} V({n1},{n2}) cost', mg.cost(P), o, flush=True)
    # --- PCG ---
    for scale in (1.0, 1.5):
        P.update(nu1=2, nu2=2, mg_omega=0.8); o = {}
        for tol in (1e-1, 1e-2, 1e-3, 1e-5, 1e-8):
            mg = MG(N, 4, np.float64, scale); mg.build(Wp); mg.S[0][...] = Sp; mg.p[0][...] = 0
            try:
                it = mg.pcg(P, tol, 300); e = ferr(mg.p[0]); o[str(tol)] = (it, round(e, 6))
            except Exception as ex: o[str(tol)] = str(ex)
        res[f'pcg_s{scale}'] = o; print('pcg scale', scale, '(its, flux err) by residual tol', o, flush=True)
    if len(sys.argv) > 3: json.dump(res, open(sys.argv[3], 'w'), indent=1)

if __name__ == '__main__': main()
