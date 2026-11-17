#!/usr/bin/env python3
"""독립 그래프 지표 (analyze.py 를 import 하지 않고 따로 구현).
usage: vgraph.py RUN_DIR [snap]
"""
import numpy as np, json, sys, os, glob
import scipy.sparse as sp, scipy.sparse.linalg as spl
from collections import defaultdict, deque

def load(d, snap=None):
    fs = sorted(glob.glob(os.path.join(d, 'edges_*.npz')), key=lambda f: int(os.path.basename(f)[6:-4]))
    f = fs[-1] if snap is None else os.path.join(d, f'edges_{snap}.npz')
    Z = np.load(f); P = json.load(open(os.path.join(d, 'params.json')))
    return Z, P, f

def nbr(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))

def edge_list(Z):
    C = Z['C'].astype(float); Q = Z['Q'].astype(float); wet = Z['wet']
    dirs = [tuple(int(v) for v in x) for x in Z['dirs']]; N = wet.shape[0]
    idx = np.arange(N * N).reshape(N, N)
    U = []; V = []; QQ = []; CC = []; KK = []
    for k, d in enumerate(dirs):
        act = wet & nbr(wet, d)
        u = idx[act]; v = nbr(idx, d)[act]; q = Q[k][act]; c = C[k][act]
        sw = q < 0
        U.append(np.where(sw, v, u)); V.append(np.where(sw, u, v)); QQ.append(np.abs(q)); CC.append(c); KK.append(np.full(u.size, k))
    return [np.concatenate(a) for a in (U, V, QQ, CC, KK)], dirs, N

