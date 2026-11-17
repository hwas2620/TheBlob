#!/usr/bin/env python3
# independent metrics from native arrays (h, Cn=max adjacent edge C, twet, age). No tube render.
import sys, os, json, numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from skimage.measure import euler_number, label
HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.dirname(HERE)
S8 = np.ones((3, 3))
out_all = {}
for r in sys.argv[1:]:
    d = r if os.path.isabs(r) else os.path.join(EXP, 'runs', r); nm = os.path.basename(d)
    h = np.load(os.path.join(d, 'body_native.npy')).astype(float); C = np.load(os.path.join(d, 'vein_native.npy')).astype(float)
    tw = np.load(os.path.join(d, 'twet.npy')).astype(float); age = np.load(os.path.join(d, 'age.npy')).astype(float)
    M = json.load(open(os.path.join(d, 'metrics.json'))); P = json.load(open(os.path.join(d, 'params.json')))
    N = h.shape[0]; Y, X = np.mgrid[0:N, 0:N].astype(float); wet = age >= 0
    o = dict(run=nm, seed=P['seed'], grad=P['food_grad'], t_end=M['t_end'])
    # ---- mass ----
    V0 = M['V0']; V = h.sum()
    o['V0'] = V0; o['V_end'] = round(float(V), 4); o['mass_rel_err_final_f32'] = float((V - V0) / V0)
    o['h_neg_cells'] = int((h < 0).sum()); o['h_on_dry'] = float(np.abs(h[~wet]).sum()); o['logged_mass_err_max'] = M['mass_err_max']
    o['n_log'] = len(M['log'])
    # ---- body / trail ----
    lab, nl = ndi.label(wet, structure=S8); sz = np.bincount(lab.ravel())[1:]; big = lab == (np.argmax(sz) + 1)
    ever = tw >= 0
    o['wet_cells'] = int(wet.sum()); o['ever_wet_cells'] = int(ever.sum()); o['trail_dry_cells'] = int((ever & ~wet).sum())
    o['wet_frac_of_coloured_region'] = round(float(wet.sum() / ever.sum()), 3)
    o['components'] = int(nl); o['vol_frac_largest'] = round(float(h[big].sum() / V), 3)
    o['sheet_cells_h>0.5'] = int((wet & (h > 0.5)).sum()); o['thin_cells_h<0.3'] = int((wet & (h < 0.3)).sum())
    # second largest component volume
    vols = ndi.sum(h, lab, index=np.arange(1, nl + 1)); vs = np.sort(vols)[::-1]
    o['vol_frac_top3_components'] = [round(float(x / V), 3) for x in vs[:3]]
    # ---- front segmentation: cells wetted in last 30 time units ----
    t = M['t_end']; recent = wet & (tw > t - 30)
    fl, fn = ndi.label(ndi.binary_dilation(recent, iterations=2), structure=S8)
    fs = np.sort(ndi.sum(recent, fl, index=np.arange(1, fn + 1)))[::-1] if fn else np.array([])
    o['recent_cells_30t'] = int(recent.sum()); o['front_patch_sizes'] = [int(x) for x in fs[:6]]
    o['front_patches_ge10pct'] = int((fs >= 0.1 * recent.sum()).sum()) if fn else 0
    cx, cy = (h * X).sum() / V, (h * Y).sum() / V; c0 = N / 2 - 0.5
    o['centroid_disp'] = round(float(np.hypot(cx - c0, cy - c0)), 2)
    if recent.sum() > 5:
        # directions of recent growth seen from the START point (not the current centroid)
        ang = np.arctan2(Y[recent] - c0, X[recent] - c0)
        Rv = np.hypot(np.cos(ang).mean(), np.sin(ang).mean()); o['recent_dir_resultant_from_start'] = round(float(Rv), 3)
        hist = np.histogram(ang, bins=12, range=(-np.pi, np.pi))[0]; o['recent_dir_hist_30deg'] = [int(x) for x in hist]
        srt = np.sort(hist)[::-1]; o['recent_frac_in_best_120deg'] = round(float(max(sum(np.roll(hist, -i)[:4]) for i in range(12)) / hist.sum()), 3)
    # ---- travel direction & rear->front profile over ALL wet cells ----
    tr = M['traj']; i0 = int(len(tr) * 0.6); ddx = tr[-1][1] - tr[i0][1]; ddy = tr[-1][2] - tr[i0][2]
    if np.hypot(ddx, ddy) < 1: ddx, ddy = cx - c0, cy - c0
    nrm = np.hypot(ddx, ddy); ux, uy = ddx / nrm, ddy / nrm; o['dir'] = [round(ux, 2), round(uy, 2)]
    s = X * ux + Y * uy; w = -X * uy + Y * ux
    smax = s[big].max(); back = smax - s            # distance behind the leading edge
    prof = []
    for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 20), (20, 30), (30, 40), (40, 60), (60, 200)):
        mb = big & (back >= lo) & (back < hi); cv = C[mb]
        if mb.sum() == 0: continue
        prof.append(dict(back=f'{lo}-{hi}', cells=int(mb.sum()), h_mean=round(float(h[mb].mean()), 3), age_med=round(float(np.median(age[mb])), 1),
                         C_p50=round(float(np.percentile(cv, 50)), 1), C_p90=round(float(np.percentile(cv, 90)), 1), C_max=round(float(cv.max()), 1),
                         r_max_rel=round(float(cv.max() ** 0.25), 2), n_C_gt100=int((cv > 100).sum()), width_ext=round(float(np.ptp(w[mb]) + 1), 1)))
    o['profile_front_to_rear'] = prof
    # radius (C^1/4) of strongest vein: zone 5-20 behind front vs >30 behind
    zf = big & (back >= 5) & (back < 20); zr = big & (back >= 30)
    if zf.any() and zr.any():
        o['Cmax_near_front_5_20'] = round(float(C[zf].max()), 1); o['Cmax_rear_gt30'] = round(float(C[zr].max()), 1)
        o['radius_ratio_rear_over_front_(C^0.25)'] = round(float((C[zr].max() / C[zf].max()) ** 0.25), 2)
        o['Cp90_ratio_rear_over_front'] = round(float(np.percentile(C[zr], 90) / np.percentile(C[zf], 90)), 3)
    # ---- native vein topology at absolute thresholds (no render) ----
    topo = {}
    for thr in (4, 10, 30, 100):
        vm = wet & (C > thr)
        if vm.sum() < 10: topo[thr] = dict(cells=int(vm.sum())); continue
        vl, vn = ndi.label(vm, structure=S8); vsz = np.bincount(vl.ravel())[1:]
        sk = skeletonize(vm); nbn = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - sk
        junc = sk & (nbn >= 3); jl, nj = ndi.label(ndi.binary_dilation(junc), structure=S8)
        sl, sn = ndi.label(sk, structure=S8)
        topo[thr] = dict(cells=int(vm.sum()), frac_of_wet=round(float(vm.sum() / wet.sum()), 3), comps=int(vn), largest_frac=round(float(vsz.max() / vm.sum()), 3),
                         skel_len=int(sk.sum()), branch_pts=int(nj), endpoints=int((sk & (nbn == 1)).sum()), loops=int(sn - euler_number(sk, connectivity=2)))
    o['native_topology_by_C_threshold'] = topo
    # ---- lattice alignment of veins at ~8-cell scale: structure tensor of vein mask (C>10) ----
    vm = (wet & (C > 10)).astype(float)
    g = ndi.gaussian_filter(vm, 1.0); gy, gx = np.gradient(g)
    Jxx = ndi.gaussian_filter(gx * gx, 4.0); Jyy = ndi.gaussian_filter(gy * gy, 4.0); Jxy = ndi.gaussian_filter(gx * gy, 4.0)
    th = (0.5 * np.arctan2(2 * Jxy, Jxx - Jyy) + np.pi / 2) % np.pi           # line orientation (perpendicular to gradient)
    coh = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / (Jxx + Jyy + 1e-12)
    m = (vm > 0) & (coh > 0.3)
    if m.sum() > 20:
        deg = np.degrees(th[m]); dev = np.abs(((deg + 22.5) % 45) - 22.5)       # deviation from nearest lattice direction, 0..22.5
        o['orient_n'] = int(m.sum()); o['orient_frac_within_7.5deg_of_lattice_dir'] = round(float((dev < 7.5).mean()), 3)   # isotropic expectation 0.333
        o['orient_hist_15deg_bins_0..180'] = [int(x) for x in np.histogram(deg, bins=12, range=(0, 180))[0]]
        o['orient_mean_dev_deg'] = round(float(dev.mean()), 2)                  # isotropic expectation 11.25
    out_all[nm] = o
    print(json.dumps(o, ensure_ascii=False))
json.dump(out_all, open(os.path.join(HERE, 'indep_' + '_'.join(os.path.basename(a) for a in sys.argv[1:])[:80] + '.json'), 'w'), indent=1)
