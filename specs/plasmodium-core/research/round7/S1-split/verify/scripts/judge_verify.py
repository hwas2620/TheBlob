#!/usr/bin/env python3
"""[검증] 미리 정한 기준(criteria.json)을 채점 요약에 기계적으로 적용해 주장별 표와 판정을 낸다.

usage: judge_verify.py [--json OUT]
읽는 것: verify/summaries/numpy_<실행>.json (채점기 bmet.py 의 출력), verify/summaries/extra_<실행>.json (extra_metrics.py),
         stage0/results/b/numpy_b_mig_s1~15.json (H4 의 견줄 범위: 작성자 쪽 기존 지금 규칙 실행)
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.normpath(os.path.join(HERE, '..'))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'stage0'))
CR = json.load(open(os.path.join(HERE, 'criteria.json')))
T0, T1 = CR['tags']['current'], CR['tags']['candidate']
OUT = {}


def S(scn, seed, tag, kind='numpy'):
    f = os.path.join(V, 'summaries', f'{kind}_b_{scn}_s{seed}_{tag}.json')
    return json.load(open(f)) if os.path.exists(f) else None


def f(x, fmt='%.3f'):
    if x is None: return '없음'
    if isinstance(x, bool): return '예' if x else '아니오'
    return fmt % x


def pairs(scn):
    out = []
    for s in CR['plan'][scn]:
        a, b = S(scn, s, T0), S(scn, s, T1)
        out.append((s, a, b, S(scn, s, T0, 'extra'), S(scn, s, T1, 'extra')))
    return out


def complete(rows):
    return all(a is not None and b is not None and a.get('complete') and b.get('complete') for _, a, b, _, _ in rows)


def verdict(name, v, why):
    print(f'\n  ▶ {name} 판정: **{v}** — {why}')
    OUT[name] = dict(verdict=v, why=why)


def h1():
    c = CR['H1']; rows = pairs('long')
    print('\n## H1 — ' + c['claim'])
    print('| 시드 | out_frac 지금 | out_frac 후보 | 끝 넓이 지금 | 끝 넓이 후보 | 후보: 기억 셀을 지운 몸 밖 부피(최대) | 후보: 기억 가닥으로만 이어진 저장 시각 수 | 그때 한 주기에 오가는 부피 비율(중앙 / 최대) |')
    print('|---|---|---|---|---|---|---|---|')
    tab = []
    for s, a, b, ea, eb in rows:
        if a is None or b is None: print(f'| {s} | 없음 | | | | | | |'); continue
        cuts = [q for q in (eb or {}).get('cuts', []) if q.get('joined') and q['out'] < 0.10 and q['out_strip'] >= 0.10]
        car = [q['carry'] for q in cuts if q.get('carry') is not None]
        osm = max([v for v in (eb or {}).get('series', {}).get('out_strip', []) if v is not None], default=None)
        nst = len((eb or {}).get('series', {}).get('t', []))
        print(f"| {s} | {f(a['out_frac'])} | {f(b['out_frac'])} | {a['area_end']} | {b['area_end']} | {f(osm)} | {len(cuts)}/{nst} | {f(np.median(car) if car else None, '%.1e')} / {f(max(car) if car else None, '%.1e')} |")
        tab.append(dict(seed=s, base=a['out_frac'], cand=b['out_frac'], area_base=a['area_end'], area_cand=b['area_end'], out_strip_max=osm, n_nominal=len(cuts), n_states=nst, carry_med=float(np.median(car)) if car else None, carry_max=max(car) if car else None))
    OUT['H1_table'] = tab
    if not complete(rows): return verdict('H1', '판정 불가', '끝나지 않은 실행이 있다')
    n = len(tab); ok = sum(1 for r in tab if r['cand'] < c['cand_out_frac_lt']); split = sum(1 for r in tab if r['base'] >= c['base_split_ge'])
    lo, hi = c['base_stated_range']; stated = sum(1 for r in tab if lo <= r['base'] <= hi)
    nominal = sum(1 for r in tab if r['n_nominal'] > 0 and (r['carry_med'] is not None and r['carry_med'] < CR['explore']['carry_nominal_lt']))
    msg = f'후보 < {c["cand_out_frac_lt"]} 이 {ok}/{n}, 지금 규칙 ≥ {c["base_split_ge"]} 이 {split}/{n} (지금 규칙이 {lo}~{hi} 안인 시드 {stated}/{n}), 이름만 이어진 구간이 있는 후보 시드 {nominal}/{n}'
    if ok == n and split >= 2 / 3 * n - 1e-9:
        v = '확인' if nominal == 0 else '부분 확인'
        if nominal: msg += ' → 숫자는 확인, 뜻은 유보 (미리 정한 규칙: 숫자가 3/3 이어도 (나)의 뜻으로 이름만 이어진 몸이면 부분 확인)'
    elif ok == n: v = '부분 확인'; msg += ' → 후보는 3/3 이지만 지금 규칙이 새 시드에서 충분히 갈라지지 않았다'
    elif ok >= 2 / 3 * n - 1e-9: v = '부분 확인'
    else: v = '반박'
    verdict('H1', v, msg)


def h2():
    c = CR['H2']; rows = pairs('food4')
    print('\n## H2 — ' + c['claim'])
    print('| 시드 | 닿은 시각 지금 (먹이 4개) | 닿은 시각 후보 | 모두 닿음 지금/후보 | out_frac 지금 | out_frac 후보 | 굵은 쌍 지금 | 굵은 쌍 후보 | 같은 성분 ≥0.9 인 쌍 지금/후보 | 먹는 동안 몸 최소 지금/후보 | 통과 지금/후보 | 먹은 양 지금/후보 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    tab = []
    for s, a, b, ea, eb in rows:
        if a is None or b is None: print(f'| {s} | 없음 |' + ' |' * 10); continue
        tt = lambda r: '/'.join(f(v, '%.0f') for v in r['t_touch'])
        print(f"| {s} | {tt(a)} | {tt(b)} | {f(a['reached'])}/{f(b['reached'])} | {f(a['out_frac'])} | {f(b['out_frac'])} | {a['thick']}/{a['pairs']} | {b['thick']}/{b['pairs']} | {a['same_ok']}/{b['same_ok']} | {f(a.get('body_min'))}/{f(b.get('body_min'))} | {f(a['pass'])}/{f(b['pass'])} | {f((ea or {}).get('vol', {}).get('Vinj'), '%.0f')}/{f((eb or {}).get('vol', {}).get('Vinj'), '%.0f')} |")
        tab.append(dict(seed=s, reached_base=a['reached'], reached_cand=b['reached'], out_base=a['out_frac'], out_cand=b['out_frac'], thick_base=a['thick'], thick_cand=b['thick'], pass_base=a['pass'], pass_cand=b['pass'],
                        t_touch_base=a['t_touch'], t_touch_cand=b['t_touch'], body_min_cand=b.get('body_min'), same_ok_cand=b['same_ok'], vinj_base=(ea or {}).get('vol', {}).get('Vinj'), vinj_cand=(eb or {}).get('vol', {}).get('Vinj')))
    OUT['H2_table'] = tab
    if not complete(rows): return verdict('H2', '판정 불가', '끝나지 않은 실행이 있다')
    ob = np.array([r['out_base'] for r in tab]); oc = np.array([r['out_cand'] for r in tab]); d = oc - ob
    print(f'  out_frac: 지금 규칙 평균 {ob.mean():.3f} (범위 {ob.min():.3f}~{ob.max():.3f}), 후보 평균 {oc.mean():.3f} (범위 {oc.min():.3f}~{oc.max():.3f}), 짝 차이(후보 − 지금) {d.mean():+.3f} ± {d.std(ddof=1):.3f}, 후보가 더 나쁜 시드 {int((d > 0).sum())}/{d.size}')
    vb = np.array([r['vinj_base'] for r in tab]); vc = np.array([r['vinj_cand'] for r in tab])
    print(f'  먹은 양(T=700 까지, 넷 합쳐 4800 가운데): 지금 규칙 평균 {vb.mean():.0f}, 후보 평균 {vc.mean():.0f}, 짝 차이 {np.mean(vc - vb):+.0f} ± {np.std(vc - vb, ddof=1):.0f}')
    OUT['H2_stats'] = dict(out_base_mean=float(ob.mean()), out_cand_mean=float(oc.mean()), diff_mean=float(d.mean()), diff_sd=float(d.std(ddof=1)), cand_worse=int((d > 0).sum()), vinj_base_mean=float(vb.mean()), vinj_cand_mean=float(vc.mean()))
    n = len(tab); na = sum(r['reached_cand'] for r in tab); nb_ = sum(r['out_cand'] < c['cand_out_frac_lt'] for r in tab); tb = sum(r['thick_base'] for r in tab); tc = sum(r['thick_cand'] for r in tab)
    each = all(r['thick_cand'] >= r['thick_base'] for r in tab)
    msg = (f'(a) 모든 먹이에 닿음 {na}/{n} (지금 규칙 {sum(r["reached_base"] for r in tab)}/{n}), (b) out_frac < {c["cand_out_frac_lt"]} 이 {nb_}/{n} (지금 규칙 {sum(r["out_base"] < c["cand_out_frac_lt"] for r in tab)}/{n}), '
           f'(c) 굵은 쌍의 합 후보 {tc} 대 지금 {tb} (시드마다 후보 ≥ 지금: {"예" if each else "아니오"}). 통과 시드: 후보 {sum(r["pass_cand"] for r in tab)}/{n}, 지금 {sum(r["pass_base"] for r in tab)}/{n}')
    if na == n and nb_ == n and tc > tb and each: v = '확인'
    elif na >= c['partial_min_seeds'] and nb_ >= c['partial_min_seeds'] and tc > tb: v = '부분 확인'
    elif na <= n // 2 or nb_ <= n // 2 or tc <= tb: v = '반박'
    else: v = '부분 확인과 반박의 사이'
    verdict('H2', v, msg)


def h3():
    c = CR['H3']
    print('\n## H3 — ' + c['claim'])
    print('| 시나리오 | 시드 | 통과 지금/후보 | 굵은 쌍 지금/후보 | 닿은 시각 지금 | 닿은 시각 후보 | 최대 차이 | 가장 가는 쌍의 배율 지금/후보 | 같은 성분 ≥0.9 지금/후보 | 몸 최소 지금/후보 | 먹은 양 지금/후보 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    tab = []; ok_all = True
    for scn in ('food3', 'food3_256', 'asym3'):
        rows = pairs(scn); ok_all &= complete(rows)
        for s, a, b, ea, eb in rows:
            if a is None or b is None: print(f'| {scn} | {s} | 없음 |' + ' |' * 8); continue
            d = [abs(x - y) if (x is not None and y is not None) else None for x, y in zip(a['t_touch'], b['t_touch'])]
            late = [(y - x) if (x is not None and y is not None) else None for x, y in zip(a['t_touch'], b['t_touch'])]
            dmax = None if None in d else max(d); tt = lambda r: '/'.join(f(v, '%.1f') for v in r['t_touch'])
            mr = lambda r: min(r['ratio'].values()) if r.get('ratio') and len(r['ratio']) == r['pairs'] else 0.0
            print(f"| {scn} | {s} | {f(a['pass'])}/{f(b['pass'])} | {a['thick']}/{b['thick']} | {tt(a)} | {tt(b)} | {f(dmax, '%.1f')} | {f(mr(a), '%.1f')}/{f(mr(b), '%.1f')} | {a['same_ok']}/{b['same_ok']} | {f(a.get('body_min'))}/{f(b.get('body_min'))} | {f((ea or {}).get('vol', {}).get('Vinj'), '%.0f')}/{f((eb or {}).get('vol', {}).get('Vinj'), '%.0f')} |")
            tab.append(dict(scn=scn, seed=s, pass_base=a['pass'], pass_cand=b['pass'], thick_base=a['thick'], thick_cand=b['thick'], dmax=dmax, late_max=None if None in late else max(late), minratio_base=mr(a), minratio_cand=mr(b),
                            same_ok_base=a['same_ok'], same_ok_cand=b['same_ok'], body_min_base=a.get('body_min'), body_min_cand=b.get('body_min')))
    OUT['H3_table'] = tab
    if not ok_all: return verdict('H3', '판정 불가', '끝나지 않은 실행이 있다')
    n = len(tab); same_pass = sum(r['pass_base'] == r['pass_cand'] for r in tab); same_thick = sum(r['thick_base'] == r['thick_cand'] for r in tab)
    touch_ok = sum(r['dmax'] is not None and r['dmax'] <= c['touch_same_within'] for r in tab); pb = sum(r['pass_base'] for r in tab); pc = sum(r['pass_cand'] for r in tab)
    tb = sum(r['thick_base'] for r in tab); tc = sum(r['thick_cand'] for r in tab); late = max((r['late_max'] for r in tab if r['late_max'] is not None), default=0.0)
    msg = f'pass 같음 {same_pass}/{n}, thick 같음 {same_thick}/{n}, 닿은 시각 차이 ≤ {c["touch_same_within"]} 인 쌍 {touch_ok}/{n} (가장 늦어진 것 {late:+.1f}). Σpass 후보 {pc} 대 지금 {pb}, Σthick 후보 {tc} 대 지금 {tb}'
    if same_pass == n and same_thick == n and touch_ok == n: v = '확인'
    elif pc <= pb - c['refute_pass_drop'] or late > c['touch_late_refute']: v = '반박'
    elif touch_ok == n and pc >= pb - c['partial_pass_slack'] and tc >= tb - c['partial_thick_slack']: v = '부분 확인'
    else: v = '부분 확인과 반박의 사이 (수치를 보고 고른다)'
    verdict('H3 (숫자만. 그림의 "멈춰 선 가장자리"는 따로 본다)', v, msg)


def h4():
    c = CR['H4']; rows = pairs('mig')
    print('\n## H4 — ' + c['claim'])
    base15 = []
    for s in range(1, 16):
        p = os.path.join(STAGE0, 'results', 'b', f'numpy_b_mig_s{s}.json')
        if os.path.exists(p): base15.append(json.load(open(p)))
    if not complete(rows):
        for s, a, b, ea, eb in rows: print(f'  시드 {s}:', '있음' if a and b else '없음')
        return verdict('H4', '판정 불가', '끝나지 않은 실행이 있다')
    print(f'견줄 범위: 기존 지금 규칙 실행 {len(base15)}개 + 내 v0 {len(rows)}개')
    print('| 지표 | 기존 15개의 범위 | 내 v0 (시드 ' + ', '.join(str(r[0]) for r in rows) + ') | 19개의 범위 | 후보 (같은 시드) | 범위 안 | 후보 중앙이 범위 안 | 짝 차이(후보 − 지금) 평균 ± 표준편차 |')
    print('|---|---|---|---|---|---|---|---|')
    fail = []; tab = []
    for k in c['metrics']:
        fm = '%.4f' if k == 'out_frac' else ('%.2f' if k == 'disp300' else '%.3f')
        b15 = [o[k] for o in base15]; v0 = [a[k] for _, a, _, _, _ in rows]; vp = [b[k] for _, _, b, _, _ in rows]
        lo, hi = min(b15 + v0), max(b15 + v0); inside = [lo <= x <= hi for x in vp]; med_in = bool(lo <= float(np.median(vp)) <= hi); d = np.array(vp) - np.array(v0)
        ok = sum(inside) >= c['min_inside_per_metric'] and med_in
        if not ok: fail.append(k)
        print(f"| {k} | {fm % min(b15)}~{fm % max(b15)} | {' / '.join(fm % x for x in v0)} | {fm % lo}~{fm % hi} | {' / '.join(fm % x for x in vp)} | {sum(inside)}/{len(vp)} | {f(med_in)} | {d.mean():+.3g} ± {d.std(ddof=1):.3g} |")
        tab.append(dict(metric=k, base15=[min(b15), max(b15)], v0=v0, cand=vp, range19=[lo, hi], inside=int(sum(inside)), median_inside=med_in, diff_mean=float(d.mean()), diff_sd=float(d.std(ddof=1)), sd15=float(np.std(b15, ddof=1))))
    g = c['gate']; gate_fail = []
    for s, a, b, ea, eb in rows:
        chk = lambda r: dict(move=(r['disp300'] >= g['disp300_ge'] and r['disp_angle'] <= g['disp_angle_le']), veinT=r['veinT'] >= g['veinT_ge'], gross=r['gross_net'] >= g['gross_net_ge'], out=r['out_frac'] <= g['out_frac_le'])
        ca, cb = chk(a), chk(b)
        for k in ca:
            if ca[k] and not cb[k]: gate_fail.append(f'시드 {s}: {k}')
    print('  관문 문턱을 지금 규칙은 넘는데 후보가 못 넘는 것:', ', '.join(gate_fail) if gate_fail else '없음')
    # 주장 밖: 유인원에 닿은 뒤(t=300~400)의 움직임
    print('\n  주장 밖 — 유인원에 닿은 뒤 (포만 항이 걸리는 구간)')
    print('  | 시드 | 닿은 시각 지금/후보 | 새로 젖은 셀 t=300~400 지금/후보 | 넓이 t=400 지금/후보 | 이동 각 지금/후보 | 음수 스텝 지금/후보 |')
    print('  |---|---|---|---|---|---|')
    nw0 = []; nw1 = []; ar0 = []; ar1 = []
    for s, a, b, ea, eb in rows:
        w = lambda e: next((x[2] for x in e['new_by_window'] if x[0] == 300), None)
        nw0.append(w(ea)); nw1.append(w(eb)); ar0.append(a['area_end']); ar1.append(b['area_end'])
        print(f"  | {s} | {f(a['t_touch'][0], '%.1f')}/{f(b['t_touch'][0], '%.1f')} | {w(ea):.0f}/{w(eb):.0f} | {a['area_end']}/{b['area_end']} | {a['disp_angle']}/{b['disp_angle']} | {a['neg_end']}/{b['neg_end']} |")
    dn = np.array(nw1) - np.array(nw0); da = np.array(ar1) - np.array(ar0)
    sys_new = bool((np.all(dn > 0) or np.all(dn < 0)) and abs(dn.mean()) > c['extra_sd_factor'] * np.std(nw0, ddof=1))
    sys_area = bool((np.all(da > 0) or np.all(da < 0)) and abs(da.mean()) > c['extra_sd_factor'] * np.std(ar0, ddof=1))
    print(f'  새로 젖은 셀의 짝 차이 {dn.mean():+.0f} ± {dn.std(ddof=1):.0f} (지금 규칙의 시드 표준편차 {np.std(nw0, ddof=1):.0f}) → 한쪽으로 쏠린 차이: {f(sys_new)} · 넓이의 짝 차이 {da.mean():+.0f} ± {da.std(ddof=1):.0f} (시드 표준편차 {np.std(ar0, ddof=1):.0f}) → {f(sys_area)}')
    OUT['H4_table'] = tab; OUT['H4_extra'] = dict(new300_400_base=nw0, new300_400_cand=nw1, area400_base=ar0, area400_cand=ar1, systematic_new=sys_new, systematic_area=sys_area)
    msg = f'어긴 지표 {len(fail)}개' + (f' ({", ".join(fail)})' if fail else '') + f', 관문 문턱을 잃은 것 {len(gate_fail)}건'
    v = '반박' if (len(fail) >= 2 or gate_fail) else ('부분 확인' if len(fail) == 1 else '확인')
    verdict('H4', v, msg)


ALLSCN = ('food3', 'food3_256', 'asym3', 'food4', 'mig', 'long')
FOODSCN = ('food3', 'food3_256', 'asym3', 'food4')


def h5():
    c = CR['H5']
    print('\n## H5 — ' + c['claim'])
    print('| 시나리오 | 시드 | 음수 스텝 지금 | 음수 스텝 후보 | 음수 셀·스텝 지금/후보 | 스텝 끝 최소 두께 지금 | 후보 | 스텝 안 최소 지금/후보 |')
    print('|---|---|---|---|---|---|---|---|')
    tab = []; ok_all = True
    for scn in ALLSCN:
        rows = pairs(scn); ok_all &= complete(rows)
        for s, a, b, ea, eb in rows:
            if a is None or b is None: print(f'| {scn} | {s} | 없음 | | | | | |'); continue
            print(f"| {scn} | {s} | {a['neg_end']} | {b['neg_end']} | {a['neg_end_cellsteps']}/{b['neg_end_cellsteps']} | {a['h_min_end']:.5f} | {b['h_min_end']:.5f} | {a['h_min_in']:.4f}/{b['h_min_in']:.4f} |")
            tab.append(dict(scn=scn, seed=s, base=a['neg_end'], cand=b['neg_end'], hmin_base=a['h_min_end'], hmin_cand=b['h_min_end'], cs_base=a['neg_end_cellsteps'], cs_cand=b['neg_end_cellsteps'], hin_base=a['h_min_in'], hin_cand=b['h_min_in']))
    OUT['H5_table'] = tab
    if not ok_all: return verdict('H5', '판정 불가', '끝나지 않은 실행이 있다')
    fd = [r for r in tab if r['scn'] in FOODSCN]; st = [r for r in tab if r['scn'] not in FOODSCN]
    f_ok = sum(r['cand'] <= c['food_single_digit_le'] for r in fd); f10 = sum(r['cand'] >= 10 for r in fd); f100 = sum(r['cand'] >= 100 for r in fd)
    s_ok = sum(r['cand'] <= c['starved_few_le'] for r in st); s20 = sum(r['cand'] > 20 for r in st)
    b_th = sum(r['base'] >= c['base_food_thousands_ge'] for r in fd); b_st0 = sum(r['base'] == 0 for r in st)
    deep = min(r['hmin_cand'] for r in tab)
    msg = (f'후보의 먹이 실행 ≤ {c["food_single_digit_le"]}: {f_ok}/{len(fd)} (최대 {max(r["cand"] for r in fd)}), 굶은 실행 ≤ {c["starved_few_le"]}: {s_ok}/{len(st)} (최대 {max(r["cand"] for r in st)}). '
           f'지금 규칙: 먹이 실행 ≥ {c["base_food_thousands_ge"]} 이 {b_th}/{len(fd)}, 굶은 실행 0 이 {b_st0}/{len(st)}. 후보의 스텝 끝 최소 두께 {deep:.5f} (작성자: {c["depth_stated"]} 쯤)')
    base_ok = b_th >= c['base_food_frac_min'] * len(fd) - 1e-9 and b_st0 == len(st)
    if f100 or f10 >= 3 or s20: v = '반박'
    elif f_ok == len(fd) and s_ok == len(st): v = '확인' if base_ok else '부분 확인'
    elif f10 <= 2 and not f100 and not s20: v = '부분 확인'
    else: v = '부분 확인과 반박의 사이'
    if not base_ok: msg += ' · 지금 규칙 쪽 서술("먹이 실행은 수천, 굶은 실행은 0")이 새 시드에서 다 맞지는 않는다'
    if deep < c['depth_flag_below']: msg += f' · 깊이가 {c["depth_flag_below"]} 보다 깊다'
    verdict('H5', v, msg)


def h6():
    c = CR['H6']
    print('\n## H6 — ' + c['claim'])
    print('| 시나리오 | 시드 | mass_err 지금 | mass_err 후보 | V_crumb | 버린 셀 수 | V_crumb/V_end | V_crumb/V0 | 진짜 부피 변화 (V_end−V0−Vinj)/V0 | 장부 | 누적 버림이 줄어든 횟수(합) | 절댓값 합/V0 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    tab = []; ok_all = True
    for scn in ALLSCN:
        rows = pairs(scn); ok_all &= complete(rows)
        for s, a, b, ea, eb in rows:
            if a is None or b is None or eb is None: print(f'| {scn} | {s} | 없음 |' + ' |' * 9); continue
            v = eb['vol']; ab = v.get('step_abs_sum', v.get('drop_abs_sum_logres', 0.0)) / v['V0']
            print(f"| {scn} | {s} | {a['mass_err']:.1e} | {b['mass_err']:.1e} | {v['V_crumb']:.4f} | {v['crumb_cells']} | {v['crumb_over_Vend']:.1e} | {v['crumb_over_V0']:.1e} | {v['true_change']:.1e} | {v['books']:.0e} | {v.get('drop_neg_incr', 0)} ({v.get('drop_neg_sum', 0.0):.4f}) | {ab:.1e} |")
            tab.append(dict(scn=scn, seed=s, me_base=a['mass_err'], me_cand=b['mass_err'], V_crumb=v['V_crumb'], cells=v['crumb_cells'], over_Vend=v['crumb_over_Vend'], over_V0=v['crumb_over_V0'], true_change=v['true_change'], books=v['books'],
                            neg_incr=v.get('drop_neg_incr', 0), neg_sum=v.get('drop_neg_sum', 0.0), abs_over_V0=ab, base_true_change=(ea or {}).get('vol', {}).get('true_change')))
    OUT['H6_table'] = tab
    if not ok_all: return verdict('H6', '판정 불가', '끝나지 않은 실행이 있다')
    # V_crumb 는 부호가 있다(음수 두께 셀을 버리면 음수). 크기로 견준다: |V_crumb| (기준을 적을 때 부호를 생각하지 못했다. scripts/criteria_changes.json 에 적었다)
    n = len(tab); me_ok = sum(r['me_cand'] <= max(c['mass_err_factor'] * r['me_base'], c['mass_err_floor']) for r in tab); ve = sum(abs(r['over_Vend']) < c['crumb_frac_lt'] for r in tab); v0 = sum(abs(r['over_V0']) < c['crumb_frac_lt'] for r in tab)
    bk = sum(r['books'] <= c['books_tol'] for r in tab); ab = sum(r['abs_over_V0'] < c['crumb_frac_lt'] for r in tab)
    msg = (f'mass_err 같은 크기 {me_ok}/{n}, V_crumb/V_end < 1e-3: {ve}/{n} (크기의 최대 {max(abs(r["over_Vend"]) for r in tab):.1e}), |V_crumb|/V0 < 1e-3: {v0}/{n} (크기의 최대 {max(abs(r["over_V0"]) for r in tab):.1e}), V_crumb 가 음수(부피가 생김)인 실행 {sum(r["V_crumb"] < 0 for r in tab)}/{n}, 장부 맞음 {bk}/{n}, '
           f'절댓값 합/V0 < 1e-3: {ab}/{n} (최대 {max(r["abs_over_V0"] for r in tab):.1e}), 음수 셀을 버린 실행 {sum(r["neg_incr"] > 0 for r in tab)}/{n}')
    if ve < n or bk < n: v = '반박'
    elif me_ok == n and v0 == n and ab == n: v = '확인'
    else: v = '부분 확인'
    verdict('H6', v, msg)


def explore():
    e = CR['explore']
    print('\n## (가) 붙잡은 옛 관이 쌓이는가 — ' + e['accum_rule'])
    for scn in ('long',):
        print('| 시드 | 규칙 | 넓이: 200~400 / 400~800 / 800~1200 / 1200~1600 / 1600~2000 | 얇은 셀 | 기억으로만 남은 셀 | 얇은 셀의 부피 비율(끝) | 새로 젖은 셀 (같은 구간) | 한 번이라도 젖은 셀 |')
        print('|---|---|---|---|---|---|---|---|')
        acc = []
        for s, a, b, ea, eb in pairs(scn):
            for tag, ex in ((T0, ea), (T1, eb)):
                if ex is None: continue
                sr = ex['series']; t = np.array(sr['t']); segs = [(200, 400), (400, 800), (800, 1200), (1200, 1600), (1600, 2000.5)]
                m = lambda k: [float(np.mean([v for v, tt in zip(sr[k], t) if lo <= tt < hi])) for lo, hi in segs]
                ar, th, mo = m('area'), m('thin'), m('memonly')
                nw = [x[2] for x in ex['new_by_window'] if x[0] >= 200][:5]
                print(f"| {s} | {tag} | {' / '.join('%.0f' % v for v in ar)} | {' / '.join('%.0f' % v for v in th)} | {' / '.join('%.0f' % v for v in mo)} | {sr['vthin'][-1]:.3f} | {' / '.join('%.0f' % v for v in nw)} | {ex['ever_wet']} |")
                if tag == T1:
                    grow = lambda v: bool(v[2] < v[3] < v[4] and v[4] > (1 + e['accum_growth_gt']) * v[3])
                    acc.append(dict(seed=s, area=ar, thin=th, memonly=mo, grow_area=grow(ar), grow_thin=grow(th), new=nw))
        OUT['accum'] = acc
        if acc: print(f"  → 후보에서 'T=2000 까지 포화하지 않고 쌓인다' (넓이): {sum(r['grow_area'] for r in acc)}/{len(acc)}, (얇은 셀): {sum(r['grow_thin'] for r in acc)}/{len(acc)}")
    print('\n## (나) 붙잡힌 가닥이 물질을 나르는가 — ' + e['strip_rule'] + ' · ' + e['carry_rule'])
    print('| 시나리오 | 시드 | 규칙 | out_frac | 기억 셀을 지운 out(최대) | 저장 시각 수 | 가닥으로만 이어진 시각 수 | 그 구간 | 병목 전도도 C (중앙) | 절단 총유량 (중앙) | 한 주기 오가는 부피/작은 덩어리 (중앙, 최대) | 판단 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    car = []
    for scn in ('long', 'food4', 'mig', 'food3', 'food3_256', 'asym3'):
        for s, a, b, ea, eb in pairs(scn):
            for tag, sm, ex in ((T0, a, ea), (T1, b, eb)):
                if ex is None or sm is None: continue
                cuts = [q for q in ex['cuts'] if q.get('joined') and q['out_strip'] >= 0.10 and q['out'] < 0.10]
                osm = max([v for v in ex['series']['out_strip'] if v is not None], default=0.0)
                if not cuts and (scn not in ('long', 'food4')): continue
                cc = [q['carry'] for q in cuts]; bn = [q['bnC'] for q in cuts]; cq = [q['cutQ'] for q in cuts]
                if cuts:
                    md = float(np.median(cc)); kind = '실제로 나른다' if md >= e['carry_real_ge'] else ('이름만 이어져 있다' if md < e['carry_nominal_lt'] else '약하게 나른다')
                    print(f"| {scn} | {s} | {tag} | {sm['out_frac']:.3f} | {osm:.3f} | {len(ex['series']['t'])} | {len(cuts)} | t={cuts[0]['t']:.0f}~{cuts[-1]['t']:.0f} | {np.median(bn):.2g} | {np.median(cq):.2g} | {md:.1e}, {max(cc):.1e} | {kind} |")
                    car.append(dict(scn=scn, seed=s, tag=tag, out=sm['out_frac'], out_strip_max=osm, n=len(cuts), t0=cuts[0]['t'], t1=cuts[-1]['t'], bnC_med=float(np.median(bn)), cutQ_med=float(np.median(cq)), carry_med=md, carry_max=max(cc), kind=kind))
                else:
                    print(f"| {scn} | {s} | {tag} | {sm['out_frac']:.3f} | {osm:.3f} | {len(ex['series']['t'])} | 0 | - | - | - | - | - |")
    OUT['carry'] = car
    # 기능으로 본 갈라짐: 기억으로만 남은 셀을 지우고 잰 몸 밖 부피 (지금 규칙에서는 out 과 같다)
    print('\n## (나-2) 오래 굶긴 실행: 기능으로 갈라져 있던 시간 (기억으로만 남은 셀을 지운 몸 밖 부피 ≥ 0.10 인 저장 시각의 비율)')
    print('| 시드 | 규칙 | out_frac (채점기) | 지운 뒤의 최대 | 갈라져 있던 시각의 비율: 채점기 정의 | 지운 뒤 | 처음 갈라진 시각 (지운 뒤) | 끝(t=T)의 값 (지운 뒤) | 유인원 원반이 젖어 있던 시각의 비율 (t ≥ 400) |')
    print('|---|---|---|---|---|---|---|---|---|')
    fs = []
    for s, a, b, ea, eb in pairs('long'):
        for tag, sm, ex in ((T0, a, ea), (T1, b, eb)):
            if ex is None or sm is None: continue
            sr = ex['series']; t = np.array(sr['t']); o = np.array(sr['out'], float); os_ = np.array([v if v is not None else 0.0 for v in sr['out_strip']], float)
            first = next((tt for tt, v in zip(t, os_) if v >= 0.10), None); dw = np.array([d[0] for d in sr['disc_wet']]); late = t >= 400
            print(f"| {s} | {tag} | {sm['out_frac']:.3f} | {os_.max():.3f} | {(o >= 0.10).mean():.2f} | {(os_ >= 0.10).mean():.2f} | {f(first, '%.0f')} | {os_[-1]:.3f} | {(dw[late] > 0).mean():.2f} |")
            fs.append(dict(seed=s, tag=tag, out=sm['out_frac'], strip_max=float(os_.max()), frac_out=float((o >= 0.10).mean()), frac_strip=float((os_ >= 0.10).mean()), first=first, end=float(os_[-1]), disc_wet_frac=float((dw[late] > 0).mean())))
    OUT['functional_split'] = fs
    print('\n## (다-3) 멈춤: 마지막으로 새 셀이 젖은 시각과 마지막으로 셀이 마른 시각 (그 뒤로 끝까지 젖음도 마름도 없으면 몸이 멈춘 것이다)')
    print('| 시나리오 | 시드 | 규칙 | 마지막으로 젖은 시각 | 마지막으로 마른 시각 | 끝까지 변화 없던 시간 | 끝 넓이 | 한 번이라도 젖은 셀의 비율 |')
    print('|---|---|---|---|---|---|---|---|')
    st = []
    for scn in ('long', 'mig', 'food4', 'food3', 'food3_256', 'asym3'):
        for s, a, b, ea, eb in pairs(scn):
            for tag, ex in ((T0, ea), (T1, eb)):
                if ex is None or 'still_for' not in ex: continue
                if scn != 'long' and ex['still_for'] < 5: continue
                print(f"| {scn} | {s} | {tag} | {f(ex['last_new_t'], '%.1f')} | {f(ex['last_dry_t'], '%.1f')} | {ex['still_for']:.1f} | {ex['area_end']} | {ex['ever_wet_frac']:.3f} |")
                st.append(dict(scn=scn, seed=s, tag=tag, last_new=ex['last_new_t'], last_dry=ex['last_dry_t'], still_for=ex['still_for'], ever_wet_frac=ex['ever_wet_frac']))
    OUT['still'] = st
    print('\n## (다-2) 먼 먹이 넷: 먹이를 덮은 것이 본체인가 (가장 큰 덩어리에 든 젖은 셀이 먹이 원반에 있는가. 저장 시각 기준)')
    print('| 시드 | 규칙 | 끝에 덮여 있는 먹이 | 끝에 본체가 덮고 있는 먹이 | 먹이별 처음 덮인 시각 | 먹이별 본체가 처음 덮은 시각 | 덮여 있던 시각 가운데 본체가 덮은 비율 |')
    print('|---|---|---|---|---|---|---|')
    fb = []
    for s, a, b, ea, eb in pairs('food4'):
        for tag, ex in ((T0, ea), (T1, eb)):
            if ex is None or 'food_body' not in ex: continue
            q = ex['food_body']; yn = lambda v: ''.join('O' if x else 'x' for x in v); tt = lambda v: '/'.join(f(x, '%.0f') for x in v)
            print(f"| {s} | {tag} | {yn(q['end_covered'])} | {yn(q['end_by_body'])} | {tt(q['first_covered_t'])} | {tt(q['first_by_body_t'])} | {'/'.join(f(x, '%.2f') for x in q['frac_covered_by_body'])} |")
            fb.append(dict(seed=s, tag=tag, **q))
    OUT['food_body'] = fb


def main():
    print(f'# 판정 (기준 파일 criteria.json, 지금 규칙 = {T0}, 후보 = {T1})')
    for fn in (h1, h2, h3, h4, h5, h6, explore):
        try: fn()
        except Exception as ex:      # 끝나지 않은 실행이 있을 때도 나머지 표는 낸다
            import traceback; print(f'\n[{fn.__name__} 실패: {ex!r}]'); traceback.print_exc()
    if '--json' in sys.argv:
        json.dump(OUT, open(sys.argv[sys.argv.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
