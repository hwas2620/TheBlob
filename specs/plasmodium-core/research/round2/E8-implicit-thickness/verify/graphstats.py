#!/usr/bin/env python3
"""render-independent network statistics straight from the edge conductances in state.npz"""
import sys, os, json, numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))
def stats(C, act, h=None, thr_list=(3, 15, 100, 500), verbose=True, Cmin=0.02, Cmax=1000.):
    N = act.shape[0]; idx = np.arange(N * N).reshape(N, N); out = {}
    allC = np.concatenate([C[k][act & nb(act, d)] for k, d in enumerate(DIRS)])
    out['n_act'] = int(act.sum()); out['n_edges'] = int(allC.size)
    out['frac_edges_at_Cmin(<1.5Cmin)'] = float((allC < 1.5 * Cmin).mean()); out['frac_edges_at_Cmax(>0.9Cmax)'] = float((allC > 0.9 * Cmax).mean())
    out['frac_edges_mid(1..0.9Cmax)'] = float(((allC > 1) & (allC <= 0.9 * Cmax)).mean())
    out['logC_hist_edges(-2..3, 10 bins)'] = np.histogram(np.log10(allC), bins=np.linspace(-2, 3.0001, 11))[0].tolist()
    for thr in thr_list:
        r = []; c = []; ori = np.zeros(4, int); wrap = 0
        for k, d in enumerate(DIRS):
            m = act & nb(act, d) & (C[k] > thr)
            r.append(idx[m]); c.append(nb(idx, d)[m]); ori[k] = int(m.sum())
            ys, xs = np.nonzero(m); wrap += int(((xs + d[0] >= N) | (ys + d[1] >= N) | (ys + d[1] < 0)).sum())
        r = np.concatenate(r); c = np.concatenate(c); E = len(r)
        if E == 0: out[f'thr{thr}'] = dict(E=0); continue
        A = sp.coo_matrix((np.ones(E), (r, c)), shape=(N * N, N * N)); A = A + A.T
        deg = np.asarray((A > 0).sum(1)).ravel(); nodes = deg > 0; V = int(nodes.sum())
        nc, lab = connected_components(A, directed=False); lab_n = lab[nodes]; sizes = np.bincount(lab_n); sizes = sizes[sizes > 0]
        ncomp = len(sizes)
        # edges per component -> largest comp share of edges
        ecomp = np.bincount(lab[r], minlength=nc); big = ecomp.max() / E
        out[f'thr{thr}'] = dict(E=E, V=V, vein_node_frac_of_body=round(V / act.sum(), 3), comps=ncomp, largest_edge_frac=round(float(big), 3), cycles=int(E - V + ncomp),
                                deg1=int((deg == 1).sum()), deg2=int((deg == 2).sum()), deg3=int((deg == 3).sum()), deg4p=int((deg >= 4).sum()),
                                edges_by_dir_E_S_SE_NE=ori.tolist(), axis_frac=round(float(ori[:2].sum() / E), 3), wrap_edges=wrap)
    # seam occupancy
    out['act_cols_x0_x127'] = [int(act[:, 0].sum()), int(act[:, -1].sum())]; out['act_rows_y0_y127'] = [int(act[0].sum()), int(act[-1].sum())]
    if h is not None:
        out['h_min'] = float(h.min()); out['h_max'] = float(h.max()); out['h_act_p1_p50_p99'] = [float(x) for x in np.percentile(h[act], [1, 50, 99])]
        out['mass_outside_act_frac'] = float(h[~act].sum() / h.sum())
    return out
if __name__ == '__main__':
    for f in sys.argv[1:]:
        z = np.load(f); o = stats(z['C'].astype(float), z['act'], z['h'].astype(float))
        print('==', f); print(json.dumps(o, indent=None))
