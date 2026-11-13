#!/usr/bin/env python3
"""Independent metrics for E6 verification (reads edges_4.npz only; writes nothing but stdout/json in verify/)."""
import numpy as np, json, sys, os
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from PIL import Image, ImageDraw
import networkx as nx

S = 4
def holes_for(z, q, amin_cells=9.0):
    C = z['C'].astype(float); wet = z['wet']; N = wet.shape[0]
    cref = np.percentile(C, 99.9)
    sel = np.nonzero(C >= q * cref)[0]
    # 2-core of largest component (drop dead-end twigs) so only cycle-forming edges are drawn
    G = nx.Graph()
    a = [(int(round(z['ex1'][e])), int(round(z['ey1'][e]))) for e in sel]; b = [(int(round(z['ex2'][e])), int(round(z['ey2'][e]))) for e in sel]
    G.add_edges_from(zip(a, b))
    if G.number_of_edges() == 0: return dict(q=q, n_edges=0)
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    lf = len(comps[0]) / G.number_of_nodes()
    Gc = nx.k_core(G.subgraph(comps[0]).copy(), 2)
    cyc = Gc.number_of_edges() - Gc.number_of_nodes() + nx.number_connected_components(Gc) if Gc.number_of_nodes() else 0
    im = Image.new('L', (N * S, N * S), 0); dr = ImageDraw.Draw(im)
    for (u, v) in Gc.edges():
        dr.line([((u[0] + .5) * S, (u[1] + .5) * S), ((v[0] + .5) * S, (v[1] + .5) * S)], fill=255, width=1)
    m = np.asarray(im) > 0
    hol = ndi.binary_fill_holes(m) & ~m
    lab, n = ndi.label(hol)
    areas = np.bincount(lab.ravel())[1:] / (S * S) if n else np.array([])
    big = np.nonzero(areas >= amin_cells)[0]
    src = z['src']; cents = ndi.center_of_mass(hol, lab, big + 1) if len(big) else []
    d = np.array([np.hypot(c[1] / S - src[0], c[0] / S - src[1]) for c in cents]) if len(big) else np.array([])
    out = dict(q=q, n_edges=int(len(sel)), frac_edges=round(len(sel) / len(C), 4), largest_comp_frac=round(lf, 3), cyclomatic_2core=int(cyc),
               holes_ge9=int(len(big)), holes_ge25=int((areas >= 25).sum()), holes_ge100=int((areas >= 100).sum()))
    if len(big) >= 4:
        med = np.median(d); A = areas[big]
        out['hole_area_med_rear_half'] = round(float(np.median(A[d <= med])), 1); out['hole_area_med_front_half'] = round(float(np.median(A[d > med])), 1)
    return out

def taper(z, q=0.01):
    C = z['C'].astype(float); cref = np.percentile(C, 99.9); src = z['src']
    mx = 0.5 * (z['ex1'] + z['ex2']); my = 0.5 * (z['ey1'] + z['ey2']); d = np.hypot(mx - src[0], my - src[1])
    ve = C >= q * cref; w = C[ve] ** 0.25; dd = d[ve]
    rho = spearmanr(w, dd).correlation
    t = np.quantile(dd, [1 / 3, 2 / 3])
    med = [float(np.median(w[dd <= t[0]])), float(np.median(w[(dd > t[0]) & (dd <= t[1])])), float(np.median(w[dd > t[1]]))]
    p90 = [float(np.percentile(w[dd <= t[0]], 90)), float(np.percentile(w[(dd > t[0]) & (dd <= t[1])], 90)), float(np.percentile(w[dd > t[1]], 90))]
    return dict(q=q, spearman_width_vs_dist=round(float(rho), 3), medw_rear_mid_front=[round(x, 2) for x in med], p90w_rear_mid_front=[round(x, 2) for x in p90],
                Cmax=round(float(C.max()), 1), C_p999=round(float(cref), 1), C_p50=float(np.median(C)))

def lattice_align(z, q=0.03):
    """strong-edge geometry: share of strong-edge length in straight runs >= 6 edges; structure-tensor orientation concentration on lattice directions."""
    C = z['C'].astype(float); wet = z['wet']; N = wet.shape[0]; cref = np.percentile(C, 99.9); sel = np.nonzero(C >= q * cref)[0]
    dx = np.round(z['ex2'] - z['ex1']).astype(int); dy = np.round(z['ey2'] - z['ey1']).astype(int)
    key = {}
    for e in sel: key[(int(round(z['ex1'][e])), int(round(z['ey1'][e])), dx[e], dy[e])] = e
    runlen = {}
    for (x, y, a, b) in key:                       # start of a run = no predecessor in same direction
        if (x - a, y - b, a, b) in key: continue
        n = 0; xx, yy = x, y
        while (xx, yy, a, b) in key: n += 1; xx += a; yy += b
        runlen[(x, y, a, b)] = (n, np.hypot(a, b))
    L = np.array([n * l for n, l in runlen.values()]); n_ = np.array([n for n, l in runlen.values()])
    tot = L.sum()
    im = Image.new('L', (N * S, N * S), 0); dr = ImageDraw.Draw(im)
    for e in sel: dr.line([((z['ex1'][e] + .5) * S, (z['ey1'][e] + .5) * S), ((z['ex2'][e] + .5) * S, (z['ey2'][e] + .5) * S)], fill=255, width=2)
    f = ndi.gaussian_filter((np.asarray(im) > 0).astype(float), 1.5 * S)      # smooth over 1.5 cells, then tensor over 3 cells
    gy, gx = np.gradient(f); sg = 3.0 * S
    Jxx = ndi.gaussian_filter(gx * gx, sg); Jyy = ndi.gaussian_filter(gy * gy, sg); Jxy = ndi.gaussian_filter(gx * gy, sg)
    ang = 0.5 * np.degrees(np.arctan2(2 * Jxy, Jxx - Jyy)) + 90.0            # line direction
    coh = np.hypot(Jxx - Jyy, 2 * Jxy) / (Jxx + Jyy + 1e-12)
    m = (np.asarray(im) > 0) & (coh > 0.5)
    dev = np.abs(((ang[m] + 22.5) % 45.0) - 22.5)                              # deviation from nearest lattice direction (0..22.5)
    axis_share = float(sum(n * l for (k, (n, l)) in runlen.items() if k[2] == 0 or k[3] == 0) / tot)
    return dict(q=q, strong_len=round(float(tot), 1), len_share_in_runs_ge6=round(float(L[n_ >= 6].sum() / tot), 3), len_share_in_runs_ge10=round(float(L[n_ >= 10].sum() / tot), 3),
                max_run_edges=int(n_.max()), axis_len_share=round(axis_share, 3),
                orient_within7p5deg_of_lattice=round(float((dev < 7.5).mean()), 3), uniform_expect=0.333, n_px=int(m.sum()))

if __name__ == '__main__':
    res = {}
    for tag, path in [a.split('=') for a in sys.argv[1:]]:
        z = np.load(os.path.join(path, 'edges_4.npz'))
        r = dict(holes=[holes_for(z, q) for q in (0.001, 0.01, 0.03, 0.1)], taper=taper(z), lattice=lattice_align(z))
        res[tag] = r
        print('==', tag)
        for h in r['holes']: print('  holes', h)
        print('  taper', r['taper']); print('  lattice', r['lattice'])
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'indep_metrics.json'), 'w'), indent=1)
