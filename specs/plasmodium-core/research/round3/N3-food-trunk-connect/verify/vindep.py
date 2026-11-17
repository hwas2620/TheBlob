#!/usr/bin/env python3
"""Independent native edge-graph metrics for N3 (verifier's own implementation; does NOT import graphm).
Edge convention (read from n3.py): C[k, y, x] = conductance of the edge from cell (y, x) to cell (y+dy, x+dx) mod N, DIRS[k] = (dx, dy).
Own union-find, own heap Dijkstra, own chain tracing.  No np.roll."""
import numpy as np, heapq, json, sys, os, glob
from scipy.stats import spearmanr

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
LEN = [1.0, 1.0, 2 ** 0.5, 2 ** 0.5]


def load(f):
    Z = np.load(f, allow_pickle=True)
    return {k: Z[k] for k in Z.files}


def active_edges(C, wet):
    """arrays a, b (flat node ids), k, c, for every edge whose two end cells are wet"""
    N = wet.shape[0]; A = []; B = []; K = []; Cc = []
    ys, xs = np.nonzero(wet)
    for k, (dx, dy) in enumerate(DIRS):
        y2 = (ys + dy) % N; x2 = (xs + dx) % N; m = wet[y2, x2]
        A.append(ys[m] * N + xs[m]); B.append(y2[m] * N + x2[m]); K.append(np.full(int(m.sum()), k)); Cc.append(C[k, ys[m], xs[m]].astype(float))
    return np.concatenate(A), np.concatenate(B), np.concatenate(K), np.concatenate(Cc)


class UF:
    def __init__(self): self.p = {}
    def find(self, x):
        p = self.p
        if x not in p: p[x] = x; return x
        r = x
        while p[r] != r: r = p[r]
        while p[x] != r: p[x], x = r, p[x]
        return r
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra] = rb


def disc_mask(N, fx, fy, r):
    yy, xx = np.mgrid[0:N, 0:N]
    dx = (xx - fx + N / 2) % N - N / 2; dy = (yy - fy + N / 2) % N - N / 2
    return (dx * dx + dy * dy) < r * r


def vein_stats(a, b, c, thr, indisc=None):
    """largest component (edge share) of the graph of edges with C > thr.  'ex' variants count only edges that are not entirely inside a food disc
    (the disc cells still act as connectors)."""
    m = c > thr; E = int(m.sum())
    if E < 3: return dict(E=E)
    av = a[m].tolist(); bv = b[m].tolist(); uf = UF()
    for u, v in zip(av, bv): uf.union(u, v)
    roots = [uf.find(u) for u in av]
    cnt = {}; deg = {}
    for u, v, r in zip(av, bv, roots):
        cnt[r] = cnt.get(r, 0) + 1; deg[u] = deg.get(u, 0) + 1; deg[v] = deg.get(v, 0) + 1
    V = len(deg); nc = len(cnt)
    out = dict(E=E, V=V, comps=nc, largest=round(max(cnt.values()) / E, 3), endpoints=sum(1 for d in deg.values() if d == 1),
               junctions=sum(1 for d in deg.values() if d >= 3), cycles=E - V + nc, C_med=round(float(np.median(c[m])), 2))
    if indisc is not None:
        ins = indisc[a[m]] & indisc[b[m]]
        cntx = {}
        for r, i in zip(roots, ins.tolist()):
            if not i: cntx[r] = cntx.get(r, 0) + 1
        Ex = int((~ins).sum())
        out.update(E_in_disc=int(ins.sum()), E_ex=Ex, largest_ex=round(max(cntx.values()) / Ex, 3) if Ex >= 3 else None,
                   C_med_ex=round(float(np.median(c[m][~ins])), 2) if Ex else None, C_med_in=round(float(np.median(c[m][ins])), 2) if ins.any() else None)
    out['_roots'] = dict(zip(av, roots)); out['_roots'].update(zip(bv, roots)); out['_cnt'] = cnt
    return out


