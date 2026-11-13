#!/usr/bin/env python3
# usage: fluxprof.py run ...  -> per band along the travel direction (rear -> front): p90 over vein edges of gross <|Q|> and net |<Q>| (last 5-period window), and their sums
import sys, os, json, numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__)); DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
for nm in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', nm); m = json.load(open(os.path.join(d, 'metrics.json'))); P = json.load(open(os.path.join(d, 'params.json')))
    C = np.load(os.path.join(d, 'C_edges.npy')); G = np.load(os.path.join(d, 'Qgross.npy')); Nn = np.load(os.path.join(d, 'Qnet.npy')); h = np.load(os.path.join(d, 'body_native.npy'))
    wet = h > 0; N = h.shape[0]; Y, X = np.mgrid[0:N, 0:N]; cd = max(1.0, 2 * P['D0'])
    if 'dir' not in m: print(nm, 'no dir'); continue
    ux, uy = m['dir']; lab, nl = ndi.label(wet, structure=np.ones((3, 3))); big = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    s = X * ux + Y * uy; s0, s1 = s[big].min(), s[big].max(); out = []
    for b in range(6):
        lo = s0 + (s1 - s0) * b / 6; hi = s0 + (s1 - s0) * (b + 1) / 6; g = []; n = []
        for k in range(4):
            mk = big & (s >= lo) & (s <= hi) & (C[k] > cd) & (G[k] > 0); g.append(G[k][mk]); n.append(Nn[k][mk])
        g = np.concatenate(g); n = np.concatenate(n)
        out.append(dict(band=b, edges=int(g.size), gross_p90=round(float(np.percentile(g, 90)), 3) if g.size else 0, net_p90=round(float(np.percentile(n, 90)), 3) if g.size else 0,
                        gross_max=round(float(g.max()), 3) if g.size else 0, net_max=round(float(n.max()), 3) if g.size else 0, ratio_sum=round(float(g.sum() / max(n.sum(), 1e-12)), 2) if g.size else 0))
    json.dump(out, open(os.path.join(d, 'fluxprof.json'), 'w'), indent=1)
    print(nm, ' gross_p90:', [o['gross_p90'] for o in out], ' net_p90:', [o['net_p90'] for o in out], ' gross_max:', [o['gross_max'] for o in out], ' net_max:', [o['net_max'] for o in out], ' gross/net:', [o['ratio_sum'] for o in out])
