#!/usr/bin/env python3
"""CRITERIA.md 대로 판정한다. data/summary.json 을 읽어 data/verdict.json 을 쓰고 판정 글을 표준 출력에 낸다.

usage: judge.py > logs/judge_out.txt
"""
import itertools, json, os
import numpy as np

VER = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
R = json.load(open(os.path.join(VER, 'data', 'summary.json')))
BY = {(r['scn'], r['seed'], r['tag']): r for r in R}
OK, BAD, UNK = '맞음', '틀림', '판정 못 함'


def pairs(scn, key):
    seeds = sorted({r['seed'] for r in R if r['scn'] == scn and r['tag'] == 'v16c'})
    c = []; g = []; s_ = []
    for s in seeds:
        a = BY.get((scn, s, 'v16c')); b = BY.get((scn, s, 'v16gh'))
        if a is None or b is None or a.get(key) is None or b.get(key) is None: continue
        c.append(float(a[key])); g.append(float(b[key])); s_.append(s)
    return np.array(c), np.array(g), s_


def signflip(d):
    """한쪽 p 두 개: (p(평균 ≤ 관측), p(평균 ≥ 관측)), 모든 2^n 부호"""
    n = d.size
    if n == 0: return 1.0, 1.0
    S = np.array(list(itertools.product((-1, 1), repeat=n)))
    m = (S * np.abs(d)).mean(1); o = d.mean(); e = 1e-12
    return float((m <= o + e).mean()), float((m >= o - e).mean())


def boot(d):
    rng = np.random.default_rng(0); idx = rng.integers(0, d.size, (10000, d.size))
    mm = d[idx].mean(1)
    return float(np.percentile(mm, 5)), float(np.percentile(mm, 95))


def fewer(scn, key, floor):
    """주장 2·3: 후보가 대조보다 적은가"""
    c, g, s = pairs(scn, key); d = g - c
    pl, pg = signflip(d)
    out = dict(key=key, n=len(s), ctrl_mean=float(c.mean()), cand_mean=float(g.mean()), d_mean=float(d.mean()), p_less=pl, p_greater=pg,
               per_seed={int(a): [round(float(x), 4), round(float(y), 4)] for a, x, y in zip(s, c, g)})
    if c.mean() < floor: v = UNK; why = f'대조 평균 {c.mean():.4g} < {floor} (시험이 그것을 만들지 못함)'
    elif d.mean() < 0 and pl < 0.05: v = OK; why = 'd<0, p<0.05'
    elif d.mean() >= 0: v = BAD; why = 'd>=0'
    else: v = UNK; why = f'd<0 이지만 p={pl:.3f}'
    out.update(verdict=v, why=why)
    return out


def noninf(scn, key, worse, delta_fn):
    """주장 4: 나빠지지 않는가. worse=+1 이면 값이 클수록 나쁨"""
    c, g, s = pairs(scn, key); d = (g - c) * worse
    delta = delta_fn(c)
    lo, hi = boot(d); pl, pg = signflip(d)
    out = dict(key=key, n=len(s), ctrl_mean=float(c.mean()), cand_mean=float(g.mean()), d_worse_mean=float(d.mean()), ci90=[lo, hi], delta=float(delta), p_worse=pg,
               per_seed={int(a): [x, y] for a, x, y in zip(s, c.tolist(), g.tolist())})
    if hi < delta: v = OK; why = f'CI 위 끝 {hi:.3g} < δ {delta:.3g}'
    elif d.mean() > delta and pg < 0.05: v = BAD; why = f'평균 {d.mean():.3g} > δ, p={pg:.3f}'
    else: v = UNK; why = f'CI [{lo:.3g}, {hi:.3g}], δ {delta:.3g}'
    out.update(verdict=v, why=why)
    return out


def combine(vs):
    if any(v == BAD for v in vs): return BAD
    if all(v == OK for v in vs): return OK
    return UNK


V = {}
P = []
pr = lambda *a: P.append(' '.join(str(x) for x in a))