def min_resist_path(a, b, k, c, G, r, N, srcs, tgts):
    """heap Dijkstra over all active edges, weight = L / (G (C + r)); multi-source srcs -> any tgt.  Returns list of edge indices of the path."""
    gk = G[k, a // N, a % N].astype(float); w = np.array(LEN)[k] / (gk * (c + r))
    adj = {}
    for i, (u, v) in enumerate(zip(a.tolist(), b.tolist())):
        adj.setdefault(u, []).append((v, i)); adj.setdefault(v, []).append((u, i))
    dist = {s: 0.0 for s in srcs}; prev = {}
    pq = [(0.0, s) for s in srcs]; heapq.heapify(pq); T = set(tgts); done = set(); end = None
    while pq:
        d, u = heapq.heappop(pq)
        if u in done: continue
        done.add(u)
        if u in T: end = u; break
        for v, i in adj.get(u, ()):
            nd = d + w[i]
            if nd < dist.get(v, np.inf): dist[v] = nd; prev[v] = (u, i); heapq.heappush(pq, (nd, v))
    if end is None: return None, None
    es = []; u = end
    while u in prev: u, i = prev[u]; es.append(i)
    return es, dist[end]


def bottleneck(a, b, c, srcs, tgts):
    """widest path: largest C* such that the two discs are joined by edges with C >= C* (disc cells pre-merged)"""
    uf = UF(); S = 'S'; Tn = 'T'
    for s in srcs: uf.union(s, S)
    for t in tgts: uf.union(t, Tn)
    if uf.find(S) == uf.find(Tn): return float('inf')
    order = np.argsort(-c)
    al = a.tolist(); bl = b.tolist()
    for i in order.tolist():
        uf.union(al[i], bl[i])
        if uf.find(S) == uf.find(Tn): return float(c[i])
    return 0.0


def body_components(a, b, wet, h):
    uf = UF()
    for n in np.nonzero(wet.ravel())[0].tolist(): uf.find(n)
    for u, v in zip(a.tolist(), b.tolist()): uf.union(u, v)
    vol = {}; hf = h.ravel()
    for n in list(uf.p):
        r = uf.find(n); vol[r] = vol.get(r, 0.0) + float(hf[n])
    tot = sum(vol.values())
    return len(vol), (max(vol.values()) / tot if tot > 0 else 0.0), uf


def chords(a, b, c, thr, N, Lmin=5):
    """trace chains between special (deg != 2) nodes of the vein graph; return share of chord length within +-7.5 deg of a lattice direction (0/45/90/135)"""
    m = c > thr; av = a[m].tolist(); bv = b[m].tolist(); adj = {}
    for u, v in zip(av, bv): adj.setdefault(u, []).append(v); adj.setdefault(v, []).append(u)
    def step(u, v):
        return ((v % N - u % N + N // 2) % N - N // 2, (v // N - u // N + N // 2) % N - N // 2)
    seen = set(); tot = 0.0; lat = 0.0; n = 0
    for s in [u for u in adj if len(adj[u]) != 2]:
        for v in adj[s]:
            if (s, v) in seen: continue
            seen.add((s, v)); dx, dy = step(s, v); p, q = s, v; guard = 0
            while len(adj[q]) == 2 and guard < 100000:
                nx = adj[q][0] if adj[q][0] != p else adj[q][1]
                sx, sy = step(q, nx); dx += sx; dy += sy; p, q = q, nx; guard += 1
            seen.add((q, p))
            L = (dx * dx + dy * dy) ** 0.5
            if L >= Lmin:
                ang = np.degrees(np.arctan2(dy, dx)) % 45.0; dev = min(ang, 45.0 - ang)
                tot += L; n += 1
                if dev < 7.5: lat += L
    return (round(lat / tot, 3) if tot > 0 else None), n


def analyse(S, thrs=(4.0, 10.0, 30.0), verbose=False):
    C = S['C'].astype(float); wet = S['wet'].astype(bool); h = S['h'].astype(float); N = wet.shape[0]
    foods = np.asarray(S['foods']).reshape(-1, 2); fr = float(S['food_r']); r = float(S['r'])
    a, b, k, c = active_edges(C, wet)
    discs = [disc_mask(N, fx, fy, fr) for fx, fy in foods]
    indisc = np.zeros(N * N, bool)
    for d in discs: indisc |= d.ravel()
    out = dict(t=float(S['t']), area=int(wet.sum()), n_act=int(a.size), act_C_med=round(float(np.median(c)), 3) if a.size else None)
    vs = {}
    for thr in thrs:
        v = vein_stats(a, b, c, thr, indisc); vs[thr] = v
        out[f'v{int(thr)}'] = {kk: vv for kk, vv in v.items() if not kk.startswith('_')}
    nb_, lv, uf_body = body_components(a, b, wet, h)
    out['body_comps'] = nb_; out['body_largest_vol'] = round(lv, 3)
    out['vol_on_discs'] = round(float(h[indisc.reshape(N, N)].sum() / max(h.sum(), 1e-12)), 3)
    out['h_min'] = round(float(h[wet].min()), 3) if wet.any() else None; out['n_h_neg'] = int((h[wet] < 0).sum()); out['n_h_lt_hmin'] = int((h[wet] < 0.15).sum())
    # reservoir membership of the vein graph (thr 4)
    v4 = vs[4.0]
    if '_roots' in v4:
        roots = v4['_roots']; cnt = v4['_cnt']; big = max(cnt, key=cnt.get); res = []
        for d in discs:
            cells = np.nonzero((d & wet).ravel())[0].tolist(); rs = set(roots[n] for n in cells if n in roots)
            res.append(dict(wet_cells=len(cells), in_graph=bool(rs), in_largest=big in rs, comp_share=round(sum(cnt[x] for x in rs) / v4['E'], 3)))
        out['res'] = res
    out['chord_lat_frac'], out['chord_n'] = chords(a, b, c, 4.0, N)
    if len(foods) >= 2:
        sa = np.nonzero((discs[0] & wet).ravel())[0].tolist(); sb = np.nonzero((discs[1] & wet).ravel())[0].tolist()
        P = dict(wetA=len(sa), wetB=len(sb))
        if sa and sb:
            es, dist = min_resist_path(a, b, k, c, S['G'], r, N, sa, sb)
            if es is None: P['connected'] = False
            else:
                es = np.array(es, int); ins = indisc[a[es]] & indisc[b[es]]; eo = es[~ins] if (~ins).sum() >= 3 else es
                pc = c[eo]; vm = c > 4.0; inall = indisc[a] & indisc[b]; onp = np.zeros(a.size, bool); onp[es] = True
                med_all = float(np.median(c[vm])) if vm.any() else float('nan')
                m_ex = vm & ~inall; m_exnp = vm & ~inall & ~onp
                P.update(connected=True, n_path=int(es.size), n_out=int(eo.size), path_C_med=round(float(np.median(pc)), 2), path_C_min=round(float(pc.min()), 3),
                         vein_med_all=round(med_all, 2), ratio_all=round(float(np.median(pc) / med_all), 2),
                         vein_med_exdisc=round(float(np.median(c[m_ex])), 2) if m_ex.any() else None,
                         ratio_exdisc=round(float(np.median(pc) / np.median(c[m_ex])), 2) if m_ex.any() else None,
                         n_vein_exdisc_offpath=int(m_exnp.sum()),
                         vein_med_offpath=round(float(np.median(c[m_exnp])), 2) if m_exnp.sum() >= 5 else None,
                         ratio_offpath=round(float(np.median(pc) / np.median(c[m_exnp])), 2) if m_exnp.sum() >= 5 else None,
                         path_share_of_exdisc_veins=round(float((vm & ~inall & onp).sum() / max(m_ex.sum(), 1)), 3),
                         path_h_med=round(float(np.median(h.ravel()[a[eo]])), 3), path_h_min=round(float(h.ravel()[a[eo]].min()), 3),
                         path_cells_h_lt_hmin=int((h.ravel()[a[eo]] < 0.15).sum()))
                if 'Qmean' in S and 'Qgross' in S:
                    qn = np.abs(S['Qmean'][k[eo], a[eo] // N, a[eo] % N].astype(float)); qg = S['Qgross'][k[eo], a[eo] // N, a[eo] % N].astype(float)
                    P.update(path_net_med=round(float(np.median(qn)), 4), path_gross_med=round(float(np.median(qg)), 4))
                # local straightness / lattice locking of the path: chords of 10 consecutive path cells
                seq = [int(b[es[0]])] if False else None
            P['bottleneck_C'] = round(bottleneck(a, b, c, sa, sb), 3)
            if '_roots' in v4:
                roots = v4['_roots']; ra = set(roots[n] for n in sa if n in roots); rb = set(roots[n] for n in sb if n in roots); P['same_vein_comp'] = bool(ra & rb)
        out['path'] = P
    return out


def pos_spearman(S, angle_deg, thrs=(4.0, 10.0, 30.0)):
    """Spearman(position along axis, log C) over vein edges; position = projection of the edge midpoint on the food axis, unwrapped about the wet circular mean"""
    C = S['C'].astype(float); wet = S['wet'].astype(bool); N = wet.shape[0]
    a, b, k, c = active_edges(C, wet)
    ys, xs = np.nonzero(wet)
    def cmean(v): ang = 2 * np.pi * v / N; return (np.arctan2(np.sin(ang).mean(), np.cos(ang).mean()) % (2 * np.pi)) * N / (2 * np.pi)
    cx, cy = cmean(xs), cmean(ys)
    ux, uy = np.cos(np.radians(angle_deg)), np.sin(np.radians(angle_deg))
    ex = ((a % N) - cx + N / 2) % N - N / 2 + 0.5 * np.array([d[0] for d in DIRS])[k]
    ey = ((a // N) - cy + N / 2) % N - N / 2 + 0.5 * np.array([d[1] for d in DIRS])[k]
    pos = ex * ux + ey * uy
    wx = (xs - cx + N / 2) % N - N / 2; wy = (ys - cy + N / 2) % N - N / 2
    span = float((wx * ux + wy * uy).max() - (wx * ux + wy * uy).min())
    out = dict(span=round(span, 1))
    for thr in thrs:
        m = c > thr
        out[f'sp{int(thr)}'] = round(float(spearmanr(pos[m], np.log(c[m]))[0]), 3) if m.sum() > 10 else None
        out[f'n{int(thr)}'] = int(m.sum())
    return out


if __name__ == '__main__':
    for f in sys.argv[1:]:
        S = load(f); o = analyse(S); print(f); print(json.dumps(o, indent=1))
