#!/usr/bin/env python3
"""[H1] summ/*.json 을 짧은 표로. usage: tab.py mig|food RUN ..."""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); kind = sys.argv[1]
for r in sys.argv[2:]:
    f = os.path.join(HERE, 'summ', r + '.json')
    if not os.path.exists(f): print(r, '(없음)'); continue
    o = json.load(open(f)); m = json.load(open(os.path.join(HERE, 'runs', r, 'metrics.json')))
    if kind == 'mig':
        print(f"{r:18s} vein4 {o['vein4_largest_med']:.3f}/{o['vein4_largest_min']:.3f} v10 {o['vein10_largest_med']:.3f} v30 {o['vein30_largest_med']:.3f} cyc {o['cycles4_med']:3.0f} disp {o['disp_track']:5.1f}@{o['disp_dir_deg']:5.1f} touch {m['t_touch'][0]} body {o['body_largest_vol_min']:.3f} frag {o.get('body_ncomp_end')} amp {o.get('m_sheet_amp')} hmin {o['m_h_min_seen']:.3f} mgmax {o['m_mg_err'][2]:.2f}")
    else:
        f3 = lambda d: '/'.join(f'{v:g}' for v in d.values())
        print(f"{r:18s} same4 {f3(o['same4']):14s} same10 {f3(o['same10']):14s} pathC {f3(o['pathminC_med']):18s} veinmed {o['vein_medC_med']:5.1f} veinL {o['vein4_largest_med']:.3f} body {o['body_largest_vol_min']:.3f} touch {'/'.join('%.0f'%t if t else '-' for t in o['t_touch'])} hmin {o['m_h_min_seen']:.3f} negend {o['m_neg_end_cellsteps']} mgmax {o['m_mg_err'][2]:.2f}")
