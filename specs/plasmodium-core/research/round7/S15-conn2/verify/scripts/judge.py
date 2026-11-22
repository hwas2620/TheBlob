#!/usr/bin/env python3
"""verify/data/summary.json 을 읽고 CRITERIA.md 의 문턱으로 주장 1~4 를 판정한다.

usage: judge.py            → verify/data/verdict.json 과 화면 출력
판정: 맞음 / 틀림 / 판정 못 함. 문턱은 실행 전에 정했다(CRITERIA.md). 여기 숫자를 바꾸면 CRITERIA_CHANGES.md 에 적는다.
"""
import json, os, sys
import numpy as np
from scipy.stats import binomtest

HERE = os.path.dirname(os.path.abspath(__file__))
OK, NO, UN = '맞음', '틀림', '판정 못 함'

SEEDS = dict(long=list(range(201, 213)), food4=list(range(201, 207)), food3=list(range(201, 209)), asym3=list(range(201, 209)), mig=list(range(201, 209)))


def pairs(R, scn):
    """같은 시드의 (대조, 후보) 쌍. 둘 다 끝까지 돈 것만"""
    out = []
    for s in SEEDS[scn]:
        c = R.get(f'b_{scn}_s{s}_v15c'); k = R.get(f'b_{scn}_s{s}_v15k')
        if c and k: out.append((s, c, k))
    return out


def sign_p(c, k):
    """후보가 더 작은 쪽인 한쪽 부호 검정 (같은 값은 뺀다). 돌려줌: (p, 후보가 작은 시드 수, 다른 시드 수)"""
    d = np.asarray(k, float) - np.asarray(c, float); lo = int((d < 0).sum()); n = int((d != 0).sum())
    return (binomtest(lo, n, 0.5, alternative='greater').pvalue if n > 0 else 1.0), lo, n


def combine(vs):
    if any(v == NO for v in vs): return NO
    if all(v == OK for v in vs): return OK
    return UN


def claim1(R):
    P = pairs(R, 'long'); n = len(P); r = dict(n_pairs=n)
    if n < 10: r['verdict'] = UN; r['why'] = f'끝난 쌍이 {n} (10 미만)'; return r
    if not all(c['complete'] and k['complete'] for _, c, k in P): r['verdict'] = UN; r['why'] = '끝까지 돌지 못한 실행이 있다'; return r
    # 1a 갈라진 시간
    sc = [c['split_frac'] for _, c, _ in P]; sk = [k['split_frac'] for _, _, k in P]
    a = dict(control_mean=float(np.mean(sc)), candidate_mean=float(np.mean(sk)), candidate_max=float(np.max(sk)), control_per_seed=sc, candidate_per_seed=sk)
    a['verdict'] = OK if (a['candidate_mean'] <= 0.01 and a['candidate_max'] <= 0.03) else (NO if (a['candidate_mean'] > 0.05 or a['candidate_max'] > 0.20) else UN)
    # 1b 가장 큰 조각 밖의 부피
    vc = [c['volout_mean'] for _, c, _ in P]; vk = [k['volout_mean'] for _, _, k in P]; vkmax = max(k['volout_max'] for _, _, k in P)
    b = dict(control_mean=float(np.mean(vc)), candidate_mean=float(np.mean(vk)), candidate_step_max=float(vkmax), candidate_run_mean_max=float(np.max(vk)), control_per_seed=vc, candidate_per_seed=vk)
    b['verdict'] = OK if (b['candidate_mean'] <= 0.001 and vkmax <= 0.01) else (NO if (b['candidate_mean'] > 0.01 or b['candidate_run_mean_max'] > 0.03) else UN)
    # 1c 큰 굵은 조각 둘 이상 (주 문턱: h >= 0.6, 부피 >= 몸의 10%)
    def c1c(key):
        fc = [c[key] for _, c, _ in P]; fk = [k[key] for _, _, k in P]; p, lo, nn = sign_p(fc, fk)
        o = dict(key=key, control_mean=float(np.mean(fc)), candidate_mean=float(np.mean(fk)), sign_p=p, cand_lower=lo, differ=nn, control_per_seed=fc, candidate_per_seed=fk)
        Fc, Fk = o['control_mean'], o['candidate_mean']
        if Fc < 0.05: o['verdict'] = UN; o['why'] = '대조에서도 드물다 (0.05 미만): 견줄 것이 없다'
        elif Fk <= 0.5 * Fc and p <= 0.05: o['verdict'] = OK
        elif Fk > 0.8 * Fc: o['verdict'] = NO
        else: o['verdict'] = UN
        return o
    c = c1c('big2_0.6_0.1')
    c['sensitivity'] = {k_: {kk: v for kk, v in c1c(k_).items() if kk in ('control_mean', 'candidate_mean', 'sign_p', 'verdict')}
                        for k_ in [f'big2_{x}_{y}' for x in (0.3, 0.45, 0.6) for y in (0.05, 0.1, 0.2)] if k_ != 'big2_0.6_0.1'}
    r.update(a_split=a, b_volout=b, c_big2=c); r['verdict'] = combine([a['verdict'], b['verdict'], c['verdict']])
    return r


