#!/usr/bin/env python3
"""[verify] 실험자가 저장한 state_t*.npz 에서 내 지표(vmet.py)를 계산해, 같은 시각의 실험자 gseries 값과 나란히 찍는다."""
import json, os, sys, numpy as np, vmet
HERE = os.path.dirname(os.path.abspath(__file__)); nbad = 0; ncmp = 0
for run in sys.argv[1:]:
    rd = os.path.join(HERE, '..', 'runs', run)
    states, G, P = vmet.load_states(rd); met = json.load(open(os.path.join(rd, 'metrics.json')))
    gs = {round(g['t']): g for g in met['gseries']}
    for g in met.get('full', {}).values(): gs.setdefault(round(g['t']), g)      # 스냅숏 시각의 값(graphm.full 의 quick 부분)
    for S in states:
        r = vmet.analyse_state(S, G, P); g = gs.get(round(r['t']))
        if g is None: continue
        line = [f"{run} t={r['t']:.0f}", f"정맥최대 {r['vein4_largest']:.3f}|{g['vein']['largest']:.3f}", f"순환 {r['vein4_cycles']}|{g['vein']['cycles']}", f"간선 {r['vein4_E']}|{g['vein']['edges']}",
                f"몸최대부피 {r['body_largest_vol']:.3f}|{g['body']['largest_vol']:.3f}", f"몸조각 {r['body_ncomp']}|{g['body']['comps']}"]
        ok = abs(r['vein4_largest'] - g['vein']['largest']) < 2e-3 and r['vein4_cycles'] == g['vein']['cycles'] and abs(r['body_largest_vol'] - g['body']['largest_vol']) < 2e-3
        for k, d in r['pairs'].items():
            gp = g.get('path', {}).get(k, {})
            mine = (d['path'] or {}).get('minC', float('nan')); his = gp.get('C_min', float('nan')) if gp.get('connected') else float('nan')
            line.append(f"{k}: 같은성분 {int(d['same4'])}|{int(bool(gp.get('same_vein_comp')))} 경로최소C {mine:.1f}|{his if his==his else float('nan'):.1f} 병목 {d['bottleneck']:.1f}")
            ok = ok and (d['same4'] == bool(gp.get('same_vein_comp'))) and (abs(mine - his) <= 0.02 * max(abs(his), 1) or (mine != mine and his != his))
        ncmp += 1; nbad += (not ok)
        print(('OK  ' if ok else 'DIFF') + ' ' + ' '.join(line))
print(f'비교 {ncmp}건 중 불일치 {nbad}건 (형식: 내 값|실험자 값)')
