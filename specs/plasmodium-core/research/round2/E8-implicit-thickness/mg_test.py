#!/usr/bin/env python3
"""GPU-style solver emulation for the per-step system (1/(kappa dt) + L_C) p = b on the saved (veined) state of a run.
Multigrid V(2,2): damped Jacobi (omega=0.8) smoother, 2x2 cell aggregation (piecewise-constant P), Galerkin coarse operator
A_c = P^T A P  (= coarse edge conductance is the SUM of fine conductances crossing the aggregate boundary; screening sums too),
levels until <= 8x8 aggregates, coarsest solved by 30 Jacobi sweeps.  Used (a) stand-alone, (b) as preconditioner of CG.
Counts cycles needed to cut the warm-start error (previous step's exact p) by 10x.  One V(2,2) cycle ~ 4*(1+1/4+...) + residual/transfer
~ 7-9 fine-grid-pass equivalents.
usage: mg_test.py NAME [NAME ...] -> mg_test.json
"""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl, json, os, sys
import e8
HERE = os.path.dirname(os.path.abspath(__file__))

def build(P, S, uniform=False):
    N = P['N']; dt = P['period'] / P['spp']; omega = 2 * np.pi / P['period']
    kappa = omega * (P['delta_over_R'] * P['R']) ** 2 / 2; scr = 1 / (kappa * dt)
    act = S['act']; n = N * N; idx = np.arange(n).reshape(N, N)
    rows = []; cols = []; vals = []; diag = np.where(act, scr, 1.0)          # inactive cells: identity rows (decoupled)
    for k, dd in enumerate(e8.DIRS):
        Ck = np.ones((N, N)) if uniform else S['C'][k].astype(float)
        g = e8.WGT[k] * Ck * (act & e8.nb(act, dd)); m = g > 0
        a_ = idx[m]; b_ = e8.nb(idx, dd)[m]; w = g[m]
        rows += [a_, b_]; cols += [b_, a_]; vals += [-w, -w]; diag = diag + g + e8.rev(g, dd)
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag.ravel())
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)), act, scr, kappa, dt, omega

def hierarchy(A, N):
    lv = [(A, None)]; n = N
    while n > 8:
        nc = n // 2; i = np.arange(n * n); y, x = divmod(i, n)
        Pm = sp.csr_matrix((np.ones(n * n), (i, (np.minimum(y // 2, nc - 1)) * nc + np.minimum(x // 2, nc - 1))), shape=(n * n, nc * nc))
        A = (Pm.T @ A @ Pm).tocsr(); lv[-1] = (lv[-1][0], Pm); lv.append((A, None)); n = nc
    return lv

def vcycle(lv, b, x=None, l=0, nu=2, w=0.8):
    A, Pm = lv[l]; D = A.diagonal()
    if x is None: x = np.zeros_like(b)
    if Pm is None:
        for _ in range(30): x = x + w * (b - A @ x) / D
        return x
    for _ in range(nu): x = x + w * (b - A @ x) / D
    x = x + Pm @ vcycle(lv, Pm.T @ (b - A @ x), None, l + 1, nu, w)
    for _ in range(nu): x = x + w * (b - A @ x) / D
    return x

res = []
for name in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', name); P = json.load(open(os.path.join(d, 'params.json'))); S = np.load(os.path.join(d, 'state.npz'))
    N = P['N']; hs = P['hstar']
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    for label in ('uniform', 'veined'):
        A, act, scr, kappa, dt, omega = build(P, S, label == 'uniform')
        lu = spl.splu(A.tocsc()); kw = 2 * np.pi / 80.0
        h = np.where(act, hs, 0.0).ravel(); sols = []
        for j in range(1, 4):
            heq = (hs - P['a'] * hs * np.cos(kw * xx - omega * j * dt)).ravel() * act.ravel()
            b = (h - heq) / dt * act.ravel(); p = lu.solve(b); sols.append((b, p))
            Lp = A @ p - np.where(act.ravel(), scr, 1.0) * p; h = h - dt * Lp * act.ravel()
        b, pstar = sols[-1]; p0 = sols[-2][1]; e0 = np.linalg.norm(p0 - pstar)
        lv = hierarchy(A, N)
        x = p0.copy(); nmg = None; errs = []
        for it in range(1, 201):
            x = vcycle(lv, b, x); e = np.linalg.norm(x - pstar) / e0; errs.append(e)
            if not np.isfinite(e) or e > 1e6: nmg = 'diverged'; break
            if e < 0.1: nmg = it; break
        cnt = [0]; hit = [None]
        def cb(xk):
            cnt[0] += 1
            if hit[0] is None and np.linalg.norm(xk - pstar) < 0.1 * e0: hit[0] = cnt[0]
        M = spl.LinearOperator(A.shape, matvec=lambda r: vcycle(lv, r))
        spl.cg(A, b, x0=p0, M=M, rtol=1e-10, maxiter=100, callback=cb)
        Cs = S['C'][:, act]
        r = dict(run=name, C=label, N=N, n_active=int(act.sum()), delta_over_R=P['delta_over_R'], screen_len_cells=float(np.sqrt(kappa * dt)), levels=len(lv),
                 mg_cycles_10x=nmg if nmg else '>200', err_after_1_2_5_cycles=[float('%.3g' % e) for e in (errs + [np.nan] * 5)[:5:1]][0:5:1],
                 mgpcg_iters_10x=hit[0], contrast_p99_p1=float(np.percentile(Cs, 99) / np.percentile(Cs, 1)) if label == 'veined' else 1.0)
        res.append(r); print(r, flush=True)
json.dump(res, open(os.path.join(HERE, 'mg_test.json'), 'w'), indent=1)
