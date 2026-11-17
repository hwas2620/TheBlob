#!/usr/bin/env python3
"""[V1] 맥동의 진폭·주기와 시간 간격을 바꾼 탐색의 표. 실행별 수치는 v1_runs.json 에 모아 두었다.

usage: tabspeed.py                    v1_runs.json 으로 표를 찍는다
       tabspeed.py --collect R5 V1    실행 폴더에서 v1_runs.json 을 다시 만든다 (R5 = 5차 H1 폴더, V1 = 이 실험의 실행 폴더)
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = [21, 22, 23]
# (표시 이름, 폴더 열쇠, 이름 틀에 넣을 꼬리표)
ROWS = [('기준: dt 0.1, 진폭 0.1, 주기 4', 'R5', 'tri96d'),
        ('진폭 0.2 · 직접 풀이', 'V1', 'tri_E2x'), ('진폭 0.2', 'V1', 'tri_E2'),
        ('주기 2 · 직접 풀이', 'V1', 'tri_P2x'), ('주기 2', 'V1', 'tri_P2'),
        ('진폭 0.05', 'V1', 'tri_e05'),
        ('dt 0.2, 진폭 0.05', 'V1', 'tri_dt2e05'), ('dt 0.2, 주기 8', 'V1', 'tri_dt2p8'),
        ('dt 0.4, 진폭 0.025', 'V1', 'tri_dt4e025'), ('dt 0.4, 주기 16', 'V1', 'tri_dt4p16')]


def collect(roots):
    out = {}
    for _, key, tag in ROWS:
        for pre in ('Ym', 'Y3'):
            for s in SEEDS:
                run = f'{pre}_{tag}_s{s}'
                fs = os.path.join(roots[key], 'summ', run + '.json'); fm = os.path.join(roots[key], 'runs', run, 'metrics.json'); fp = os.path.join(roots[key], 'runs', run, 'params.json')
                if not (os.path.exists(fs) and os.path.exists(fm)): continue
                S = json.load(open(fs)); m = json.load(open(fm)); p = json.load(open(fp))
                r = dict(dt=p['dt'], eps=p['eps'], period=p['period'], solver=p['solver'], ncyc=p.get('ncyc'), osc_sub=p.get('osc_sub'), body=S['body_largest_vol_min'],
                         h_min_in_step=m['h_min_seen'], h_min_end=m.get('h_min_end_of_step'), neg_end_cellsteps=m.get('neg_end_cellsteps'), flux_err=m.get('mg_err'))
                if pre == 'Ym':
                    tr = m['traj']; d = lambda t: next((float(np.hypot(a[1] - 95.5, a[2] - 95.5)) for a in tr if abs(a[0] - t) < 1e-6), None)
                    r.update(vein4=S['vein4_largest_med'], d200=d(200), d300=d(300), t_touch=m['t_touch'][0])
                else:
                    r.update(pathminC=S['pathminC_med'], vein_medC=S['vein_medC_med'], t_touch=S['t_touch'])
                out[run] = r
    json.dump(out, open(os.path.join(HERE, 'v1_runs.json'), 'w'), indent=0, ensure_ascii=False)
    print(len(out), '개 실행을 v1_runs.json 에 모았다')


def rng(a, f='%.2f'):
    a = [x for x in a if x is not None]
    return '-' if not a else (f % a[0] if min(a) == max(a) else (f + '~' + f) % (min(a), max(a)))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--collect':
        collect(dict(R5=sys.argv[2], V1=sys.argv[3])); return
    R = json.load(open(os.path.join(HERE, 'v1_runs.json')))
    print('풀이는 따로 적지 않으면 멀티그리드 2사이클. 192², 삼각 격자 무늬 P=96.')
    print('\n이주 (먹이 하나, T=400)')
    print('  %-30s %3s  %-10s %-8s %-8s %-9s %-10s %-13s %-10s %s' % ('설정', '시드', '정맥', 't=200', 't=300', '닿은 시각', '몸', '스텝 안 최소', '스텝끝 음수', '유량 오차 중앙'))
    for lab, _, tag in ROWS:
        rs = [R[f'Ym_{tag}_s{s}'] for s in SEEDS if f'Ym_{tag}_s{s}' in R]
        if not rs: continue
        fe = [r['flux_err'][0] for r in rs if r['flux_err']]
        print('  %-30s %3d  %-10s %-8s %-8s %-9s %-10s %-13s %-10s %s' % (lab, len(rs), rng([r['vein4'] for r in rs]), rng([r['d200'] for r in rs], '%.0f'), rng([r['d300'] for r in rs], '%.0f'), rng([r['t_touch'] for r in rs], '%.0f'),
                                                                   rng([r['body'] for r in rs]), rng([r['h_min_in_step'] for r in rs], '%.3f'), rng([r['neg_end_cellsteps'] for r in rs], '%d'), rng(fe, '%.3f')))
    print('\n대칭 먹이 셋 (T=480). 굵은 쌍 = 두 먹이 사이 경로의 최소 전도도가 정맥 중앙값의 5배 이상인 쌍')
    print('  %-30s %3s  %-7s %-12s %-10s %-15s %-15s %s' % ('설정', '시드', '굵은 쌍', '경로 최소 C', '몸', '스텝 안 최소', '스텝 끝 최소', '유량 오차 중앙'))
    for lab, _, tag in ROWS:
        rs = [R[f'Y3_{tag}_s{s}'] for s in SEEDS if f'Y3_{tag}_s{s}' in R]
        if not rs: continue
        pc = [x for r in rs for x in r['pathminC'].values()]; thick = sum(x >= 5 * r['vein_medC'] for r in rs for x in r['pathminC'].values()); fe = [r['flux_err'][0] for r in rs if r['flux_err']]
        print('  %-30s %3d  %2d/%-4d %-12s %-10s %-15s %-15s %s' % (lab, len(rs), thick, len(pc), rng(pc, '%.0f'), rng([r['body'] for r in rs]), rng([r['h_min_in_step'] for r in rs], '%.3f'), rng([r['h_min_end'] for r in rs], '%.3f'), rng(fe, '%.3f')))


if __name__ == '__main__':
    main()
