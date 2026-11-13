#!/usr/bin/env python3
"""N1 frozen-geometry sweep: which per-step MG configuration is stable/accurate in the coupled h-p time loop?
usage: python3 fsweep.py RUN_DIR step [step...]   -> prints table, writes RUN_DIR/fsweep_<steps>.json
Frozen geometry (wet set, C, age fixed); phases advance with their natural frequency; h evolves with the APPROXIMATE flux.
Also: extreme eigenvalues of the V-cycle error propagator E = I - B A (ARPACK on the matrix-free cycle)."""
import numpy as np, json, sys, os, time
import scipy.sparse as sp, scipy.sparse.linalg as spl
from n1 import DIRS, nb, rev, MG, k_jac_n

rd = sys.argv[1]; P = json.load(open(os.path.join(rd, 'params.json'))); steps = [int(s) for s in sys.argv[2:]]
dt = P['dt']; OUT = {}

def matrix(W, wet, sig):
    shp = wet.shape; idx = -np.ones(shp, np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
    rows = []; cols = []; vals = []
    for k, d in enumerate(DIRS):
        m = W[k] > 0; a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
        rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
    ar = np.arange(n); rows.append(ar); cols.append(ar); vals.append(np.full(n, sig))
    return sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()

def flux(W, p): return np.array([W[k] * (p - nb(p, d)) for k, d in enumerate(DIRS)])

def setup(Z, scale, mass='exact'):
    N = int(Z['N']); y0, y1, x0, x1 = Z['win']; mg = MG(N, 4, np.float64, scale, mass); sl = (slice(1 + y0, 1 + y1), slice(1 + x0, 1 + x1))
    for k in range(4): mg.W[0][(k,) + sl] = Z['W'][k]
    mg.M[0][sl] = np.where(Z['wet'], float(Z['sig']), 0.0); mg.build(True); return mg, sl

def frozen(Z, lu, scale, ncyc, nu, beta=0.0, theta_relax=1.0, nsteps=120, eps=None):
    W = Z['W']; wet = Z['wet']; C = Z['C']; age = Z['age']; th0 = Z['theta']; eps = P['eps'] if eps is None else eps
    base = P['h0'] * np.exp(-age / P['tau_a']) * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f'])); tube = Z['tube0']
    wv = 2 * np.pi / P['period']; om = wv * (1 + P['d_omega'] * (1 - np.exp(-age / P['tau_a'])))
    am = W > 0; thick = am & (C > 100)
    mg, sl = setup(Z, scale); h = Z['h'].copy(); p_old = np.where(wet, Z['p_prev'], 0.0); p_old2 = p_old.copy(); ea = []; et = []; hmin = 1e9
    for s in range(nsteps):
        rhs = np.where(wet, (h - (base + tube) * (1 + eps * np.cos(th0 + om * s * dt))) / dt, 0.0); mg.S[0][sl] = rhs
        mg.p[0][sl] = p_old + beta * (p_old - p_old2)
        for _ in range(ncyc): mg.vcycle(0, nu, nu, 20, 0.8)
        p = mg.p[0][sl].copy()
        if theta_relax != 1.0: p = p_old + theta_relax * (p - p_old)
        if not np.isfinite(p).all() or np.abs(p).max() > 1e9: hmin = -np.inf; break
        Q = flux(W, p); pe = np.zeros(wet.shape); pe[wet] = lu.solve(rhs[wet]); Qe = flux(W, pe)
        ea.append(float(np.sqrt(((Q - Qe)[am] ** 2).sum() / (Qe[am] ** 2).sum())))
        if thick.any(): et.append(float(np.sqrt(((Q - Qe)[thick] ** 2).sum() / (Qe[thick] ** 2).sum())))
        div = np.zeros(wet.shape)
        for k, d in enumerate(DIRS): div += Q[k] - rev(Q[k], d)
        h = h - dt * div; hmin = min(hmin, float(h[wet].min())); p_old2 = p_old; p_old = p
    l = slice(len(ea) // 3, None)
    return dict(all_med=round(float(np.median(ea[l])), 3), all_max=round(float(np.max(ea[l])), 3), thick_med=round(float(np.median(et[l])), 3) if et else None, hmin=round(hmin, 3))

def eig_extremes(Z, scale, nu):
    wet = Z['wet']; n = int(wet.sum()); mg, sl = setup(Z, scale); mg.S[0][...] = 0
    def mv(v):
        buf = np.zeros(wet.shape); buf[wet] = v; mg.p[0][...] = 0; mg.p[0][sl] = buf; mg.vcycle(0, nu, nu, 20, 0.8); return mg.p[0][sl][wet].copy()
    op = spl.LinearOperator((n, n), matvec=mv, dtype=np.float64)
    try:
        lo = spl.eigs(op, k=4, which='SR', return_eigenvectors=False, maxiter=3000, tol=1e-4); hi = spl.eigs(op, k=4, which='LR', return_eigenvectors=False, maxiter=3000, tol=1e-4)
        return dict(min_real=round(float(lo.real.min()), 3), max_real=round(float(hi.real.max()), 3), max_imag=round(float(max(np.abs(lo.imag).max(), np.abs(hi.imag).max())), 4))
    except Exception as ex: return dict(err=repr(ex)[:120])

import os as _os
EIGS = (1.5, 1.33, 1.25, 1.0) if not _os.environ.get('FS_EIGS') else tuple(float(x) for x in _os.environ['FS_EIGS'].split(',') if x)
confs = [(1.5, 1, 2, 0, 1), (1.5, 2, 2, 0, 1), (1.5, 3, 2, 0, 1), (1.5, 1, 3, 0, 1), (1.5, 1, 2, 0, 0.8), (1.5, 1, 2, 0, 0.67),
         (1.33, 1, 2, 0, 1), (1.33, 2, 2, 0, 1), (1.25, 1, 2, 0, 1), (1.25, 2, 2, 0, 1), (1.25, 1, 3, 0, 1), (1.0, 1, 2, 0, 1), (1.0, 2, 2, 0, 1),
         (1.25, 1, 2, 1.0, 1), (1.25, 1, 2, 0.5, 1), (1.0, 1, 2, 1.0, 1), (1.5, 2, 2, 1.0, 1), (1.25, 2, 2, 1.0, 1)]
if _os.environ.get('FS_CONFS'): confs = [tuple(c) for c in json.loads(_os.environ['FS_CONFS'])]
TAG = _os.environ.get('FS_TAG', '')
for st in steps:
    Zf = np.load(os.path.join(rd, f'ckpt_{st}.npz')); Z = {k: Zf[k] for k in Zf.files}; lu = spl.splu(matrix(Z['W'], Z['wet'], float(Z['sig'])))
    print(f'\n=== ckpt step {st}: wet {int(Z["wet"].sum())}'); OUT[st] = {}
    for sc in EIGS:
        e = eig_extremes(Z, sc, 2); OUT[st][f'eig_scale{sc}'] = e; print(f'  V(2,2) error-propagator eigenvalues, scale {sc}: {e}', flush=True)
    for (sc, nc_, nu, be, th) in confs:
        r = frozen(Z, lu, sc, nc_, nu, be, th); key = f'scale{sc}_cyc{nc_}_V{nu}{nu}_extrap{be}_relax{th}'; OUT[st][key] = r
        print(f'  {key:40s} {r}', flush=True)
json.dump(OUT, open(os.path.join(rd, 'fsweep_' + TAG + '_'.join(map(str, steps)) + '.json'), 'w'), indent=1)