# ---------- 주장 1
cl = [r for r in R if r['scn'] == 'long' and r['tag'] == 'v16gh']; dn = [r for r in R if r['scn'] == 'long' and r['tag'] == 'v16ghd']
fails = []
for r in cl:
    if r.get('error'): fails.append([r['run'], 'error', r['error']]); continue
    if r['snap_comps_gt1']: fails.append([r['run'], 'snap_comps', r['snap_comps_gt1'][:5]])
    if r['comps_end'] != 1: fails.append([r['run'], 'comps_end', r['comps_end']])
    if (r['V_crumb'] or 0) != 0 or (r['crumb_cells'] or 0) != 0: fails.append([r['run'], 'V_crumb', r['V_crumb'], r['crumb_cells']])
for r in dn:
    if r.get('error'): fails.append([r['run'], 'error', r['error']]); continue
    if r['dense_bad'] != 0: fails.append([r['run'], 'dense_comps', r['dense_bad'], r['dense_bad_first']])
    if r['dense_n'] < int(round(float(r['T']) / 0.1)): fails.append([r['run'], 'dense_n', r['dense_n']])
    if (r['V_crumb'] or 0) != 0: fails.append([r['run'], 'V_crumb', r['V_crumb']])
ctl = [r for r in R if r['scn'] == 'long' and r['tag'] == 'v16c']
ctrl_tear = [[r['seed'], len(r['snap_comps_gt1']), round(r['max_detached_frac'], 4), r['comps_end'], r['V_crumb']] for r in ctl]
V['claim1'] = dict(verdict=OK if not fails else BAD, n_cand_runs=len(cl), n_dense=len(dn), fails=fails,
                   dense=[[r['seed'], r.get('dense_n'), r.get('dense_bad'), r.get('same_as_v16gh'), r.get('maxdiff_vs_v16gh')] for r in dn],
                   ctrl_tear_runs=int(sum(x[1] > 0 or x[3] != 1 for x in ctrl_tear)), ctrl_tear=ctrl_tear,
                   ctrl_Vcrumb=[[r['seed'], r['V_crumb'], r['crumb_cells']] for r in ctl],
                   area_end=[[r['seed'], BY[('long', r['seed'], 'v16c')]['area_end'], r['area_end']] for r in cl])
pr('== 주장 1 (long, 후보에서 찢어짐 없음):', V['claim1']['verdict'])
pr('  후보 long', len(cl), '실행 + 촘촘', len(dn), '실행. 어김:', fails if fails else '없음')
pr('  촘촘 [시드, 검사한 스텝 수, 어긴 스텝, v16gh 와 끝 h 비트 같음, 최대 차]:', V['claim1']['dense'])
pr('  대조에서 찢어진 실행:', V['claim1']['ctrl_tear_runs'], '/', len(ctl), ' [시드, 찢어진 저장 상태 수, 떨어진 부피 비율 최대, 끝 성분 수, V_crumb]:', ctrl_tear)

# ---------- 주장 2
c2 = fewer('long', 'f_D2_main', 0.01); c2b = fewer('long', 'f_D1_main', 0.0)
v2 = c2['verdict']
if v2 == OK and c2b['d_mean'] > 0 and c2b['p_greater'] < 0.05: v2 = UNK; c2['why'] += ' / D1 이 반대로 유의하게 늚 → 낮춤'
sens = {}
for nm in ('main', 'f02', 'f10', 'h07'):
    for D in ('D1', 'D2'):
        for suf in ('', '_late'):
            k = f'f_{D}_{nm}{suf}'; x = fewer('long', k, 0.0); sens[k] = [round(x['ctrl_mean'], 3), round(x['cand_mean'], 3), round(x['p_less'], 4), round(x['p_greater'], 4)]
V['claim2'] = dict(verdict=v2, primary=c2, D1=c2b, sensitivity=sens)
pr('\n== 주장 2 (long, 아령이 대조보다 드묾):', v2, '|', c2['why'])
pr(f"  f_D2 (t 200~2000 중 실 아령 비율) 대조 {c2['ctrl_mean']:.3f} → 후보 {c2['cand_mean']:.3f}, p(적음)={c2['p_less']:.4f}")
pr(f"  f_D1 (굵은 덩이 둘 이상, 이음 무관) 대조 {c2b['ctrl_mean']:.3f} → 후보 {c2b['cand_mean']:.3f}, p(적음)={c2b['p_less']:.4f}, p(많음)={c2b['p_greater']:.4f}")
pr('  시드별 f_D2 [대조, 후보]:', c2['per_seed'])
pr('  시드별 f_D1 [대조, 후보]:', c2b['per_seed'])
pr('  민감도 [대조, 후보, p(적음), p(많음)]:')
for k, v in sens.items(): pr('   ', k, v)

