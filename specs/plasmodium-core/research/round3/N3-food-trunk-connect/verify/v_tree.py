#!/usr/bin/env python3
"""H1 tree check: own Kruskal max-C spanning tree of the reservoir's vein component, Strahler order rooted at the reservoir, and radial thinning Spearman(distance from food, log C)"""
import numpy as np, sys, os, glob, json
from scipy.stats import spearmanr
import vindep
sys.setrecursionlimit(100000)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def tree(S, thr=4.0):
    C = S['C'].astype(float); wet = S['wet'].astype(bool); N = wet.shape[0]; fx, fy = np.asarray(S['foods']).reshape(-1, 2)[0]; fr = float(S['food_r'])
    a, b, k, c = vindep.active_edges(C, wet); m = c > thr; a = a[m]; b = b[m]; c = c[m]
    d = vindep.disc_mask(N, fx, fy, fr).ravel()
    uf = vindep.UF(); adj = {}
    for i in np.argsort(-c).tolist():                      # Kruskal, largest C first
        u, v = int(a[i]), int(b[i])
        if uf.find(u) != uf.find(v): uf.union(u, v); adj.setdefault(u, []).append(v); adj.setdefault(v, []).append(u)
    roots = [n for n in adj if d[n]]
    if not roots: return None
    root = max(roots, key=lambda n: len(adj[n]))
    # iterative post-order Strahler
    order = []; par = {root: None}; st = [root]
    while st:
        u = st.pop(); order.append(u)
        for v in adj[u]:
            if v not in par: par[v] = u; st.append(v)
    S_ = {}
    kids = {}
    for v, p in par.items():
        if p is not None: kids.setdefault(p, []).append(v)
    for u in reversed(order):
        ch = [S_[x] for x in kids.get(u, [])]
        if not ch: S_[u] = 1
        else:
            mx = max(ch); S_[u] = mx + 1 if ch.count(mx) >= 2 else mx
    comp = set(order); mk = np.array([(int(x) in comp) for x in a])
    rad = np.hypot(((a % N) - fx + N / 2) % N - N / 2, ((a // N) - fy + N / 2) % N - N / 2)
    out = dict(strahler=S_[root], tree_nodes=len(order), comp_edge_share=round(float(mk.mean()), 3))
    mm = mk & (rad > fr)
    out['sp_radius_logC'] = round(float(spearmanr(rad[mm], np.log(c[mm]))[0]), 3)
    for thr2 in (10, 30):
        m2 = mm & (c > thr2); out[f'sp_radius_logC_thr{thr2}'] = round(float(spearmanr(rad[m2], np.log(c[m2]))[0]), 3) if m2.sum() > 10 else None
    return out
for run in sys.argv[1:]:
    root = os.path.join(ROOT, 'verify') if run.startswith('V') else ROOT
    for f in sorted(glob.glob(os.path.join(root, 'runs', run, 'state_t*.npz')))[1:]:
        print(run, os.path.basename(f)[6:-4], tree(vindep.load(f)))