def graph_metrics(U, V, Q, C, thr, j0, root_xy, X, Y):
    m = Q >= thr * j0
    u = U[m]; v = V[m]; q = Q[m]; c = C[m]
    nodes, inv = np.unique(np.concatenate([u, v]), return_inverse=True)
    n = len(nodes); ui = inv[:len(u)]; vi = inv[len(u):]
    A = sp.coo_matrix((np.ones(len(u)), (ui, vi)), shape=(n, n)); A = A + A.T
    ncomp, lab = sp.csgraph.connected_components(A, directed=False)
    deg = np.asarray((A > 0).sum(1)).ravel()
    ecomp = np.bincount(lab[ui], minlength=ncomp)
    big = int(np.argmax(ecomp))
    out = dict(thr=thr, edges=int(len(u)), nodes=int(n), comps=int(ncomp), loops=int(len(u) - n + ncomp),
               branch_nodes=int((deg >= 3).sum()), tips=int((deg == 1).sum()), deg3_frac=round(float((deg == 3).sum() / max((deg >= 3).sum(), 1)), 3),
               largest_edge_frac=round(float(ecomp[big] / len(u)), 3))
    # flux / radius hierarchy on vein edges (render independent)
    r = c ** 0.25
    out['Q_p10_p50_p90_max'] = [round(float(x), 2) for x in np.percentile(q, [10, 50, 90, 100])]
    out['Q_ratio_p90_p10'] = round(float(np.percentile(q, 90) / np.percentile(q, 10)), 2)
    out['r_p10_p50_p90_max'] = [round(float(x), 2) for x in np.percentile(r, [10, 50, 90, 100])]
    out['r_ratio_p90_p10'] = round(float(np.percentile(r, 90) / np.percentile(r, 10)), 2)
    # Strahler on the largest component, directed along flow (u->v); only valid if DAG
    out_adj = defaultdict(list); indeg = np.zeros(n, int); outdeg = np.zeros(n, int)
    for a, b in zip(ui.tolist(), vi.tolist()):
        out_adj[a].append(b); indeg[b] += 1; outdeg[a] += 1
    order = np.zeros(n, int); pend = outdeg.copy(); in_adj = defaultdict(list)
    for a, b in zip(ui.tolist(), vi.tolist()): in_adj[b].append(a)
    dq = deque(np.nonzero(pend == 0)[0].tolist())
    while dq:
        x = dq.popleft(); ch = [order[y] for y in out_adj[x]]
        if not ch: order[x] = 1
        else:
            mx = max(ch); order[x] = mx + 1 if ch.count(mx) >= 2 else mx
        for p in in_adj[x]:
            pend[p] -= 1
            if pend[p] == 0: dq.append(p)
    out['strahler_max'] = int(order.max()); out['strahler_unassigned'] = int((order == 0).sum())
    # number of streams per order: a stream starts where no child has the same order
    cnt = defaultdict(int)
    for x in range(n):
        if order[x] > 0 and not any(order[y] == order[x] for y in out_adj[x]): cnt[int(order[x])] += 1
    out['streams'] = dict(sorted(cnt.items()))
    ks = sorted(cnt); rb = [cnt[a] / cnt[b] for a, b in zip(ks[:-1], ks[1:])]
    out['horton_RB'] = round(float(np.exp(np.mean(np.log(rb)))), 2) if rb else None
    # nodes with >1 incoming vein (converging = reconnection / loop-making or multi-root)
    out['nodes_indeg_ge2'] = int((indeg >= 2).sum())
    # ---- lattice locking: chord direction of vein segments between junction/tip nodes ----
    xf = X.ravel()[nodes]; yf = Y.ravel()[nodes]
    special = (deg != 2)
    adj = defaultdict(list)
    for a, b in zip(ui.tolist(), vi.tolist()): adj[a].append(b); adj[b].append(a)
    seen = set(); chords = []
    for s in np.nonzero(special)[0].tolist():
        for nb0 in adj[s]:
            if (s, nb0) in seen: continue
            path = [s, nb0]; seen.add((s, nb0))
            while not special[path[-1]]:
                nx = [y for y in adj[path[-1]] if y != path[-2]]
                if not nx: break
                path.append(nx[0])
            seen.add((path[-1], path[-2]))
            dx = xf[path[-1]] - xf[path[0]]; dy = yf[path[-1]] - yf[path[0]]
            chords.append((np.hypot(dx, dy), np.arctan2(dy, dx), len(path) - 1))
    ch = np.array(chords) if chords else np.zeros((0, 3))
    out['segments'] = int(len(ch))
    for Lmin in (5, 10):
        mm = ch[:, 0] >= Lmin
        if mm.sum() >= 10:
            w = ch[mm, 0]; th = ch[mm, 1]
            out[f'chord_L>={Lmin}'] = dict(n=int(mm.sum()), A4=round(float(abs((w * np.exp(4j * th)).sum() / w.sum())), 3),
                                           A8=round(float(abs((w * np.exp(8j * th)).sum() / w.sum())), 3),
                                           A8_re=round(float(((w * np.exp(8j * th)).sum() / w.sum()).real), 3),
                                           # fraction of chord length within 7.5 deg of a lattice direction (isotropic expectation = 15/45 = 0.333)
                                           frac_within7p5deg=round(float(w[np.abs(((np.degrees(th) + 22.5) % 45) - 22.5) < 7.5].sum() / w.sum()), 3),
                                           tortuosity_med=round(float(np.median(ch[mm, 2] / ch[mm, 0])), 3))
    return out, (nodes, ui, vi, q, c)

