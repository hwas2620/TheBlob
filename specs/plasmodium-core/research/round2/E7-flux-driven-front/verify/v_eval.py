#!/usr/bin/env python3
# independent re-evaluation: common eval at 3 thresholds on stored arrays (rendered + native)
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.dirname(HERE)
EVAL = os.path.join(os.path.dirname(EXP), 'common', 'eval_morph.py')
runs = sys.argv[1:]
keys = ('body_solidity','body_components','body_largest_frac','vein_area_frac','vein_components','vein_largest_frac','branch_points','loops','endpoints','width_p10','width_p50','width_p90','width_ratio_p90_p10','strength_ratio_p90_p10')
res = {}
for r in runs:
    d = r if os.path.isabs(r) else os.path.join(EXP, 'runs', r)
    nm = os.path.basename(d)
    for tag, bn, vn in (('render4x', 'body.npy', 'vein.npy'), ('native', 'body_native.npy', 'vein_native.npy')):
        o = os.path.join(HERE, f'eval_{nm}_{tag}.json')
        subprocess.run([sys.executable, EVAL, os.path.join(d, bn), os.path.join(d, vn), '--out', o], stdout=subprocess.DEVNULL)
        e = json.load(open(o))
        for rel, m in e['sweeps'].items():
            v = m['verdict']
            print(nm, tag, 'rel', rel, {k: m.get(k) for k in keys}, 'ALL3' if v.get('all_three') else 'fail(net=%s,br=%s,hi=%s)' % (v.get('network_like'), v.get('branched'), v.get('hierarchical')))
