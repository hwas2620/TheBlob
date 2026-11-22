#!/usr/bin/env python3
"""판정 밖의 덧붙임 (CRITERIA_CHANGES.md). data/extra.json 을 쓰고 글을 표준 출력에 낸다.

1. 주장 3 을 큰 몸(부피가 가장 큰 젖은 성분)에만 재기: 대조의 떨어진 부스러기가 '죽은 실'·'끝 줄'로 세어지는지
2. 주장 2 를 한 주기 평균 두께(hmean)로 재기: 맥동으로 0.5 를 잠깐 넘는 관(cap 0.5 × 1.1)을 굵은 칸에서 빼기
3. 주장 2: 큰 덩이 둘 이상이 어디든(찢어진 조각 포함) 있는 비율, 시각 구간별 D2 비율
4. 대조가 크게 찢어지는 시각 (떨어진 부피 > 5% 가 처음인 저장 상태)
5. 먼 먹이 시험 (v16c_far, v16gh_far)
6. long 의 몸 모양 (넓이, 굵은 부피 비율, 이동, 정맥 간선)
"""
import glob, json, os, sys
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlib as V
import judge_lib as J

VER = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SEEDS = range(271, 283)


def per_run(job):
    seed, tag = job
    d = V.run_dir('long', seed, tag); out = dict(seed=seed, tag=tag); rows = []
    for S in V.load_vs(d):
        t = float(S['t'])
        wet = S['wet'].astype(bool); h = S['h'].astype(float); hm = S['hmean'].astype(float)
        r = dict(t=t)
        hh = np.where(hm > 0, hm, h)
        db = V.dumbbell(wet, hh, 0.5, 0.05); r['D2_hmean'] = db['D2']; r['D1_hmean'] = db['D1']
        if t >= 1500 - 1e-6:
            lab, nc = V.torus_label(wet)
            if nc > 1:
                vol = np.bincount(lab.ravel(), weights=np.where(wet, h, 0).ravel()); vol[0] = 0; main = lab == int(np.argmax(vol))
            else: main = wet
            S2 = dict(S); S2['wet'] = main
            lc = V.late_cells(S2); r.update({f'main_{k}': lc[k] for k in ('film', 'dead', 'endline', 'area')})
        rows.append(r)
    m = lambda k, t0, t1: float(np.mean([r[k] for r in rows if t0 - 1e-6 <= r['t'] <= t1 + 1e-6 and k in r]))
    for k in ('main_film', 'main_dead', 'main_endline', 'main_area'): out[k] = m(k, 1500, 2000)
    for k in ('D2_hmean', 'D1_hmean'): out['f_' + k] = m(k, 200, 2000); out['f_' + k + '_late'] = m(k, 1000, 2000)
    return out


