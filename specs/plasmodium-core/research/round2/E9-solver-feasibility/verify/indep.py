#!/usr/bin/env python3
# independent metrics from vein_native.npy (node max-C) : ring crossings, hierarchy, lattice-angle bias, cap saturation
import numpy as np, json, sys, os
from scipy import ndimage as ndi
def ana(d, thr=10.0):
    v = np.load(os.path.join(d, 'vein_native.npy')).astype(float); b = np.load(os.path.join(d, 'body_native.npy')) > 0
    m = json.load(open(os.path.join(d, 'metrics.json'))); P = json.load(open(os.path.join(d, 'params.json')))
    N = v.shape[0]; c = N // 2; R = m.get('R_final', P['R_frac'] * N)
    jj, ii = np.mgrid[0:N, 0:N]; dist = np.hypot(ii - c, jj - c); ang = np.degrees(np.arctan2(jj - c, ii - c))
    out = dict(run=os.path.basename(d), N=N, R=R, Cmax=float(v.max()), rings={}, angles=[])
    for f in (0.15, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95):
        ann = (np.abs(dist - f * R) < 1.0) & (v > thr)
        lab, n = ndi.label(ann, structure=np.ones((3, 3)))
        if n == 0: out['rings'][f] = (0, 0, 0); continue
        mx = ndi.maximum(v, lab, range(1, n + 1))
        out['rings'][f] = (int(n), round(float(np.median(mx)), 1), round(float(np.max(mx)), 1))
        if f in (0.4, 0.55, 0.7):
            for k in range(1, n + 1):
                sel = lab == k; w = v[sel]
                a = np.degrees(np.arctan2((w * (jj[sel] - c)).sum(), (w * (ii[sel] - c)).sum()))
                out['angles'].append((f, float(a), float(mx[k - 1])))
    vv = v[b & (v > 1.0)]
    out['vein_nodes'] = int(vv.size); out['C_pct_50_90_99_max'] = [round(float(x), 1) for x in np.percentile(vv, [50, 90, 99, 100])]
    cap = P.get('Ccap', 0)
    if cap > 0:
        at = b & (v >= 0.999 * cap)
        out['cap'] = cap; out['frac_vein_nodes_at_cap'] = round(float(at.sum() / max(vv.size, 1)), 4)
        out['cap_reach_over_R'] = round(float(dist[at].max() / R), 3) if at.any() else 0
        out['n_nodes_at_cap'] = int(at.sum())
    # veinless area: fraction of body further than 0.1R from any node with C>thr
    dt = ndi.distance_transform_edt(~(v > thr)); inner = b & (dist < 0.8 * R)
    out['frac_inner_body_farther_than_0.1R_from_vein'] = round(float((dt[inner] > 0.1 * R).mean()), 3)
    out['max_gap_over_R'] = round(float(dt[inner].max() / R), 3)
    return out
if __name__ == '__main__':
    allang = []
    for d in sys.argv[1:]:
        o = ana(d); ang = o.pop('angles'); allang += ang
        print(json.dumps(o))
        a = np.array([x[1] for x in ang]); dd = np.minimum(a % 45, 45 - a % 45)
        print('   ring-crossing angles n=%d  mean dist to nearest lattice dir = %.1f deg (uniform: 11.25)  |<e^{i8th}>| = %.2f' % (len(a), dd.mean(), abs(np.exp(1j * 8 * np.radians(a)).mean())))
    a = np.array([x[1] for x in allang]); w = np.array([x[2] for x in allang]) ** (2 / 3); dd = np.minimum(a % 45, 45 - a % 45)
    print('POOLED n=%d mean dist=%.2f (uniform 11.25, sd of mean %.2f)  flux-weighted mean dist=%.2f  R8=%.3f (noise ~%.3f)  hist(0-7.5,7.5-15,15-22.5)=%s' % (
        len(a), dd.mean(), 6.5 / np.sqrt(len(a)), (dd * w).sum() / w.sum(), abs(np.exp(1j * 8 * np.radians(a)).mean()), 1 / np.sqrt(len(a)), np.histogram(dd, [0, 7.5, 15, 22.5])[0].tolist()))
    big = w > np.percentile(w, 66)
    print('TOP third by flux: n=%d mean dist=%.2f hist=%s' % (big.sum(), dd[big].mean(), np.histogram(dd[big], [0, 7.5, 15, 22.5])[0].tolist()))
