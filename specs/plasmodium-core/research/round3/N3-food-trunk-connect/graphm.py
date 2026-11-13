#!/usr/bin/env python3
"""N3 native edge-graph metrics (torus aware). Everything is measured on the edge conductance graph, never on a render.

usage: python3 graphm.py RUN_DIR [RUN_DIR ...]      -> re-analyses every state_t*.npz of the run, writes graph.json

state dict keys: C[4,N,N], wet, h, age, sage, eage[4], Qmean[4] (signed window mean), Qgross[4], G[4], cen (wrapped x,y), t,
                 foods [[fx,fy],...], food_r, r (leak conductance), dirv (unit travel vector)
"""
import numpy as np, json, sys, os, glob
from scipy.stats import spearmanr
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra, minimum_spanning_tree, breadth_first_order

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
LS = np.array([1.0, 1.0, 2 ** .5, 2 ** .5])
CTHR = 4.0


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))


def mimg(v, N): return (v + N / 2) % N - N / 2


def edges_of(mask4, N):
    """flattened node ids (a, b), direction index k, and (ys, xs) of the owning cell for every edge where mask4[k] is true"""
    A = []; B = []; K = []; YS = []; XS = []
    for k, d in enumerate(DIRS):
        ys, xs = np.nonzero(mask4[k])
        A.append(ys * N + xs); B.append(((ys + d[1]) % N) * N + ((xs + d[0]) % N)); K.append(np.full(ys.size, k)); YS.append(ys); XS.append(xs)
    return [np.concatenate(v) for v in (A, B, K, YS, XS)]


def act_mask(wet): return np.array([wet & nb(wet, d) for d in DIRS])


def basic(C, wet, cthr=CTHR):
    N = wet.shape[0]; act = act_mask(wet)
    a, b, k, ys, xs = edges_of((C > cthr) & act, N)
    E = a.size
    if E < 3: return dict(edges=int(E), largest=0.0, comps=0, endpoints=0, junctions=0, cycles=0, end_per_junc=None), None
    nodes, inv = np.unique(np.concatenate([a, b]), return_inverse=True); V = nodes.size
    ai = inv[:E]; bi = inv[E:]
    nc, lab = connected_components(coo_matrix((np.ones(E), (ai, bi)), shape=(V, V)), directed=False)
    deg = np.bincount(np.concatenate([ai, bi]), minlength=V)
    csize = np.bincount(lab[ai], minlength=nc)
    ne = int((deg == 1).sum()); nj = int((deg >= 3).sum())
    out = dict(edges=int(E), nodes=int(V), comps=int(nc), largest=round(float(csize.max() / E), 3), comps_ge10=int((csize >= 10).sum()),
               endpoints=ne, junctions=nj, cycles=int(E - V + nc), end_per_junc=round(ne / max(nj, 1), 3),
               C_med=round(float(np.median(C[k, ys, xs])), 2), C_p90=round(float(np.percentile(C[k, ys, xs], 90)), 1), C_max=round(float(C[k, ys, xs].max()), 1))
    return out, dict(a=a, b=b, k=k, ys=ys, xs=xs, nodes=nodes, ai=ai, bi=bi, lab=lab, csize=csize, deg=deg, c=C[k, ys, xs])


def sheet_link(C, wet, h, cthr=CTHR, hs=0.5):
    """vein graph joined through the thick sheet: edges = (C > cthr) or (both end cells have h > hs).  Returns the share of VEIN edges in the largest
    such component and the share of vein edges whose component contains sheet cells.  (two trunks that both end in the front sheet count as connected here)"""
    N = wet.shape[0]; act = act_mask(wet); sh = wet & (h > hs)
    vm = (C > cthr) & act; sm = np.array([sh & nb(sh, d) for d in DIRS]) & act
    a, b, k, ys, xs = edges_of(vm | sm, N)
    if a.size < 3 or vm.sum() < 3: return dict(largest_ws=None, touch_sheet=None)
    isv = vm[k, ys, xs]
    nc, lab = connected_components(coo_matrix((np.ones(a.size), (a, b)), shape=(N * N, N * N)), directed=False)
    cs = np.bincount(lab[a[isv]], minlength=nc); hassheet = np.zeros(nc, bool); hassheet[np.unique(lab[np.nonzero(sh.ravel())[0]])] = True
    return dict(largest_ws=round(float(cs.max() / isv.sum()), 3), touch_sheet=round(float(cs[hassheet].sum() / isv.sum()), 3), sheet_cells=int(sh.sum()))


