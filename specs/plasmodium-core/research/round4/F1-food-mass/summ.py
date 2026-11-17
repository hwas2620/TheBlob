#!/usr/bin/env python3
"""먹이 둘(또는 그 이상) 실행 요약. usage: summ.py [-v] RUN [RUN ...]   (runs/<RUN>/metrics.json)
창 = 모든 먹이에 닿은 뒤 20 시간단위부터 끝까지(20 간격 표본). 경로 = 먹이 0-1 사이 최소 저항 경로."""
import json, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
V = '-v' in sys.argv
def longest(ts, ok):
    best = 0.0; start = None
    for t, o in zip(ts, ok):
        if o:
            if start is None: start = t
            best = max(best, t - start + 20)
        else: start = None
    return best
rows = []
for r in [a for a in sys.argv[1:] if a != '-v']:
    f = os.path.join(HERE, 'runs', r, 'metrics.json')
    if not os.path.exists(f): print(r, '(없음)'); continue
    m = json.load(open(f)); gs = m['gseries']; tt = m['t_touch']
    d = dict(run=r, touch=tt, exh=m.get('t_exh'), hmin=round(m['h_min_seen'], 3), neg=m.get('neg_cellsteps'), lim_steps=m.get('lim_steps'), lim_cut_max=round(m.get('lim_cut_max') or 0, 4),
             h_prelim_min=round(m.get('h_prelimit_min') or 0, 3), mass_err=float('%.1e' % m['mass_err_max']), Vend_over_V0=round(m['V_end'] / m['V0'], 2), area_end=m['area_end'])
    if any(v is None for v in tt): d['note'] = 'did not touch all foods'; rows.append(d); print(d); continue
    tb = max(tt); post = [g for g in gs if g['t'] >= tb + 20]
    ts = [g['t'] for g in post]; key = sorted(post[0].get('path', {'0-1': {}}))[0]
    P = [g['path'][key] for g in post]
    same = [bool(p.get('same_vein_comp')) for p in P]; conn = [bool(p.get('connected')) for p in P]
    rmin90 = [(p.get('C_min') or 0) / max(g['vein']['C_p90'], 1e-9) if p.get('connected') else 0.0 for g, p in zip(post, P)]
    cmed = [p.get('C_med') or 0 if p.get('connected') else 0 for p in P]; cmin = [p.get('C_min') or 0 if p.get('connected') else 0 for p in P]
    nout = [p.get('n_out') or 0 for p in P if p.get('connected')]
    bv = [g['body']['largest_vol'] for g in post]; bc = [g['body']['comps'] for g in post]
    vf = [sum(g.get('vol_on_food') or [0]) for g in post]; ed = [g['vein']['edges'] for g in post]; cy = [g['vein']['cycles'] for g in post]
    lg = [g['vein']['largest'] for g in post]
    med = lambda x: round(float(np.median(x)), 3) if len(x) else None
    d.update(window=f'{ts[0]:.0f}-{ts[-1]:.0f}', n=len(post), same_comp_frac=round(float(np.mean(same)), 2), longest_same=longest(ts, same), conn_frac=round(float(np.mean(conn)), 2),
             minC_over_p90_med=med(rmin90), minC_over_p90_ge1_frac=round(float(np.mean([x >= 1 for x in rmin90])), 2), longest_ge1=longest(ts, [x >= 1 for x in rmin90]),
             path_Cmed_med=med(cmed), path_Cmin_med=med(cmin), path_nout_med=med(nout), body_largest_vol_min=round(min(bv), 3), body_largest_vol_med=med(bv), body_comps_end=bc[-1],
             vol_on_food_med=med(vf), vein_edges_med=med(ed), vein_edges_end=ed[-1], cycles_med=med(cy), vein_largest_med=med(lg))
    rows.append(d)
    print('=== ' + r); print('   ' + ' '.join(f'{k}={v}' for k, v in d.items() if k != 'run'))
    if V:
        print('    t: same|minC/p90|Cmin|Cmed|n_out|largest_vol|comps|vol_on_food|edges|h_food|fM')
        for g, p in zip(post, P):
            print(f'    {g["t"]:4.0f}: {int(bool(p.get("same_vein_comp")))}|{round((p.get("C_min") or 0)/max(g["vein"]["C_p90"],1e-9),2) if p.get("connected") else "-"}|{p.get("C_min")}|{p.get("C_med")}|{p.get("n_out")}|{g["body"]["largest_vol"]}|{g["body"]["comps"]}|{g.get("vol_on_food")}|{g["vein"]["edges"]}|{g.get("h_on_food")}|{g.get("fM")}')
json.dump(rows, open(os.path.join(HERE, 'summ_last.json'), 'w'), indent=1, ensure_ascii=False)
