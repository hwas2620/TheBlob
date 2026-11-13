#!/usr/bin/env python3
"""마지막 평가 시점의 구역별(전진면 쪽 1/3 = front, 가운데 = mid, 뒤 1/3 = rear; 나이 기준) 정맥 지표와 공통 eval 결과를 표로 낸다.
사용: zones.py RUN1 RUN2 ...  (출력: 마크다운 표)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
hdr = ['run', 't', 'n', 'dens', 'BP', 'loops', 'largest', 'w10/w50/w90', 'wr', 'sr',
       'skel/1000px F|M|R', 'BP/1e4px F|M|R', 'w_med F|M|R', 'str_med F|M|R', 'eval BP', 'eval wr', 'eval sr', 'eval lg', 'all3']
print('| ' + ' | '.join(hdr) + ' |'); print('|' + '---|' * len(hdr))
for nm in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', nm)
    try:
        C = json.load(open(os.path.join(d, 'curve.json')))['curve']
    except Exception as e:
        print(f'| {nm} | (없음: {e}) |'); continue
    m = C[-1]; z = m.get('zones', {})
    def trip(k):
        return ' / '.join(str(z.get(q, {}).get(k, '-')) for q in ('front', 'mid', 'rear'))
    ev = {}
    try:
        ev = json.load(open(os.path.join(d, 'eval.json'))).get('primary', {})
    except Exception:
        pass
    row = [nm, m['t'], m.get('n', '-'), m.get('dens', '-'), m.get('branch_points'), m.get('loops'), m.get('vein_largest_frac'),
           f"{m.get('width_p10')}/{m.get('width_p50')}/{m.get('width_p90')}", m.get('width_ratio_p90_p10'), m.get('strength_ratio_p90_p10'),
           trip('skel_per_1000px'), trip('bp_per_1e4px'), trip('width_median'), trip('strength_median'),
           ev.get('branch_points'), ev.get('width_ratio_p90_p10'), ev.get('strength_ratio_p90_p10'), ev.get('vein_largest_frac'),
           (ev.get('verdict') or {}).get('all_three')]
    print('| ' + ' | '.join(str(x) for x in row) + ' |')