def body_comps(wet, h):
    N = wet.shape[0]; n = int(wet.sum())
    if n == 0: return dict(comps=0, largest_area=0, largest_vol=0)
    idx = -np.ones(N * N, np.int64); idx[wet.ravel()] = np.arange(n)
    a, b, k, ys, xs = edges_of(act_mask(wet), N)
    nc, lab = connected_components(coo_matrix((np.ones(a.size), (idx[a], idx[b])), shape=(n, n)), directed=False)
    area = np.bincount(lab, minlength=nc); vol = np.bincount(lab, weights=h[wet], minlength=nc)
    big = int(np.argmax(vol))
    return dict(comps=int(nc), largest_area=round(float(area[big] / n), 3), largest_vol=round(float(vol[big] / max(vol.sum(), 1e-12)), 3)), (lab, big, idx)


def disc(N, fx, fy, r):
    jj, ii = np.mgrid[0:N, 0:N]
    return np.hypot(mimg(ii - fx, N), mimg(jj - fy, N)) < r


def food_path(C, G, wet, mA, mB, r, cthr=CTHR, Qm=None, Qg=None):
    """min-resistance path between the wet cells of two food discs over ALL active edges; weights L/(G (C+r))"""
    N = wet.shape[0]
    sa = np.nonzero((mA & wet).ravel())[0]; sb = np.nonzero((mB & wet).ravel())[0]
    if sa.size == 0 or sb.size == 0: return dict(connected=False, reason='food not wet')
    act = act_mask(wet); a, b, k, ys, xs = edges_of(act, N)
    c = C[k, ys, xs]; w = LS[k] / (G[k, ys, xs] * (c + r))
    VA = N * N; VB = N * N + 1; tiny = 1e-9
    rows = np.concatenate([a, np.full(sa.size, VA), np.full(sb.size, VB)]); cols = np.concatenate([b, sa, sb])
    vals = np.concatenate([w, np.full(sa.size + sb.size, tiny)])
    g = csr_matrix((vals, (rows, cols)), shape=(N * N + 2, N * N + 2))
    dist, pred = dijkstra(g, directed=False, indices=VA, return_predecessors=True)
    if not np.isfinite(dist[VB]): return dict(connected=False, reason='no wet path')
    path = [VB]
    while path[-1] != VA: path.append(int(pred[path[-1]]))
    path = path[1:-1]                                       # real cells from B side to A side
    key = {}
    for i in range(a.size): key[(int(a[i]), int(b[i]))] = i
    pc = []; inside = []; pq = []; pg = []
    mAf = mA.ravel(); mBf = mB.ravel()
    for u, v in zip(path[:-1], path[1:]):
        i = key.get((u, v)); sg = 1.0
        if i is None: i = key[(v, u)]; sg = -1.0
        pc.append(c[i]); inside.append((mAf[u] or mBf[u]) and (mAf[v] or mBf[v]))
        if Qm is not None: pq.append(sg * Qm[k[i], ys[i], xs[i]]); pg.append(Qg[k[i], ys[i], xs[i]])
    pc = np.array(pc); inside = np.array(inside, bool)
    if pc.size == 0: return dict(connected=True, n=0)
    po = pc[~inside] if (~inside).sum() >= 3 else pc         # path edges outside the food discs
    vm = (C > cthr) & act
    allv = C[vm]; med_v = float(np.median(allv)) if allv.size else float('nan'); med_all = float(np.median(C[act]))
    # are the two foods in the same vein-graph component?
    same = False
    bs, gi = basic(C, wet, cthr)
    if gi is not None:
        nodeset = gi['nodes']; lab = gi['lab']
        la = set(lab[np.searchsorted(nodeset, sa[np.isin(sa, nodeset)])].tolist()); lb = set(lab[np.searchsorted(nodeset, sb[np.isin(sb, nodeset)])].tolist())
        same = len(la & lb) > 0
    fx = {}
    if Qm is not None and len(pq) == pc.size:
        pq_ = np.array(pq); pg_ = np.array(pg); mo = ~inside if (~inside).sum() >= 3 else np.ones(pc.size, bool)
        fx = dict(path_net_med_signed_B_to_A=round(float(np.median(pq_[mo])), 4), path_absnet_med=round(float(np.median(np.abs(pq_[mo]))), 4), path_gross_med=round(float(np.median(pg_[mo])), 4),
                  path_gross_over_net=round(float(pg_[mo].sum() / max(np.abs(pq_[mo]).sum(), 1e-12)), 2))
    return dict(fx, connected=True, n=int(pc.size), n_out=int(po.size), resist=round(float(dist[VB]), 4), C_med=round(float(np.median(po)), 2), C_min=round(float(po.min()), 3),
                C_gmean=round(float(np.exp(np.log(np.maximum(po, 1e-9)).mean())), 2), frac_vein=round(float((po > cthr).mean()), 3),
                vein_med=round(med_v, 2), act_med=round(med_all, 2), ratio_vs_vein_med=round(float(np.median(po) / med_v), 2) if med_v == med_v else None,
                ratio_min_vs_vein_med=round(float(po.min() / med_v), 3) if med_v == med_v else None, same_vein_comp=bool(same),
                path=[int(v) for v in path])


