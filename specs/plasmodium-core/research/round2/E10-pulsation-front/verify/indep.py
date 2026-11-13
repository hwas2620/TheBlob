#!/usr/bin/env python3
"""Independent re-measurement for E10 (reviewer). usage: python3 indep.py RUN_DIR [RUN_DIR ...]"""
import numpy as np, json, sys, os
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
LS = [1, 1, 2 ** .5, 2 ** .5]

def analyse(rd, cthr=4.0):
    C = np.load(os.path.join(rd, 'C_edges.npy')).astype(float)
    h = np.load(os.path.join(rd, 'body_native.npy')).astype(float)
    age = np.load(os.path.join(rd, 'age.npy')).astype(float)
    met = json.load(open(os.path.join(rd, 'metrics.json')))
    N = h.shape[0]; wet = age >= 0
    jj, ii = np.mgrid[0:N, 0:N]
    out = dict(run=os.path.basename(rd.rstrip('/')), wet=int(wet.sum()), disp=met.get('disp'), t_end=met.get('t_end'))
    # volume budget
    V = h.sum(); sheet = wet & (h > 0.5)
    out['vol_frac_sheet(h>0.5)'] = round(float(h[sheet].sum() / V), 3); out['area_frac_sheet'] = round(float(sheet.sum() / wet.sum()), 3)
    # vein graph
    ea = []; eb = []; ec = []; ek = []
    for k, d in enumerate(DIRS):
        ys, xs = np.nonzero(C[k] > cthr)
        ea.append(ys * N + xs); eb.append((ys + d[1]) * N + (xs + d[0])); ec.append(C[k][ys, xs]); ek.append(np.full(ys.size, k))
    ea = np.concatenate(ea); eb = np.concatenate(eb); ec = np.concatenate(ec); ek = np.concatenate(ek)
    E = ea.size
    nodes, inv = np.unique(np.concatenate([ea, eb]), return_inverse=True); V_ = nodes.size
    a = inv[:E]; b = inv[E:]
    g = coo_matrix((np.ones(E), (a, b)), shape=(V_, V_))
    nc, lab = connected_components(g, directed=False)
    deg = np.bincount(np.concatenate([a, b]), minlength=V_)
    elab = lab[a]; csize = np.bincount(elab, minlength=nc)
    out['vein_edges'] = int(E); out['vein_nodes'] = int(V_); out['vein_components'] = int(nc)
    out['vein_largest_frac_edges'] = round(float(csize.max() / E), 3)
    out['vein_comp_ge10_edges'] = int((csize >= 10).sum())
    out['cycles(E-V+comp)'] = int(E - V_ + nc)
    out['deg1_endpoints'] = int((deg == 1).sum()); out['deg>=3_junction_nodes'] = int((deg >= 3).sum())
    # lattice orientation (length weighted)
    Lk = np.array(LS)[ek]
    fr = [float(Lk[ek == k].sum() / Lk.sum()) for k in range(4)]
    out['orient_len_frac[x,y,diag+,diag-]'] = [round(v, 3) for v in fr]
    # which components touch the sheet
    ny, nx = np.divmod(nodes, N)
    touch_sheet = ndi.binary_dilation(sheet, iterations=1)[ny, nx]
    comp_touch = np.zeros(nc, bool); np.logical_or.at(comp_touch, lab, touch_sheet)
    out['frac_vein_edges_in_comps_touching_sheet'] = round(float(csize[comp_touch].sum() / E), 3)
    # top 5% C edges: connected to the sheet through vein graph?
    top = ec >= np.percentile(ec, 95)
    out['top5pct_C_thr'] = round(float(np.percentile(ec, 95)), 1)
    out['top5pct_edges_in_comp_touching_sheet'] = round(float(comp_touch[elab[top]].mean()), 3)
    out['top5pct_edges_in_largest_comp'] = round(float((elab[top] == np.argmax(csize)).mean()), 3)
    # travel direction
    dr = met.get('dir')
    if dr is None:
        tr = met['traj']; dx = tr[-1][1] - tr[0][1]; dy = tr[-1][2] - tr[0][2]; n_ = max(np.hypot(dx, dy), 1e-9); dr = [dx / n_, dy / n_]
    ya, xa = np.divmod(ea, N)
    s = (xa + 0.5 * np.array([d[0] for d in DIRS])[ek]) * dr[0] + (ya + 0.5 * np.array([d[1] for d in DIRS])[ek]) * dr[1]
    sw = (ii * dr[0] + jj * dr[1])[wet]; smin, smax = sw.min(), sw.max()
    u = (s - smin) / (smax - smin)                      # 0 = rear, 1 = front
    rho, pv = spearmanr(u, np.log(ec)); out['spearman_logC_vs_position(rear0->front1)'] = round(float(rho), 3)
    agee = np.maximum(age[ya, xa], 0); rho2, _ = spearmanr(agee, np.log(ec)); out['spearman_logC_vs_age'] = round(float(rho2), 3)
    bands = np.clip((u * 6).astype(int), 0, 5)
    prof = []
    for bnd in range(6):
        m = bands == bnd
        if m.sum() < 3: prof.append(dict(n=int(m.sum()))); continue
        prof.append(dict(n=int(m.sum()), C_med=round(float(np.median(ec[m])), 1), C_p90=round(float(np.percentile(ec[m], 90)), 1), C_max=round(float(ec[m].max()), 1), C_sum=round(float(ec[m].sum()), 0)))
    out['bands_rear_to_front'] = prof
    # share of all vein edges that are "thick" (C>100) per half
    thick = ec > 100
    out['n_thick(C>100)'] = int(thick.sum()); out['thick_frac_rear_half'] = round(float((thick & (u < 0.5)).sum() / max(thick.sum(), 1)), 3)
    out['vein_edges_frac_rear_half'] = round(float((u < 0.5).mean()), 3)
    # flux gross/net if available
    try:
        gn = np.load(os.path.join(rd, 'Qnet.npy')).astype(float); gg = np.load(os.path.join(rd, 'Qgross.npy')).astype(float)
        qn = np.concatenate([gn[k][C[k] > cthr] for k in range(4)]); qg = np.concatenate([gg[k][C[k] > cthr] for k in range(4)])
        ok = qg > 0
        out['vein_gross/net'] = round(float(qg[ok].sum() / max(qn[ok].sum(), 1e-12)), 2)
        rr = []
        for bnd in range(6):
            m = (bands == bnd) & ok
            rr.append(None if m.sum() < 3 else [round(float(np.median(qg[m])), 3), round(float(np.median(qn[m])), 3)])
        out['bands_median_[gross,net]'] = rr
    except Exception as ex: out['flux_err'] = str(ex)
    # pulsation amplitude
    try:
        ha = np.load(os.path.join(rd, 'hamp.npy')).astype(float); hm = np.load(os.path.join(rd, 'hmean.npy')).astype(float)
        m = hm > 0.5
        out['hamp_sheet_mean'] = round(float(ha[m].mean()), 4); out['hamp_sheet_rel'] = round(float((ha[m] / hm[m]).mean()), 4)
    except Exception as ex: pass
    # mass
    try:
        sr = np.load(os.path.join(rd, 'series.npz')); vol = sr['vol'].astype(float); out['vol_rel_range(float32 series)'] = float((vol.max() - vol.min()) / vol[0])
        new = sr['new'].astype(float); out['area_end/area_max'] = round(float(sr['area'][-1] / sr['area'].max()), 3)
    except Exception as ex: pass
    # front shape: angular span of recently wetted cells seen from the h-centroid; octagon facet test on the wet outline
    tw = np.load(os.path.join(rd, 'twet.npy')).astype(float)
    cx = (h * ii).sum() / V; cy = (h * jj).sum() / V
    young = wet & (age < 10) & (age >= 0)
    ang = np.arctan2(jj - cy, ii - cx)
    hist = np.histogram(ang[young], bins=36, range=(-np.pi, np.pi))[0]
    out['young_cells'] = int(young.sum()); out['young_sector_frac(10deg bins >=3 cells)'] = round(float((hist >= 3).mean()), 3)
    # boundary normal orientation histogram of the outer wet+slime footprint front (young boundary cells): axis/diagonal facet excess
    bnd = young & ~ndi.binary_erosion(wet | (tw >= 0), structure=np.ones((3, 3)))
    gx = ndi.sobel(ndi.gaussian_filter((wet | (tw >= 0)).astype(float), 2.0), axis=1); gy = ndi.sobel(ndi.gaussian_filter((wet | (tw >= 0)).astype(float), 2.0), axis=0)
    th = np.degrees(np.arctan2(-gy[bnd], -gx[bnd])) % 45.0
    th = np.minimum(th, 45 - th)       # 0 = normal exactly on an axis or diagonal, 22.5 = in between
    out['front_boundary_cells'] = int(bnd.sum())
    out['front_normal_frac_within_7.5deg_of_lattice_dir(iso=0.333)'] = round(float((th < 7.5).mean()), 3) if bnd.sum() else None
    return out

if __name__ == '__main__':
    for rd in sys.argv[1:]:
        print(json.dumps(analyse(rd), ensure_ascii=False))
