#!/usr/bin/env python3
"""[verify5] 부작용 집계: 스텝 안 최소 두께, 스텝 끝 최소 두께·음수 셀·스텝, 멀티그리드 유량 오차(중앙/p99/최대, 굵은 간선 C>100 의 중앙/최대), 몸 조각 수(끝), 부피 오차.
usage: side2.py ROOT seeds 시험(Ym|Y3|..) 변형 ..."""
import json, sys, os, numpy as np
ROOT = sys.argv[1]; seeds = [int(x) for x in sys.argv[2].split(',')]; test = sys.argv[3]
for v in sys.argv[4:]:
    R = []
    for s in seeds:
        d = os.path.join(ROOT, 'runs', f'{test}_{v}_s{s}')
        if not os.path.exists(d + '/metrics.json'): continue
        m = json.load(open(d + '/metrics.json')); e = np.array(json.load(open(d + '/mg_err_series.json')))
        last = m['full'][sorted(m['full'])[-1]] if m.get('full') else {}
        R.append(dict(s=s, hmin=m['h_min_seen'], hend=m['h_min_end_of_step'], negend=m['neg_end_cellsteps'], negin=m['neg_cellsteps'], mass=m['mass_err_max'],
                      med=float(np.median(e[:, 1])), p99=float(np.percentile(e[:, 1], 99)), mx=float(e[:, 1].max()), tmed=float(np.median(e[:, 2])), tmx=float(e[:, 2].max()), n=len(e),
                      frac03=float((e[:, 1] > 0.3).mean()), comps=(last.get('body') or {}).get('comps')))
    if not R: continue
    g = lambda k: [r[k] for r in R]
    print(f"{test} {v:9s} n={len(R)} | 스텝 안 최소 두께 {min(g('hmin')):+.3f}~{max(g('hmin')):+.3f} (< -0.1: {sum(x < -0.1 for x in g('hmin'))}, < -0.05: {sum(x < -0.05 for x in g('hmin'))}) | 스텝 끝 최소 {min(g('hend')):+.3f} | 스텝 끝 음수 셀·스텝 중앙 {np.median(g('negend')):.0f} 범위 {min(g('negend'))}~{max(g('negend'))} (>100 인 실행 {sum(x > 100 for x in g('negend'))}) | 스텝 안 음수 셀·스텝 중앙 {np.median(g('negin')):.0f}"
          f" | 유량 오차 중앙 {np.median(g('med')):.3f} ({min(g('med')):.3f}~{max(g('med')):.3f}) p99 {np.median(g('p99')):.2f} ({min(g('p99')):.2f}~{max(g('p99')):.2f}) 최대 {np.median(g('mx')):.2f} ({min(g('mx')):.2f}~{max(g('mx')):.2f}) >0.3 인 점검 비율 {100*np.mean(g('frac03')):.2f}% | 굵은 간선 오차 중앙 {np.median(g('tmed')):.3f} 최대 {max(g('tmx')):.2f} | 몸 조각(끝) 중앙 {np.median([c for c in g('comps') if c is not None]):.0f} ({min(c for c in g('comps') if c is not None)}~{max(c for c in g('comps') if c is not None)}) | 부피 오차 최대 {max(g('mass')):.1e}")
