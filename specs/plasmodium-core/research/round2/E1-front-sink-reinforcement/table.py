#!/usr/bin/env python3
# usage: table.py name1 name2 ...  -> eval_morph (render) + graph analysis (thr = 2 j0) + anisotropy, one line per run
import sys, json, os
from analyze import analyse, HERE
print('%-16s| %4s %4s %5s %5s %4s %4s %1s | %4s %4s %4s %5s %2s %2s %4s %5s %6s | %-17s | %-19s | %5s %5s %5s %5s' % ('run', 'bp', 'loop', 'vfrac', 'vlarg', 'wr', 'sr', 'ok',
      'br', 'tips', 'loop', 'L/br', 'Sd', 'Sc', 'RB', 'murr', 'ss', 'n80@.3/.5/.7/.9R', 'r@.1/.5/.9R', 'A4', 'A6', 'A8', 'dev'))
for nm in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', nm)
    try: m = json.load(open(os.path.join(d, 'metrics.json')))
    except Exception: print('%-16s| (no metrics)' % nm); continue
    e = m.get('eval_primary', {}); L = m['log'][-1] if m['log'] else {}; a = L.get('aniso', {})
    if 'error' in L: print('%-16s| ERROR %s' % (nm, L['error'])); continue
    try:
        r = analyse(nm); g = r['thr']['2'] or {}
        pr = {p['pos']: p for p in r['profile']}
        n80 = '/'.join(str(pr[k].get('n80', '-')) for k in (0.3, 0.5, 0.7, 0.9)) if 0.3 in pr else '-'
        rr = '/'.join('%.2f' % pr[k].get('r_mean_top', 0) for k in (0.1, 0.5, 0.9)) if 0.1 in pr else '-'
    except Exception as ex: g = {}; n80 = rr = 'n/a'
    mu = (g.get('murray_exp_p25_p50_p75') or [None, None, None])[1]; ss = (g.get('steady_log10_C_over_Qg_p25_p50_p75') or [None] * 3)[1]
    print('%-16s| %4s %4s %5s %5s %4s %4s %1s | %4s %4s %4s %5s %2s %2s %4s %5s %6s | %-17s | %-19s | %5s %5s %5s %5s' % (nm, e.get('branch_points'), e.get('loops'), e.get('vein_area_frac'), e.get('vein_largest_frac'),
          e.get('width_ratio_p90_p10'), e.get('strength_ratio_p90_p10'), str(e.get('verdict', {}).get('all_three'))[0],
          g.get('branch_nodes'), g.get('tips'), g.get('loops'), g.get('loops_per_branch'), g.get('strahler_div'), g.get('strahler_conv'), g.get('bif_ratio_div'), mu, ss, n80, rr,
          a.get('A4'), a.get('A6'), a.get('A8'), a.get('dev_from_radial_deg')))
