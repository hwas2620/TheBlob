"""[S24 진단 3] food4 먹이 닿은 시각: 지금 모델(s23c), S23 후보(s23v), 진단 꼬리표(S24 runs) 견줌 (판정 아님).
python3 d2food.py y1 [시드 761 770]"""
import sys, os, json, numpy as np
R23 = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model/runs'; R24 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model', 'runs')
tags = sys.argv[1].split(','); a, b = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (761, 770)
T = 700.0
def tt(R, s, tg):
    f = os.path.join(R, f'b_food4_s{s}_{tg}', 'metrics.json')
    return json.load(open(f))['t_touch'] if os.path.exists(f) else None
fm = lambda v: ' '.join('  -  ' if x is None else f'{x:5.0f}' for x in v)
last = {k: [] for k in ['s23c', 's23v'] + tags}
for s in range(a, b + 1):
    row = {'s23c': tt(R23, s, 's23c'), 's23v': tt(R23, s, 's23v')}
    for tg in tags: row[tg] = tt(R24, s, tg)
    print(f's{s} ' + ' | '.join(f'{k} {fm(v)}' if v else f'{k} (없음)' for k, v in row.items()))
    for k, v in row.items():
        if v: last[k].append(max(T if x is None else x for x in v))
print('마지막 먹이(못 닿으면 700) 중앙값: ' + ', '.join(f'{k} {np.median(v):.0f} (n {len(v)})' for k, v in last.items() if v))
for k in ['s23v'] + tags:
    if len(last[k]) == len(last['s23c']) and last[k]:
        d = np.array(last[k]) - np.array(last['s23c']); print(f'  {k} - s23c: 중앙 {np.median(d):+.1f}  {d.round(0).tolist()}')
