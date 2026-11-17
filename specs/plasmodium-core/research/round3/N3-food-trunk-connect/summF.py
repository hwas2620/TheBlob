#!/usr/bin/env python3
"""steps 5-7 summary: two foods.  usage: summF.py [-v] RUN [RUN...]"""
import json, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
V = '-v' in sys.argv
def longest(ts, ok):
    best = 0.0; start = None
    for t, o in zip(ts, ok):
        if o:
            if start is None: start = t
            best = max(best, t - start)
        else: start = None
    return best
rows = []
for r in [a for a in sys.argv[1:] if a != '-v']:
    m = json.load(open(os.path.join(HERE, 'runs', r, 'metrics.json')))
    gs = m['gseries']; tt = m['t_touch']; tb = max(tt) if all(v is not None for v in tt) else None
    print(f'=== {r} touch={tt} cover={m["t_cover"]} exh={m["t_exh"]} Vinj={m["Vinj"]:.0f} mass_err={m["mass_err_max"]:.1e} hmin={m["h_min_seen"]:.3f} area_end={m["area_end"]} bridge_kept={m["bridge_kept_cellsteps"]} tube_kept={m["tube_kept_cellsteps"]}')
    if tb is None: print('    did not touch all foods'); continue
    post = [g for g in gs if g['t'] >= tb + 20]
    ts = [g['t'] for g in post]; key = sorted(post[0].get('path', {'0-1': {}}))[0]
    P = [g['path'][key] for g in post]
    conn = [bool(p.get('connected')) for p in P]; ratio = [p.get('ratio_vs_vein_med') or 0 if p.get('connected') else 0 for p in P]
    rmin = [p.get('ratio_min_vs_vein_med') or 0 if p.get('connected') else 0 for p in P]; same = [bool(p.get('same_vein_comp')) for p in P]
    fv = [p.get('frac_vein') or 0 if p.get('connected') else 0 for p in P]
    lg = [g['vein']['largest'] for g in post]; ws = [g['vein'].get('largest_ws') or 0 for g in post]; ej = [g['vein']['end_per_junc'] for g in post]
    bc = [g['body']['comps'] for g in post]; bv = [g['body']['largest_vol'] for g in post]; ar = [g['area'] for g in post]
    med = lambda x: float(np.median(x))
    d = dict(run=r, n=len(post), window=f'{ts[0]:.0f}-{ts[-1]:.0f}', conn_frac=np.mean(conn), ratio_med=med(ratio), ratio_min=min(ratio), ratio_ge10_frac=np.mean([x >= 10 for x in ratio]),
             longest_ge10=longest(ts, [x >= 10 for x in ratio]), same_comp_frac=np.mean(same), longest_same=longest(ts, same), path_frac_vein_med=med(fv), minC_ratio_med=med(rmin),
             largest_med=med(lg), largest_ge08_frac=np.mean([x >= 0.8 for x in lg]), largest_final=lg[-1], ws_med=med(ws), endjunc_med=med(ej), body_comps_end=bc[-1], body_largest_vol_min=min(bv), area_min=min(ar), area_end=ar[-1])
    rows.append(d)
    print('    ' + ' '.join(f'{k}={v:.3g}' if isinstance(v, float) else f'{k}={v}' for k, v in d.items() if k != 'run'))
    if V:
        print('    t: ratio|minratio|fracvein|same|largest|ws|end/junc|area|bodycomps|largestvol|h_food|fM')
        for g, p in zip(post, P):
            print(f'    {g["t"]:4.0f}: {p.get("ratio_vs_vein_med")}|{p.get("ratio_min_vs_vein_med")}|{p.get("frac_vein")}|{int(bool(p.get("same_vein_comp")))}|{g["vein"]["largest"]}|{g["vein"].get("largest_ws")}|{g["vein"]["end_per_junc"]}|{g["area"]}|{g["body"]["comps"]}|{g["body"]["largest_vol"]}|{g.get("h_on_food")}|{g.get("fM")}')
json.dump(rows, open(os.path.join(HERE, 'summF_last.json'), 'w'), indent=1)
