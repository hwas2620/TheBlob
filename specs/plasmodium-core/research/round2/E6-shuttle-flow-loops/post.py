#!/usr/bin/env python3
"""post.py - extra hierarchy metrics from the edge dumps + loop/hierarchy trade-off table and plot.
usage: post.py [--plot OUT.png] name_or_prefix ...
 trunk_ratio = w_p99.9 / w_p50 over vein edges (tube width w = 0.7 C^(1/4); vein edge: w >= 0.35 * w_p99.5)
 taper_rho   = Spearman correlation between tube width and distance from the DC source point over vein edges
               (-1: thick at the source, thin far away = stem->branch taper; 0: no relation)
 top10_share = share of total tube volume (sum C^(1/2) L) held by the thickest 10% of vein length
"""
import sys, os, json, glob, numpy as np
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__))

def extra(nm, snap=None):
    fs = sorted(glob.glob(os.path.join(HERE, 'runs', nm, 'edges_*.npz')))
    z = np.load(fs[-1] if snap is None else fs[snap]); C = z['C'].astype(float)
    w = 0.7 * C ** 0.25; ve = w >= 0.35 * np.percentile(w, 99.5)
    mx = 0.5 * (z['ex1'] + z['ex2']); my = 0.5 * (z['ey1'] + z['ey2']); L = np.hypot(z['ex2'] - z['ex1'], z['ey2'] - z['ey1'])
    d = np.hypot(mx - z['src'][0], my - z['src'][1])
    wv = w[ve]; o = np.argsort(-wv); vol = (C[ve] ** 0.5 * L[ve])[o]; cl = np.cumsum(L[ve][o]); top = cl <= 0.1 * cl[-1]
    return dict(trunk_ratio=round(float(np.percentile(wv, 99.9) / np.median(wv)), 2), taper_rho=round(float(spearmanr(wv, d[ve])[0]), 3),
                top10_share=round(float(vol[top].sum() / vol.sum()), 3), w_max=round(float(w.max()), 2), w_med_vein=round(float(np.median(wv)), 2))

def collect(args):
    names = []
    for a in args:
        hit = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(HERE, 'runs', a + '*', 'metrics.json')))
        names += [h for h in hit if h not in names]
    rows = []
    for nm in names:
        m = json.load(open(os.path.join(HERE, 'runs', nm, 'metrics.json'))); e = m.get('eval_primary', {}); last = [l for l in m['log'] if 'own' in l][-1]['own']
        x = extra(nm)
        rows.append(dict(run=nm, bp=e.get('branch_points'), largest=e.get('vein_largest_frac'), w_ratio=e.get('width_ratio_p90_p10'), s_ratio=e.get('strength_ratio_p90_p10'),
                         all3='Y' if e.get('verdict', {}).get('all_three') else 'n', loops_eval=e.get('loops'), Lbig02=last['r0.2'].get('loops_big'), Lbig035=last['r0.35'].get('loops_big'), **x))
    return rows

if __name__ == '__main__':
    args = sys.argv[1:]; plot = None; md = False
    while args and args[0].startswith('--'):
        if args[0] == '--plot': plot = args[1]; args = args[2:]
        elif args[0] == '--md': md = True; args = args[1:]
    rows = collect(args); hdr = list(rows[0].keys())
    if md:
        print('| ' + ' | '.join(hdr) + ' |'); print('|' + '---|' * len(hdr))
        for r in rows: print('| ' + ' | '.join(str(r[h]) for h in hdr) + ' |')
    else:
        wd = [max(len(str(r[h])) for r in rows + [dict(zip(hdr, hdr))]) for h in hdr]
        for r in [dict(zip(hdr, hdr))] + rows: print('  '.join(str(r[h]).ljust(w_) for h, w_ in zip(hdr, wd)))
    json.dump(rows, open(os.path.join(HERE, 'post_rows.json'), 'w'), indent=1)