def quick(S, cthr=CTHR):
    """cheap per-interval record"""
    C = S['C']; wet = S['wet']; h = S['h']; N = wet.shape[0]
    out = dict(t=round(float(S['t']), 2), area=int(wet.sum()))
    bs, gi = basic(C, wet, cthr); bs.update(sheet_link(C, wet, h, cthr)); out['vein'] = bs
    bc, _ = body_comps(wet, h); out['body'] = bc
    foods = [tuple(float(x) for x in v) for v in np.asarray(S.get('foods', [])).reshape(-1, 2)]; fr = float(S.get('food_r', 4.0))
    discs = [disc(N, fx, fy, fr) for fx, fy in foods]
    if gi is not None and foods:
        nodes = gi['nodes']; lab = gi['lab']; csize = gi['csize']; big = int(np.argmax(csize)); res = []
        age = S['age']; young = wet & (age < 10)
        for m in discs:
            fn = np.nonzero((m & wet).ravel())[0]; fn = fn[np.isin(fn, nodes)]
            if fn.size == 0: res.append(dict(in_graph=False)); continue
            comps = np.unique(lab[np.searchsorted(nodes, fn)])
            innode = np.isin(lab, comps); mk = np.zeros(N * N, bool); mk[nodes[innode]] = True; mk = mk.reshape(N, N)
            near = mk.copy()
            for dy in range(-2, 3):
                for dx in range(-2, 3): near |= np.roll(mk, (dy, dx), (0, 1))
            res.append(dict(in_graph=True, in_largest=bool(big in comps), comp_edge_frac=round(float(csize[comps].sum() / csize.sum()), 3),
                            front_reach=round(float((near & young).sum() / max(young.sum(), 1)), 3), young=int(young.sum())))
        out['res'] = res
    if len(foods) >= 2:
        prs = {}
        for i in range(len(foods)):
            for j in range(i + 1, len(foods)):
                fp = food_path(C, S['G'], wet, discs[i], discs[j], S['r'], cthr); fp.pop('path', None); prs[f'{i}-{j}'] = fp
        out['path'] = prs
    return out


