#!/usr/bin/env python3
"""time series of quick graph metrics.  usage: ts.py RUN [RUN...]"""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
for r in sys.argv[1:]:
    m = json.load(open(os.path.join(HERE, 'runs', r, 'metrics.json')))
    print(f'=== {r} touch={m["t_touch"]} cover={m["t_cover"]} exh={m["t_exh"]} Vinj={m["Vinj"]:.0f} mass_err={m["mass_err_max"]:.1e} hmin={m["h_min_seen"]:.3f} bridge_kept={m["bridge_kept_cellsteps"]} tube_kept={m["tube_kept_cellsteps"]}')
    print('   t   area  E    largest comps end/junc cyc | body comps largVol | new[tow,side,away] | res0[inL,frac,front] | path[ratio,min/med,frac_vein,same] | h_food wetfood')
    for g in m['gseries']:
        v = g['vein']; b = g['body']; res = g.get('res', [{}]); r0 = res[0] if res else {}
        pth = g.get('path', {}); ps = ' '.join(f'{k}:{p.get("ratio_vs_vein_med")},{p.get("ratio_min_vs_vein_med")},{p.get("frac_vein")},{int(bool(p.get("same_vein_comp")))}' if p.get('connected') else f'{k}:--' for k, p in pth.items())
        rs = ' '.join(f'{int(bool(x.get("in_largest")))},{x.get("comp_edge_frac")},{x.get("front_reach")}' if x.get('in_graph') else '--' for x in res)
        print(f' {g["t"]:5.0f} {g["area"]:5d} {v["edges"]:4d} {v.get("largest")}/{v.get("largest_ws")} {v.get("comps")} {v.get("end_per_junc")} {v.get("cycles")} | {b["comps"]} {b["largest_vol"]} | {g.get("new_dir[toward,side,away]")} | {rs} | {ps} | {g.get("h_on_food")} {g.get("wet_food_cells")}')
