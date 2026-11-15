#!/usr/bin/env python3
"""[H1] 변형별 요약(시드 묶음). usage: cmp6.py s1,s2,... VAR ..."""
import json, sys, numpy as np, os
seeds = [int(x) for x in sys.argv[1].split(',')]
def g(r, k):
    f = 'summ/%s.json' % r
    return json.load(open(f))[k] if os.path.exists(f) else None
f2 = lambda a: ' '.join('%.2f' % x for x in a)
print('--- 이주 (t>=200): 정맥 최대 성분 C>4 | C>30 | 순환 | 이동(셀) | 목표에 닿은 시각 | 몸 최대 성분')
for v in sys.argv[2:]:
    S = [s for s in seeds if g('Ym_%s_s%d' % (v, s), 'run')]
    if not S: continue
    a = [g('Ym_%s_s%d' % (v, s), 'vein4_largest_med') for s in S]; b = [g('Ym_%s_s%d' % (v, s), 'vein30_largest_med') for s in S]
    c = [g('Ym_%s_s%d' % (v, s), 'cycles4_med') for s in S]; d = [g('Ym_%s_s%d' % (v, s), 'disp_track') for s in S]
    t = [json.load(open('runs/Ym_%s_s%d/metrics.json' % (v, s)))['t_touch'][0] for s in S]; bd = [g('Ym_%s_s%d' % (v, s), 'body_largest_vol_min') for s in S]
    print('%-10s %s (중앙 %.2f, >=0.85: %d/%d) | %s (중앙 %.2f) | %s | %s | %s | %.2f~%.2f' % (v, f2(a), np.median(a), sum(x >= 0.85 for x in a), len(a), f2(b), np.median(b), ' '.join('%d' % x for x in c), ' '.join('%.0f' % x for x in d), ' '.join('%.0f' % (x if x else -1) for x in t), min(bd), max(bd)))
print('--- 먹이 셋 (먹는 동안): 같은 성분(C>4)>=0.9 인 쌍 | 경로 최소 C 범위(중앙) | 5x 정맥 중앙 넘는 쌍 | 몸 최대 성분 최소 | 둘째 먹이에 닿은 시각 | 스텝 안 최소 두께 | 유량 오차 최대')
for v in sys.argv[2:]:
    S = [s for s in seeds if g('Y3_%s_s%d' % (v, s), 'run')]
    if not S: continue
    same = [x for s in S for x in g('Y3_%s_s%d' % (v, s), 'same4').values()]; pc = [x for s in S for x in g('Y3_%s_s%d' % (v, s), 'pathminC_med').values()]
    thick = sum(x >= 5 * g('Y3_%s_s%d' % (v, s), 'vein_medC_med') for s in S for x in g('Y3_%s_s%d' % (v, s), 'pathminC_med').values())
    bd = [g('Y3_%s_s%d' % (v, s), 'body_largest_vol_min') for s in S]; tt = [g('Y3_%s_s%d' % (v, s), 't_touch')[1] for s in S]
    hm = [g('Y3_%s_s%d' % (v, s), 'm_h_min_seen') for s in S]; mg = [g('Y3_%s_s%d' % (v, s), 'm_mg_err')[2] for s in S]
    print('%-10s %d/%d | %.0f~%.0f (%.0f) | %d/%d | %s | %s | %.3f~%.3f | %.2f~%.2f' % (v, sum(x >= 0.9 for x in same), len(same), min(pc), max(pc), np.median(pc), thick, len(pc), f2(bd), ' '.join('%.0f' % x for x in tt), min(hm), max(hm), min(mg), max(mg)))
