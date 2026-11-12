#!/usr/bin/env python3
"""usage: moving_stats.py NAME ...  -> per-snapshot graph metrics and vein-set overlap between consecutive snapshots (lab frame vs body frame).
vein edge = |Q| >= 2 j0.  J_lab = Jaccard of vein-edge sets at fixed lattice position (restricted to cells wet at both times);
J_body = same after shifting the earlier set by the body displacement (rounded to whole cells)."""
import numpy as np, json, sys, os, glob
from analyze import analyse, HERE
for nm in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', nm); P = json.load(open(os.path.join(d, 'params.json')))
    fs = sorted(glob.glob(os.path.join(d, 'edges_*.npz')), key=lambda f: int(os.path.basename(f)[6:-4]))
    prev = None; rows = []
    for i, f in enumerate(fs):
        Z = np.load(f); V = np.abs(Z['Q']) >= 2 * P['j0']; wet = Z['wet']; cx = float(Z['centre'][0])
        r = analyse(nm, snap=i + 1); e = r['thr']['2'] or {}
        mid = [p for p in r['profile'] if p.get('n80')]
        row = dict(snap=i + 1, t=r['t'], br=e.get('branch_nodes'), loops=e.get('loops'), Sd=e.get('strahler_div'), Sc=e.get('strahler_conv'), lf=e.get('largest_frac'),
                   ss=(e.get('steady_log10_C_over_Qg_p25_p50_p75') or [None] * 3), n80=[p['n80'] for p in mid], qmax=[p['q_max_frac'] for p in mid])
        if prev is not None:
            Vp, wp, cxp = prev; both = wet & wp
            a = V & both[None]; b = Vp & both[None]
            row['J_lab'] = round(float((a & b).sum() / max((a | b).sum(), 1)), 3)
            sh = int(round(cx - cxp)); Vs = np.roll(Vp, sh, axis=2); ws = np.roll(wp, sh, axis=1); both = wet & ws
            a = V & both[None]; b = Vs & both[None]
            row['J_body'] = round(float((a & b).sum() / max((a | b).sum(), 1)), 3); row['shift'] = sh
        prev = (V, wet, cx); rows.append(row)
    json.dump(rows, open(os.path.join(d, 'moving_stats.json'), 'w'), indent=1)
    L = rows[-1]; Jl = [r['J_lab'] for r in rows[1:]]; Jb = [r['J_body'] for r in rows[1:]]
    print('%-18s br=%s Sd=%s Sc=%s loops=%s lf=%s ss(p25,p50,p75)=%s n80(rear->front)=%s qmaxfrac=%s | J_lab(mean last4)=%.2f J_body=%.2f shift=%s | br over time=%s' % (
        nm, L['br'], L['Sd'], L['Sc'], L['loops'], L['lf'], L['ss'], L['n80'], L['qmax'], np.mean(Jl[-4:]), np.mean(Jb[-4:]), L.get('shift'), [r['br'] for r in rows]))
