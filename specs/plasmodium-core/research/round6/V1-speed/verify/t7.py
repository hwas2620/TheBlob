#!/usr/bin/env python3
"""[검증자] T7: 유량 오차를 재는 스텝의 위상에 따라 오차가 달라지는가. 같은 시드(61)의 실행을 check_every=20(스텝 mod 40 이 0, 20 뿐)과 check_every=7(40 위상 모두)로 견준다.
계산은 같고(검산은 풀이에 영향을 주지 않는다) 표본만 다르다. 먼저 두 실행의 다른 지표가 같은지 확인한다."""
import json, numpy as np, os
HERE = os.path.dirname(os.path.abspath(__file__))
for tag in ('Ym', 'Y3'):
    for st in ('base', 'cand'):
        a = '%s_%s_s61' % (tag, st); b = a + 'k7'
        if not os.path.exists(os.path.join(HERE, 'runs', b, 'metrics.json')): print(b, '(아직 없음)'); continue
        Ma = json.load(open(os.path.join(HERE, 'runs', a, 'metrics.json'))); Mb = json.load(open(os.path.join(HERE, 'runs', b, 'metrics.json')))
        same = all(Ma[k] == Mb[k] for k in ('h_min_seen', 'h_min_end_of_step', 'neg_end_cellsteps', 't_touch', 'area_end', 'traj', 'V_end'))
        ea = np.array(json.load(open(os.path.join(HERE, 'runs', a, 'mg_err_series.json')))); eb = np.array(json.load(open(os.path.join(HERE, 'runs', b, 'mg_err_series.json'))))
        ph = (eb[:, 0].astype(int) % 40); binmed = np.array([np.median(eb[ph == p, 1]) for p in range(40)])
        q = lambda e: '중앙 %.3f, 90%% %.3f, 최대 %.3f (n=%d)' % (np.median(e[:, 1]), np.percentile(e[:, 1], 90), e[:, 1].max(), len(e))
        print('%s: 다른 지표 동일 %s | 20스텝마다: %s | 7스텝마다: %s | 위상 칸(스텝 mod 40)별 중앙값의 범위 %.3f~%.3f (칸 0: %.3f, 칸 20: %.3f, 가장 큰 칸 %d) | 0.15 넘는 표본 비율 20스텝 %.2f, 7스텝 %.2f' % (
            a, same, q(ea), q(eb), binmed.min(), binmed.max(), binmed[0], binmed[20], int(np.argmax(binmed)), (ea[:, 1] > 0.15).mean(), (eb[:, 1] > 0.15).mean()))
