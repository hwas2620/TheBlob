#!/usr/bin/env python3
"""time series (every 20 time units) of my own metrics on the verifier re-runs (verify/runs/NAME/gs_t*.npz); also compares with graphm values stored in metrics.json gseries"""
import json, sys, os, glob, numpy as np
import vindep
HERE = os.path.dirname(os.path.abspath(__file__))
def longest_run(flags, step=20):
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0; best = max(best, cur)
    return best * step
allout = {}
for run in sys.argv[1:]:
    m = json.load(open(os.path.join(HERE, 'runs', run, 'metrics.json'))); gs = {round(g['t']): g for g in m['gseries']}
    tt = [v for v in m['t_touch'] if v is not None]; t_both = max(tt) if len(tt) == len(m['t_touch']) else None
    print(f'=== {run} touch={m["t_touch"]} hmin_seen={m["h_min_seen"]:.3f} mass_err={m["mass_err_max"]:.1e} bridge_kept={m["bridge_kept_cellsteps"]} area_end={m["area_end"]}')
    rows = []
    for f in sorted(glob.glob(os.path.join(HERE, 'runs', run, 'gs_t*.npz'))):
        S = vindep.load(f); o = vindep.analyse(S); o['hmin_win'] = float(S['hmin_win']); o['nneg_win'] = int(S['nneg_win']); rows.append(o)
        g = gs.get(round(o['t']), {}); gp = (g.get('path') or {}).get('0-1', {}); p = o.get('path') or {}
        v4, v10, v30 = o['v4'], o['v10'], o['v30']
        print(f' t={o["t"]:5.0f} E4={v4.get("E"):4d} L4/10/30={v4.get("largest")}/{v10.get("largest")}/{v30.get("largest")} Lex4={v4.get("largest_ex")} (graphm {g.get("vein",{}).get("largest")}) e/j={v4.get("endpoints")}/{v4.get("junctions")} cyc={v4.get("cycles")} '
              f'| path Cmed={p.get("path_C_med")} Cmin={p.get("path_C_min")} bott={p.get("bottleneck_C")} r_all={p.get("ratio_all")} (graphm {gp.get("ratio_vs_vein_med")}) r_off={p.get("ratio_offpath")} share={p.get("path_share_of_exdisc_veins")} same={p.get("same_vein_comp")} net/gross={p.get("path_net_med")}/{p.get("path_gross_med")} '
              f'| area={o["area"]} bcomp={o["body_comps"]} bigvol={o["body_largest_vol"]} discvol={o["vol_on_discs"]} hmin_win={o["hmin_win"]:.2f} negcellsteps={o["nneg_win"]} lat={o["chord_lat_frac"]}({o["chord_n"]})')
    allout[run] = rows
    if t_both is not None and len(m['t_touch']) >= 2:
        t0 = 20 * (int(t_both // 20) + 2)       # first sample at least 20 after both foods touched (experimenter: 80 for touch 47, 220 for touch 189~193)
        W = [r for r in rows if r['t'] >= t0 - 1e-6]
        def col(fn): return [fn(r) for r in W]
        L4 = col(lambda r: r['v4'].get('largest', 0)); L10 = col(lambda r: r['v10'].get('largest', 0)); L30 = col(lambda r: r['v30'].get('largest', 0)); Lex = col(lambda r: r['v4'].get('largest_ex') or 0)
        ra = col(lambda r: (r.get('path') or {}).get('ratio_all') or 0.0); ro = col(lambda r: (r.get('path') or {}).get('ratio_offpath') or 0.0); rx = col(lambda r: (r.get('path') or {}).get('ratio_exdisc') or 0.0)
        bt = col(lambda r: (r.get('path') or {}).get('bottleneck_C') or 0.0); pm = col(lambda r: (r.get('path') or {}).get('path_C_med') or 0.0)
        same = col(lambda r: bool((r.get('path') or {}).get('same_vein_comp')))
        s = dict(window=[t0, W[-1]['t']], n=len(W), largest4_med=float(np.median(L4)), largest10_med=float(np.median(L10)), largest30_med=float(np.median(L30)), largest_exdisc_med=float(np.median(Lex)),
                 largest4_ge08=float(np.mean(np.array(L4) >= 0.8)), largest10_ge08=float(np.mean(np.array(L10) >= 0.8)), largest30_ge08=float(np.mean(np.array(L30) >= 0.8)),
                 ratio_all_med=float(np.median(ra)), ratio_all_ge10=float(np.mean(np.array(ra) >= 10)), ratio_all_run=longest_run(np.array(ra) >= 10),
                 ratio_exdisc_med=float(np.median(rx)), ratio_offpath_med=float(np.median(ro)), ratio_offpath_ge10=float(np.mean(np.array(ro) >= 10)), ratio_offpath_run=longest_run(np.array(ro) >= 10),
                 path_C_med_range=[min(pm), max(pm)], bottleneck_range=[min(bt), max(bt)], bottleneck_med=float(np.median(bt)), same_frac=float(np.mean(same)),
                 E4_range=[min(r['v4'].get('E', 0) for r in W), max(r['v4'].get('E', 0) for r in W)], body_comps_end=W[-1]['body_comps'], body_largest_vol_min=min(r['body_largest_vol'] for r in W),
                 hmin=min(r['hmin_win'] for r in rows), neg_cellsteps_total=sum(r['nneg_win'] for r in rows), samples_with_neg=sum(1 for r in rows if r['nneg_win'] > 0), n_samples=len(rows))
        print(' SUMMARY', json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()}))
        allout[run + '_summary'] = s
json.dump(allout, open('v_series_%s.json' % sys.argv[1][:10], 'w'), indent=1, default=float)
