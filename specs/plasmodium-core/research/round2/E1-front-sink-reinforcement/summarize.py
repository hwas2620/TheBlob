#!/usr/bin/env python3
# usage: summarize.py name1 name2 ...  -> one line per run
import sys, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
print('%-22s %4s %4s %6s %6s %5s %5s %5s | %-16s | %5s %5s %5s %5s | %s' % ('run', 'bp', 'loop', 'vfrac', 'vlarg', 'wr', 'sr', 'all3', 'veins@.25/.5/.75/.9', 'A4', 'A6', 'A8', 'dev', 'native bp/vfrac/sr'))
for nm in sys.argv[1:]:
    try:
        m = json.load(open(os.path.join(HERE, 'runs', nm, 'metrics.json')))
    except Exception as ex:
        print('%-22s (no metrics: %s)' % (nm, ex)); continue
    e = m.get('eval_primary', {}); n = m.get('eval_native_primary', {}); L = m['log'][-1] if m['log'] else {}
    if 'error' in L: print('%-22s ERROR %s at step %s' % (nm, L['error'], L['step'])); continue
    r = L.get('rings', {}); a = L.get('aniso', {})
    rv = '/'.join(str(r[k]['veins']) if r.get(k) else '-' for k in ('0.25', '0.5', '0.75', '0.9'))
    print('%-22s %4s %4s %6s %6s %5s %5s %5s | %-16s | %5s %5s %5s %5s | %s/%s/%s' % (nm, e.get('branch_points'), e.get('loops'), e.get('vein_area_frac'), e.get('vein_largest_frac'),
          e.get('width_ratio_p90_p10'), e.get('strength_ratio_p90_p10'), str(e.get('verdict', {}).get('all_three'))[0], rv,
          a.get('A4'), a.get('A6'), a.get('A8'), a.get('dev_from_radial_deg'), n.get('branch_points'), n.get('vein_area_frac'), n.get('strength_ratio_p90_p10')))