def claim2(R):
    P = pairs(R, 'long'); n = len(P); r = dict(n_pairs=n)
    if n < 10: r['verdict'] = UN; r['why'] = f'끝난 쌍이 {n}'; return r
    vs = []
    for key in ('late_thin', 'late_line'):
        fc = [c[key] for _, c, _ in P]; fk = [k[key] for _, _, k in P]; p, lo, nn = sign_p(fc, fk)
        o = dict(control_mean=float(np.mean(fc)), candidate_mean=float(np.mean(fk)), ratio=float(np.mean(fk) / max(np.mean(fc), 1e-12)), sign_p=p, cand_lower=lo, differ=nn,
                 control_per_seed=fc, candidate_per_seed=fk)
        if o['candidate_mean'] >= o['control_mean']: o['verdict'] = NO
        elif o['candidate_mean'] < 0.9 * o['control_mean'] and p <= 0.05: o['verdict'] = OK
        else: o['verdict'] = UN
        r[key] = o; vs.append(o['verdict'])
    # 넓이로 나눈 값 (보고만, 판정에 쓰지 않는다)
    for key in ('late_thin_frac', 'late_line_frac', 'late_area'):
        r[key] = dict(control_mean=float(np.mean([c[key] for _, c, _ in P])), candidate_mean=float(np.mean([k[key] for _, _, k in P])))
    r['verdict'] = combine(vs)
    return r


def worse_time(tc, tk, n):
    d = np.asarray(tk, float) - np.asarray(tc, float); med_c = float(np.median(tc)); md = float(np.median(d)); slower = int((d > 0).sum())
    big = md > 0.15 * med_c; cons = slower >= 0.75 * n
    return dict(median_control=med_c, median_diff=md, cand_slower=slower, n=n, flag='worse' if (big and cons) else ('unclear' if big else 'ok'), control=list(tc), candidate=list(tk))


def claim3(R):
    r = {}; flags = []
    for scn in ('food3', 'asym3', 'food4'):
        P = pairs(R, scn); n = len(P); o = dict(n_pairs=n)
        if n < len(SEEDS[scn]) or not all(c['complete'] and k['complete'] for _, c, k in P):
            o['flag'] = 'unclear'; o['why'] = '빠진 실행 또는 끝까지 돌지 못한 실행'; r[scn] = o; flags.append('unclear'); continue
        Rc = sum(c['n_reached'] for _, c, _ in P); Rk = sum(k['n_reached'] for _, _, k in P)
        o['reach'] = dict(control=Rc, candidate=Rk, of=sum(c['n_foods'] for _, c, _ in P), flag='worse' if Rk <= Rc - 2 else 'ok')
        o['t_all'] = worse_time([c['t_all'] for _, c, _ in P], [k['t_all'] for _, _, k in P], n)
        ec = np.array([c['eaten'] for _, c, _ in P]); ek = np.array([k['eaten'] for _, _, k in P])
        rat = np.where(ec > 0, ek / np.maximum(ec, 1e-12), np.where(ek > 0, 2.0, 1.0)); lower = int((rat < 1).sum()); big = float(np.median(rat)) < 0.9
        o['eaten'] = dict(median_ratio=float(np.median(rat)), cand_lower=lower, n=n, control=ec.tolist(), candidate=ek.tolist(),
                          flag='worse' if (big and lower >= 0.75 * n) else ('unclear' if big else 'ok'))
        o['bmet_pass'] = dict(control=sum(bool((c.get('bmet') or {}).get('pass')) for _, c, _ in P), candidate=sum(bool((k.get('bmet') or {}).get('pass')) for _, _, k in P))
        fl = [o['reach']['flag'], o['t_all']['flag'], o['eaten']['flag']]
        o['flag'] = 'worse' if 'worse' in fl else ('unclear' if 'unclear' in fl else 'ok'); r[scn] = o; flags.append(o['flag'])
    P = pairs(R, 'mig'); n = len(P); o = dict(n_pairs=n)
    if n < len(SEEDS['mig']) or not all(c['complete'] and k['complete'] for _, c, k in P):
        o['flag'] = 'unclear'; o['why'] = '빠진 실행 또는 끝까지 돌지 못한 실행'
    else:
        o['t_touch'] = worse_time([c['t_touch'] for _, c, _ in P], [k['t_touch'] for _, _, k in P], n)
        dc = np.array([c['disp_toward'] for _, c, _ in P]); dk = np.array([k['disp_toward'] for _, _, k in P]); d = dk - dc
        big = float(np.median(d)) < -0.15 * float(np.median(dc)); lower = int((d < 0).sum())
        o['disp_toward'] = dict(median_control=float(np.median(dc)), median_diff=float(np.median(d)), cand_lower=lower, n=n, control=dc.tolist(), candidate=dk.tolist(),
                                flag='worse' if (big and lower >= 0.75 * n) else ('unclear' if big else 'ok'))
        fl = [o['t_touch']['flag'], o['disp_toward']['flag']]; o['flag'] = 'worse' if 'worse' in fl else ('unclear' if 'unclear' in fl else 'ok')
    r['mig'] = o; flags.append(o['flag'])
    r['verdict'] = NO if 'worse' in flags else (UN if 'unclear' in flags else OK)
    return r


