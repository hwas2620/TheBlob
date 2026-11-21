#!/usr/bin/env python3
"""vjudge.py — CRITERIA.md 3절의 판정. 문턱은 thresholds.json 에서만 읽는다.
읽는 것: verify/data/x_<run>.json, bmet_<run>.json (vextract.py 가 만든 것). 쓰는 것: verify/judge_v.txt (사람이 읽는 표), verify/judge_v.json (숫자 전부).
4절의 탐색 값(판정에 쓰지 않음)도 함께 낸다."""
import json, os, glob, sys
import numpy as np
from scipy.stats import binom

V = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S6-neck-mg3/verify'
REF = '/home/user/TheBlob/specs/plasmodium-core/stage0/ref'
TH = json.load(open(os.path.join(V, 'thresholds.json')))
PLAN = {'long': list(range(101, 111)), 'food4': list(range(101, 111)) + list(range(121, 131)), 'food3': list(range(101, 111)), 'asym3': list(range(101, 111)), 'mig': list(range(101, 111))}
THR = TH['split_thr']
LINES = []; OUT = {}


def say(*a):
    s = ' '.join(str(x) for x in a); LINES.append(s); print(s)


def med(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return float(np.median(v)) if v else None


def r3(x, n=3):
    return None if x is None else round(float(x), n)


def load():
    D = {}
    for f in glob.glob(os.path.join(V, 'data', 'x_b_*.json')):
        x = json.load(open(f)); run = x['run']; bf = os.path.join(V, 'data', f'bmet_{run}.json')
        if x['tag'] not in ('vc', 'vnk') or not os.path.exists(bf): continue
        x['bmet'] = json.load(open(bf)); D.setdefault(x['scn'], {}).setdefault(x['seed'], {})[x['tag']] = x
    return D


def params_ok(x):
    p = x['params_check']; ok = p['ncyc'] == 3 and p['solver'] == 'mg' and p['crumb_dry'] == 1 and abs((p['thin_h'] or 0) - 0.15) < 1e-12
    ok = ok and ((p['neck_keep'] in (0, None)) if x['tag'] == 'vc' else (p['neck_keep'] == 1))
    return bool(ok)


def complete(x):
    # 끝까지 돌았는가 (bmet 의 기준과 같다: 멈춤 없이 스텝 수가 맞음)
    return bool(x['complete'] and x['bmet'].get('complete', False))


def pairs(D, scn):
    ps = []; bad = []
    for s in PLAN[scn]:
        g = D.get(scn, {}).get(s, {})
        if 'vc' in g and 'vnk' in g and params_ok(g['vc']) and params_ok(g['vnk']) and complete(g['vc']) and complete(g['vnk']): ps.append((s, g['vc'], g['vnk']))
        else: bad.append((s, {t: (('ok' if complete(g[t]) else 'incomplete:' + str(g[t]['m_stop'])) + ('' if params_ok(g[t]) else ',params?')) if t in g else 'missing' for t in ('vc', 'vnk')}))
    enough = len(ps) >= TH['min_complete_frac'] * len(PLAN[scn])
    return ps, bad, enough


def S_split(x): return sum(1 for r in x['rows'] if r['out'] >= THR)
def max_out(x): return max((r['out'] for r in x['rows']), default=1.0)


def streak(flags, gap=0):
    best = cur = 0; miss = 0
    for f in flags:
        if f: cur += 1 + (miss if cur > 0 else 0); miss = 0; best = max(best, cur)
        else:
            miss += 1
            if miss > gap: cur = 0; miss = 0
    return best


def c1c2w2(D):
    ps, bad, enough = pairs(D, 'long')
    say('\n== long: 쌍', len(ps), '/', len(PLAN['long']), '빠짐:', bad)
    rows = []
    for s, a, b in ps:
        rows.append(dict(seed=s, S_ctrl=S_split(a), S_cand=S_split(b), max_ctrl=r3(max_out(a), 4), max_cand=r3(max_out(b), 4),
                         streak_ctrl=streak([r['out'] >= THR for r in a['rows']]), streak_cand=streak([r['out'] >= THR for r in b['rows']]),
                         neck_frac=r3(b['m_neck_updates'] / b['neck_update_total'], 3)))
    for r in rows: say('  ', r)
    Sc = sum(r['S_ctrl'] for r in rows); Sk = sum(r['S_cand'] for r in rows)
    better = sum(r['S_cand'] < r['S_ctrl'] for r in rows); worse = sum(r['S_cand'] > r['S_ctrl'] for r in rows)
    T = TH['C1']
    if not enough: v1 = '판정 못 함 (끝난 쌍 부족)'
    elif Sc < T['min_ctrl_split_states']: v1 = '판정 못 함 (대조가 거의 갈라지지 않음)'
    elif Sk <= T['confirm_max_ratio'] * Sc and better >= T['confirm_min_better'] and better >= T['confirm_better_over_worse'] * worse: v1 = '확인'
    elif Sk >= T['refute_min_ratio'] * Sc or worse > better: v1 = '반박'
    else: v1 = '재현 안 됨'
    say(f'C1: 갈라진 상태 수 합 대조 {Sc} / 후보 {Sk} (비 {Sk / max(Sc, 1):.2f}), 나아진 시드 {better}, 나빠진 시드 {worse} -> {v1}')
    # C2: 후보 실행 전부(계획 시드). 끝까지 못 간 후보는 미달
    cand = [D.get('long', {}).get(s, {}).get('vnk') for s in PLAN['long']]; cand_ran = [x for x in cand if x is not None and params_ok(x)]
    k = sum(1 for x in cand_ran if complete(x) and max_out(x) < THR)
    ctrl_ran = [D.get('long', {}).get(s, {}).get('vc') for s in PLAN['long']]; ctrl_ran = [x for x in ctrl_ran if x is not None and params_ok(x)]
    k0 = sum(1 for x in ctrl_ran if complete(x) and max_out(x) < THR)
    T = TH['C2']
    if len(cand_ran) < TH['min_complete_frac'] * len(PLAN['long']): v2 = '판정 못 함'
    elif k >= T['confirm_min_runs']: v2 = '확인'
    elif k <= T['refute_max_runs']: v2 = '반박'
    else: v2 = '재현 안 됨'
    say(f'C2: 바깥 몫 최대 < {THR} 인 후보 실행 {k}/{len(cand_ran)} (대조 {k0}/{len(ctrl_ran)}) -> {v2}')
    # W2
    T = TH['W2']; st = [(x['seed'], streak([r['out'] >= THR for r in x['rows']]), S_split(x)) for x in cand_ran]
    if len(cand_ran) < TH['min_complete_frac'] * len(PLAN['long']): vw2 = '판정 못 함'
    elif any(s_ >= T['streak_confirm'] for _, s_, _ in st): vw2 = '확인 (걱정이 맞다)'
    elif all(S_ <= T['refute_max_S'] for _, _, S_ in st): vw2 = '반박 (걱정이 아니다)'
    else: vw2 = '일부 맞음 (짧게만 갈라진다)'
    say(f'W2: 후보 (시드, 가장 긴 연속 갈라짐[저장 상태], 갈라진 상태 수) = {st} -> {vw2}')
    OUT['long_rows'] = rows; OUT['C1'] = dict(S_ctrl=Sc, S_cand=Sk, better=better, worse=worse, verdict=v1); OUT['C2'] = dict(k=k, n=len(cand_ran), k_ctrl=k0, verdict=v2); OUT['W2'] = dict(streaks=st, verdict=vw2)
    return ps


def c7(ps):
    T = TH['C7']; rA = []; tc = 0.0; tk = 0.0; rows = []
    for s, a, b in ps:
        la = [r for r in a['rows'] if T['late_t0'] <= r['t'] <= T['late_t1']]; lb = [r for r in b['rows'] if T['late_t0'] <= r['t'] <= T['late_t1']]
        Aa = np.mean([r['area'] for r in la]); Ab = np.mean([r['area'] for r in lb]); ta = np.mean([r['thin'] for r in la]); tb = np.mean([r['thin'] for r in lb])
        rA.append(Ab / Aa); tc += ta; tk += tb
        rows.append(dict(seed=s, A_late_ctrl=r3(Aa, 0), A_late_cand=r3(Ab, 0), thin_ctrl=r3(ta, 0), thin_cand=r3(tb, 0), area_end_ctrl=a['m_area_end'], area_end_cand=b['m_area_end']))
    for r in rows: say('  ', r)
    mrA = med(rA); rthin = tk / max(tc, 1e-9); rend = med([r['area_end_cand'] / max(r['area_end_ctrl'], 1) for r in rows])
    if len(ps) < TH['min_complete_frac'] * len(PLAN['long']): v = '판정 못 함'
    elif mrA <= T['rA_ok'] and rthin <= T['rthin_ok']: v = '확인'
    elif mrA >= T['rA_bad'] or rthin >= T['rthin_bad']: v = '반박'
    else: v = '재현 안 됨'
    say(f'C7: 늦은 넓이 비의 중앙 {mrA:.3f}, 얇은 넓이 합의 비 {rthin:.3f}, (참고) t=2000 넓이 비의 중앙 {rend:.3f} -> {v}')
    OUT['C7'] = dict(rows=rows, med_rA=mrA, r_thin=rthin, med_r_end=rend, verdict=v)


def w3(D):
    W = TH['W3']; res = {}
    for tag in ('vnk', 'vc'):
        per = []; allst = 0; runs = []
        for s in PLAN['long']:
            x = D.get('long', {}).get(s, {}).get(tag)
            if x is None or not params_ok(x): continue
            st = [r for r in x['rows'] if r['t'] >= W['t_min'] and r.get('n_neck', 0) > 0 and r.get('n_link_edges', 0) > 0]
            allst += len(st)
            pin = med([r['pin'] for r in st]); Rs = med([r.get('R_same') for r in st]); Rv = med([r.get('R_vein') for r in st])
            fl = [(r['t'] >= W['t_min'] and r.get('n_neck', 0) > 0 and (r.get('link_len') or 0) >= W['thread_len']) for r in x['rows'] if r['t'] >= W['t_min']]
            thr_streak = streak(fl, gap=W['thread_gap'])
            runs.append(dict(seed=s, n_neck_states=len(st), pin=r3(pin), R_same=r3(Rs), R_vein=r3(Rv), link_len_med=r3(med([r.get('link_len') for r in st]), 1),
                             h_neck_med=r3(med([r.get('h_neck_med') for r in st])), C_link_med=r3(med([r.get('C_link_med') for r in st]), 1),
                             Qm_over_Qg=r3(med([r['Qm_link_med'] / r['Qg_link_med'] if r.get('Qg_link_med') else None for r in st])),
                             thread_streak=thr_streak, neck_frac=r3(x['m_neck_updates'] / x['neck_update_total'], 3) if tag == 'vnk' else None))
            if len(st) >= W['min_states_per_run']: per.append((pin, Rs))
        P = med([p for p, _ in per]); R = med([r for _, r in per])
        res[tag] = dict(runs=runs, n_runs_used=len(per), n_states=allst, pin=P, R_same=R, n_thread_runs=sum(r['thread_streak'] >= W['thread_streak'] for r in runs))
    r = res['vnk']
    if r['n_runs_used'] < W['min_runs'] or r['n_states'] < W['min_states_total'] or r['pin'] is None or r['R_same'] is None: v = '판정 못 함'
    elif r['pin'] >= W['pin_confirm'] and r['R_same'] <= W['Rsame_confirm_max']: v = '확인 (걱정이 맞다: 억지 가닥)'
    elif r['pin'] < W['pin_confirm'] and r['R_same'] >= W['Rsame_refute_min']: v = '반박 (걱정이 아니다: 나르는 관)'
    else: v = '섞임 (일부 맞음)'
    say('\n== W3: 후보 long 의 이음 (실행마다)')
    for q in r['runs']: say('  ', q)
    say(f"W3: 이음 상태 {r['n_states']}개, 쓴 실행 {r['n_runs_used']}, pin 중앙 {r3(r['pin'])}, R_same 중앙 {r3(r['R_same'])}, 길고 가는 실(>= {W['thread_streak']} 저장 상태) 실행 {r['n_thread_runs']} -> {v}")
    c = res['vc']
    say('   (탐색) 대조 long 에서 같은 방법으로 찾은 "이음이 될 뻔한 곳":')
    for q in c['runs']: say('    ', q)
    say(f"   (탐색) 대조: 이음 상태 {c['n_states']}개, pin(C<=20 비율) 중앙 {r3(c['pin'])}, R_same 중앙 {r3(c['R_same'])}, 길고 가는 실 실행 {c['n_thread_runs']}")
    OUT['W3'] = dict(res=res, verdict=v)


def c3(D):
    ps, bad, enough = pairs(D, 'mig'); T = TH['C3']
    say('\n== mig: 쌍', len(ps), '/', len(PLAN['mig']), '빠짐:', bad)
    nk = [b['m_neck_updates'] for _, _, b in ps]
    ident = []
    for s, a, b in ps:
        same = all(np.array_equal(np.load(os.path.join(REF, 'runs', a['run'], f)), np.load(os.path.join(REF, 'runs', b['run'], f))) for f in ('h.npy', 'C_edges.npy'))
        ident.append(same)
    rows = []
    for s, a, b in ps:
        ba, bb = a['bmet'], b['bmet']
        rows.append(dict(seed=s, disp_c=ba.get('disp300'), disp_k=bb.get('disp300'), ang_c=ba.get('disp_angle'), ang_k=bb.get('disp_angle'), veinT_c=ba.get('veinT'), veinT_k=bb.get('veinT'),
                         area_c=ba.get('area_end'), area_k=bb.get('area_end'), neck_updates=b['m_neck_updates'], identical=ident[len(rows)]))
    for r in rows: say('  ', r)
    mp = lambda d_, a_: (d_ is not None and a_ is not None and d_ >= T['mig_disp_min'] and a_ <= T['mig_angle_max'])
    pc = sum(mp(r['disp_c'], r['ang_c']) for r in rows); pk = sum(mp(r['disp_k'], r['ang_k']) for r in rows)
    dc, dk = med([r['disp_c'] for r in rows]), med([r['disp_k'] for r in rows]); ac, ak = med([r['ang_c'] for r in rows]), med([r['ang_k'] for r in rows])
    vc_, vk_ = med([r['veinT_c'] for r in rows]), med([r['veinT_k'] for r in rows]); arc, ark = med([r['area_c'] for r in rows]), med([r['area_k'] for r in rows])
    if not enough: v = '판정 못 함'
    elif all(n == 0 for n in nk) and all(ident): v = '확인 (이음이 한 번도 작동하지 않아 끝 상태가 비트 단위로 같다)'
    else:
        dr = abs(dk / dc - 1); da = abs(ak - ac); dv = abs(vk_ - vc_); drr = abs(ark / arc - 1)
        if pk >= pc - T['pass_drop_ok'] and dr <= T['disp_rel_ok'] and da <= T['angle_ok'] and dv <= T['veinT_ok'] and drr <= T['area_rel_ok']: v = '확인'
        elif pk <= pc - T['pass_drop_bad'] or dr > T['disp_rel_bad'] or da > T['angle_bad'] or drr > T['area_rel_bad']: v = '반박'
        else: v = '재현 안 됨'
    say(f'C3: 한 방향 이주 대조 {pc} 후보 {pk}; disp300 중앙 {dc} -> {dk}; 각 중앙 {ac} -> {ak}; veinT 중앙 {vc_} -> {vk_}; area_end 중앙 {arc} -> {ark}; 이음 작동 횟수 {nk}; 끝 상태 같음 {sum(ident)}/{len(ident)} -> {v}')
    OUT['C3'] = dict(rows=rows, pass_ctrl=pc, pass_cand=pk, verdict=v)
    return ps


def food_tab(D, scn):
    ps, bad, enough = pairs(D, scn)
    say(f'\n== {scn}: 쌍', len(ps), '/', len(PLAN[scn]), '빠짐:', bad)
    rows = []
    for s, a, b in ps:
        ta, tb = a['m_t_touch'], b['m_t_touch']
        rows.append(dict(seed=s, reach_c=a['bmet']['reached'], reach_k=b['bmet']['reached'], pass_c=a['bmet']['pass'], pass_k=b['bmet']['pass'], thick_c=a['bmet']['thick'], thick_k=b['bmet']['thick'],
                         t_touch_c=ta, t_touch_k=tb, tall_c=max(ta) if all(v is not None for v in ta) else None, tall_k=max(tb) if all(v is not None for v in tb) else None,
                         neck_frac=r3(b['m_neck_updates'] / b['neck_update_total'], 3), same_c=a['bmet'].get('same_ok'), same_k=b['bmet'].get('same_ok'), body_c=a['bmet'].get('body_min'), body_k=b['bmet'].get('body_min')))
    for r in rows: say('  ', r)
    agg = dict(n=len(rows), reach_c=sum(r['reach_c'] for r in rows), reach_k=sum(r['reach_k'] for r in rows), pass_c=sum(r['pass_c'] for r in rows), pass_k=sum(r['pass_k'] for r in rows),
               thick_c=sum(r['thick_c'] for r in rows), thick_k=sum(r['thick_k'] for r in rows), tall_c=med([r['tall_c'] for r in rows]), tall_k=med([r['tall_k'] for r in rows]))
    say('   합:', agg)
    return ps, rows, agg, enough


def c4(D):
    T = TH['C4']; st = {}; flags = []
    for scn in ('food3', 'asym3'):
        ps, rows, g, enough = food_tab(D, scn)
        d = (g['tall_k'] - g['tall_c']) if (g['tall_k'] is not None and g['tall_c'] is not None) else None
        tol_ok = max(T['tall_abs_ok'], T['tall_rel_ok'] * (g['tall_c'] or 0)); tol_bad = max(T['tall_abs_bad'], T['tall_rel_bad'] * (g['tall_c'] or 0))
        if not enough: s = 'none'
        elif g['reach_k'] <= g['reach_c'] - T['reach_drop_bad'] or g['pass_k'] <= g['pass_c'] - T['pass_drop_bad'] or g['thick_k'] <= g['thick_c'] - T['thick_drop_bad'] or (d is not None and d > tol_bad): s = 'bad'
        elif g['reach_k'] >= g['reach_c'] - T['reach_drop_ok'] and g['pass_k'] >= g['pass_c'] - T['pass_drop_ok'] and g['thick_k'] >= g['thick_c'] - T['thick_drop_ok'] and (d is None or d <= tol_ok): s = 'ok'
        else: s = 'mid'
        if d is not None and d < -tol_ok: flags.append(f'{scn}: t_all 이 {d:.1f} 빨라짐')
        st[scn] = dict(agg=g, d_tall=d, tol_ok=tol_ok, tol_bad=tol_bad, state=s, rows=rows)
        say(f'   {scn}: t_all 중앙 차 {d} (OK 문턱 {tol_ok}, 나쁨 문턱 {tol_bad}) -> {s}')
    ss = [st[k]['state'] for k in st]
    if 'none' in ss: v = '판정 못 함'
    elif 'bad' in ss: v = '반박'
    elif all(x == 'ok' for x in ss): v = '확인' + (' (단, 좋아지는 쪽으로 바뀜: ' + '; '.join(flags) + ')' if flags else '')
    else: v = '재현 안 됨'
    say('C4 ->', v); OUT['C4'] = dict(scn=st, verdict=v)


def c5w1(D):
    T = TH['C5']; ps, rows, g, enough = food_tab(D, 'food4')
    if not enough: v = '판정 못 함'
    elif g['reach_k'] <= g['reach_c'] - T['reach_drop_bad'] or g['pass_k'] <= g['pass_c'] - T['pass_drop_bad'] or (g['thick_c'] > 0 and g['thick_k'] < T['thick_ratio_bad'] * g['thick_c']): v = '반박'
    elif g['reach_k'] >= g['reach_c'] - T['reach_drop_ok'] and g['pass_k'] >= g['pass_c'] - T['pass_drop_ok'] and (g['thick_c'] == 0 or g['thick_k'] >= T['thick_ratio_ok'] * g['thick_c']): v = '확인'
    else: v = '재현 안 됨'
    per_food = [[sum(r['t_touch_c'][i] is not None for r in rows), sum(r['t_touch_k'][i] is not None for r in rows)] for i in range(4)]
    say(f'C5: 네 먹이 모두 닿음 대조 {g["reach_c"]} 후보 {g["reach_k"]}; 통과 {g["pass_c"]} -> {g["pass_k"]}; 굵은 쌍 {g["thick_c"]} -> {g["thick_k"]}; 먹이별 닿은 시드 [대조, 후보] {per_food} -> {v}')
    OUT['C5'] = dict(agg=g, per_food=per_food, rows=rows, verdict=v)
    W = TH['W1']; i = W['far_food_index']
    b = sum(1 for r in rows if r['t_touch_k'][i] is None and r['t_touch_c'][i] is not None); c = sum(1 for r in rows if r['t_touch_k'][i] is not None and r['t_touch_c'][i] is None)
    p = float(binom.sf(b - 1, b + c, 0.5)) if b + c > 0 else 1.0
    dl = [r['t_touch_k'][i] - r['t_touch_c'][i] for r in rows if r['t_touch_k'][i] is not None and r['t_touch_c'][i] is not None]; md = med(dl)
    miss_c = sum(r['t_touch_c'][i] is None for r in rows); miss_k = sum(r['t_touch_k'][i] is None for r in rows)
    if not enough: vw = '판정 못 함'
    elif b - c >= W['diff_confirm'] and p <= W['p_confirm']: vw = '확인 (걱정이 맞다)'
    elif b - c <= W['diff_refute'] and (md is None or md < W['delay_flag']): vw = '반박 (걱정이 아니다)'
    elif b - c <= W['diff_refute']: vw = '일부 맞음 (놓치지는 않으나 늦게 닿음)'
    else: vw = '판정 못 함'
    say(f'W1: 가장 먼 먹이(1번) 놓침 대조 {miss_c}/{len(rows)} 후보 {miss_k}/{len(rows)}; b(후보만 놓침)={b} c(대조만 놓침)={c} p={p:.3f}; 둘 다 닿은 {len(dl)}쌍의 시각 차 중앙 {md} -> {vw}')
    # 탐색: 이음 작동과 놓침
    for r in rows:
        r['far_miss_c'] = r['t_touch_c'][i] is None; r['far_miss_k'] = r['t_touch_k'][i] is None
    say('   (탐색) 후보에서 가장 먼 먹이를 놓친 시드의 이음 작동 몫:', [(r['seed'], r['neck_frac']) for r in rows if r['far_miss_k']], ' 닿은 시드:', [(r['seed'], r['neck_frac']) for r in rows if not r['far_miss_k']])
    OUT['W1'] = dict(b=b, c=c, p=p, miss_ctrl=miss_c, miss_cand=miss_k, delays=dl, med_delay=md, verdict=vw)


def c6(D):
    T = TH['C6']; viol = []; scn_st = {}; hmin = {}
    for scn in PLAN:
        for s in PLAN[scn]:
            x = D.get(scn, {}).get(s, {}).get('vnk')
            if x is None: continue
            if (x['m_neg_end_steps'] or 0) != 0 or (x['m_h_min_end_of_step'] or 0) < 0 or (x['m_mass_err_max'] is None) or x['m_mass_err_max'] >= T['mass_err_max']:
                viol.append((x['run'], x['m_neg_end_steps'], x['m_h_min_end_of_step'], x['m_mass_err_max']))
        ps, _, enough = pairs(D, scn)
        nc = sum(a['m_neg_cellsteps'] for _, a, _ in ps); nk = sum(b['m_neg_cellsteps'] for _, _, b in ps)
        st = 'none' if not enough else ('bad' if nk > T['neg_bad_mult'] * nc + T['neg_bad_add'] else ('ok' if nk <= T['neg_ok_mult'] * nc + T['neg_ok_add'] else 'mid'))
        me = [max(a['m_mass_err_max'] for _, a, _ in ps) if ps else None, max(b['m_mass_err_max'] for _, _, b in ps) if ps else None]
        hm = [min(a['m_h_min_seen'] for _, a, _ in ps) if ps else None, min(b['m_h_min_seen'] for _, _, b in ps) if ps else None]
        more = sum(b['m_neg_cellsteps'] > a['m_neg_cellsteps'] for _, a, b in ps)
        scn_st[scn] = dict(neg_cellsteps_ctrl=nc, neg_cellsteps_cand=nk, state=st, mass_err_max=me, h_min_seen=hm, pairs=len(ps), seeds_cand_more=more,
                           neg_end_ctrl=sum(a['m_neg_end_steps'] for _, a, _ in ps), neg_end_cand=sum(b['m_neg_end_steps'] for _, _, b in ps))
        say(f'   C6 {scn}:', scn_st[scn])
    ss = [v['state'] for v in scn_st.values()]
    if viol or 'bad' in ss: v = '반박'
    elif 'none' in ss: v = '판정 못 함 (일부 시나리오 쌍 부족)'
    elif all(x == 'ok' for x in ss): v = '확인'
    else: v = '재현 안 됨'
    say('C6: 끝 음수·부피 어김', viol, '->', v)
    OUT['C6'] = dict(viol=viol, scn=scn_st, verdict=v)


def explore(D):
    say('\n== 탐색 (판정에 쓰지 않음)')
    for scn in PLAN:
        fr = [D[scn][s]['vnk']['m_neck_updates'] / D[scn][s]['vnk']['neck_update_total'] for s in PLAN[scn] if s in D.get(scn, {}) and 'vnk' in D[scn][s]]
        if fr: say(f'  이음 작동 시간 몫 {scn}: 중앙 {med(fr):.3f}, 최대 {max(fr):.3f}, 0 인 실행 {sum(f == 0 for f in fr)}/{len(fr)}')
    ps, _, _ = pairs(D, 'long')
    for k in ('turnover', 'sheet_amp', 'veinT', 'strahler', 'gross_net', 'area_end'):
        say(f'  long {k}: 대조 중앙 {r3(med([a["bmet"].get(k) for _, a, _ in ps]))}, 후보 중앙 {r3(med([b["bmet"].get(k) for _, _, b in ps]))}')
    segs = {}
    for _, a, b in ps:
        for tag, x in (('vc', a), ('vnk', b)):
            for sg in x['bmet'].get('segments', []):
                segs.setdefault((tag, tuple(sg['t'])), []).append(sg['out_frac'])
    say('  long 구간별 바깥 몫 최대의 중앙 (대조, 후보):', {f'{k[1]}': (r3(med(segs.get(('vc', k[1]), []))), r3(med(segs.get(('vnk', k[1]), [])))) for k in segs if k[0] == 'vc'})
    # CRITERIA_CHANGES 2026-11-21T20:11:45Z: 두꺼운 몸이 큰 덩어리 둘 이상(n_big >= 2)인 상태의 몫 (t >= 100)
    nb_rows = []
    for s, a, b in ps:
        fa = [r.get('n_big', 0) >= 2 for r in a['rows'] if r['t'] >= 100]; fb = [r.get('n_big', 0) >= 2 for r in b['rows'] if r['t'] >= 100]
        nb_rows.append((s, r3(np.mean(fa), 2), r3(np.mean(fb), 2)))
    say('  (탐색) 두꺼운 몸이 큰 덩어리 둘 이상인 상태의 몫 (시드, 대조, 후보):', nb_rows)
    say(f'  (탐색) 그 몫의 평균: 대조 {r3(np.mean([x[1] for x in nb_rows]), 3)}, 후보 {r3(np.mean([x[2] for x in nb_rows]), 3)}')
    OUT['explore_nbig'] = nb_rows


def main():
    D = load()
    say('판정 (vjudge.py). 문턱 파일 thresholds.json, 갈라짐 문턱', THR)
    say('불러온 실행 수:', {k: sum(len(v) for v in D[k].values()) for k in D})
    ps = c1c2w2(D); c7(ps); w3(D); c3(D); c4(D); c5w1(D); c6(D); explore(D)
    say('\n== 요약')
    for k in ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'W1', 'W2', 'W3'):
        if k in OUT: say(f'{k}: {OUT[k]["verdict"]}')
    open(os.path.join(V, 'judge_v.txt'), 'w').write('\n'.join(LINES) + '\n')
    json.dump(OUT, open(os.path.join(V, 'judge_v.json'), 'w'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    main()
