#!/usr/bin/env python3
"""검증자 실행(verify/runs/*/mg_err_series.json)에서 멀티그리드 유량 오차의 분위수를 다시 낸다.
주 세션이 검증 뒤에 덧붙인 집계다(검증자의 것이 아니다). usage: mgerr_p99.py <verify/runs 경로>
mg_err_series.json 의 한 줄은 [t, 유량 오차, ...] 이다. 실행별 원자료(runs/)는 저장소에 넣지 않았다."""
import json, os, sys, numpy as np
S = sys.argv[1]
print('run ncyc n median p90 p99 max frac>0.4')
for n in sorted(os.listdir(S)):
    p = os.path.join(S, n, 'mg_err_series.json'); q = os.path.join(S, n, 'params.json')
    if not (os.path.exists(p) and os.path.exists(q)): continue
    P = json.load(open(q))
    if P.get('solver') != 'mg': continue
    E = np.array(json.load(open(p)))
    if E.size == 0: continue
    e = E[:, 1]
    print('%-20s %d %4d %.3f %.3f %.3f %.3f %.3f' % (n, P.get('ncyc'), len(e), np.median(e), np.percentile(e, 90), np.percentile(e, 99), e.max(), (e > 0.4).mean()))
