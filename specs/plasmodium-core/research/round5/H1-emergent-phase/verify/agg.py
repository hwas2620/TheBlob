#!/usr/bin/env python3
"""[verify5] 변형별 집계(작성자 주장 M0/M4/M5/M6 의 수치와 같은 정의). usage: agg.py ROOT seeds(쉼표) Ym이름틀 ... 
ROOT = summ/ 와 runs/ 가 있는 폴더. 이름틀 예: base wave tri96d n03T320 (Ym_<틀>_s<시드>, Y3_<틀>_s<시드>)
'굵은 쌍' = 경로 최소 C(쌍별 창 중앙값) >= 5 x 그 실행의 정맥 중앙 C(창 중앙값)."""
import json, sys, os, numpy as np
ROOT = sys.argv[1]; seeds = [int(x) for x in sys.argv[2].split(',')]; variants = sys.argv[3:]
def S(r):
    f = os.path.join(ROOT, 'summ', r + '.json'); return json.load(open(f)) if os.path.exists(f) else None
def M(r):
    f = os.path.join(ROOT, 'runs', r, 'metrics.json'); return json.load(open(f)) if os.path.exists(f) else None
f2 = lambda a: ' '.join('%.2f' % x for x in a)
rng = lambda a, fmt='%.2f': (fmt + '~' + fmt) % (min(a), max(a)) if len(a) else '-'
out = {}
base = {s: (S('Ym_base_s%d' % s), M('Ym_base_s%d' % s)) for s in seeds}
print('=== Ym (t>=200)')
for v in variants:
    ss = [s for s in seeds if S('Ym_%s_s%d' % (v, s)) and M('Ym_%s_s%d' % (v, s))]
    if not ss: continue
    o = [S('Ym_%s_s%d' % (v, s)) for s in ss]; m = [M('Ym_%s_s%d' % (v, s)) for s in ss]
    v4 = [x['vein4_largest_med'] for x in o]; v10 = [x['vein10_largest_med'] for x in o]; v30 = [x['vein30_largest_med'] for x in o]; cyc = [x['cycles4_med'] for x in o]
    disp = [x['disp_track'] for x in o]; tt = [y['t_touch'][0] for y in m]; hm = [y['h_min_seen'] for y in m]
    print(f"{v:10s} 시드 {ss}")
    print(f"   정맥최대 C>4: {f2(v4)} | 범위 {rng(v4)} 중앙 {np.median(v4):.3f} | >=0.8: {sum(x >= 0.8 for x in v4)}/{len(v4)} >=0.85: {sum(x >= 0.85 for x in v4)}/{len(v4)}")
    print(f"   C>10: {f2(v10)} (중앙 {np.median(v10):.2f}) | C>30: {f2(v30)} (중앙 {np.median(v30):.2f}) | 순환: {' '.join('%d' % c for c in cyc)} (중앙 {np.median(cyc):.0f})")
    print(f"   이동: {' '.join('%.1f' % d for d in disp)} | 닿은 시각: {' '.join(str(t) for t in tt)} | 스텝 안 최소 두께 {rng(hm, '%.3f')} | 몸 최대(창 최소) {rng([x['body_largest_vol_min'] for x in o])} | 조각(끝) {' '.join(str(x['body_ncomp_end']) for x in o)}")
    if v != 'base' and all(base[s][0] for s in ss):
        dv = [a - base[s][0]['vein4_largest_med'] for a, s in zip(v4, ss)]
        dd = [a - base[s][0]['disp_track'] for a, s in zip(disp, ss)]
        ok = [(t, base[s][1]['t_touch'][0]) for t, s in zip(tt, ss)]
        dt_ = [100 * (t / b - 1) if (t and b) else float('nan') for t, b in ok]
        print(f"   base 대비: 정맥최대 차 {f2(dv)} (base 보다 높은 시드 {sum(x > 0 for x in dv)}/{len(dv)}) | 이동 차 {' '.join('%+.1f' % x for x in dd)} (범위 {min(dd):+.1f}~{max(dd):+.1f}, 양수 {sum(x > 0 for x in dd)}/{len(dd)}, 중앙 {np.median(dd):+.1f})")
        print(f"            닿는 시각 차 % {' '.join('%+.1f' % x for x in dt_)} (범위 {np.nanmin(dt_):+.1f}~{np.nanmax(dt_):+.1f}, 중앙 {np.nanmedian(dt_):+.1f})")
print('=== Y3 (먹는 동안)')
for v in variants:
    ss = [s for s in seeds if S('Y3_%s_s%d' % (v, s))]
    if not ss: continue
    o = [S('Y3_%s_s%d' % (v, s)) for s in ss]
    same = [x for y in o for x in y.get('same4', {}).values()]; same10 = [x for y in o for x in y.get('same10', {}).values()]; pc = [x for y in o for x in y.get('pathminC_med', {}).values()]
    thick = [x >= 5 * y['vein_medC_med'] for y in o for x in y.get('pathminC_med', {}).values()]
    bd = [y.get('body_largest_vol_min', float('nan')) for y in o]; hm = [y['m_h_min_seen'] for y in o]; mg = [y['m_mg_err'][2] for y in o]; ne = [y['m_neg_end_cellsteps'] for y in o]
    tt = [y['t_touch'] for y in o]
    print(f"{v:10s} 시드 {ss}")
    print(f"   같은 성분(C>4)>=0.9 쌍 {sum(x >= 0.9 for x in same)}/{len(same)} (C>10: {sum(x >= 0.9 for x in same10)}/{len(same10)}) | 값: {' '.join('/'.join('%g' % x for x in y.get('same4', {}).values()) for y in o)}")
    print(f"   경로 최소 C 범위 {rng(pc, '%.0f')} 중앙 {np.median(pc):.0f} | 값: {' '.join('/'.join('%.0f' % x for x in y.get('pathminC_med', {}).values()) for y in o)} | 정맥 중앙 C: {' '.join('%.1f' % y['vein_medC_med'] for y in o)}")
    print(f"   굵은 쌍(>=5x 정맥 중앙) {sum(thick)}/{len(thick)} | 몸 최대(창 최소): {f2(bd)} (<0.9: {sum(b < 0.9 for b in bd)}/{len(bd)}, <0.95: {sum(b < 0.95 for b in bd)}/{len(bd)})")
    print(f"   스텝 안 최소 두께: {' '.join('%.3f' % x for x in hm)} (최소 {min(hm):.3f}, < -0.1: {sum(x < -0.1 for x in hm)}/{len(hm)}) | 스텝 끝 음수 셀·스텝: {' '.join(str(x) for x in ne)} | 유량 오차 최대 {rng(mg)}")
    print(f"   닿은 시각: {' '.join('/'.join('%.0f' % t if t is not None else '-' for t in x) for x in tt)}")
