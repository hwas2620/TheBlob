#!/usr/bin/env python3
"""Reviewer check of the GPU claim (Jacobi 40 sweeps/step, warm start) on the final state of a pulsating run.
Frozen geometry (wet set, C, age fixed; no wetting/drying/adaptation), phases advance with their natural frequency.
Each step solves  p/(kappa dt) + sum W (p_i-p_j) = (h-h*)/dt  exactly or with k damped-Jacobi sweeps from the previous p, then h <- h - dt div Q.
Compares per-edge gross flux over the 2nd of two periods."""
import numpy as np, json, sys, os, time
import scipy.sparse as sp, scipy.sparse.linalg as spl
rd = sys.argv[1]
P = json.load(open(os.path.join(rd, 'params.json')))
N = P['N']; dt = P['dt']; kap = P['kappa']
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]; Ls = [1.0, 1.0, 2 ** .5, 2 ** .5]
rng = np.random.default_rng(P['seed'])
G = [np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in DIRS]
h0 = np.load(os.path.join(rd, 'body_native.npy')).astype(float); age = np.load(os.path.join(rd, 'age.npy')).astype(float)
th0 = np.nan_to_num(np.load(os.path.join(rd, 'theta.npy')).astype(float)); C = np.load(os.path.join(rd, 'C_edges.npy')).astype(float)
wet = age >= 0; age = np.maximum(age, 0)
nb = lambda a, d: np.roll(a, (-d[1], -d[0]), (0, 1)); rev = lambda a, d: np.roll(a, (d[1], d[0]), (0, 1))
act = [wet & nb(wet, d) for d in DIRS]
W = [act[k] * G[k] * (C[k] + P['r']) / Ls[k] for k in range(4)]
Cn = np.zeros((N, N))
for k, d in enumerate(DIRS): Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d)))
base = P['h0'] * np.exp(-age / P['tau_a']) * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f']))
tube = np.minimum(P['beta'] * np.sqrt(Cn), P['cap'])
wv = 2 * np.pi / P['period']; om = wv * (1 + P['d_omega'] * (1 - np.exp(-age / P['tau_a'])))
idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
rows = []; cols = []; vals = []
for k, d in enumerate(DIRS):
    m = W[k] > 0; a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
    rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
ar = np.arange(n); rows.append(ar); cols.append(ar); vals.append(np.full(n, 1.0 / (kap * dt)))
A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
Dg = A.diagonal(); R = A - sp.diags(Dg); lu = spl.splu(A.tocsc())
print('wet', n, 'W max', round(max(float(w.max()) for w in W), 1), 'diag min/med/max', [round(float(x), 2) for x in (Dg.min(), np.median(Dg), Dg.max())],
      'screening 1/(kappa dt)', 1 / (kap * dt))

def hstar(t):
    mod = 1 + P['eps'] * np.cos(th0 + om * t)
    return (base + tube) * mod

def simulate(k, omega=0.9, steps=80):
    h = h0.copy(); p = np.zeros(n); gross = [np.zeros((N, N)) for _ in DIRS]; net = [np.zeros((N, N)) for _ in DIRS]; res = []
    for s in range(steps):
        b = ((h - hstar(s * dt)) / dt)[wet]
        if k is None: p = lu.solve(b)
        else:
            for _ in range(k): p = (1 - omega) * p + omega * (b - R @ p) / Dg
            res.append(float(np.linalg.norm(A @ p - b) / np.linalg.norm(b)))
        pp = np.zeros((N, N)); pp[wet] = p
        div = np.zeros((N, N))
        for kk, d in enumerate(DIRS):
            Q = W[kk] * (pp - nb(pp, d)); div += Q - rev(Q, d)
            if s >= steps - 40: gross[kk] += np.abs(Q) / 40; net[kk] += Q / 40
        h = h - dt * div
    return h, np.array(gross), np.array(net), res

hE, gE, nE, _ = simulate(None)
print('exact: h min', round(float(hE[wet].min()), 4), 'mass err', float(abs(hE.sum() - h0.sum()) / h0.sum()))
thick = (C > 100); mid = (C > 4) & (C <= 100); sheet = np.array(act) & (C <= 4)
for k in (10, 40, 160, 640):
    t0 = time.time(); hJ, gJ, nJ, res = simulate(k)
    f = lambda m: [round(float(x), 3) for x in np.percentile(gJ[m] / np.maximum(gE[m], 1e-12), [10, 50, 90])]
    tot = lambda m: round(float(gJ[m].sum() / gE[m].sum()), 3)
    print(f'jacobi k={k}: residual last {res[-1]:.3f} (median {np.median(res):.3f}) | gross-flux ratio J/E  thick(C>100) total {tot(thick)} p10/50/90 {f(thick)} | mid(4<C<=100) total {tot(mid)} | sheet(C<=4) total {tot(sheet)}',
          '| h dev rms / exact change rms', round(float(np.sqrt(((hJ - hE)[wet] ** 2).mean()) / np.sqrt(((hE - h0)[wet] ** 2).mean())), 3),
          '| h min', round(float(hJ[wet].min()), 4), 'mass err', float(abs(hJ.sum() - h0.sum()) / h0.sum()), f'| {time.time() - t0:.1f}s')
