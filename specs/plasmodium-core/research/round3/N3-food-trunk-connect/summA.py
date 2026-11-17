#!/usr/bin/env python3
"""step 2 summary: thickness-gradient cause separation.  usage: summA.py RUN [RUN...]"""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
for r in [a for a in sys.argv[1:] if a != '-v']:
    m = json.load(open(os.path.join(HERE, 'runs', r, 'metrics.json')))
    print(f'=== {r}  disp={m["disp"]} touch={m["t_touch"]} mass_err={m["mass_err_max"]:.1e} hmin={m["h_min_seen"]}')
    gj = os.path.join(HERE, 'runs', r, 'graph.json'); full = json.load(open(gj)) if os.path.exists(gj) else m['full']
    for tk in sorted(full):
        f = full[tk]; v = f['vein']; fa = f.get('flux_age', {}); pos = f.get('pos', {})
        ax = pos.get('disp') or pos.get('food0') or {}
        print(f' {tk}: E={v["edges"]} largest={v["largest"]} ws={v.get("largest_ws")} comps={v["comps"]} end/junc={v["end_per_junc"]} cyc={v["cycles"]} Cmed={v["C_med"]} Cmax={v["C_max"]} strahler={f.get("strahler",{}).get("strahler_max")} '
              f'| sp(logC,pos disp)={pos.get("disp",{}).get("spearman_logC_pos")} food0={pos.get("food0",{}).get("spearman_logC_pos")} thick_rear={ax.get("thick_frac_rear_half")}/{ax.get("n_thick_C>100")}')
        print(f'      sp(logC,age)={fa.get("spearman_logC_edgeage")} sp(logC,Qnet)={fa.get("spearman_logC_logQnet")} sp(logC,Qgross)={fa.get("spearman_logC_logQgross")} '
              f'partial(age|Qnet)={fa.get("partial_logC_age_given_Qnet")} partial(Qnet|age)={fa.get("partial_logC_Qnet_given_age")} partial(age|Qgross)={fa.get("partial_logC_age_given_Qgross")} G/N={fa.get("vein_gross_over_net")}')
        if '-v' in sys.argv:
            print('      age bins (C_med vein | n | Qnet_med | Qgross_med | G/N):', ' ; '.join(f'{b["age"]}: {b.get("C_med")}|{b["n_vein"]}|{b.get("Qnet_med")}|{b.get("Qgross_med")}|{b.get("gross_over_net")}' for b in fa.get('age_bins', [])))
            if ax:
                print('      bands rear->front (C_med|n|Qnet|Qgross|age):', ' ; '.join(f'{b.get("C_med")}|{b["n"]}|{b.get("Qnet_med")}|{b.get("Qgross_med")}|{b.get("edgeage_med")}' for b in ax['bands_rear_to_front']))
                print('      sections rear->front (net_fwd|abs|n80|top1|nvein|C_top):', ' ; '.join(f'{s.get("net_fwd")}|{s.get("abs_sum")}|{s.get("n80")}|{s.get("top1_share")}|{s.get("n_vein")}|{s.get("C_of_top_flux_edge")}' for s in ax['sections']))
