#!/usr/bin/env python3
# usage: profile.py run ...  -> vein statistics in 6 bands along the travel direction (rear -> front), largest body component
import sys, os, json, numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
for nm in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', nm); m = json.load(open(os.path.join(d, 'metrics.json'))); P = json.load(open(os.path.join(d, 'params.json')))
    h = np.load(os.path.join(d, 'body_native.npy')); C = np.load(os.path.join(d, 'vein_native.npy')); wet = h > 0
    if 'dir' not in m: print(nm, 'no direction'); continue
    ux, uy = m['dir']; N = h.shape[0]; Y, X = np.mgrid[0:N, 0:N]
    lab, nl = ndi.label(wet, structure=np.ones((3, 3))); big = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    s = X * ux + Y * uy; w = -X * uy + Y * ux
    s0, s1 = s[big].min(), s[big].max(); cd = P.get('c_draw', 0) if P.get('c_draw', 0) > 0 else max(1.0, 2 * P['D0'])
    vm = big & (C > cd)
    print(f'{nm}: dir=({ux:.2f},{uy:.2f}) len={s1 - s0:.0f}  vein thr C>{cd}   [band rear->front] cells | sheet(h>0.5) cells | vein cells | veins crossing band mid-line | C p50 / p90 / max of vein cells | mean h')
    out = []
    for b in range(6):
        lo = s0 + (s1 - s0) * b / 6; hi = s0 + (s1 - s0) * (b + 1) / 6
        mb = big & (s >= lo) & (s <= hi); vb = vm & mb
        mid = np.abs(s - (lo + hi) / 2) < 0.75
        line = (vm & mid); order = np.argsort(w[line]); ww = np.sort(w[line])
        ncross = int(1 + (np.diff(ww) > 1.6).sum()) if ww.size else 0
        cv = C[vb]
        row = dict(band=b, cells=int(mb.sum()), sheet=int((mb & (h > 0.5)).sum()), vein=int(vb.sum()), ncross=ncross,
                   Cp50=round(float(np.percentile(cv, 50)), 1) if cv.size else 0, Cp90=round(float(np.percentile(cv, 90)), 1) if cv.size else 0,
                   Cmax=round(float(cv.max()), 1) if cv.size else 0, hmean=round(float(h[mb].mean()), 3) if mb.any() else 0)
        out.append(row); print('   ', row)
    json.dump(out, open(os.path.join(d, 'profile.json'), 'w'), indent=1)
