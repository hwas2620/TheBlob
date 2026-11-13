#!/usr/bin/env python3
"""re-measure the experimenter's saved states (state_t*.npz) with vindep and print next to the values stored in metrics.json['full'] (graphm)"""
import json, sys, os, glob
import vindep
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res = {}
for run in sys.argv[1:]:
    m = json.load(open(os.path.join(ROOT, 'runs', run, 'metrics.json')))
    gj = os.path.join(ROOT, 'runs', run, 'graph.json'); full = json.load(open(gj)) if os.path.exists(gj) else m['full']
    print(f'=== {run} touch={m["t_touch"]} hmin={m["h_min_seen"]:.3f}')
    res[run] = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'runs', run, 'state_t*.npz'))):
        S = vindep.load(f); o = vindep.analyse(S); tk = os.path.basename(f)[6:-4]; res[run][tk] = o
        g = full.get(tk, {}); gv = g.get('vein', {}); gp = (g.get('path') or {}).get('0-1', {})
        v4, v10, v30 = o['v4'], o['v10'], o['v30']
        print(f' {tk}: MINE E={v4.get("E")} largest thr4/10/30 = {v4.get("largest")}/{v10.get("largest")}/{v30.get("largest")}  ex-disc = {v4.get("largest_ex")}/{v10.get("largest_ex")}/{v30.get("largest_ex")} '
              f'E_in_disc={v4.get("E_in_disc")} E_ex={v4.get("E_ex")} end={v4.get("endpoints")} junc={v4.get("junctions")} cyc={v4.get("cycles")} | THEIRS E={gv.get("edges")} largest={gv.get("largest")} end={gv.get("endpoints")} junc={gv.get("junctions")} cyc={gv.get("cycles")}')
        p = o.get('path')
        if p:
            print(f'      path MINE conn={p.get("connected")} n_out={p.get("n_out")} Cmed={p.get("path_C_med")} Cmin={p.get("path_C_min")} bottleneck={p.get("bottleneck_C")} veinmed all/exdisc/offpath={p.get("vein_med_all")}/{p.get("vein_med_exdisc")}/{p.get("vein_med_offpath")} '
                  f'ratio all/exdisc/offpath={p.get("ratio_all")}/{p.get("ratio_exdisc")}/{p.get("ratio_offpath")} path_share={p.get("path_share_of_exdisc_veins")} same={p.get("same_vein_comp")} h_med/min={p.get("path_h_med")}/{p.get("path_h_min")} net/gross={p.get("path_net_med")}/{p.get("path_gross_med")}'
                  f' | THEIRS Cmed={gp.get("C_med")} Cmin={gp.get("C_min")} ratio={gp.get("ratio_vs_vein_med")} veinmed={gp.get("vein_med")} same={gp.get("same_vein_comp")}')
        print(f'      body: area={o["area"]} comps={o["body_comps"]} largest_vol={o["body_largest_vol"]} vol_on_discs={o["vol_on_discs"]} hmin={o["h_min"]} n_neg={o["n_h_neg"]} n<hmin={o["n_h_lt_hmin"]} chord_lat={o["chord_lat_frac"]}({o["chord_n"]}) res={o.get("res")}')
json.dump(res, open('v_states_%s.json' % (sys.argv[1][:12]), 'w'), indent=1)