# ---------- 주장 3
c3 = {k: fewer('long', f'late_{k}', 1.0) for k in ('film', 'dead', 'endline')}
c3x = {k: fewer('long', k, 0.0) for k in ('late_deadC', 'late_film_per_area', 'late_dead_per_area', 'late_endline_per_area', 'late_area', 'late_onewide', 'late_vein_edges', 'late_thick_frac')}
V['claim3'] = dict(verdict=combine([x['verdict'] for x in c3.values()]), parts=c3, secondary={k: {kk: x[kk] for kk in ('ctrl_mean', 'cand_mean', 'p_less', 'p_greater', 'per_seed')} for k, x in c3x.items()})
pr('\n== 주장 3 (long t 1500~2000, 칸 수가 대조보다 적음):', V['claim3']['verdict'])
for k, x in c3.items(): pr(f"  {k:8s} 대조 {x['ctrl_mean']:8.1f} → 후보 {x['cand_mean']:8.1f}  p(적음)={x['p_less']:.4f}  {x['verdict']} ({x['why']})")
for k, x in c3.items(): pr(f"    시드별 {k}:", x['per_seed'])
pr('  보조 [대조 → 후보, p(적음), p(많음)]:')
for k, x in c3x.items(): pr(f"    {k:22s} {x['ctrl_mean']:9.4g} → {x['cand_mean']:9.4g}  {x['p_less']:.4f} {x['p_greater']:.4f}")

# ---------- 주장 4
c4 = {}
for scn in ('food3', 'asym3', 'food4'):
    c4[scn] = noninf(scn, 't_all', +1, lambda c: max(15.0, 0.10 * c.mean()))
    c4[scn + ':t_first'] = noninf(scn, 't_first', +1, lambda c: max(10.0, 0.10 * c.mean()))
    c4[scn + ':eaten'] = noninf(scn, 'eaten', -1, lambda c: 0.05)
c4['mig'] = noninf('mig', 't_mig', +1, lambda c: max(15.0, 0.10 * c.mean()))
c4['mig:disp'] = noninf('mig', 'disp', -1, lambda c: 0.10 * c.mean())
missed = {}
for scn in ('food3', 'asym3', 'food4', 'mig'):
    mc = sum(r['missed'] for r in R if r['scn'] == scn and r['tag'] == 'v16c'); mg = sum(r['missed'] for r in R if r['scn'] == scn and r['tag'] == 'v16gh')
    missed[scn] = dict(ctrl=mc, cand=mg, verdict=BAD if mg - mc >= 2 else OK)
prim = [c4[s]['verdict'] for s in ('food3', 'asym3', 'food4', 'mig')]
sec = [v['verdict'] for k, v in c4.items() if ':' in k] + [m['verdict'] for m in missed.values()]
v4 = BAD if BAD in prim else (OK if all(v == OK for v in prim) and BAD not in sec else UNK)
V['claim4'] = dict(verdict=v4, metrics=c4, missed=missed)
pr('\n== 주장 4 (먹이 찾기·굶은 이주가 나빠지지 않음):', v4)
for k, x in c4.items():
    pr(f"  {k:14s} 대조 {x['ctrl_mean']:8.2f} → 후보 {x['cand_mean']:8.2f}  나빠짐 평균 {x['d_worse_mean']:+7.2f}  90%CI [{x['ci90'][0]:+.2f}, {x['ci90'][1]:+.2f}]  δ {x['delta']:.2f}  p(나빠짐)={x['p_worse']:.3f}  {x['verdict']}")
for k in ('food3', 'asym3', 'food4', 'mig'): pr(f"    시드별 {k} [대조, 후보]:", c4[k]['per_seed'])
pr('  놓친 먹이 [대조, 후보]:', {k: [v['ctrl'], v['cand']] for k, v in missed.items()})

# ---------- 주장 5
cand = [r for r in R if r['tag'] in ('v16gh', 'v16ghd')]
f5 = []
for r in cand:
    if r.get('error'): f5.append([r['run'], 'error']); continue
    why = []
    if r['neg_end_cellsteps'] != 0: why.append(f"neg_end={r['neg_end_cellsteps']}")
    if not (r['mass_err_max'] < 1e-10): why.append(f"mass_err={r['mass_err_max']:.3g}")
    if (r['V_crumb'] or 0) != 0: why.append(f"V_crumb={r['V_crumb']:.3g}")
    if r['stop']: why.append(f"stop={r['stop']}")
    if r['comps_end'] != 1: why.append(f"comps_end={r['comps_end']}")
    if why: f5.append([r['run']] + why)
