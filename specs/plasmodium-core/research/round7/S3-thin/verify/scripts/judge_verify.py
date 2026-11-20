#!/usr/bin/env python3
"""[S3 검증] criteria.json 의 기준대로 판정한다. 문턱은 모두 criteria.json 에서 읽는다.

usage: judge_verify.py [--json OUT]
읽는 것: ../summaries/numpy_<실행>.json (bmet.py), ../summaries/extra_<실행>.json (extra_metrics.py)
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.dirname(HERE); SUM = os.path.join(V, 'summaries')
K = json.load(open(os.path.join(HERE, 'criteria.json')))
OUT = {}


def ctag(scn, s): return 'vcd' if s in K['seeds'][scn]['existing_vcd'] else 'vcdv'


def load(scn, s, tag):
    n = f'b_{scn}_s{s}_{tag}'; f = os.path.join(SUM, f'numpy_{n}.json'); e = os.path.join(SUM, f'extra_{n}.json')
    if not os.path.exists(f): return None
    o = json.load(open(f)); o['_extra'] = json.load(open(e)) if os.path.exists(e) else None
    if not o.get('complete'): print('  [불완전]', n); return None
    return o


def pairs(scns):
    out = []
    for scn in scns:
        for s in K['seeds'][scn]['seeds']:
            c = load(scn, s, ctag(scn, s)); a = load(scn, s, 'vthAv')
            out.append((scn, s, c, a))
    return out


def med(v):
    v = [x for x in v if x is not None]
    return float(np.median(v)) if v else None


def fm(x, f='%.3g'):
    return '없음' if x is None else (f % x)


def say(*a): print(*a)


def lag300(o):
    for t, l, L, c in (o.get('lag') or []):
        if abs(t - 300) < 1e-6: return l
    return None


def gate_ok(o):
    g = K['C3']['gate']; fails = []
    for k, rule in g.items():
        v = lag300(o) if k == 'lag300' else o.get(k)
        if v is None: fails.append(k); continue
        if rule[0] == '>=' and not v >= rule[1]: fails.append(k)
        elif rule[0] == '>' and not v > rule[1]: fails.append(k)
        elif rule[0] == 'in' and not (rule[1] <= v <= rule[2]): fails.append(k)
    return fails


def main():
    P_food = pairs(K['groups']['food_all']); P_near = [p for p in P_food if p[0] in K['groups']['food_near']]
    P_mig = pairs(['mig']); P_long = pairs(['long']); P_all = P_food + P_mig + P_long
    miss = [(scn, s) for scn, s, c, a in P_all if c is None or a is None]
    say(f'짝 수: 먹이 {len(P_food)}, 가까운 먹이 {len(P_near)}, mig {len(P_mig)}, long {len(P_long)}. 빠진 짝: {miss}')
    ok = lambda P: [(scn, s, c, a) for scn, s, c, a in P if c is not None and a is not None]
    P_food, P_near, P_mig, P_long, P_all = ok(P_food), ok(P_near), ok(P_mig), ok(P_long), ok(P_all)

    # ── C1 ──
    k = K['C1']; say('\n== C1 음수 두께 (먹이 실행) ==')
    say('%-10s %4s | %10s %10s | %10s %10s | %10s %10s' % ('시나리오', '시드', 'neg 대조', 'neg 후보', 'hmin 대조', 'hmin 후보', 'hend 대조', 'hend 후보'))
    for scn, s, c, a in P_food:
        say('%-10s %4d | %10d %10d | %10.4f %10.4f | %10.4f %10.4f' % (scn, s, c['neg_end'], a['neg_end'], c['h_min_in'], a['h_min_in'], c['h_min_end'], a['h_min_end']))
    n = len(P_food); le = sum(a['neg_end'] <= c['neg_end'] for _, _, c, a in P_food); gt = sum(a['neg_end'] > c['neg_end'] for _, _, c, a in P_food)
    zero = sum(a['neg_end'] == 0 for _, _, c, a in P_food); zc = sum(c['neg_end'] == 0 for _, _, c, a in P_food)
    hc = med([abs(c['h_min_in']) for _, _, c, a in P_food]); ha = med([abs(a['h_min_in']) for _, _, c, a in P_food]); r = ha / hc
    if le == n and zero >= k['confirm']['cand_zero_min'] and r < k['confirm']['hmin_med_ratio_lt']: v = '확인'
    elif gt >= k['refute']['pairs_gt_min'] or r >= k['refute']['hmin_med_ratio_ge']: v = '반박'
    else: v = '부분 확인'
    say(f'후보 ≤ 대조 {le}/{n}, 후보 > 대조 {gt}, 후보 0 {zero}/{n} (대조 0 {zc}/{n}), |h_min_in| 중앙 대조 {hc:.4f} 후보 {ha:.4f} (비 {r:.3f}) → {v}')
    OUT['C1'] = dict(n=n, le=le, gt=gt, cand_zero=zero, ctrl_zero=zc, hmin_med_ctrl=hc, hmin_med_cand=ha, ratio=r, sum_neg_ctrl=sum(c['neg_end'] for _, _, c, a in P_food), sum_neg_cand=sum(a['neg_end'] for _, _, c, a in P_food), verdict=v)

    # ── C2 ──
    k = K['C2']; say('\n== C2 전진 ==')
    late_mig = []; dd = []
    for scn, s, c, a in P_mig:
        tc, ta = c['t_touch'][0], a['t_touch'][0]
        d = None if (tc is None or ta is None) else ta - tc
        if (tc is not None and ta is None) or (d is not None and d > k['mig_late']): late_mig.append(s)
        dd.append(a['disp300'] - c['disp300'])
        say(f'  mig s{s}: 닿은 시각 {tc} → {ta}, disp300 {c["disp300"]} → {a["disp300"]} (차 {a["disp300"] - c["disp300"]:+.2f}), 각 {c.get("disp_angle")} → {a.get("disp_angle")}')
    dmed = med(dd); cmed = med([c['disp300'] for _, _, c, a in P_mig]); rel = dmed / cmed
    late_food = []; dts = []
    for scn, s, c, a in P_near:
        for i, (tc, ta) in enumerate(zip(c['t_touch'], a['t_touch'])):
            if tc is None: continue
            if ta is None or ta - tc > k['food_late']: late_food.append((scn, s, i, tc, ta))
            if ta is not None: dts.append(ta - tc)
    say(f'  mig 10 넘게 늦음: {late_mig}, disp300 짝 차이 중앙 {dmed:+.2f} (대조 중앙 {cmed:.2f}, 비 {rel:+.3f})')
    say(f'  가까운 먹이: 10 넘게 늦거나 못 닿은 먹이 {late_food}. 닿은 시각 차이 범위 {min(dts):+.1f} ~ {max(dts):+.1f}, |차이| 중앙 {med([abs(x) for x in dts]):.1f}')
    if len(late_mig) <= k['mig_late_max_confirm'] and rel >= k['disp_med_rel_confirm'] and not late_food: v = '확인'
    elif rel < k['disp_med_rel_refute'] or len(late_food) >= k['food_late_refute'] or len(late_mig) >= k['mig_late_refute']: v = '반박'
    else: v = '부분 확인'
    say('  →', v)
    OUT['C2'] = dict(mig_late=late_mig, disp_diff_med=dmed, disp_ctrl_med=cmed, disp_rel=rel, food_late=late_food, touch_diff_range=[min(dts), max(dts)], touch_absdiff_med=med([abs(x) for x in dts]), verdict=v)

    # ── C3 ──
    k = K['C3']; say('\n== C3 몸과 정맥 ==')
    mig_in = {}
    for key in k['mig_keys']:
        cv = [c[key] for _, _, c, a in P_mig]; av = [a[key] for _, _, c, a in P_mig]
        lo, hi = min(cv), max(cv); w = hi - lo; L, H = lo - k['range_widen'] * w, hi + k['range_widen'] * w
        nin = sum(L <= x <= H for x in av); d = [x - y for x, y in zip(av, cv)]
        mig_in[key] = dict(ctrl=cv, cand=av, range=[lo, hi], wide=[L, H], n_in=nin, ok=nin >= k['mig_in_min'], diff_med=med(d), diff_mean=float(np.mean(d)), diff_sd=float(np.std(d, ddof=1)), ctrl_sd=float(np.std(cv, ddof=1)),
                            n_lower=sum(x < 0 for x in d))
        say(f'  {key:10s} 대조 {lo:.3f}~{hi:.3f} (넓힘 {L:.3f}~{H:.3f}) 후보 {min(av):.3f}~{max(av):.3f} 안 {nin}/{len(av)}, 짝 차이 중앙 {med(d):+.3f} 평균 {np.mean(d):+.3f} ± {np.std(d, ddof=1):.3f}, 대조 sd {np.std(cv, ddof=1):.3f}')
    lost = 0; gained = 0; gate_rows = []
    for scn, s, c, a in P_mig:
        fc, fa = gate_ok(c), gate_ok(a); gate_rows.append((s, fc, fa))
        if not fc and fa: lost += 1
        if fc and not fa: gained += 1
        say(f'  mig s{s} 관문 B3·B4 못 넘은 것: 대조 {fc or "-"} / 후보 {fa or "-"}')
    thr_lost = lost - gained
    same = 0; rows = []
    for scn, s, c, a in P_near:
        eq = (c['pass'] == a['pass']) and (c['thick'] == a['thick']); same += eq
        rows.append((scn, s, c['pass'], a['pass'], c['thick'], a['thick'], c['same_ok'], a['same_ok'], c['body_min'], a['body_min'], c['ratio'], a['ratio']))
        say(f'  {scn:9s} s{s}: 통과 {c["pass"]!s:5s} → {a["pass"]!s:5s} 굵은 쌍 {c["thick"]} → {a["thick"]} 같은 성분 {c["same_ok"]} → {a["same_ok"]} 몸 {c["body_min"]} → {a["body_min"]}  배율 {c["ratio"]} → {a["ratio"]}' + ('' if eq else '   ★다름'))
    pc = sum(c['pass'] for _, _, c, a in P_near); pa = sum(a['pass'] for _, _, c, a in P_near); n = len(P_near)
    nok = sum(m['ok'] for m in mig_in.values())
    if nok == len(mig_in) and same >= k['same_confirm'] and pa >= pc - k['pass_drop_confirm_max'] and thr_lost <= k['thr_lost_confirm_max']: v = '확인'
    elif pa <= pc - k['pass_drop_refute'] or same < k['same_refute_lt'] or (len(mig_in) - nok) >= 2 or thr_lost >= k['thr_lost_refute']: v = '반박'
    else: v = '부분 확인'
    say(f'  같은 쌍 {same}/{n}, Σpass 대조 {pc} 후보 {pa}, Σthick 대조 {sum(c["thick"] for _, _, c, a in P_near)} 후보 {sum(a["thick"] for _, _, c, a in P_near)}, mig 지표 안 {nok}/{len(mig_in)}, 문턱 잃음 {lost}−{gained}={thr_lost} → {v}')
    OUT['C3'] = dict(mig=mig_in, gate=[dict(seed=s, ctrl_fail=fc, cand_fail=fa) for s, fc, fa in gate_rows], thr_lost=thr_lost, same=same, n=n, pass_ctrl=pc, pass_cand=pa, rows=rows, verdict=v)

    # ── C4 ──
    k = K['C4']; say('\n== C4 long 몸 밖 부피 ==')
    oc = [c['out_frac'] for _, _, c, a in P_long]; oa = [a['out_frac'] for _, _, c, a in P_long]
    for (scn, s, c, a) in P_long:
        say(f'  long s{s}: out {c["out_frac"]} → {a["out_frac"]}, 끝 넓이 {c["area_end"]} → {a["area_end"]}, 음수 스텝 {c["neg_end"]} → {a["neg_end"]}, veinT {c["veinT"]} → {a["veinT"]}, gross_net {c["gross_net"]} → {a["gross_net"]}, turnover {c.get("turnover")} → {a.get("turnover")}')
        for sc, sa in zip(c.get('segments') or [], a.get('segments') or []):
            say(f'      {sc["t"]}: veinT {sc["veinT"]}→{sa["veinT"]} strahler {sc["strahler"]}→{sa["strahler"]} rad {sc["rad_ratio"]}→{sa["rad_ratio"]} amp {sc["sheet_amp"]}→{sa["sheet_amp"]} out {sc["out_frac"]}→{sa["out_frac"]} area {sc["area"]}→{sa["area"]}')
    mc, ma = float(np.mean(oc)), float(np.mean(oa))
    if ma <= mc + k['mean_margin']: v = '확인'
    elif all(y > x + k['mean_margin'] for x, y in zip(oc, oa)): v = '반박'
    else: v = '부분 확인'
    say(f'  평균 대조 {mc:.3f} 후보 {ma:.3f} → {v}')
    OUT['C4'] = dict(ctrl=oc, cand=oa, mean_ctrl=mc, mean_cand=ma, verdict=v)

    # ── C5 ──
    k = K['C5']; say('\n== C5 젖은 넓이 ==')
    res = {}
    for lab, P in (('near', P_near), ('mig', P_mig)):
        rel = [abs(a['area_end'] - c['area_end']) / c['area_end'] for _, _, c, a in P]; sgn = [(a['area_end'] - c['area_end']) / c['area_end'] for _, _, c, a in P]
        res[lab] = dict(med_abs=med(rel), med_signed=med(sgn), big=sum(x > k['big'] for x in rel), max_abs=max(rel))
        say(f'  {lab}: |Δ|/대조 중앙 {med(rel):.4f}, 부호 있는 중앙 {med(sgn):+.4f}, 최대 {max(rel):.3f}, 0.10 넘음 {res[lab]["big"]}')
    if all(r['med_abs'] <= k['med_confirm'] and r['big'] == 0 for r in res.values()): v = '확인'
    elif any(r['med_abs'] > k['med_refute'] for r in res.values()) or sum(r['big'] for r in res.values()) >= k['big_refute']: v = '반박'
    else: v = '부분 확인'
    say('  →', v); OUT['C5'] = dict(res, verdict=v)

    # ── C6 (그림의 정량 대리: 굵은 쌍의 집합이 다른 asym3 시드) ──
    say('\n== C6 (그림은 따로. 정량 대리: asym3 에서 굵은 쌍(배율 ≥ 5)의 집합이 다른 시드) ==')
    diff = []
    for scn, s, c, a in P_food:
        if scn != 'asym3': continue
        sc = {p for p, r in (c['ratio'] or {}).items() if r >= 5}; sa = {p for p, r in (a['ratio'] or {}).items() if r >= 5}
        if sc != sa: diff.append((s, sorted(sc), sorted(sa)))
    say('  다른 시드:', diff); OUT['C6_proxy'] = dict(asym3_diff=diff, n=len(diff))

    # ── C7 ──
    k = K['C7']; say('\n== C7 후보의 스텝 끝 음수 0 ==')
    z = [(scn, s) for scn, s, c, a in P_all if a['neg_end'] != 0]; n0 = len(P_all) - len(z)
    v = '확인' if n0 >= k['all'] else ('부분 확인' if n0 >= k['partial_min'] else '반박')
    say(f'  후보 0 인 실행 {n0}/{len(P_all)}; 0 이 아닌 것 {z} → {v}')
    zc = sum(c['neg_end'] == 0 for _, _, c, a in P_all)
    OUT['C7'] = dict(n=len(P_all), cand_zero=n0, nonzero=z, ctrl_zero=zc, verdict=v)

    # ── W1 ──
    k = K['W1']; say('\n== W1 asym3 굵은 쌍·통과 ==')
    A = [p for p in P_food if p[0] == 'asym3']
    L = sum(c['pass'] and not a['pass'] for _, _, c, a in A); G = sum(a['pass'] and not c['pass'] for _, _, c, a in A)
    dth = sum(a['thick'] - c['thick'] for _, _, c, a in A); D2 = [s for _, s, c, a in A if c['thick'] - a['thick'] >= 2]
    mr = []
    for _, s, c, a in A:
        rc = min((c['ratio'] or {'x': 0}).values()); ra = min((a['ratio'] or {'x': 0}).values())
        mr.append((s, rc, ra, ra / rc if rc > 0 else None))
    lr = med([np.log(x[3]) for x in mr if x[3]]);
    if L - G <= k['chance']['LmG_max'] and dth >= k['chance']['dthick_min'] and len(D2) <= k['chance']['D2_max']: v = '재현 안 됨 (우연)'
    elif L - G >= k['systematic']['LmG_min'] or dth <= k['systematic']['dthick_max'] or len(D2) >= k['systematic']['D2_min']: v = '재현됨 (체계적)'
    else: v = '판정 못 함'
    say(f'  잃음 {L}, 얻음 {G}, Δthick {dth:+d}, 굵은 쌍이 2개 이상 준 시드 {D2}, 가장 가는 쌍 배율의 짝 비 중앙 {np.exp(lr):.3f} → {v}')
    for s, rc, ra, q in mr: say(f'    s{s}: 가장 가는 쌍의 배율 {rc} → {ra}')
    OUT['W1'] = dict(L=L, G=G, dthick=dth, D2=D2, minratio=mr, minratio_pair_med=float(np.exp(lr)), pass_ctrl=sum(c['pass'] for _, _, c, a in A), pass_cand=sum(a['pass'] for _, _, c, a in A), verdict=v)

    # ── W2 ──
    k = K['W2']; say('\n== W2 스텝 안 최소 두께가 더 깊어진 실행 ==')
    deep = [(scn, s, c['h_min_in'], a['h_min_in']) for scn, s, c, a in P_all if a['h_min_in'] < k['deep_abs'] and a['h_min_in'] < k['deep_factor'] * c['h_min_in']]
    deeper_any = [(scn, s, round(c['h_min_in'], 4), round(a['h_min_in'], 4)) for scn, s, c, a in P_all if a['h_min_in'] < c['h_min_in']]
    v = '재현 안 됨' if len(deep) == 0 else ('드묾' if len(deep) <= k['rare'] else '재현됨')
    say(f'  깊어진 실행 {deep} → {v}')
    say(f'  (견줌) 후보가 대조보다 조금이라도 깊은 실행 {len(deeper_any)}/{len(P_all)}: {deeper_any}')
    say(f'  가장 깊은 값: 대조 {min(c["h_min_in"] for _, _, c, a in P_all):.4f}, 후보 {min(a["h_min_in"] for _, _, c, a in P_all):.4f}')
    OUT['W2'] = dict(deep=deep, deeper_any=deeper_any, min_ctrl=min(c['h_min_in'] for _, _, c, a in P_all), min_cand=min(a['h_min_in'] for _, _, c, a in P_all), verdict=v)

    # ── W3 ──
    k = K['W3']; say('\n== W3 굶은 이주 gross_net ==')
    d = [(s, c['gross_net'], a['gross_net'], a['gross_net'] - c['gross_net']) for _, s, c, a in P_mig]
    nl = sum(x[3] < 0 for x in d); dm = med([x[3] for x in d]); below = [s for s, _, ga, _ in d if ga < k['gate']]
    for x in d: say(f'  s{x[0]}: {x[1]:.3f} → {x[2]:.3f} ({x[3]:+.3f})')
    if nl >= k['lower_min'] and dm <= k['med_le']: v = '재현됨 (낮아진다)'
    elif nl <= k['not_lower_max'] or dm > k['not_med_gt']: v = '재현 안 됨'
    else: v = '판정 못 함'
    say(f'  낮아진 시드 {nl}/{len(d)}, 짝 차이 중앙 {dm:+.3f}, 평균 {np.mean([x[3] for x in d]):+.3f}, 문턱 3 아래 후보 {below} → {v}')
    OUT['W3'] = dict(rows=d, n_lower=nl, diff_med=dm, diff_mean=float(np.mean([x[3] for x in d])), below_gate=below, verdict=v)

    # ── W4 ──
    k = K['W4']; say('\n== W4 먹이를 다 먹은 뒤 몸 밖 부피 ==')
    rows = []
    for scn, s, c, a in P_near:
        r = []
        for o in (c, a):
            e = o['_extra']; te = e['t_exh']
            if te is None or any(x is None for x in te): r.append((None, None, None)); continue
            tt = [x for x in (o['t_touch'] or []) if x is not None]
            w0 = max(tt) + 20 if len(tt) == len(o['t_touch']) else None; w1 = min(te); t_all = max(te)
            post = [x['out'] for x in e['rows'] if x['t'] > t_all]; eat = [x['out'] for x in e['rows'] if w0 is not None and w0 <= x['t'] <= w1 + 1e-6]
            pre = [x['out'] for x in e['rows'] if x['t'] <= t_all]
            r.append((max(post) if post else None, max(eat) if eat else None, max(pre) if pre else None))
        rows.append((scn, s, r[0], r[1]))
        say(f'  {scn:9s} s{s}: 다 먹은 뒤 최대 {fm(r[0][0], "%.4f")} → {fm(r[1][0], "%.4f")} | 먹는 동안 최대 {fm(r[0][1], "%.4f")} → {fm(r[1][1], "%.4f")} | 다 먹기 전 최대 {fm(r[0][2], "%.4f")} → {fm(r[1][2], "%.4f")}')
    ok_ = [(scn, s, rc, ra) for scn, s, rc, ra in rows if rc[0] is not None and ra[0] is not None]
    jumps = [(scn, s, rc[0], ra[0]) for scn, s, rc, ra in ok_ if ra[0] > k['thr'] and rc[0] <= k['thr']]
    jc = med([rc[0] for _, _, rc, ra in ok_]); ja = med([ra[0] for _, _, rc, ra in ok_]); q = ja / jc
    ec = med([rc[1] for _, _, rc, ra in ok_ if rc[1] is not None]); ea = med([ra[1] for _, _, rc, ra in ok_ if ra[1] is not None])
    nh = sum(ra[0] > rc[0] for _, _, rc, ra in ok_)
    if len(jumps) >= k['repro_jumps'] or q > k['repro_ratio']: v = '재현됨'
    elif len(jumps) == 0 and q <= k['no_ratio']: v = '재현 안 됨'
    else: v = '드묾'
    say(f'  쓴 짝 {len(ok_)}, 튄 실행 {jumps}, 다 먹은 뒤 최대의 중앙 대조 {jc:.4f} 후보 {ja:.4f} (비 {q:.2f}), 후보가 큰 짝 {nh}/{len(ok_)}; 먹는 동안 중앙 {ec:.4f} → {ea:.4f} → {v}')
    OUT['W4'] = dict(rows=rows, jumps=jumps, post_med_ctrl=jc, post_med_cand=ja, ratio=q, n_cand_higher=nh, n=len(ok_), eat_med_ctrl=ec, eat_med_cand=ea, verdict=v)

    # ── S1 ──
    k = K['S1']; say('\n== S1 부피 오차 ==')
    bad = [(scn, s, c['mass_err'], a['mass_err']) for scn, s, c, a in P_all if a['mass_err'] > max(k['factor'] * c['mass_err'], k['floor'])]
    worst = max(a['mass_err'] for _, _, c, a in P_all)
    v = '문제' if worst > k['bad'] else ('같음' if not bad else '나빠짐')
    say(f'  짝 대조의 10배를 넘은 후보 {bad}, 후보 최대 {worst:.2e}, 대조 최대 {max(c["mass_err"] for _, _, c, a in P_all):.2e} → {v}')
    OUT['S1'] = dict(bad=bad, worst_cand=worst, worst_ctrl=max(c['mass_err'] for _, _, c, a in P_all), verdict=v)

    # ── S2 ──
    k = K['S2']; say('\n== S2 압력 풀이 오차 (다중격자 대 정확한 풀이의 흐름 차이) ==')
    rm = []; rp = []; rx = []; rt = []; big = []
    for scn, s, c, a in P_all:
        fc, fa = c['flux_err'], a['flux_err']
        rm.append(fa[0] / fc[0]); rp.append(fa[1] / fc[1]); rx.append(fa[2] / fc[2]); rt.append(fa[3] / fc[3])
        if fa[2] > k['max_abs'] and fc[2] <= k['max_abs']: big.append((scn, s, fc[2], fa[2]))
        say(f'  {scn:9s} s{s}: 중앙 {fc[0]:.4f}→{fa[0]:.4f}  p90 {fc[1]:.4f}→{fa[1]:.4f}  최대 {fc[2]:.3f}→{fa[2]:.3f}  굵은 간선 중앙 {fc[3]:.4f}→{fa[3]:.4f}')
    mrm, mrp, mrx, mrt = med(rm), med(rp), med(rx), med(rt)
    if mrm > k['bad'] or mrp > k['bad'] or len(big) >= k['max_abs_runs']: v = '나빠짐'
    elif mrm <= k['same_med'] and mrp <= k['same_p90']: v = '같음'
    else: v = '조금 나빠짐'
    by = {}
    for (scn, s, c, a), x, y, zz in zip(P_all, rm, rp, rx): by.setdefault(scn, []).append((x, y, zz))
    for scn, l in by.items(): say(f'    {scn:9s} 비 중앙: 중앙 {med([x[0] for x in l]):.3f}, p90 {med([x[1] for x in l]):.3f}, 최대 {med([x[2] for x in l]):.3f}')
    say(f'  짝 비의 중앙: 중앙 지표 {mrm:.3f}, p90 {mrp:.3f}, 최대 {mrx:.3f}, 굵은 간선 {mrt:.3f}. 비 > 1 인 짝(p90) {sum(x > 1 for x in rp)}/{len(rp)}. 후보 최대 > 1.0 (대조 ≤ 1.0) {big} → {v}')
    OUT['S2'] = dict(ratio_med=mrm, ratio_p90=mrp, ratio_max=mrx, ratio_thick=mrt, n_p90_worse=sum(x > 1 for x in rp), n=len(rp), big=big, by_scn={s_: dict(med=med([x[0] for x in l]), p90=med([x[1] for x in l]), max=med([x[2] for x in l])) for s_, l in by.items()}, verdict=v)

    # ── S3 ──
    k = K['S3']; say('\n== S3 food3_256 ==')
    F = [p for p in P_food if p[0] == 'food3_256']; prob = []
    for _, s, c, a in F:
        say(f'  s{s}: 통과 {c["pass"]}→{a["pass"]} 굵은 쌍 {c["thick"]}→{a["thick"]} out {c["out_frac"]}→{a["out_frac"]} 넓이 {c["area_end"]}→{a["area_end"]} 음수 스텝 {c["neg_end"]}→{a["neg_end"]}')
        if (c['pass'] and not a['pass']) or a['out_frac'] > k['out'] or a['thick'] != c['thick']: prob.append(s)
    v = '문제 없음' if not prob else '문제'
    say('  →', v); OUT['S3'] = dict(problem=prob, verdict=v)

    # ── S4 (탐색) ──
    say('\n== S4 (탐색) 끝의 얇은 셀, 버린 부피, 몸 밖(흐름 기준), food4 ==')
    s4 = []
    for scn, s, c, a in P_all:
        ec, ea = c['_extra'], a['_extra']
        thc, tha = ec['rows'][-1]['thin_g'], ea['rows'][-1]['thin_g']
        mthc = med([r['thin_g'] for r in ec['rows']]); mtha = med([r['thin_g'] for r in ea['rows']])
        ofc = max(r['out_flow'] for r in ec['rows']); ofa = max(r['out_flow'] for r in ea['rows'])
        s4.append(dict(scn=scn, seed=s, thin_end=[thc, tha], thin_med=[mthc, mtha], V_crumb=[ec['V_crumb'] / ec['V0'], ea['V_crumb'] / ea['V0']], crumb_cells=[ec['crumb_cells'], ea['crumb_cells']],
                       out_flow=[ofc, ofa], out=[c['out_frac'], a['out_frac']], neg_cellsteps=[ec['neg_cellsteps'], ea['neg_cellsteps']]))
        say(f'  {scn:9s} s{s}: 얇은 셀 끝 {thc}→{tha} 중앙 {mthc}→{mtha} | V_crumb/V0 {ec["V_crumb"] / ec["V0"]:+.1e}→{ea["V_crumb"] / ea["V0"]:+.1e} 셀 {ec["crumb_cells"]}→{ea["crumb_cells"]} | out {c["out_frac"]}→{a["out_frac"]}, 흐름 기준 {ofc:.4f}→{ofa:.4f} | 음수 셀·스텝 {ec["neg_cellsteps"]}→{ea["neg_cellsteps"]}')
    for scn, s, c, a in P_food:
        if scn == 'food4': say(f'  food4 s{s}: 닿은 시각 {c["t_touch"]} → {a["t_touch"]}, 굵은 쌍 {c["thick"]}→{a["thick"]}, out {c["out_frac"]}→{a["out_frac"]}, fM_end {c["_extra"]["fM_end"]} → {a["_extra"]["fM_end"]}')
    OUT['S4'] = s4


if __name__ == '__main__':
    main()
    if '--json' in sys.argv:
        json.dump(OUT, open(sys.argv[sys.argv.index('--json') + 1], 'w'), ensure_ascii=False, indent=1, default=lambda o: o if not isinstance(o, (np.integer, np.floating, np.bool_)) else o.item())