def strahler(gi, C, root_node=None):
    """Strahler order on the max-C spanning tree of the largest vein component, rooted at root_node (index into gi['nodes']) or the max-C node"""
    lab = gi['lab']; csize = gi['csize']; big = int(np.argmax(csize)); ai = gi['ai']; bi = gi['bi']; c = gi['c']
    m = lab[ai] == big
    V = gi['nodes'].size
    g = coo_matrix((1.0 / np.maximum(c[m], 1e-9), (ai[m], bi[m])), shape=(V, V)).tocsr()
    T = minimum_spanning_tree(g); T = T + T.T
    if root_node is None or lab[root_node] != big:
        e = np.argmax(np.where(m, c, -1)); root_node = int(ai[e])
    order, pred = breadth_first_order(T, root_node, directed=False, return_predecessors=True)
    st = np.zeros(V, int); kids = [[] for _ in range(V)]
    for v in order[1:]: kids[pred[v]].append(v)
    for v in order[::-1]:
        ch = [st[x] for x in kids[v]]
        if not ch: st[v] = 1
        else:
            mx = max(ch); st[v] = mx + 1 if ch.count(mx) >= 2 else mx
    # stream counts per order (a stream starts where no child has the same order)
    cnt = {}
    for v in order:
        if not any(st[x] == st[v] for x in kids[v]): cnt[int(st[v])] = cnt.get(int(st[v]), 0) + 1
    return dict(strahler_max=int(st[root_node]), streams=dict(sorted(cnt.items())), tree_nodes=int(order.size))


def chord_orient(gi, N):
    deg = gi['deg']; ai = gi['ai']; bi = gi['bi']; nodes = gi['nodes']
    yf, xf = np.divmod(nodes, N)
    adj = [[] for _ in range(nodes.size)]
    for u, v in zip(ai.tolist(), bi.tolist()): adj[u].append(v); adj[v].append(u)
    special = deg != 2; seen = set(); ch = []
    for s in np.nonzero(special)[0].tolist():
        for n0 in adj[s]:
            if (s, n0) in seen: continue
            path = [s, n0]; seen.add((s, n0)); dx = mimg(xf[n0] - xf[s], N); dy = mimg(yf[n0] - yf[s], N)
            while not special[path[-1]]:
                nx = [y for y in adj[path[-1]] if y != path[-2]]
                if not nx: break
                dx += mimg(xf[nx[0]] - xf[path[-1]], N); dy += mimg(yf[nx[0]] - yf[path[-1]], N); path.append(nx[0])
            seen.add((path[-1], path[-2]))
            ch.append((np.hypot(dx, dy), np.arctan2(dy, dx), len(path) - 1))
    ch = np.array(ch) if ch else np.zeros((0, 3)); out = dict(segments=int(len(ch)))
    for Lmin in (5, 10):
        mm = ch[:, 0] >= Lmin
        if mm.sum() >= 10:
            w = ch[mm, 0]; th = ch[mm, 1]
            out[f'L>={Lmin}'] = dict(n=int(mm.sum()), frac_within7p5=round(float(w[np.abs(((np.degrees(th) + 22.5) % 45) - 22.5) < 7.5].sum() / w.sum()), 3),
                                    A8_re=round(float(((w * np.exp(8j * th)).sum() / w.sum()).real), 3))
    # raw edge direction shares (length weighted): x, y, diag+, diag-
    Lk = LS[gi['k']]; out['edge_len_frac[x,y,d+,d-]'] = [round(float(Lk[gi['k'] == q].sum() / Lk.sum()), 3) for q in range(4)]
    return out


def _sp(x, y):
    if len(x) < 8 or np.std(x) == 0 or np.std(y) == 0: return None
    return round(float(spearmanr(x, y)[0]), 3)


