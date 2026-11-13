#!/usr/bin/env python3
"""steps 3/4 summary: reach + reservoir.  usage: summB.py [-v] RUN [RUN...]"""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
V = '-v' in sys.argv
for r in [a for a in sys.argv[1:] if a != '-v']:
    m = json.load(open(os.path.join(HERE, 'runs', r, 'metrics.json')))
    gj = os.path.join(HERE, 'runs', r, 'graph.json'); full = json.load(open(gj)) if os.path.exists(gj) else m['full']
    tt = m['t_touch'][0]; gs = m['gseries']
    pre = [g for g in gs if 40 < g['t'] <= (tt if tt else 1e9) + 1e-6]; nd = [sum(g['new_dir[toward,side,away]'][i] for g in pre) for i in range(3)]
    early = [g for g in gs if g['t'] <= 20]; ne = [sum(g['new_dir[toward,side,away]'][i] for g in early) for i in range(3)]
    post = [g for g in gs if tt and g['t'] > tt + 20]
    print(f'=== {r} touch={m["t_touch"]} cover={m["t_cover"]} exh={m["t_exh"]} Vinj={m["Vinj"]:.0f} disp={m["disp"]} mass_err={m["mass_err_max"]:.1e} hmin={m["h_min_seen"]:.3f}')
    print(f'    new wet cells t<=20 [toward,side,away]={ne};  40<t<=touch: {nd} away_frac={nd[2]/max(sum(nd),1):.3f} toward_frac={nd[0]/max(sum(nd),1):.3f}')
    if post:
        lg = [g['vein']['largest'] for g in post]; ws = [g['vein'].get('largest_ws') for g in post if g['vein'].get('largest_ws') is not None]
        inl = [int(bool(g.get('res', [{}])[0].get('in_largest'))) for g in post]; fr = [g.get('res', [{}])[0].get('front_reach', 0) or 0 for g in post]
        cf = [g.get('res', [{}])[0].get('comp_edge_frac', 0) or 0 for g in post]
        print(f'    after touch+20 (n={len(post)}): largest min/med/max={min(lg)}/{sorted(lg)[len(lg)//2]}/{max(lg)} frac>=0.8={sum(v>=0.8 for v in lg)/len(lg):.2f}' + (f' ws_med={sorted(ws)[len(ws)//2]}' if ws else '') +
              f' | reservoir in largest {sum(inl)}/{len(inl)}, res-comp edge frac med={sorted(cf)[len(cf)//2]}, front_reach med={sorted(fr)[len(fr)//2]}')
    for tk in sorted(full):
        f = full[tk]; v = f['vein']
        if not V and tk != sorted(full)[-1] and tk != sorted(full)[2]: continue
        fs = f.get('food_stats', [{}])[0]; st = f.get('strahler', {}); orr = f.get('orient', {}).get('L>=5', {})
        r0 = (f.get('res') or [{}])[0]
        print(f'  {tk}: E={v["edges"]} largest={v["largest"]} ws={v.get("largest_ws")} end/junc={v["end_per_junc"]} cyc={v["cycles"]} Cmed={v.get("C_med")} Cmax={v.get("C_max")} | strahler={st.get("strahler_max")}(food-rooted={st.get("rooted_at_food0")}) '
              f'orient7.5={orr.get("frac_within7p5")} | res: inL={r0.get("in_largest")} frac={r0.get("comp_edge_frac")} front={r0.get("front_reach")} | h_food={fs.get("h_mean_on_food")} wetfood={fs.get("wet_cells")} vol3r={fs.get("vol_frac_within_3r")} body={f["body"]["comps"]},{f["body"]["largest_vol"]}')
        if fs.get('rings'):
            print('      rings R:(n_vein|C_max|C_med|net_out|n80|top1): ' + ' ; '.join(f'{x["R"]}:{x.get("n_vein")}|{x.get("C_max")}|{x.get("C_med_vein")}|{x.get("net_out")}|{x.get("n80")}|{x.get("top1_share")}' for x in fs['rings'] if x.get('n_act')))