ctrl_h = [[r['run'], r['neg_end_cellsteps'], r['mass_err_max'], r['V_crumb'], r['stop'], r['comps_end']] for r in R if r['tag'] == 'v16c' and not r.get('error')]
V['claim5'] = dict(verdict=OK if not f5 else BAD, n=len(cand), fails=f5, mass_err_max_cand=max(r['mass_err_max'] for r in cand if not r.get('error')),
                   ctrl_unhealthy=[x for x in ctrl_h if x[1] != 0 or not (x[2] < 1e-10) or (x[3] or 0) != 0 or x[4] or x[5] != 1])
pr('\n== 주장 5 (후보 실행 모두 건강):', V['claim5']['verdict'], f"({len(cand)} 실행, 질량 오차 최대 {V['claim5']['mass_err_max_cand']:.2e})")
pr('  어김:', f5 if f5 else '없음')
pr('  (참고) 대조에서 같은 검사를 어긴 실행:', len(V['claim5']['ctrl_unhealthy']), V['claim5']['ctrl_unhealthy'][:12])

V['n_runs'] = len(R)
# ---------- 판정 밖 (CRITERIA_CHANGES 1·3). extra.py 를 먼저 돌려야 있다. 판정을 바꾸지 않는다
fx = os.path.join(VER, 'data', 'extra.json'); fw = os.path.join(VER, 'data', 'worst.json')
if os.path.exists(fx):
    EX = json.load(open(fx)); sm = lambda k: {kk: EX[k][kk] for kk in ('ctrl', 'cand', 'p_less', 'p_greater')}
    V['robustness_not_verdict'] = dict(
        claim2_hmean_all=sm('f_D2_hmean'), claim2_hmean_late=sm('f_D2_hmean_late'), claim2_nbig2_anywhere=sm('f_nbig2_anywhere'),
        claim2_by_window={k: sm(k) for k in EX if k.startswith('f_D2 t')},
        claim3_mainbody={k: sm(k) for k in ('main_film', 'main_dead', 'main_endline', 'main_area', 'main_endline_per_area', 'main_dead_per_area')},
        ctrl_big_tear=EX['ctrl_tear'], far_food=EX.get('far'))
    pr('\n== 판정 밖 튼튼함 검사 (CRITERIA_CHANGES.md 1·3, 판정은 바꾸지 않음) [대조 → 후보, p(적음), p(많음)]')
    for k, v in V['robustness_not_verdict'].items():
        if k in ('claim2_by_window', 'claim3_mainbody'):
            for kk, vv in v.items(): pr(f"  {k}:{kk:24s} {vv['ctrl']:8.3f} → {vv['cand']:8.3f}  {vv['p_less']:.4f} {vv['p_greater']:.4f}")
        elif k == 'ctrl_big_tear': pr('  대조가 크게 찢어진 첫 시각 [t, 떨어진 부피]:', v)
        elif k == 'far_food' and v: pr(f"  먼 먹이 t_all {v['t_all']['ctrl_mean']:.1f} → {v['t_all']['cand_mean']:.1f}, 90%CI [{v['t_all']['ci90'][0]:+.1f}, {v['t_all']['ci90'][1]:+.1f}], δ {v['t_all']['delta']:.1f} → {v['t_all']['verdict']}; 놓친 먹이 {v['missed']}; 시드별 {v['t_all']['per_seed']}")
        elif isinstance(v, dict) and 'ctrl' in v: pr(f"  {k:24s} {v['ctrl']:8.3f} → {v['cand']:8.3f}  {v['p_less']:.4f} {v['p_greater']:.4f}")
if os.path.exists(fw):
    V['worst'] = json.load(open(fw)); pr('\n== 가장 나쁜 사례와 그림:', json.dumps({k: v for k, v in V['worst'].items() if k != 'figs'}, ensure_ascii=False))
json.dump(V, open(os.path.join(VER, 'data', 'verdict.json'), 'w'), indent=1, ensure_ascii=False)
print('\n'.join(P))