def main():
    d = sys.argv[1]; snap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    Z, P, f = load(d, snap)
    (U, V, Q, C, K), dirs, N = edge_list(Z)
    wet = Z['wet']; S = Z['S'].astype(float); X = Z['X'].astype(float); Y = Z['Y'].astype(float)
    cx, cy = Z['centre']; R = float(Z['R']); j0 = P['j0']; g = P['gamma']
    res = dict(file=f, N=N, R=R, area=int(wet.sum()), gamma=g)
    # Kirchhoff: net outflow per node
    div = np.zeros(N * N); np.add.at(div, U, Q); np.add.at(div, V, -Q)
    res['kirchhoff_rel'] = float(np.abs(div - S.ravel())[wet.ravel()].max() / np.abs(S).max())
    res['S_sum'] = float(S.sum()); res['S_pos_total'] = float(S[S > 0].sum()); res['n_source_cells(S>0.5*max)'] = int((S > 0.5 * S.max()).sum())
    res['n_sink_cells'] = int((S < -0.5 * j0).sum())
    # potential-flow check: re-solve with regenerated edge noise g_e (same rng order as e1.py), different assembly, compare Q
    try:
        rng = np.random.default_rng(P['seed'])
        if P['jitter'] > 0: rng.uniform(-.5, .5, (N, N)); rng.uniform(-.5, .5, (N, N))
        G = [np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in dirs]
        Cf = Z['C'].astype(float); L = [np.hypot(nbr(X, dd) - X, nbr(Y, dd) - Y) for dd in dirs]
        idx = -np.ones((N, N), int); nw = int(wet.sum()); idx[wet] = np.arange(nw)
        rows = []; cols = []; vals = []
        Wl = []
        for k, dd in enumerate(dirs):
            act = wet & nbr(wet, dd); w = (G[k] * (Cf[k] + P['r']) / L[k])[act]; a = idx[act]; b = nbr(idx, dd)[act]
            rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [w, w, -w, -w]; Wl.append((act, w, a, b))
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nw, nw))
        A = A[1:, 1:].tocsc()                       # ground node 0 instead of the 1e-10 shift
        p = np.zeros(nw); p[1:] = spl.splu(A).solve(S[wet][1:])
        num = 0.0; den = 0.0; Qd = Z['Q'].astype(float)
        for k, (act, w, a, b) in enumerate(Wl):
            q2 = w * (p[a] - p[b]); q1 = Qd[k][act]
            big = np.abs(q1) >= 2 * j0
            num += ((q2 - q1)[big] ** 2).sum(); den += (q1[big] ** 2).sum()
        res['resolve_rel_L2_diff_on_veins'] = float(np.sqrt(num / den))
    except Exception as ex:
        res['resolve_error'] = repr(ex)
    res['thr'] = {}
    for thr in (1, 2, 4, 8, 16):
        o, _ = graph_metrics(U, V, Q, C, thr, j0, (cx, cy), X, Y)
        res['thr'][str(thr)] = o
    # steady state check on thr 2
    m = Q >= 2 * j0
    lr = np.log10(C[m] / Q[m] ** g)
    res['steady_log10_C_over_Qg_p5_p50_p95'] = [round(float(x), 3) for x in np.percentile(lr, [5, 50, 95])]
    res['C_all_p50_p99_max'] = [float(x) for x in np.percentile(C, [50, 99, 100])]
    # radial profile (grow): n edges carrying 80 % of crossing flux
    if P['mode'] == 'grow':
        xf = X.ravel(); yf = Y.ravel()
        du = np.hypot(xf[U] - cx, yf[U] - cy); dv = np.hypot(xf[V] - cx, yf[V] - cy)
        prof = []
        for fq in (0.1, 0.3, 0.5, 0.7, 0.9, 0.97):
            rho = fq * R; mm = (np.minimum(du, dv) < rho) & (np.maximum(du, dv) >= rho)
            q = np.sort(Q[mm])[::-1]; cs = np.cumsum(q)
            n80 = int(np.searchsorted(cs, 0.8 * cs[-1]) + 1)
            # outward minus inward flux should equal total sink outside rho
            prof.append(dict(f=fq, crossing=int(mm.sum()), n80=n80, n80_per_circ=round(n80 / (2 * np.pi * rho), 4), qmax_frac=round(float(q[0] / cs[-1]), 3)))
        res['radial'] = prof
    print(json.dumps(res, indent=1))
    name = os.path.basename(os.path.normpath(d)) + ('' if snap is None else f'_s{snap}')
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'vgraph_{name}.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