if __name__ == '__main__':
    R = json.load(open(os.path.join(VER, 'data', 'summary.json'))); BY = {(r['scn'], r['seed'], r['tag']): r for r in R}
    with Pool(4) as p: res = p.map(per_run, [(s, t) for s in SEEDS for t in ('v16c', 'v16gh')])
    E = {}; P = []; pr = lambda *a: P.append(' '.join(str(x) for x in a))
    RB = {(r['seed'], r['tag']): r for r in res}

    def cmp(get, label, floor=0.0):
        c = np.array([get('v16c', s) for s in SEEDS], float); g = np.array([get('v16gh', s) for s in SEEDS], float); d = g - c
        pl, pg = J.signflip(d)
        E[label] = dict(ctrl=float(c.mean()), cand=float(g.mean()), p_less=pl, p_greater=pg, per_seed={s: [round(float(a), 3), round(float(b), 3)] for s, a, b in zip(SEEDS, c, g)})
        pr(f'  {label:34s} 대조 {c.mean():8.3f} → 후보 {g.mean():8.3f}   p(적음)={pl:.4f} p(많음)={pg:.4f}')

    pr('1. 주장 3 을 큰 몸에만 (t 1500~2000 평균 칸 수)')
    for k in ('main_film', 'main_dead', 'main_endline', 'main_area'): cmp(lambda tg, s, k=k: RB[(s, tg)][k], k)
    cmp(lambda tg, s: RB[(s, tg)]['main_endline'] / RB[(s, tg)]['main_area'], 'main_endline_per_area')
    cmp(lambda tg, s: RB[(s, tg)]['main_dead'] / RB[(s, tg)]['main_area'], 'main_dead_per_area')
    pr('2. 주장 2 를 한 주기 평균 두께로 (굵음 = hmean > 0.5)')
    for k in ('f_D2_hmean', 'f_D2_hmean_late', 'f_D1_hmean', 'f_D1_hmean_late'): cmp(lambda tg, s, k=k: RB[(s, tg)][k], k)
    pr('3. 주장 2: 큰 덩이 둘 이상이 어디든 (찢어진 조각 포함), 그리고 시각 구간별 D2 인 저장 상태 비율')
    LR = {(s, tg): json.load(open(os.path.join(VER, 'data', 'long_rows', f'b_long_s{s}_{tg}.json'))) for s in SEEDS for tg in ('v16c', 'v16gh')}
    cmp(lambda tg, s: np.mean([r['nbig_main'] >= 2 for r in LR[(s, tg)] if r['t'] >= 200]), 'f_nbig2_anywhere')
    for t0 in range(200, 2000, 300):
        cmp(lambda tg, s, t0=t0: np.mean([r['D2_main'] for r in LR[(s, tg)] if t0 <= r['t'] < t0 + 300 + (1 if t0 + 300 >= 2000 else 0)]), f'f_D2 t{t0}~{min(t0 + 300, 2000)}')
    pr('4. 대조가 크게 찢어지는 시각 (떨어진 부피 > 5% 가 처음인 저장 상태), 그리고 그때 떨어진 부피')
    tear = {}
    for s in SEEDS:
        rr = [r for r in LR[(s, 'v16c')] if r['detached_frac'] > 0.05]
        tear[s] = [rr[0]['t'], round(rr[0]['detached_frac'], 3)] if rr else None
    E['ctrl_tear'] = tear; pr('  ', tear)
    pr('5. 먼 먹이 시험 (food3, 먹이 거리 75)')
    far = [r for r in R if r['tag'] in ('v16c_far', 'v16gh_far')]
    if far:
        pass
    E_far = J.far_food(VER)
    if E_far:
        E['far'] = E_far
        x = E_far['t_all']
        pr(f"  t_all 대조 {x['ctrl_mean']:.1f} → 후보 {x['cand_mean']:.1f}  나빠짐 평균 {x['d_worse_mean']:+.1f}  90%CI [{x['ci90'][0]:+.1f}, {x['ci90'][1]:+.1f}]  δ {x['delta']:.1f}  p(나빠짐)={x['p_worse']:.3f}  → {x['verdict']}")
        pr('   시드별 [대조, 후보]:', x['per_seed'])
        pr('   놓친 먹이 [대조, 후보]:', E_far['missed'], ' t_first:', E_far['t_first']['ctrl_mean'], '→', E_far['t_first']['cand_mean'], E_far['t_first']['verdict'])
        pr('   후보 규칙이 일한 양 [시드, ret, conn, hang, sup]:', E_far['activity'])
        pr('   건강(후보) [시드, neg_end, mass_err, V_crumb, comps_end]:', E_far['health'])
    pr('6. long 의 몸 모양')
    for k in ('late_area', 'late_thick_frac', 'late_vein_edges', 'disp', 'path_len', 'area_end'):
        cmp(lambda tg, s, k=k: BY[('long', s, tg)][k], k)
    json.dump(E, open(os.path.join(VER, 'data', 'extra.json'), 'w'), indent=1, ensure_ascii=False, default=float)
    print('\n'.join(P))
