#!/usr/bin/env python3
"""usage: tabulate.py run1 run2 ...  -> markdown table from runs/*/metrics.json"""
import json, sys, os
H = ['run', 't_end', '이동', '면적', 'h_min', '부피오차', 'Cmax(최대/끝)', 'Spearman', '최대성분', '성분', '순환', '끝점', '분기', 'Strahler', '총/순', '격자현', '진폭', '잠금R', '몸조각', '마름', '유량오차 중앙/p90/최대', 'C>100 중앙/최대', 'p-h>0.05 최대']
rows = []
for r in sys.argv[1:]:
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runs', r, 'metrics.json')
    if not os.path.exists(p): rows.append([r] + ['(없음)'] * (len(H) - 1)); continue
    M = json.load(open(p)); g = M.get('graph', {}); c = M.get('checks', {})
    ea = c.get('err_all'); et = c.get('err_thick'); ph = c.get('ph_vein_gt0p05')
    rows.append([r, M['t_end'], M['disp'], M['area_end'], f"{M['h_min_seen']:.3g}", f"{M['mass_err_max']:.1e}", f"{M['Cmax_run']:.0f}/{M['Cmax_end']:.0f}", g.get('spearman_logC_pos'), g.get('vein_largest_frac'),
                 g.get('vein_components'), g.get('cycles'), g.get('endpoints'), g.get('junctions'), g.get('strahler_max_spanning'), g.get('vein_gross_over_net'), g.get('chord_lattice_frac_7p5'),
                 M.get('hamp_sheet_mean'), M.get('lock_R'), M.get('body_components'), M.get('dry_events', ''),
                 f"{ea['med']:.3f}/{ea['p90']:.3f}/{ea['max']:.3f}" if ea else '-', f"{et['med']:.3f}/{et['max']:.3f}" if et else '-', f"{ph['max']:.3f}" if ph else '-'])
print('| ' + ' | '.join(H) + ' |'); print('|' + '---|' * len(H))
for r in rows: print('| ' + ' | '.join(str(x) for x in r) + ' |')
