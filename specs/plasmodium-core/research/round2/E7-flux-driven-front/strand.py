#!/usr/bin/env python3
# usage: strand.py run ... -> volume fraction outside the largest body component, sheet/vein/thin volume split
import sys, os, json, numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
for nm in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', nm); P = json.load(open(os.path.join(d, 'params.json')))
    h = np.load(os.path.join(d, 'body_native.npy')).astype(float); C = np.load(os.path.join(d, 'vein_native.npy')); wet = h > 0
    lab, nl = ndi.label(wet, structure=np.ones((3, 3))); sz = np.bincount(lab.ravel())[1:]; big = lab == (np.argmax(sz) + 1)
    V = h.sum(); cd = P.get('c_draw', 0) if P.get('c_draw', 0) > 0 else max(1.0, 2 * P['D0'])
    r = dict(run=nm, comps=int(nl), cells_largest=int(big.sum()), cells_other=int((wet & ~big).sum()), vol_frac_outside_largest=round(float(h[wet & ~big].sum() / V), 4),
             vol_frac_sheet=round(float(h[big & (h > 0.5)].sum() / V), 3), vol_frac_vein_nonsheet=round(float(h[big & (h <= 0.5) & (C > cd)].sum() / V), 3),
             vol_frac_thin=round(float(h[big & (h <= 0.5) & (C <= cd)].sum() / V), 3), wet_cells=int(wet.sum()), V=round(float(V), 2))
    print(json.dumps(r)); json.dump(r, open(os.path.join(d, 'strand.json'), 'w'))
