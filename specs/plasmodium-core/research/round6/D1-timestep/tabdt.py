#!/usr/bin/env python3
"""[D1] 시간 간격 실험의 표. 실행별 수치는 d1_runs.json 에 모아 두었다(실행 폴더는 저장소에 넣지 않는다).

usage: tabdt.py                 d1_runs.json 으로 표를 찍는다
       tabdt.py --collect R5 D1 S1   실행 폴더에서 d1_runs.json 을 다시 만든다
                                (R5 = 5차 H1 폴더, D1·S1 = 6차 실행 폴더. 각각 runs/<이름>/metrics.json 과 summ/<이름>.json 이 있어야 한다)
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = list(range(21, 27))
# (표시 이름, 폴더 열쇠, 실행 이름 틀)
MIG = [('무늬 없음', [('dt=0.1 멀티 2', 'R5', 'Ym_base_s%d'), ('dt=0.2 멀티 2', 'D1', 'Ym_base_dt2_s%d'), ('dt=0.4 멀티 2', 'D1', 'Ym_base_dt4_s%d')]),
       ('삼각 격자', [('dt=0.1 멀티 2', 'R5', 'Ym_tri96d_s%d'), ('dt=0.2 멀티 2', 'D1', 'Ym_tri_dt2_s%d'), ('dt=0.2 멀티 3', 'D1', 'Ym_tri_dt2_c3_s%d'), ('dt=0.4 멀티 2', 'D1', 'Ym_tri_dt4_s%d'),
                  ('dt=0.4 직접', 'D1', 'Ym_tri_dt4_exact_s%d'), ('dt=0.4 PCG 3', 'S1', 'Ym_tri_dt4_pcg3_s%d'), ('dt=0.4 PCG 4', 'S1', 'Ym_tri_dt4_pcg4_s%d'), ('dt=0.4 PCG 5', 'S1', 'Ym_tri_dt4_pcg5_s%d')])]
FOOD = [('dt=0.1 멀티 2', 'R5', 'Y3_tri96d_s%d'), ('dt=0.2 멀티 2', 'D1', 'Y3_tri_dt2_s%d'), ('dt=0.2 멀티 3', 'D1', 'Y3_tri_dt2_c3_s%d'), ('dt=0.2 멀티 4', 'D1', 'Y3_tri_dt2_c4_s%d'),
        ('dt=0.2 직접', 'D1', 'Y3_tri_dt2_exact_s%d'), ('dt=0.2 PCG 2', 'S1', 'Y3_tri_dt2_pcg2_s%d'), ('dt=0.2 PCG 3', 'S1', 'Y3_tri_dt2_pcg3_s%d'),
        ('dt=0.4 멀티 2', 'D1', 'Y3_tri_dt4_s%d'), ('dt=0.4 직접', 'D1', 'Y3_tri_dt4_exact_s%d'),
        ('dt=0.4 PCG 3', 'S1', 'Y3_tri_dt4_pcg3_s%d'), ('dt=0.4 PCG 4', 'S1', 'Y3_tri_dt4_pcg4_s%d'), ('dt=0.4 PCG 5', 'S1', 'Y3_tri_dt4_pcg5_s%d'), ('dt=0.4 PCG 6', 'S1', 'Y3_tri_dt4_pcg6_s%d')]


def collect(roots):
    out = {}
    names = [(k, p % s) for _, rows in MIG for _, k, p in rows for s in SEEDS] + [(k, p % s) for _, k, p in FOOD for s in SEEDS]
    for key, run in names:
        fs = os.path.join(roots[key], 'summ', run + '.json'); fm = os.path.join(roots[key], 'runs', run, 'metrics.json'); fp = os.path.join(roots[key], 'runs', run, 'params.json')
        if not (os.path.exists(fs) and os.path.exists(fm)): continue
        s = json.load(open(fs)); m = json.load(open(fm)); p = json.load(open(fp))
        r = dict(dt=p['dt'], solver=p['solver'], ncyc=p.get('ncyc'), osc_sub=p.get('osc_sub'), T=p['T'], body=s['body_largest_vol_min'], h_min_in_step=m['h_min_seen'], h_min_end=m.get('h_min_end_of_step'),
                 neg_end_cellsteps=m.get('neg_end_cellsteps'), flux_err=m.get('mg_err'), runtime=m['runtime'])
        if run.startswith('Ym'):
            r.update(vein4=s['vein4_largest_med'], disp=s['disp_track'], t_touch=m['t_touch'][0])
        else:
            r.update(pathminC=s['pathminC_med'], vein_medC=s['vein_medC_med'], t_touch=s['t_touch'], t_exh=m.get('t_exh'))
        out[run] = r
    json.dump(out, open(os.path.join(HERE, 'd1_runs.json'), 'w'), indent=0, ensure_ascii=False)
    print(len(out), '개 실행을 d1_runs.json 에 모았다')


def rng(a, f='%.2f'):
    a = [x for x in a if x is not None]
    return '-' if not a else (f % a[0] if min(a) == max(a) else (f + '~' + f) % (min(a), max(a)))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--collect':
        collect(dict(R5=sys.argv[2], D1=sys.argv[3], S1=sys.argv[4])); return
    R = json.load(open(os.path.join(HERE, 'd1_runs.json')))
    print('이주 (먹이 하나, 192², T=400). 정맥 = 이주 중 정맥 최대 성분(C>4)의 중앙값, 0.8 이상인 시드 수')
    for title, rows in MIG:
        print(f'[{title}]')
        print('  %-14s %3s  %-11s %5s  %-9s %-9s %-9s %-13s %-12s %s' % ('설정', '시드', '정맥', '≥0.8', '이동(셀)', '닿은 시각', '몸', '스텝 안 최소', '스텝 끝 음수', '유량 오차 중앙'))
        for lab, _, pat in rows:
            rs = [R[pat % s] for s in SEEDS if pat % s in R]
            if not rs: continue
            v = [r['vein4'] for r in rs]; fe = [r['flux_err'][0] for r in rs if r['flux_err']]
            print('  %-14s %3d  %-11s %2d/%d  %-9s %-9s %-9s %-13s %-12s %s' % (lab, len(rs), rng(v), sum(x >= 0.8 for x in v), len(v), rng([r['disp'] for r in rs], '%.0f'), rng([r['t_touch'] for r in rs], '%.0f'),
                                                                       rng([r['body'] for r in rs]), rng([r['h_min_in_step'] for r in rs], '%.3f'), rng([r['neg_end_cellsteps'] for r in rs], '%d'), rng(fe, '%.3f')))
    print('\n먹이 셋 + 삼각 격자 (192², 먹는 동안). 굵은 쌍 = 두 먹이 사이 경로의 최소 전도도가 정맥 중앙값의 5배 이상인 쌍')
    print('  %-14s %3s  %-7s %-14s %-10s %-15s %-15s %-13s %s' % ('설정', '시드', '굵은 쌍', '경로 최소 C', '몸', '스텝 안 최소', '스텝 끝 최소', '스텝 끝 음수', '유량 오차 중앙'))
    for lab, _, pat in FOOD:
        rs = [R[pat % s] for s in SEEDS if pat % s in R]
        if not rs: continue
        pc = [x for r in rs for x in r['pathminC'].values()]; thick = sum(x >= 5 * r['vein_medC'] for r in rs for x in r['pathminC'].values()); fe = [r['flux_err'][0] for r in rs if r['flux_err']]
        print('  %-14s %3d  %2d/%-4d %-14s %-10s %-15s %-15s %-13s %s' % (lab, len(rs), thick, len(pc), rng(pc, '%.0f'), rng([r['body'] for r in rs]), rng([r['h_min_in_step'] for r in rs], '%.3f'),
                                                                       rng([r['h_min_end'] for r in rs], '%.3f'), rng([r['neg_end_cellsteps'] for r in rs], '%d'), rng(fe, '%.3f')))


if __name__ == '__main__':
    main()
