#!/usr/bin/env python3
"""(c) threshold dependence of the largest vein component, reservoir membership, front reach and ring flux for B / C runs (saved states) and my V3 rerun"""
import json, sys, os, glob, numpy as np
import vindep
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = vindep.DIRS

def ring_flux(S, fx, fy, R):
    """net outward window-mean flux and gross flux through the circle of radius R around the food; my own edge enumeration"""
    C = S['C'].astype(float); wet = S['wet'].astype(bool); N = wet.shape[0]; Qm = S['Qmean'].astype(float); Qg = S['Qgross'].astype(float)
    a, b, k, c = vindep.active_edges(C, wet)
    def rad(n): return np.hypot(((n % N) - fx + N / 2) % N - N / 2, ((n // N) - fy + N / 2) % N - N / 2)
    ra, rb = rad(a), rad(b); cr = (np.minimum(ra, rb) < R) & (np.maximum(ra, rb) >= R)
    q = Qm[k[cr], a[cr] // N, a[cr] % N] * np.sign(rb[cr] - ra[cr]); g = Qg[k[cr], a[cr] // N, a[cr] % N]; cc = c[cr]
    aq = np.sort(np.abs(q))[::-1]; cs = np.cumsum(aq); n80 = int(np.searchsorted(cs, 0.8 * cs[-1]) + 1) if cs.size and cs[-1] > 0 else 0
    return dict(R=R, n_vein=int((cc > 4).sum()), net_out=round(float(q.sum()), 3), gross=round(float(g.sum()), 2), n80=n80, C_max=round(float(cc.max()), 1) if cc.size else None)

def front_reach(S, thr=4.0, rad=3):
    """share of young cells (age<10) within Chebyshev distance rad of a node of the vein component(s) that contain reservoir cells"""
    C = S['C'].astype(float); wet = S['wet'].astype(bool); N = wet.shape[0]; age = S['age']
    a, b, k, c = vindep.active_edges(C, wet); fx, fy = np.asarray(S['foods']).reshape(-1, 2)[0]
    d = vindep.disc_mask(N, fx, fy, float(S['food_r'])).ravel()
    v = vindep.vein_stats(a, b, c, thr)
    if '_roots' not in v: return None
    roots = v['_roots']; rs = set(r for n, r in roots.items() if d[n])
    mk = np.zeros(N * N, bool)
    for n, r in roots.items():
        if r in rs: mk[n] = True
    mk = mk.reshape(N, N); near = np.zeros((N, N), bool)
    ys, xs = np.nonzero(mk)
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1): near[(ys + dy) % N, (xs + dx) % N] = True
    young = wet & (age < 10)
    return round(float((near & young).sum() / max(young.sum(), 1)), 3)

for run in sys.argv[1:]:
    root = os.path.join(ROOT, 'verify') if run.startswith('V') else ROOT
    d = os.path.join(root, 'runs', run); m = json.load(open(os.path.join(d, 'metrics.json')))
    print(f'=== {run} touch={m["t_touch"]} exh={m["t_exh"]} disp={m["disp"]} hmin={m["h_min_seen"]}')
    for f in sorted(glob.glob(os.path.join(d, 'state_t*.npz'))):
        S = vindep.load(f); o = vindep.analyse(S); tk = os.path.basename(f)[6:-4]; fx, fy = np.asarray(S['foods']).reshape(-1, 2)[0]
        res = o.get('res', [{}])[0]
        fr4 = front_reach(S, 4.0); fr10 = front_reach(S, 10.0); fr30 = front_reach(S, 30.0)
        rings = [ring_flux(S, fx, fy, R) for R in (float(S['food_r']) + 0.5, 12, 24)]
        print(f' {tk}: E={o["v4"].get("E")} largest 4/10/30={o["v4"].get("largest")}/{o["v10"].get("largest")}/{o["v30"].get("largest")} res_in_largest={res.get("in_largest")} res_comp_share={res.get("comp_share")} front_reach thr4/10/30={fr4}/{fr10}/{fr30} '
              f'e/j={o["v4"].get("endpoints")}/{o["v4"].get("junctions")} cyc={o["v4"].get("cycles")} lat={o["chord_lat_frac"]}({o["chord_n"]}) bcomp={o["body_comps"]} | rings ' + ' ; '.join(f'R{r["R"]}: nv={r["n_vein"]} net={r["net_out"]} gross={r["gross"]} n80={r["n80"]} Cmax={r["C_max"]}' for r in rings))
