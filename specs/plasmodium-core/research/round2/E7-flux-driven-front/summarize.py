#!/usr/bin/env python3
# usage: summarize.py [--tsv results.tsv] name1 name2 ... (default: all runs)  -> one line per run
import sys, json, os, glob
HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]; tsv = None
if args and args[0] == '--tsv': tsv = args[1]; args = args[2:]
if not args: args = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, 'runs', '*')))
cols = ['run', 't_end', 'disp', 'path', 'vlate', 'area', 'pol', 'sect', 'F/R_ext', 'F/R_area', 'sh_sol', 'sh_frac', 'comp', 'b_sol', 'bp', 'loops', 'vfrac', 'vlarg', 'wr', 'sr', 'all3', 'nat_bp', 'nat_sr', 'mass_err', 'h_min', 'stop']
rows = []
for nm in args:
    try: m = json.load(open(os.path.join(HERE, 'runs', nm, 'metrics.json')))
    except Exception as ex: continue
    e = m.get('eval_primary', {}); n = m.get('eval_native_primary', {})
    rows.append([nm, m.get('t_end'), m.get('disp'), m.get('path_len'), m.get('late_speed'), m.get('area_end'), m.get('growth_polarisation'), m.get('growth_sector_frac'),
                 m.get('front_rear_ext_ratio'), m.get('front_rear_area_ratio'), m.get('sheet_solidity'), m.get('sheet_area_frac'), m.get('body_components'),
                 e.get('body_solidity'), e.get('branch_points'), e.get('loops'), e.get('vein_area_frac'), e.get('vein_largest_frac'), e.get('width_ratio_p90_p10'),
                 e.get('strength_ratio_p90_p10'), str(e.get('verdict', {}).get('all_three'))[0], n.get('branch_points'), n.get('strength_ratio_p90_p10'),
                 '%.1e' % m.get('mass_err_max', 0), round(m.get('h_min_seen', 0), 3), (m.get('stop') or '-').replace(' ', '_')])
fmt = lambda r: ' '.join(('%-22s' if i == 0 else '%7s') % (x if x is not None else '-') for i, x in enumerate(r))
print(fmt(cols))
for r in rows: print(fmt(r))
if tsv:
    with open(os.path.join(HERE, tsv), 'w') as f:
        f.write('\t'.join(cols) + '\n')
        for r in rows: f.write('\t'.join(str(x) for x in r) + '\n')
