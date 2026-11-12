#!/usr/bin/env python3
"""Iteration-count estimate for the per-step screened-Poisson system  (1/(kappa dt) + L_C) p = (h - heq)/dt.
For a saved run state (runs/NAME/state.npz + params.json): take the final (veined) C and, for comparison, uniform C=1.
Warm start = exact solution of the previous step.  Count sweeps needed to cut the warm-start error by 10x (rel. L2 in p):
  - damped Jacobi (omega=0.8)                      (cap 20000)
  - Jacobi-preconditioned CG
Also report the theoretical Jacobi e-folding count  n_e ~ diag/screen = (10/3) C kappa dt  for uniform C.
usage: iters.py NAME [NAME ...]   -> iters.json
"""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl, json, os, sys
import e8
HERE = os.path.dirname(os.path.abspath(__file__))
res = []
for name in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', name); P = json.load(open(os.path.join(d, 'params.json'))); S = np.load(os.path.join(d, 'state.npz'))
    N = P['N']; R = P['R']; hs = P['hstar']; dt = P['period'] / P['spp']; omega = 2 * np.pi / P['period']
    kappa = omega * (P['delta_over_R'] * R) ** 2 / 2; scr = 1 / (kappa * dt)
    act = S['act']; idx = -np.ones((N, N), int); n = int(act.sum()); idx[act] = np.arange(n)
    yy, xx = np.mgrid[0:N, 0:N].astype(float); cx = (N - 1) / 2
    kw = 2 * np.pi / (P['lam_over_D'] * 2 * R)
    for label, Cs in (('uniform', [np.ones((N, N))] * 4), ('veined', list(S['C'].astype(float)))):
        rows = []; cols = []; vals = []; diag = np.full((N, N), scr)
        for k, dd in enumerate(e8.DIRS):
            g = e8.WGT[k] * Cs[k] * (act & e8.nb(act, dd)); m = g > 0
            a_ = idx[m]; b_ = e8.nb(idx, dd)[m]; w = g[m]
            rows += [a_, b_]; cols += [b_, a_]; vals += [-w, -w]; diag += g + e8.rev(g, dd)
        rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag[act])
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
        lu = spl.splu(A.tocsc())
        # two consecutive steps of the forced problem (plane wave), starting from h = hstar
        h = np.full(n, hs); sols = []
        for j in range(1, 4):
            heq = hs - P['a'] * hs * np.cos(kw * (xx - cx) - omega * j * dt)[act]
            b = (h - heq) / dt; p = lu.solve(b); sols.append((b, p)); h = h - dt * (A @ p - scr * p)      # h_new = h - dt*L p
        b, pstar = sols[-1]; p0 = sols[-2][1]
        e0 = np.linalg.norm(p0 - pstar); D = A.diagonal()
        x = p0.copy(); nj = None
        for it in range(1, 20001):
            x = x + 0.8 * (b - A @ x) / D
            if it % 5 == 0 and np.linalg.norm(x - pstar) < 0.1 * e0: nj = it; break
        cnt = [0]; hit = [None]
        def cb(xk):
            cnt[0] += 1
            if hit[0] is None and np.linalg.norm(xk - pstar) < 0.1 * e0: hit[0] = cnt[0]
        spl.cg(A, b, x0=p0, M=sp.diags(1 / D), rtol=1e-10, maxiter=3000, callback=cb)
        r = dict(run=name, C=label, delta_over_R=P['delta_over_R'], screen_len_cells=float(np.sqrt(kappa * dt)), n_unknown=n,
                 jacobi_sweeps_10x=nj if nj else '>20000', pcg_iters_10x=hit[0], jacobi_efold_theory_uniform=round(10 / 3 * kappa * dt, 1),
                 warm_rel_err=float(e0 / np.linalg.norm(pstar - pstar.mean())), contrast=float(np.max(S['C']) / max(np.min(S['C'][:, act]), 1e-9)) if label == 'veined' else 1.0)
        res.append(r); print(r, flush=True)
json.dump(res, open(os.path.join(HERE, 'iters.json'), 'w'), indent=1)
