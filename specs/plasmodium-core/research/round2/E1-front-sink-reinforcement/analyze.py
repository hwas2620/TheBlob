#!/usr/bin/env python3
"""Render-independent edge-graph analysis of an e1.py run.

usage: analyze.py NAME [--snap K] [--quiet]     (K = which edges_K.npz; default = last)
writes runs/NAME/analysis[_K].json

All thresholds are in units of |Q|/j0  (= how many front cells' worth of flux an edge carries), and every metric is
reported for several thresholds (1, 2, 4, 8) so that nothing depends on a single hand-picked cut.

metrics
  kirchhoff      : max_i |sum_e Q_e,out - S_i| / max|S|, recomputed independently from the dumped Q and S
  per threshold  : vein edges/nodes, components, largest component fraction, cycle rank (loops = E - V + comps),
                   branch nodes (degree >= 3), tips (degree 1), Strahler max order (diverging = along flow, converging = against flow),
                   stream counts per order and mean bifurcation ratio
  murray         : at vein nodes with 1 parent + >=2 children (flux conserved within 20%): exponent a solving r_p^a = sum r_c^a with r = C^(1/4);
                   steady state of dC/dt = |Q|^g - C predicts a = 4/g
  steady         : median and IQR of log10(C / |Q|^g) on vein edges (0 = adaptation has caught up)
  profile        : grow mode -> rings at f*R ; moving modes -> cross-sections x = cx + f*Rb.  For each: number of edges that carry 80 % of the
                   crossing flux (n80), flux-weighted mean tube radius C^(1/4), max tube radius, participation ratio
"""
import numpy as np, json, sys, os, glob
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))


def strahler(nodes, out_adj, in_adj):
    """Strahler order along out_adj direction (leaves = nodes without out edges). returns dict node->order."""
    order = {}; pending = {n: len(out_adj[n]) for n in nodes}
    stack = [n for n in nodes if pending[n] == 0]
    while stack:
        n = stack.pop()
        ch = [order[c] for c in out_adj[n]]
        if not ch: order[n] = 1
        else:
            m = max(ch); order[n] = m + 1 if ch.count(m) >= 2 else m
        for q in in_adj[n]:
            pending[q] -= 1
            if pending[q] == 0: stack.append(q)
    return order   # nodes on directed cycles (should not exist for potential flow) stay unassigned


def stream_counts(order, out_adj):
    cnt = defaultdict(int)
    for n, o in order.items():
        if not any(order.get(c) == o for c in out_adj[n]): cnt[o] += 1
    return dict(sorted(cnt.items()))


