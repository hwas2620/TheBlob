#!/usr/bin/env python3
"""[verify] 실험자 metrics.json 의 gseries(20 간격)에서 내 창 정의로 쌍별 요약을 다시 낸다(실험자 summ3.py 를 쓰지 않음).
gseries 값 자체는 cmp_exp.py 로 저장 상태 75건에서 내 계산과 같음을 확인했다. usage: gs_exp.py RUN ..."""
import json, os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for r in sys.argv[1:]:
    m = json.load(open(os.path.join(HERE, '..', 'runs', r, 'metrics.json'))); gs = m['gseries']; tt = m['t_touch']
    if any(v is None for v in tt): print(r, '닿지 못한 먹이 있음', tt); continue
    ex = [v for v in m['t_exh'] if v is not None]; t1 = min(ex) if ex else 1e9; t0 = max(tt) + 20
    W = [g for g in gs if t0 <= g['t'] <= t1]
    keys = sorted(W[0]['path']); same = {}; cmin = {}
    for k in keys:
        same[k] = round(float(np.mean([bool(g['path'][k].get('same_vein_comp')) for g in W])), 2)
        cmin[k] = round(float(np.median([(g['path'][k].get('C_min') or 0) if g['path'][k].get('connected') else 0 for g in W])), 0)
    cmin_all = [(g['path'][k].get('C_min') or 0) for g in W for k in keys]
    print(f"{r:24s} 창 {W[0]['t']:.0f}-{W[-1]['t']:.0f}({len(W)}) 같은성분 {list(same.values())} 경로최소C 중앙 {list(cmin.values())} (전체 표본 q25/중앙/q75 {np.percentile(cmin_all,25):.0f}/{np.median(cmin_all):.0f}/{np.percentile(cmin_all,75):.0f}) 정맥최대 중앙 {np.median([g['vein']['largest'] for g in W]):.2f} 몸최대부피 최소 {min(g['body']['largest_vol'] for g in W):.3f} "
          f"| hmin {m['h_min_seen']:.4f} 끝hmin {m.get('h_min_end_of_step')} 끝음수 {m.get('neg_end_cellsteps')} 음수 {m.get('neg_cellsteps')} | mg {[round(x,3) for x in m['mg_err']] if m.get('mg_err') else None}")
