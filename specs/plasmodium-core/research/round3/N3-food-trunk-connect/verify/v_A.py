#!/usr/bin/env python3
"""(d) thickness-gradient cause separation: my own Spearman(position along food axis, log C) on saved A states, thresholds 4/10/30"""
import json, sys, os, glob, numpy as np
import vindep
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
runs = [('A_osc_pt1_s1', ROOT), ('A_osc_pt0_s1', ROOT), ('A_osc_pt1_s2', ROOT), ('A_osc_pt0_s2', ROOT), ('A_uni_pt1_s1', ROOT), ('A_none_s1', ROOT), ('A_none_s2', ROOT),
        ('V4_osc_pt1_s3', os.path.join(ROOT, 'verify')), ('V4_osc_pt0_s3', os.path.join(ROOT, 'verify'))]
out = {}
for run, root in runs:
    d = os.path.join(root, 'runs', run)
    if not os.path.exists(os.path.join(d, 'metrics.json')): print(run, 'missing'); continue
    m = json.load(open(os.path.join(d, 'metrics.json'))); gj = os.path.join(d, 'graph.json'); full = json.load(open(gj)) if os.path.exists(gj) else m['full']
    out[run] = {}
    for f in sorted(glob.glob(os.path.join(d, 'state_t*.npz'))):
        tk = os.path.basename(f)[6:-4]; S = vindep.load(f); r = vindep.pos_spearman(S, 0.0); o = vindep.analyse(S)
        th = (full.get(tk, {}).get('pos', {}).get('disp') or {}).get('spearman_logC_pos'); thf = (full.get(tk, {}).get('pos', {}).get('food0') or {}).get('spearman_logC_pos')
        out[run][tk] = dict(r, largest=[o['v4'].get('largest'), o['v10'].get('largest'), o['v30'].get('largest')], theirs_disp=th, theirs_food=thf)
        print(f'{run:16s} {tk} span={r["span"]:6.1f} sp thr4/10/30 = {r["sp4"]}/{r["sp10"]}/{r["sp30"]} (n={r["n4"]}/{r["n10"]}/{r["n30"]}) theirs disp/food={th}/{thf} | largest 4/10/30={o["v4"].get("largest")}/{o["v10"].get("largest")}/{o["v30"].get("largest")} lat={o["chord_lat_frac"]}({o["chord_n"]})')
json.dump(out, open('v_A.json', 'w'), indent=1)
