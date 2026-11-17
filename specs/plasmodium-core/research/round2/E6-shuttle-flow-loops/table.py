#!/usr/bin/env python3
# usage: table.py [--md] prefix_or_name ...   -> one row per run (eval_morph primary + own loop metrics per snapshot)
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]; md = False
if args and args[0] == '--md': md = True; args = args[1:]
names = []
for a in args:
    hit = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(HERE, 'runs', a + '*', 'metrics.json')))
    names += [h for h in hit if h not in names]
hdr = ['run', 'bp', 'ends', 'loops(eval)', 'vfrac', 'largest', 'w_ratio', 's_ratio', 'all3', 'Lbig@.2 per snap', 'Lbig@.35 per snap', 'Lmain@.2', 'holeA_med', 'ew_ratio', 'Cmax', 'chg_last']
rows = []
for nm in names:
    m = json.load(open(os.path.join(HERE, 'runs', nm, 'metrics.json'))); e = m.get('eval_primary', {}); lg = [l for l in m['log'] if 'own' in l]
    seen = set(); lg2 = []
    for l in lg:
        if l['step'] in seen: continue
        seen.add(l['step']); lg2.append(l)
    l2 = '/'.join(str(l['own']['r0.2'].get('loops_big')) for l in lg2); l35 = '/'.join(str(l['own']['r0.35'].get('loops_big')) for l in lg2)
    last = lg2[-1]
    rows.append([nm, e.get('branch_points'), e.get('endpoints'), e.get('loops'), e.get('vein_area_frac'), e.get('vein_largest_frac'), e.get('width_ratio_p90_p10'),
                 e.get('strength_ratio_p90_p10'), 'Y' if e.get('verdict', {}).get('all_three') else 'n', l2, l35, last['own']['r0.2'].get('loops_main'),
                 last['own']['r0.2'].get('hole_area_med'), m.get('edge_width_ratio_p90_p10'), round(last['Cmax'], 1), last['rel_change_since_prev_snap']])
if md:
    print('| ' + ' | '.join(hdr) + ' |'); print('|' + '---|' * len(hdr))
    for r in rows: print('| ' + ' | '.join(str(x) for x in r) + ' |')
else:
    wd = [max(len(str(x)) for x in col) for col in zip(hdr, *rows)]
    for r in [hdr] + rows: print('  '.join(str(x).ljust(w) for x, w in zip(r, wd)))
