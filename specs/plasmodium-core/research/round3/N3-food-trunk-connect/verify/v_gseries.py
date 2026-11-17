#!/usr/bin/env python3
"""re-derive the pass-criterion table from the experimenter's own 20-unit series (metrics.json gseries) with my own window rule and arithmetic"""
import json, sys, os, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def lrun(fl):
    b = c = 0
    for f in fl: c = c + 1 if f else 0; b = max(b, c)
    return b * 20
groups = {'res': ['F2_res_s1', 'F2_res_s2', 'F2_res_s3'], 'res+inj': ['F2_inj_s1', 'F2_inj_s2', 'F2_inj_s3'], 'res+bk': ['F2_res_bk_s1', 'F2_res_bk_s2', 'F2_res_bk_s3'],
          'hres4': ['F2_hres4_s1', 'F2_hres4_s2', 'F2_hres4_s3'], 'hres4+bk': ['F2_hres4_bk_s1', 'F2_hres4_bk_s2', 'F2_hres4_bk_s3', 'F2_hres4_bk_s1_T720'], 'hres4+bk nopulse': ['F2_hres4_bk_none_s1'],
          'VERIFY': ['verify:V1_hres4_bk_s11', 'verify:V2_hres4_bk_s12_newfood', 'verify:V5_inj2_s11']}
for gname, runs in groups.items():
    print('==', gname)
    for run in runs:
        d = os.path.join(ROOT, 'verify', 'runs', run[7:]) if run.startswith('verify:') else os.path.join(ROOT, 'runs', run)
        if not os.path.exists(os.path.join(d, 'metrics.json')): print('  ', run, 'missing'); continue
        m = json.load(open(os.path.join(d, 'metrics.json'))); tt = m['t_touch']
        if any(v is None for v in tt): print('  ', run, 'food not touched', tt); continue
        t0 = 20 * (int(max(tt) // 20) + 2)
        W = [g for g in m['gseries'] if g['t'] >= t0 - 1e-6]
        L = np.array([g['vein'].get('largest', 0) for g in W]); P = [(g.get('path') or {}).get('0-1', {}) for g in W]
        ratio = np.array([(p.get('ratio_vs_vein_med') or 0.0) if p.get('connected') else 0.0 for p in P]); conn = np.array([bool(p.get('connected')) for p in P]); same = np.array([bool(p.get('same_vein_comp')) for p in P])
        E = [g['vein'].get('edges', 0) for g in W]; bc = [g['body']['comps'] for g in W]; lv = [g['body']['largest_vol'] for g in W]
        print(f'   {run:28s} window {t0}-{W[-1]["t"]:.0f} n={len(W)} touch={tt} | largest med={np.median(L):.3f} ge0.8={np.mean(L >= 0.8):.2f} min={L.min():.2f} | ratio med={np.median(ratio):.2f} ge10={np.mean(ratio >= 10):.2f} run10={lrun(ratio >= 10)} last={ratio[-1]:.1f} '
              f'| wetpath={conn.mean():.2f} same={same.mean():.2f} | E {E[0]}->{E[-1]} | body comps end={bc[-1]} largest_vol min={min(lv):.2f} end={lv[-1]:.2f} | hmin={m["h_min_seen"]:.2f}')