def _partial(rxy, rxz, ryz):
    if None in (rxy, rxz, ryz): return None
    den = np.sqrt(max((1 - rxz ** 2) * (1 - ryz ** 2), 1e-12)); return round(float((rxy - rxz * ryz) / den), 3)


AGE_BINS = [0, 25, 50, 100, 200, 1e9]


def full(S, cthr=CTHR):
    C = S['C'].astype(float); wet = S['wet']; h = S['h'].astype(float); N = wet.shape[0]
    age = S['age'].astype(float); eage = S['eage'].astype(float); Qm = S['Qmean'].astype(float); Qg = S['Qgross'].astype(float)
    cen = tuple(float(v) for v in S['cen']); act = act_mask(wet)
    out = quick(S, cthr)
    bs, gi = basic(C, wet, cthr)
    if gi is None: return out
    b16, _ = basic(C, wet, 16.0); out['vein_thr16'] = b16
    foods = [tuple(float(x) for x in v) for v in np.asarray(S.get('foods', [])).reshape(-1, 2)]; fr = float(S.get('food_r', 4.0))
    discs = [disc(N, fx, fy, fr) for fx, fy in foods]
    # ---- Strahler (root at reservoir 0 if it is in the graph) ----
    root = None
    if foods:
        fn = np.nonzero((discs[0] & wet).ravel())[0]; fn = fn[np.isin(fn, gi['nodes'])]
        if fn.size:
            cand = np.searchsorted(gi['nodes'], fn); big = int(np.argmax(gi['csize'])); cand = cand[gi['lab'][cand] == big]
            if cand.size: root = int(cand[np.argmax(gi['deg'][cand])])
    st = strahler(gi, C, root); st['rooted_at_food0'] = root is not None; out['strahler'] = st
    out['orient'] = chord_orient(gi, N)
    # ---- per vein-edge quantities ----
    k = gi['k']; ys = gi['ys']; xs = gi['xs']; c = gi['c']; lc = np.log(c)
    ea = eage[k, ys, xs]; qn = np.abs(Qm[k, ys, xs]); qg = Qg[k, ys, xs]
    dxa = np.array([d[0] for d in DIRS])[k]; dya = np.array([d[1] for d in DIRS])[k]
    jj, ii = np.mgrid[0:N, 0:N]
    msh = lambda v, sh: (v + N / 2 - sh) % N - N / 2 + sh        # wrap window shifted by sh (sh<0: more room behind)
    axes = {}
    if S.get('dirv') is not None and np.hypot(*S['dirv']) > 0.5: axes['disp'] = tuple(float(v) for v in S['dirv'])
    if foods:
        fx = mimg(foods[0][0] - S['c0'], N); fy = mimg(foods[0][1] - S['c0'], N); n_ = np.hypot(fx, fy)
        if n_ > 1: axes['food0'] = (fx / n_, fy / n_)
    okq = (qg > 0)
    r_age = _sp(ea, lc); r_net = _sp(np.log(qn[okq] + 1e-12), lc[okq]); r_gro = _sp(np.log(qg[okq] + 1e-12), lc[okq])
    r_age_net = _sp(ea[okq], np.log(qn[okq] + 1e-12)); r_age_gro = _sp(ea[okq], np.log(qg[okq] + 1e-12))
    fl = dict(spearman_logC_edgeage=r_age, spearman_logC_logQnet=r_net, spearman_logC_logQgross=r_gro, spearman_edgeage_logQnet=r_age_net, spearman_edgeage_logQgross=r_age_gro,
              partial_logC_age_given_Qnet=_partial(r_age, r_age_net, r_net), partial_logC_Qnet_given_age=_partial(r_net, r_age_net, r_age),
              partial_logC_age_given_Qgross=_partial(r_age, r_age_gro, r_gro),
              vein_gross_over_net=round(float(qg[okq].sum() / max(qn[okq].sum(), 1e-12)), 2))
    bins = []
    eall = eage[act]; call = C[act]
    for lo, hi in zip(AGE_BINS[:-1], AGE_BINS[1:]):
        m = (ea >= lo) & (ea < hi); ma = (eall >= lo) & (eall < hi)
        d = dict(age=f'{lo}-{hi if hi < 1e8 else "inf"}', n_vein=int(m.sum()), n_act=int(ma.sum()))
        if ma.sum() >= 3: d['C_med_act'] = round(float(np.median(call[ma])), 2); d['vein_frac'] = round(float((call[ma] > cthr).mean()), 3)
        if m.sum() >= 3:
            d.update(C_med=round(float(np.median(c[m])), 1), C_p90=round(float(np.percentile(c[m], 90)), 1), Qnet_med=round(float(np.median(qn[m])), 4), Qgross_med=round(float(np.median(qg[m])), 4),
                     gross_over_net=round(float(qg[m].sum() / max(qn[m].sum(), 1e-12)), 2))
        bins.append(d)
    fl['age_bins'] = bins; out['flux_age'] = fl
    # ---- position profiles and section convergence along each axis ----
    aa, ab, ak, ays, axs = edges_of(act, N)
    adx = np.array([d[0] for d in DIRS])[ak]; ady = np.array([d[1] for d in DIRS])[ak]
    aq = Qm[ak, ays, axs]; ac = C[ak, ays, axs]
    pos = {}
    for nm, (ux, uy) in axes.items():
        shx = -ux * N / 6; shy = -uy * N / 6
        mx = msh(xs - cen[0], shx) + 0.5 * dxa; my = msh(ys - cen[1], shy) + 0.5 * dya
        wx = msh(ii - cen[0], shx)[wet]; wy = msh(jj - cen[1], shy)[wet]; ax0 = msh(axs - cen[0], shx); ay0 = msh(ays - cen[1], shy)
        s = mx * ux + my * uy; sw = wx * ux + wy * uy; smin, smax = float(sw.min()), float(sw.max())
        u = (s - smin) / max(smax - smin, 1e-9)
        d = dict(axis=[round(ux, 3), round(uy, 3)], len=round(smax - smin + 1, 1), spearman_logC_pos=_sp(u, lc))
        bands = np.clip((u * 6).astype(int), 0, 5); prof = []
        for bnd in range(6):
            m = bands == bnd
            if m.sum() < 3: prof.append(dict(n=int(m.sum()))); continue
            prof.append(dict(n=int(m.sum()), C_med=round(float(np.median(c[m])), 1), C_p90=round(float(np.percentile(c[m], 90)), 1), C_max=round(float(c[m].max()), 1),
                             Qnet_med=round(float(np.median(qn[m])), 4), Qgross_med=round(float(np.median(qg[m])), 4), edgeage_med=round(float(np.median(ea[m])), 1)))
        d['bands_rear_to_front'] = prof
        thick = c > 100; d['n_thick_C>100'] = int(thick.sum()); d['thick_frac_rear_half'] = round(float((thick & (u < 0.5)).sum() / max(thick.sum(), 1)), 3)
        # sections: all active edges crossing the plane s = s_k ; flux counted positive toward +axis
        s1 = ax0 * ux + ay0 * uy; s2 = s1 + adx * ux + ady * uy; sec = []
        for f in (1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6):
            sk = smin + f * (smax - smin); cr = (np.minimum(s1, s2) < sk) & (np.maximum(s1, s2) >= sk)
            if cr.sum() < 2: sec.append(dict(f=round(f, 2), n=int(cr.sum()))); continue
            q = aq[cr] * np.sign(s2[cr] - s1[cr]); cc = ac[cr]; aqs = np.sort(np.abs(q))[::-1]; cs = np.cumsum(aqs)
            n80 = int(np.searchsorted(cs, 0.8 * cs[-1]) + 1) if cs[-1] > 0 else 0
            sec.append(dict(f=round(f, 2), n_act=int(cr.sum()), n_vein=int((cc > cthr).sum()), net_fwd=round(float(q.sum()), 4), abs_sum=round(float(cs[-1]), 4),
                            n80=n80, top1_share=round(float(aqs[0] / max(cs[-1], 1e-12)), 3), C_max=round(float(cc.max()), 1),
                            C_of_top_flux_edge=round(float(cc[np.argmax(np.abs(q))]), 1)))
        d['sections'] = sec; pos[nm] = d
    out['pos'] = pos
    # ---- reservoir / food statistics ----
    fres = []
    for fi, (fx, fy) in enumerate(foods):
        ra = np.hypot(mimg(axs - fx, N), mimg(ays - fy, N)); rb = np.hypot(mimg(axs + adx - fx, N), mimg(ays + ady - fy, N))
        rings = []
        for R in (fr + 0.5, 8, 12, 16, 24, 32, 40):
            cr = (np.minimum(ra, rb) < R) & (np.maximum(ra, rb) >= R)
            if cr.sum() < 1: rings.append(dict(R=R, n_act=0)); continue
            q = aq[cr] * np.sign(rb[cr] - ra[cr]); cc = ac[cr]; aqs = np.sort(np.abs(q))[::-1]; cs = np.cumsum(aqs)
            n80 = int(np.searchsorted(cs, 0.8 * cs[-1]) + 1) if cs[-1] > 0 else 0
            vv = cc > cthr
            gsum = float(Qg[ak, ays, axs][cr].sum())
            rings.append(dict(R=R, n_act=int(cr.sum()), n_vein=int(vv.sum()), net_out=round(float(q.sum()), 4), abs_sum=round(float(cs[-1]), 4), n80=n80,
                              top1_share=round(float(aqs[0] / max(cs[-1], 1e-12)), 3), C_max=round(float(cc.max()), 1),
                              C_med_vein=round(float(np.median(cc[vv])), 1) if vv.any() else None, C_sum=round(float(cc.sum()), 1), gross_sum=round(gsum, 4)))
        d = dict(food=fi, wet_cells=int((discs[fi] & wet).sum()), disc_cells=int(discs[fi].sum()), h_mean_on_food=round(float(h[discs[fi] & wet].mean()), 3) if (discs[fi] & wet).any() else None,
                 rings=rings, vol_frac_within_3r=round(float(h[disc(N, fx, fy, 3 * fr)].sum() / max(h.sum(), 1e-12)), 3))
        fres.append(d)
    if fres: out['food_stats'] = fres
    if len(foods) >= 2:
        for key in list(out.get('path', {})):
            i, j = [int(v) for v in key.split('-')]
            fp = food_path(C, S['G'], wet, discs[i], discs[j], S['r'], cthr, Qm, Qg)
            if fp.get('connected') and fp.get('n', 0) > 0:
                p = fp.pop('path'); yy, xx = np.divmod(np.array(p), N)
                dx = mimg(xx[1:] - xx[:-1], N); dy = mimg(yy[1:] - yy[:-1], N)
                chord = np.hypot(dx.sum(), dy.sum()); fp['tortuosity'] = round(float(np.hypot(dx, dy).sum() / max(chord, 1e-9)), 3)
            out['path'][key] = fp
    return out


def load_state(f):
    Z = np.load(f, allow_pickle=True); S = {k: Z[k] for k in Z.files}
    for k in ('t', 'food_r', 'r', 'c0'): S[k] = float(S[k])
    S['cen'] = tuple(float(v) for v in S['cen']); S['dirv'] = tuple(float(v) for v in S['dirv'])
    return S


if __name__ == '__main__':
    for rd in sys.argv[1:]:
        res = {}
        for f in sorted(glob.glob(os.path.join(rd, 'state_t*.npz'))):
            S = load_state(f); res[os.path.basename(f)[6:-4]] = full(S)
        json.dump(res, open(os.path.join(rd, 'graph.json'), 'w'), indent=1)
        print(rd, 'graph.json', list(res))
