#!/usr/bin/env python3
"""모든 runs/*/ 의 curve.json(자체 지표 시간 곡선) + eval.json(공통 채점) + hier.json(가지 단위 굵기) 을 한 표로.
출력: summary_all.md, summary_all.json. 기존 summary.md(A 계열만)는 건드리지 않는다."""
import os, json, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
def near(c, t): return min(c, key=lambda m: abs(m['t'] - t))
rows = []
for d in sorted(glob.glob(os.path.join(HERE, 'runs', '*'))):
    nm = os.path.basename(d)
    if nm.startswith('t'): continue
    try:
        C = json.load(open(os.path.join(d, 'curve.json'))); P = json.load(open(os.path.join(d, 'params.json')))
    except Exception as e:
        continue
    cur = C['curve']; T = cur[-1]['t']; last = cur[-1]
    late = [m for m in cur if m['t'] >= T / 2 and m.get('branch_points', 0) > 0]
    slope = None
    if len(late) >= 3:
        slope = round(float(np.polyfit(np.log([m['t'] for m in late]), np.log([m['branch_points'] for m in late]), 1)[0]), 2)
    ev = {}; full = {}
    try:
        full = json.load(open(os.path.join(d, 'eval.json'))); ev = full.get('primary', {})
    except Exception: pass
    h = {}
    try: h = json.load(open(os.path.join(d, 'hier.json')))
    except Exception: pass
    z = last.get('zones', {})
    r = dict(name=nm, geom=P.get('geom'), N=P['N'], n=C.get('n_particles'), area=C.get('body_area'),
             dens_end=round(C.get('n_particles', 0) / max(C.get('body_area', 1), 1), 3),
             cap=P['cap'], SA=P['SA'], RA=P['RA'], SO=P['SO'], SO_rear=P.get('SO_rear'), so_mix=P.get('so_mix'),
             nodes=P.get('nodes', 0), node_w=P.get('node_w'), front_w=P.get('front_w', 0), v=P.get('v', 0), sync=P.get('sync', 0),
             damp=P.get('damp'), dpass=P.get('diff_passes', 1), seed=P['seed'], T=T,
             BP500=near(cur, 500).get('branch_points'), BP2k=near(cur, 2000).get('branch_points'), BP8k=near(cur, 8000).get('branch_points'),
             BPend=last.get('branch_points'), loops=last.get('loops'), slope=slope,
             vfrac=last.get('vein_area_frac'), lg=last.get('vein_largest_frac'), w50=last.get('width_p50'),
             wr=last.get('width_ratio_p90_p10'), sr=last.get('strength_ratio_p90_p10'), moved=last.get('moved_frac'),
             rf_w=last.get('rear_over_front_width'), fr_sk=last.get('front_over_rear_skel_density'),
             seg_wr=h.get('seg_wr'), seg_sr=h.get('seg_sr'),
             e_BP=ev.get('branch_points'), e_wr=ev.get('width_ratio_p90_p10'), e_sr=ev.get('strength_ratio_p90_p10'),
             e_lg=ev.get('vein_largest_frac'), e_loops=ev.get('loops'), e_all3=(ev.get('verdict') or {}).get('all_three'),
             wall=C.get('wall_s'))
    rows.append(r)
json.dump(rows, open(os.path.join(HERE, 'summary_all.json'), 'w'), indent=1)
cols = ['name', 'geom', 'n', 'dens_end', 'cap', 'SA', 'RA', 'SO', 'SO_rear', 'nodes', 'front_w', 'v', 'sync', 'damp', 'dpass', 'seed', 'T',
        'BP500', 'BP2k', 'BP8k', 'BPend', 'loops', 'slope', 'vfrac', 'lg', 'w50', 'wr', 'sr', 'seg_wr', 'rf_w', 'fr_sk', 'moved',
        'e_BP', 'e_loops', 'e_wr', 'e_sr', 'e_lg', 'e_all3']
L = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
for r in rows: L.append('| ' + ' | '.join(str(r.get(c)) for c in cols) + ' |')
open(os.path.join(HERE, 'summary_all.md'), 'w').write('\n'.join(L) + '\n')
for r in rows:
    print(f"{r['name']:30s} {str(r['geom']):8s} n={r['n']:6d} d={r['dens_end']:<5} cap={r['cap']} SA={r['SA']} RA={r['RA']} SO={r['SO']}/{r['SO_rear']} nd={r['nodes']} fw={r['front_w']} v={r['v']} sy={r['sync']} "
          f"T={r['T']} BP {r['BP500']}/{r['BP2k']}/{r['BP8k']}/{r['BPend']} lp={r['loops']} sl={r['slope']} vf={r['vfrac']} lg={r['lg']} w50={r['w50']} wr={r['wr']} sr={r['sr']} segwr={r['seg_wr']} "
          f"rf_w={r['rf_w']} fr_sk={r['fr_sk']} mv={r['moved']} | eval BP={r['e_BP']} lp={r['e_loops']} wr={r['e_wr']} sr={r['e_sr']} lg={r['e_lg']} all3={r['e_all3']}")
