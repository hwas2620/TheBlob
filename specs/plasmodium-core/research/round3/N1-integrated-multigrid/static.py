#!/usr/bin/env python3
"""N1 static + frozen-geometry checks on checkpoints saved by an exact run.
usage: python3 static.py RUN_DIR [steps...]   -> prints tables, writes RUN_DIR/static.json"""
import numpy as np, json, sys, os, time
import scipy.sparse as sp, scipy.sparse.linalg as spl
import n1
from n1 import DIRS, nb, rev, MG, k_jac_n

rd = sys.argv[1]; P = json.load(open(os.path.join(rd, 'params.json')))
steps = [int(s) for s in sys.argv[2:]] or sorted(int(f[5:-4]) for f in os.listdir(rd) if f.startswith('ckpt_'))
kap = P['kappa']; dt = P['dt']; RES = {}

def load(step):
    Z = np.load(os.path.join(rd, f'ckpt_{step}.npz')); return {k: Z[k] for k in Z.files}

def matrix(W, wet, sig):
    shp = wet.shape; idx = -np.ones(shp, np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
    rows = []; cols = []; vals = []
    for k, d in enumerate(DIRS):
        m = W[k] > 0; a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
        rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
    ar = np.arange(n); rows.append(ar); cols.append(ar); vals.append(np.full(n, sig))
    return sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()

def flux(W, p): return np.array([W[k] * (p - nb(p, d)) for k, d in enumerate(DIRS)])

def setup_mg(Z, scale, mass, FT=np.float64):
    N = int(Z['N']); y0, y1, x0, x1 = Z['win']; mg = MG(N, 4, FT, scale, mass)
    sl = (slice(1 + y0, 1 + y1), slice(1 + x0, 1 + x1))
    for k in range(4): mg.W[0][(k,) + sl] = Z['W'][k]
    mg.M[0][sl] = np.where(Z['wet'], float(Z['sig']), 0.0); mg.build(True)
    return mg, sl

def static(step):
    Z = load(step); W = Z['W']; wet = Z['wet']; rhs = Z['rhs']; C = Z['C']; sig = float(Z['sig'])
    A = matrix(W, wet, sig); lu = spl.splu(A); pe = np.zeros(wet.shape); pe[wet] = lu.solve(rhs[wet]); Qe = flux(W, pe)
    am = W > 0; thick = am & (C > 100); mid = am & (C > 4) & (C <= 100)
    er = lambda Q, m: float(np.sqrt(((Q - Qe)[m] ** 2).sum() / max((Qe[m] ** 2).sum(), 1e-300))) if m.any() else float('nan')
    def score(p):
        r = rhs[wet] - A @ p[wet]; Q = flux(W, p)
        return [round(float(np.linalg.norm(r) / np.linalg.norm(rhs[wet])), 4), round(er(Q, am), 4), round(er(Q, thick), 4), round(er(Q, mid), 4)]
    import scipy.ndimage as ndi
    ncomp = ndi.label(wet, structure=np.ones((3, 3)))[1]
    info = dict(step=step, t=step * dt, nwet=int(wet.sum()), ncomp=int(ncomp), Wmax=round(float(W.max()), 1), Cmax=round(float(C.max()), 1), n_thick=int(thick.sum()), n_mid=int(mid.sum()),
                warm_start_itself=score(np.where(wet, Z['p_prev'], 0.0)), zero=score(np.zeros(wet.shape)))
    print(f"\n=== step {step} (t={step * dt:.0f}) wet {info['nwet']} comps {ncomp} Wmax {info['Wmax']} thick edges {info['n_thick']} | [res, err_all, err_thick(C>100), err_mid]  warm start alone {info['warm_start_itself']}")
    out = dict(info=info, mg={}, jac={})
    cyc = [1, 2, 3, 5, 10, 20]
    variants = [('1.5 mass-exact V22', 1.5, 'exact', 2, 2, 20), ('1.5 mass-scaled V22 (E9 as is)', 1.5, 'scaled', 2, 2, 20), ('1.0 (pure Galerkin) V22', 1.0, 'exact', 2, 2, 20),
                ('2.0 mass-exact V22', 2.0, 'exact', 2, 2, 20), ('2.0 mass-scaled V22', 2.0, 'scaled', 2, 2, 20), ('1.5 mass-exact V11', 1.5, 'exact', 1, 1, 20),
                ('1.5 mass-exact V33', 1.5, 'exact', 3, 3, 20), ('1.5 mass-exact V22 nc=4', 1.5, 'exact', 2, 2, 4), ('1.25 mass-exact V22', 1.25, 'exact', 2, 2, 20)]
    for nm, sc, ms, a1, a2, nc in variants:
        mg, sl = setup_mg(Z, sc, ms); row = {}
        for start in ('cold', 'warm'):
            mg.p[0][...] = 0
            if start == 'warm': mg.p[0][sl] = np.where(wet, Z['p_prev'], 0.0)
            mg.S[0][...] = 0; mg.S[0][sl] = rhs; done = 0; r_ = []
            for c in cyc:
                for _ in range(c - done): mg.vcycle(0, a1, a2, nc, 0.8)
                done = c; p = mg.p[0][sl].copy()
                r_.append(score(p) if np.isfinite(p).all() and np.abs(p).max() < 1e12 else [float('inf')] * 4)
            row[start] = r_
        out['mg'][nm] = row
        print(f'MG {nm:32s} cold err_all@{cyc}: {[r[1] for r in row["cold"]]}')
        print(f'   {"":32s} cold err_thick   : {[r[2] for r in row["cold"]]}')
        print(f'   {"":32s} warm err_all     : {[r[1] for r in row["warm"]]}  thick {[r[2] for r in row["warm"]]}  res {[r[0] for r in row["warm"]]}')
    mg, sl = setup_mg(Z, 1.5, 'exact')
    for om in (0.8, 0.9):
        for start in ('cold', 'warm'):
            mg.p[0][...] = 0
            if start == 'warm': mg.p[0][sl] = np.where(wet, Z['p_prev'], 0.0)
            mg.S[0][...] = 0; mg.S[0][sl] = rhs; done = 0; r_ = {}
            for k in (10, 40, 160, 640):
                k_jac_n(mg.p[0], mg.W[0], mg.S[0], mg.D[0], om, k - done, mg.T[0]); done = k; r_[k] = score(mg.p[0][sl].copy())
            out['jac'][f'om{om}_{start}'] = r_
            print(f'JAC om={om} {start}: ' + '  '.join(f'k={k}: res {v[0]} all {v[1]} thick {v[2]}' for k, v in r_.items()))
    return out

def frozen(step, nsteps=120, eps=None, confs=(('mg', 1), ('mg', 2), ('mg', 4), ('jac', 40), ('jac', 160)), scale=1.5, mass='exact'):
    """frozen geometry (wet set, C, age fixed), phases advance with their natural frequency (no coupling) -> oscillating rhs only.
    Each step: approximate solve (warm start), flux error against the exact solve from the SAME state, h <- h - dt div Q(approx)."""
    Z = load(step); W = Z['W']; wet = Z['wet']; C = Z['C']; sig = float(Z['sig']); age = Z['age']; th0 = Z['theta']
    eps = P['eps'] if eps is None else eps
    base = P['h0'] * np.exp(-age / P['tau_a']) * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f'])); tube = Z['tube0']
    wv = 2 * np.pi / P['period']; om = wv * (1 + P['d_omega'] * (1 - np.exp(-age / P['tau_a'])))
    hst = lambda s: (base + tube) * (1 + eps * np.cos(th0 + om * s * dt))
    A = matrix(W, wet, sig); lu = spl.splu(A); am = W > 0; thick = am & (C > 100)
    res = {}
    for kind, n in confs:
        mg, sl = setup_mg(Z, scale, mass); h = Z['h'].copy(); mg.p[0][sl] = np.where(wet, Z['p_prev'], 0.0); ea = []; et = []; hmin = 1e9; gr = []
        for s in range(nsteps):
            rhs = np.where(wet, (h - hst(s)) / dt, 0.0); mg.S[0][sl] = rhs
            if kind == 'mg':
                for _ in range(n): mg.vcycle(0, 2, 2, 20, 0.8)
            else: k_jac_n(mg.p[0], mg.W[0], mg.S[0], mg.D[0], 0.9, n, mg.T[0])
            p = mg.p[0][sl].copy(); Q = flux(W, p)
            pe = np.zeros(wet.shape); pe[wet] = lu.solve(rhs[wet]); Qe = flux(W, pe)
            ea.append(float(np.sqrt(((Q - Qe)[am] ** 2).sum() / (Qe[am] ** 2).sum())))
            if thick.any(): et.append(float(np.sqrt(((Q - Qe)[thick] ** 2).sum() / (Qe[thick] ** 2).sum()))); gr.append(float(np.abs(Q[thick]).sum() / np.abs(Qe[thick]).sum()))
            div = np.zeros(wet.shape)
            for k, d in enumerate(DIRS): div += Q[k] - rev(Q[k], d)
            h = h - dt * div; hmin = min(hmin, float(h[wet].min()))
        l = slice(nsteps // 3, None)
        res[f'{kind}{n}'] = dict(err_all_med=round(float(np.median(ea[l])), 4), err_all_max=round(float(np.max(ea[l])), 4), err_thick_med=round(float(np.median(et[l])), 4) if et else None,
                                 err_thick_max=round(float(np.max(et[l])), 4) if et else None, gross_ratio_thick=round(float(np.mean(gr[l])), 3) if gr else None, hmin=round(hmin, 4))
    print(f'FROZEN step {step} eps={eps} scale={scale} mass={mass}: ' + json.dumps(res))
    return res

for s in steps:
    RES[f'static_{s}'] = static(s)
for s in steps:
    RES[f'frozen_{s}'] = frozen(s)
RES[f'frozen_{steps[-1]}_eps0'] = frozen(steps[-1], eps=0.0)
RES[f'frozen_{steps[-1]}_massscaled'] = frozen(steps[-1], mass='scaled', confs=(('mg', 1), ('mg', 2)))
RES[f'frozen_{steps[-1]}_scale1'] = frozen(steps[-1], scale=1.0, confs=(('mg', 1), ('mg', 2)))
json.dump(RES, open(os.path.join(rd, 'static.json'), 'w'), indent=1)