def run_health(o):
    fails = []
    if not o['complete']: fails.append('끝까지 돌지 못함')
    if (o['neg_end_cellsteps'] or 0) != 0 or (o['h_min_end_of_step'] or 0.0) < 0: fails.append(f"스텝 끝 음수 두께 (셀·스텝 {o['neg_end_cellsteps']}, 최소 {o['h_min_end_of_step']})")
    if not (o['mass_err_max'] < 1e-10): fails.append(f"부피 오차(모델) {o['mass_err_max']:.2e}")
    if not (o['my_mass_err'] < 1e-10): fails.append(f"부피 오차(내 점검, {o['my_mass_err_src']}) {o['my_mass_err']:.2e}")
    if (o['V_crumb'] or 0.0) != 0.0 or (o['crumb_cells'] or 0) != 0: fails.append(f"버린 부피 {o['V_crumb']:.3e} ({o['crumb_cells']} 셀)")
    if o['ncomp_end'] != 1: fails.append(f"끝의 젖은 성분 {o['ncomp_end']}")
    return fails


def claim4(R):
    r = dict(runs={}, n=0, n_fail=0)
    want = [f'b_{scn}_s{s}_v15k' for scn, ss in SEEDS.items() for s in ss]
    missing = [w for w in want if w not in R]
    for name in want:
        if name not in R: continue
        f = run_health(R[name]); r['n'] += 1; r['n_fail'] += bool(f)
        r['runs'][name] = f
    r['missing'] = missing
    r['control_fail'] = {nm: run_health(o) for nm, o in R.items() if o['tag'] == 'v15c' and run_health(o)}
    r['verdict'] = NO if r['n_fail'] > 0 else (UN if missing else OK)
    return r


def main():
    R = json.load(open(os.path.join(HERE, '..', 'data', 'summary.json')))
    V = dict(claim1=claim1(R), claim2=claim2(R), claim3=claim3(R), claim4=claim4(R))
    json.dump(V, open(os.path.join(HERE, '..', 'data', 'verdict.json'), 'w'), ensure_ascii=False, indent=1)
    c1 = V['claim1']
    print('주장 1:', c1['verdict'])
    for k in ('a_split', 'b_volout', 'c_big2'):
        if k in c1: print('  ', k, c1[k]['verdict'], {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in c1[k].items() if kk in ('control_mean', 'candidate_mean', 'candidate_max', 'candidate_step_max', 'sign_p')})
    c2 = V['claim2']; print('주장 2:', c2['verdict'])
    for k in ('late_thin', 'late_line', 'late_thin_frac', 'late_line_frac', 'late_area'):
        if k in c2: print('  ', k, {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in c2[k].items() if not kk.endswith('per_seed')})
    c3 = V['claim3']; print('주장 3:', c3['verdict'])
    for scn in ('food3', 'asym3', 'food4', 'mig'):
        o = c3[scn]; print('  ', scn, o['flag'], {k: (v.get('flag'), {kk: vv for kk, vv in v.items() if kk not in ('flag', 'control', 'candidate')}) if isinstance(v, dict) else v for k, v in o.items() if k != 'flag'})
    c4 = V['claim4']; print('주장 4:', c4['verdict'], f"후보 실행 {c4['n']}개 중 실패 {c4['n_fail']}", '빠짐', c4['missing'])
    for nm, f in c4['runs'].items():
        if f: print('   ', nm, f)
    print('   대조의 건강 실패:', c4['control_fail'])


if __name__ == '__main__':
    main()