def analyse(name, snap=None):
    d = os.path.join(HERE, 'runs', name)
    P = json.load(open(os.path.join(d, 'params.json')))
    fs = sorted(glob.glob(os.path.join(d, 'edges_*.npz')), key=lambda f: int(os.path.basename(f)[6:-4]))
    f = fs[-1] if snap is None else os.path.join(d, f'edges_{snap}.npz')
    Z = np.load(f)
    C = Z['C'].astype(float); Q = Z['Q'].astype(float); wet = Z['wet']; S = Z['S'].astype(float); X = Z['X'].astype(float); Y = Z['Y'].astype(float)
    dirs = [tuple(x) for x in Z['dirs']]; N = wet.shape[0]; cx, cy = Z['centre']; R = float(Z['R']); t = float(Z['t'])
    j0 = P['j0']; g = P['gamma']
    res = dict(name=name, file=os.path.basename(f), t=t, R=R, N=N, area=int(wet.sum()))
    # ---- independent Kirchhoff check ----
    div = np.zeros((N, N))
    for k, dd in enumerate(dirs):
        div += Q[k] - np.roll(Q[k], (dd[1], dd[0]), (0, 1))
    res['kirchhoff_rel_resid'] = float(np.abs(div - S)[wet].max() / max(np.abs(S).max(), 1e-30))
    res['I_total'] = float(S[S > 0].sum())
    # ---- edge list ----
    idx = np.arange(N * N).reshape(N, N)
    U = []; V = []; QQ = []; CC = []
    for k, dd in enumerate(dirs):
        m = (np.abs(Q[k]) > 0) & wet
        u = idx[m]; v = np.roll(idx, (-dd[1], -dd[0]), (0, 1))[m]; q = Q[k][m]; c = C[k][m]
        sw = q < 0
        uu = np.where(sw, v, u); vv = np.where(sw, u, v)          # oriented along the flow
        U.append(uu); V.append(vv); QQ.append(np.abs(q)); CC.append(c)
    U = np.concatenate(U); V = np.concatenate(V); QQ = np.concatenate(QQ); CC = np.concatenate(CC)
    xf = X.ravel(); yf = Y.ravel()
    res['thr'] = {}
    for thr in (1, 2, 4, 8):
        m = QQ >= thr * j0
        u = U[m]; v = V[m]; q = QQ[m]; c = CC[m]
        if len(u) < 3: res['thr'][str(thr)] = None; continue
        nodes = np.unique(np.concatenate([u, v]))
        out_adj = defaultdict(list); in_adj = defaultdict(list)
        for a, b in zip(u.tolist(), v.tolist()): out_adj[a].append(b); in_adj[b].append(a)
        nl = nodes.tolist()
        deg = {n: len(out_adj[n]) + len(in_adj[n]) for n in nl}
        # components (union-find)
        par = {n: n for n in nl}
        def find(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for a, b in zip(u.tolist(), v.tolist()):
            ra, rb = find(a), find(b)
            if ra != rb: par[ra] = rb
        comp_e = defaultdict(int)
        for a in u.tolist(): comp_e[find(a)] += 1
        ncomp = len(set(find(n) for n in nl))
        od = strahler(nl, out_adj, in_adj); oc = strahler(nl, in_adj, out_adj)
        scd = stream_counts(od, out_adj); scc = stream_counts(oc, in_adj)
        def bif(sc):
            ks = sorted(sc); r = [sc[a] / sc[b] for a, b in zip(ks[:-1], ks[1:]) if sc[b] > 0]
            return round(float(np.exp(np.mean(np.log(r)))), 2) if r else None
        e = dict(edges=int(len(u)), nodes=int(len(nl)), comps=int(ncomp), largest_frac=round(max(comp_e.values()) / len(u), 3),
                 loops=int(len(u) - len(nl) + ncomp), branch_nodes=int(sum(1 for n in nl if deg[n] >= 3)), tips=int(sum(1 for n in nl if deg[n] == 1)),
                 strahler_div=int(max(od.values())) if od else None, strahler_conv=int(max(oc.values())) if oc else None,
                 streams_div=scd, streams_conv=scc, bif_ratio_div=bif(scd), bif_ratio_conv=bif(scc),
                 unassigned=int(len(nl) - len(od)))
        e['loops_per_branch'] = round(e['loops'] / max(e['branch_nodes'], 1), 3)
        # steady state check
        lr = np.log10(np.maximum(c, 1e-30) / (q / P['Q0']) ** g) if P['law'] == 'pow' else np.zeros(1)
        e['steady_log10_C_over_Qg_p25_p50_p75'] = [round(float(x), 3) for x in np.percentile(lr, [25, 50, 75])]
        # Murray exponent at junctions
        emap = {(a, b): (qq, cc) for a, b, qq, cc in zip(u.tolist(), v.tolist(), q.tolist(), c.tolist())}
        al = []; asym = []
        for n in nl:
            for (pa, ch, key) in ((in_adj[n], out_adj[n], 'div'), (out_adj[n], in_adj[n], 'conv')):
                if len(pa) == 1 and len(ch) >= 2:
                    ep = emap[(pa[0], n)] if key == 'div' else emap[(n, pa[0])]
                    ec = [emap[(n, c_)] if key == 'div' else emap[(c_, n)] for c_ in ch]
                    qs = sum(x[0] for x in ec)
                    if not (0.8 * ep[0] <= qs <= 1.25 * ep[0]): continue
                    rp = ep[1] ** 0.25; rc = np.array([x[1] for x in ec]) ** 0.25
                    if rc.max() >= rp or rp <= 0: continue
                    lo, hi = 0.2, 40.0
                    for _ in range(50):
                        mid = 0.5 * (lo + hi)
                        if (rc ** mid).sum() > rp ** mid: lo = mid
                        else: hi = mid
                    al.append(0.5 * (lo + hi)); asym.append(min(x[0] for x in ec) / max(x[0] for x in ec))
        if len(al) >= 5:
            e['murray_n'] = len(al); e['murray_exp_p25_p50_p75'] = [round(float(x), 2) for x in np.percentile(al, [25, 50, 75])]
            e['junction_flux_asym_median'] = round(float(np.median(asym)), 3)
        res['thr'][str(thr)] = e
    res['murray_predicted_4_over_gamma'] = round(4 / g, 3)
    # ---- profiles ----
    prof = []
    if P['mode'] == 'grow':
        du = np.hypot(xf[U] - cx, yf[U] - cy); dv = np.hypot(xf[V] - cx, yf[V] - cy)
        fr = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
        for fq in fr:
            rho = fq * R; m = (np.minimum(du, dv) < rho) & (np.maximum(du, dv) >= rho)
            prof.append((fq, m))
    else:
        Rb = P['Rb_frac'] * N; tail = P['taper'] * Rb if P['mode'] == 'teardrop' else Rb
        xs = np.concatenate([np.linspace(-0.85 * tail, 0, 5)[:-1], np.linspace(0, 0.85 * Rb, 4)])
        for x0 in xs:
            m = (np.minimum(xf[U], xf[V]) < cx + x0) & (np.maximum(xf[U], xf[V]) >= cx + x0)
            prof.append((round(float(x0 / Rb), 2), m))
    out = []
    for fq, m in prof:
        q = QQ[m]; c = CC[m]
        if q.size == 0 or q.sum() <= 0: out.append(dict(pos=fq, n=0)); continue
        o = np.argsort(-q); cs = np.cumsum(q[o]); n80 = int(np.searchsorted(cs, 0.8 * cs[-1]) + 1)
        top = o[:n80]; rad = c ** 0.25
        out.append(dict(pos=fq, crossing=int(q.size), flux=round(float(q.sum()), 2), n80=n80, PR=round(float(q.sum() ** 2 / (q.size * (q ** 2).sum())), 4),
                        r_mean_top=round(float((rad[top] * q[top]).sum() / q[top].sum()), 3), r_max=round(float(rad.max()), 3),
                        q_max_frac=round(float(q.max() / q.sum()), 3)))
    res['profile'] = out
    json.dump(res, open(os.path.join(d, 'analysis.json' if snap is None else f'analysis_{snap}.json'), 'w'), indent=1)
    return res


def line(r, thr='2'):
    e = r['thr'].get(thr)
    if not e: return '%-22s (no veins at thr %s)' % (r['name'], thr)
    mu = e.get('murray_exp_p25_p50_p75', [None] * 3)
    pr = ' '.join('%s:%d/%.2f' % (p['pos'], p.get('n80', 0), p.get('r_mean_top', 0)) for p in r['profile'] if p.get('n80'))
    return '%-22s kres=%.0e E=%5d br=%4d tips=%4d loops=%4d L/br=%.2f lf=%.2f Sd=%s Sc=%s Rb=%s murray=%s(n=%s) ss=%s | %s' % (
        r['name'], r['kirchhoff_rel_resid'], e['edges'], e['branch_nodes'], e['tips'], e['loops'], e['loops_per_branch'], e['largest_frac'], e['strahler_div'], e['strahler_conv'],
        e['bif_ratio_div'], mu[1], e.get('murray_n'), e['steady_log10_C_over_Qg_p25_p50_p75'][1], pr)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    snap = None; thr = '2'
    for a in sys.argv[1:]:
        if a.startswith('--snap='): snap = int(a.split('=')[1])
        if a.startswith('--thr='): thr = a.split('=')[1]
    for nm in args:
        try: print(line(analyse(nm, snap), thr), flush=True)
        except Exception as ex: print('%-22s analysis failed: %r' % (nm, ex))
