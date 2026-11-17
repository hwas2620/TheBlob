#!/usr/bin/env python3
"""independent native edge-graph metrics from saved arrays (written from scratch for the N1 verification).
usage: vgraph_indep.py RUN_DIR [RUN_DIR ...]"""
import numpy as np, sys, os, json
from scipy.stats import spearmanr

DXY = [(1, 0), (0, 1), (1, 1), (1, -1)]; LEN = [1.0, 1.0, 2 ** 0.5, 2 ** 0.5]


class UF:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        r = x
        while self.p[r] != r: r = self.p[r]
        while self.p[x] != r: self.p[x], x = r, self.p[x]
        return r
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra] = rb; return True
        return False


def edges(C, thr):
    N = C.shape[1]; out = []
    for k, (dx, dy) in enumerate(DXY):
        ys, xs = np.nonzero(C[k] > thr)
        for y, x in zip(ys, xs): out.append((y * N + x, (y + dy) * N + (x + dx), float(C[k, y, x]), k))
    return out


def metrics(C, wet, h, slime, thr=4.0, seglen=10):
    N = C.shape[1]; E = edges(C, thr); m = dict(thr=thr, n_edges=len(E))
    if len(E) < 10: return m
    ids = sorted(set([e[0] for e in E] + [e[1] for e in E])); loc = {v: i for i, v in enumerate(ids)}; V = len(ids)
    uf = UF(V); deg = np.zeros(V, int); adj = [[] for _ in range(V)]
    for ei, (a, b, c, k) in enumerate(E):
        ia, ib = loc[a], loc[b]; uf.union(ia, ib); deg[ia] += 1; deg[ib] += 1; adj[ia].append((ib, ei)); adj[ib].append((ia, ei))
    root = np.array([uf.find(loc[e[0]]) for e in E]); u, cnt = np.unique(root, return_counts=True); ncomp = len(u)
    m.update(n_nodes=V, comps=ncomp, largest_frac=round(cnt.max() / len(E), 3), comps_ge10=int((cnt >= 10).sum()), cycles=len(E) - V + ncomp,
             endpoints=int((deg == 1).sum()), junctions=int((deg >= 3).sum()))
    # second largest component, and length-weighted largest fraction
    L = np.array([LEN[e[3]] for e in E]); lw = np.array([L[root == r].sum() for r in u]); m['largest_frac_len'] = round(float(lw.max() / L.sum()), 3)
    srt = np.sort(cnt)[::-1]; m['top3_frac'] = [round(float(x / len(E)), 3) for x in srt[:3]]
    # position (front direction): +x (food gradient) and the axis dry-trail centroid -> wet centroid
    ex = np.array([(e[0] % N) + 0.5 * DXY[e[3]][0] for e in E]); ey = np.array([(e[0] // N) + 0.5 * DXY[e[3]][1] for e in E]); lc = np.log(np.array([e[2] for e in E]))
    m['spearman_x'] = round(float(spearmanr(ex, lc)[0]), 3)
    yy, xx = np.mgrid[0:N, 0:N]
    if slime.sum() > 0:
        tr = slime > 0.5; ax = np.array([xx[wet].mean() - xx[tr].mean(), yy[wet].mean() - yy[tr].mean()]); ax /= max(np.hypot(*ax), 1e-9)
        m['axis_deg'] = round(float(np.degrees(np.arctan2(ax[1], ax[0]))), 1); m['spearman_axis'] = round(float(spearmanr(ex * ax[0] + ey * ax[1], lc)[0]), 3)
    # thick edges and where they are (x-quantile bands rear -> front over the vein edges)
    q = np.clip(((ex - ex.min()) / max(ex.max() - ex.min(), 1e-9) * 5).astype(int), 0, 4); cv = np.exp(lc)
    m['band_medC_rear_to_front'] = [round(float(np.median(cv[q == b])), 1) if (q == b).sum() >= 3 else None for b in range(5)]
    m['band_p90C_rear_to_front'] = [round(float(np.percentile(cv[q == b], 90)), 1) if (q == b).sum() >= 3 else None for b in range(5)]
    m['n_C>100'] = int((cv > 100).sum()); m['Cmax'] = round(float(cv.max()), 1)
    m['orient_len_frac_E_N_NE_SE'] = [round(float(L[[e[3] == k for e in E]].sum() / L.sum()), 3) for k in range(4)]
    # chords: walk maximal degree-2 chains, cut into pieces of `seglen` edges
    used = np.zeros(len(E), bool); px = np.array([v % N for v in ids]); py = np.array([v // N for v in ids]); ch = []
    def walk(v, w, e0):
        path = [v, w]; used[e0] = True; prev = e0; cur = w
        while deg[cur] == 2:
            nxt = [(n_, e_) for (n_, e_) in adj[cur] if e_ != prev]
            if not nxt or used[nxt[0][1]]: break
            used[nxt[0][1]] = True; prev = nxt[0][1]; cur = nxt[0][0]; path.append(cur)
        return path
    paths = []
    for v in np.nonzero(deg != 2)[0]:
        for (w, e0) in adj[v]:
            if not used[e0]: paths.append(walk(v, w, e0))
    for ei in range(len(E)):                      # pure cycles of degree-2 nodes
        if not used[ei]: paths.append(walk(loc[E[ei][0]], loc[E[ei][1]], ei))
    for p in paths:
        for s in range(0, len(p) - 1, seglen):
            seg = p[s:s + seglen + 1]
            if len(seg) - 1 >= max(5, seglen // 2): ch.append((px[seg[-1]] - px[seg[0]], py[seg[-1]] - py[seg[0]]))
    if len(ch) >= 5:
        ch = np.array(ch, float); ln = np.hypot(ch[:, 0], ch[:, 1]); a = np.degrees(np.arctan2(ch[:, 1], ch[:, 0])) % 45.0; dev = np.minimum(a, 45 - a)
        m['chords'] = len(ch); m['chord_lattice_frac'] = round(float(ln[dev < 7.5].sum() / ln.sum()), 3)
        a180 = np.degrees(np.arctan2(ch[:, 1], ch[:, 0])) % 180.0
        m['chord_len_frac_within7p5_of_0_45_90_135'] = [round(float(ln[np.minimum(np.abs(a180 - c), 180 - np.abs(a180 - c)) < 7.5].sum() / ln.sum()), 3) for c in (0, 45, 90, 135)]
    # Strahler on a BFS-free definition: maximum-C spanning forest, root = max-C node of each of the 3 largest comps (iterative post-order)
    order = np.argsort([-e[2] for e in E]); uf2 = UF(V); tadj = [[] for _ in range(V)]
    for ei in order:
        ia, ib = loc[E[ei][0]], loc[E[ei][1]]
        if uf2.union(ia, ib): tadj[ia].append(ib); tadj[ib].append(ia)
    best = 0
    for r in u[np.argsort(-cnt)[:3]]:
        es = [ei for ei in range(len(E)) if root[ei] == r]; top = max(es, key=lambda i: E[i][2]); rt = loc[E[top][0]]
        so = {}; st = [(rt, -1, False)]
        while st:
            x, par, done = st.pop()
            if not done:
                st.append((x, par, True)); st += [(y, x, False) for y in tadj[x] if y != par]
            else:
                c = [so[y] for y in tadj[x] if y != par]
                so[x] = 1 if not c else (max(c) + 1 if c.count(max(c)) >= 2 else max(c))
        best = max(best, so[rt])
    m['strahler'] = int(best)
    return m


def vein_cells(C, thr):
    N = C.shape[1]; v = np.zeros((N, N), bool)
    for k, (dx, dy) in enumerate(DXY):
        ys, xs = np.nonzero(C[k] > thr); v[ys, xs] = True; v[ys + dy, xs + dx] = True
    return v


def front_flatness(wet):
    """fraction of the rows spanned by the wet set whose right-most wet cell lies within 1 cell of the modal front column (straight vertical front)."""
    rows = np.nonzero(wet.any(1))[0]; xr = np.array([np.nonzero(wet[r])[0].max() for r in rows]); mode = np.bincount(xr).argmax()
    return round(float((np.abs(xr - mode) <= 1).mean()), 3), int(len(rows))


if __name__ == '__main__':
    for rd in sys.argv[1:]:
        C = np.load(os.path.join(rd, 'C_edges.npy')).astype(float); wet = np.load(os.path.join(rd, 'wet.npy')); h = np.load(os.path.join(rd, 'h.npy')); sl = np.load(os.path.join(rd, 'slime.npy'))
        out = {f'thr{int(t)}': metrics(C, wet, h, sl, t) for t in (4.0, 10.0, 30.0, 100.0)}
        out['chord_seg6'] = metrics(C, wet, h, sl, 4.0, 6).get('chord_lattice_frac'); out['chord_seg16'] = metrics(C, wet, h, sl, 4.0, 16).get('chord_lattice_frac')
        out['front_flat_frac_rows'] = front_flatness(wet); out['wet'] = int(wet.sum()); out['h_min_wet'] = float(h[wet].min()); out['vol'] = float(h.sum())
        json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vg_' + os.path.basename(rd.rstrip('/')) + '.json'), 'w'), indent=1)
        a = out['thr4']
        print(os.path.basename(rd.rstrip('/')), '| E', a['n_edges'], 'comps', a['comps'], 'largest', a['largest_frac'], 'cyc', a['cycles'], 'end', a['endpoints'], 'junc', a['junctions'],
              'spX', a['spearman_x'], 'spAx', a.get('spearman_axis'), 'chord', a.get('chord_lattice_frac'), 'strahler', a.get('strahler'), 'C>100', a['n_C>100'],
              '| largest@10/30/100', out['thr10'].get('largest_frac'), out['thr30'].get('largest_frac'), out['thr100'].get('largest_frac'),
              '| spX@10/30', out['thr10'].get('spearman_x'), out['thr30'].get('spearman_x'), '| frontflat', out['front_flat_frac_rows'], '| medC bands', a['band_medC_rear_to_front'])
