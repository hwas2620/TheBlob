#!/usr/bin/env python3
"""Independent re-solve on the seed-3 rerun: Kirchhoff, formula-vs-code, steady-state distance, Jacobi cost."""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl, json, os, sys
d = sys.argv[1]
g = np.load(os.path.join(d, 'graph.npz')); e4 = np.load(os.path.join(d, 'edges_4.npz')); P = json.load(open(os.path.join(d, 'params.json')))
ei, ej, eg, eL = g['ei'], g['ej'], g['eg'], g['eL']; n = len(g['xs']); ne = len(ei); I0 = float(g['I0'])
Cpre = e4['C'].astype(float); Cpost = g['C'].astype(float); qm_saved = g['qm'].astype(float)
r = P['r']; gam = P['gamma']; N = P['N']
def lap(w):
    A = sp.coo_matrix((np.concatenate([w, w, -w, -w]), (np.concatenate([ei, ej, ei, ej]), np.concatenate([ei, ej, ej, ei]))), shape=(n, n)).tocsr()
    return A
def solve(w, S):
    A = lap(w); keep = np.arange(1, n)                      # pin node 0 (different regularisation from e6.py)
    p = np.zeros((n,) + S.shape[1:]); p[1:] = spl.splu(A[keep][:, keep].tocsc()).solve(S[1:])
    return p
w = eg * (Cpre + r) / eL
src = g['src']; sink = g['sink']
Sdc = I0 * src - I0 * sink / sink.sum()
lam = 0.86 * N; cx = float(N // 2)
phi = 2 * np.pi * (g['xs'] - cx) / lam                       # theta = 0 at the final step
a = np.cos(phi) - np.cos(phi).mean(); b = np.sin(phi) - np.sin(phi).mean()
th = np.arange(24) * 2 * np.pi / 24
norm = np.mean([0.5 * np.abs(a * np.cos(t) + b * np.sin(t)).sum() for t in th]); a *= I0 / norm; b *= I0 / norm
S = np.stack([Sdc, a, b], 1); p = solve(w, S); Q = w[:, None] * (p[ei] - p[ej])
div = np.zeros((n, 3)); np.add.at(div, ei, Q); np.add.at(div, ej, -Q)
out = {}
out['kirchhoff_rel_resid_final'] = float(np.abs(div - S).max() / np.abs(S).max())
out['sum_S'] = [float(x) for x in S.sum(0)]
out['dc_out_of_source'] = float(div[src > 0, 0].sum()); out['dc_into_sink'] = float(-div[sink > 0, 0].sum()); out['I0'] = I0
thK = np.arange(12) * 2 * np.pi / 12
qm = np.mean([np.abs(0.5 * Q[:, 0] + 0.5 * (np.cos(t) * Q[:, 1] + np.sin(t) * Q[:, 2])) for t in thK], 0)
strong = Cpre >= 0.01 * np.percentile(Cpre, 99.9)
out['qm_code_vs_mine_rel_err_strong_max'] = float(np.max(np.abs(qm - qm_saved)[strong] / qm[strong]))
out['qm_code_vs_mine_corr'] = float(np.corrcoef(qm, qm_saved)[0, 1])
dd = np.abs(0.5 * Q[:, 0]); A_ = 0.5 * np.hypot(Q[:, 1], Q[:, 2])
closed = np.where(dd >= A_, dd, (2 / np.pi) * (np.sqrt(np.maximum(A_**2 - dd**2, 0)) + dd * np.arcsin(np.minimum(dd / np.maximum(A_, 1e-300), 1))))
out['closed_form_vs_12pt_quad_rel_err_strong_p50_max'] = [float(np.median(np.abs(closed - qm)[strong] / qm[strong])), float(np.max(np.abs(closed - qm)[strong] / qm[strong]))]
# share of strong edges where DC exceeds AC amplitude (DC-dominated) vs AC-dominated
out['strong_edges'] = int(strong.sum()); out['strong_dc_dominated_frac'] = float((dd >= A_)[strong].mean())
# distance from steady state  C = qm^gamma
imb = np.abs(qm**gam - Cpre)[strong] / Cpre[strong]
out['steady_state_rel_imbalance_strong_p50_p90_max'] = [float(np.percentile(imb, 50)), float(np.percentile(imb, 90)), float(imb.max())]
out['sum_C_pre_post'] = [float(Cpre.sum()), float(Cpost.sum())]
out['w_contrast_max_over_min'] = float(w.max() / w.min()); out['Cmax_over_r'] = float(Cpre.max() / r)
# Jacobi cost
def jac_stats(w, tag):
    A = lap(w); D = A.diagonal()
    Dh = sp.diags(1 / np.sqrt(D)); M = (Dh @ A @ Dh).tocsc()
    vals = spl.eigsh(M, k=3, sigma=-1e-9, which='LM', return_eigenvectors=False)
    lam2 = float(np.sort(vals)[1])
    out[f'jacobi_lambda2_{tag}'] = lam2; out[f'jacobi_sweeps_per_decade_omega0.8_{tag}'] = float(np.log(10) / (0.8 * lam2))
    return A, D
A, D = jac_stats(w, 'final_network')
jac_stats(eg * (1.0 + r) / eL, 'uniform_C1')
Qex = Q[:, 0]; x = np.zeros(n); s = Sdc; errs = {}
k = 0
for target in (60, 600, 6000, 60000):
    while k < target:
        x += 0.8 * (s - A @ x) / D; k += 1
    Qk = w * (x[ei] - x[ej]); errs[target] = float(np.abs(Qk - Qex)[strong].sum() / np.abs(Qex)[strong].sum())
out['jacobi_coldstart_dc_flux_L1_relerr_on_strong_edges'] = errs
# warm start across one adaptation step (near steady state): exact p at Cpre -> sweeps at Cpost
w2 = eg * (Cpost + r) / eL; p2 = solve(w2, Sdc[:, None])[:, 0]; Q2 = w2 * (p2[ei] - p2[ej]); A2 = lap(w2); D2 = A2.diagonal()
x = p[:, 0].copy(); werr = {0: float(np.abs(w2 * (x[ei] - x[ej]) - Q2)[strong].sum() / np.abs(Q2)[strong].sum())}
for k in range(1, 61):
    x += 0.8 * (Sdc - A2 @ x) / D2
werr[60] = float(np.abs(w2 * (x[ei] - x[ej]) - Q2)[strong].sum() / np.abs(Q2)[strong].sum())
out['warmstart_one_step_near_steady_relerr'] = werr
out['rel_change_C_one_step_strong'] = float(np.abs(Cpost - Cpre)[strong].sum() / Cpre[strong].sum())
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'solve_check.json'), 'w'), indent=1)
