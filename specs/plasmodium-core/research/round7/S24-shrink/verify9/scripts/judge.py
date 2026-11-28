#!/usr/bin/env python3
"""verify9 판정: verify9/out/run_*.json 을 읽어 CRITERIA.md 의 기준을 적용한다. judge.json 과 judge.txt 를 쓴다.

usage: judge.py [OUT_DIR] [RESULT_PREFIX]
"""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
V9 = os.path.normpath(os.path.join(HERE, '..'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(V9, 'out')
PRE = sys.argv[2] if len(sys.argv) > 2 else os.path.join(V9, 'judge')
RUNS = os.path.normpath(os.path.join(V9, '..', 'model', 'runs'))

OK, NO, NA, PART = '맞음', '틀림', '판정 못 함', '일부 틀림'
FOOD_SCN = ('food3', 'asym3', 'food4'); PAIR_SCN = ('mig', 'long', 'food3', 'asym3', 'food4', 'slimeall'); FLOW_SCN = ('mig', 'long', 'food3', 'asym3', 'food4')
ATTR_DEG = 27.0


def load():
    R = {}
    for f in sorted(glob.glob(os.path.join(OUT, 'run_*.json'))):
        r = json.load(open(f)); R[r['name']] = r
    return R


def cfg(r): return {'v9c': 'c', 'v9b': 'b'}.get(r['tag'], r['tag'])


def pairs(R, scns):
    c = {(r['scn'], r['seed']): r for r in R.values() if cfg(r) == 'c' and r['scn'] in scns}
    b = {(r['scn'], r['seed']): r for r in R.values() if cfg(r) == 'b' and r['scn'] in scns and r['R_init'] == 12.0}
    ks = sorted(set(c) & set(b)); return [(k, c[k], b[k]) for k in ks]


def ratio(a, b): return float(a / b) if b > 0 else (float('nan') if a == 0 else float('inf'))
def fmt(x, p=3): return 'nan' if x is None or (isinstance(x, float) and not np.isfinite(x)) else (f'{x:.{p}f}' if isinstance(x, float) else str(x))


def overall(primary, subs=()):
    allv = list(primary) + list(subs)
    if all(v == OK for v in allv): return OK
    if any(v == NO for v in primary): return NO
    if any(v == NO for v in subs): return PART
    return NA


def snaps(r, t0=None, t1=None):
    return [s for s in r['snaps'] if (t0 is None or s['t'] >= t0 - 1e-9) and (t1 is None or s['t'] < t1 - 1e-9)]


def wrapdeg(a): return (a + 180.0) % 360.0 - 180.0


def direction(r, dmin=25.0):
    tr = np.array(r['met']['traj'], float); c0 = r['c0']
    d = np.hypot(tr[:, 1] - c0, tr[:, 2] - c0); i = int(np.argmax(d >= dmin)) if (d >= dmin).any() else len(d) - 1
    ang = np.degrees(np.arctan2(tr[i, 2] - c0, tr[i, 1] - c0)); return float(wrapdeg(ang - ATTR_DEG)), float(tr[i, 0]), bool((d >= dmin).any())


def disp_end(r):
    tr = np.array(r['met']['traj'], float); return float(np.hypot(tr[-1, 1] - r['c0'], tr[-1, 2] - r['c0']))


def main():
    R = load(); J = {}; T = []
    say = T.append
    say(f'verify9 판정 — 실행 {len(R)}개 (대조 {sum(cfg(r) == "c" for r in R.values())}, 후보 {sum(cfg(r) == "b" for r in R.values())}, 기타 {sum(cfg(r) not in "bc" for r in R.values())})')
    cand_all = [r for r in R.values() if cfg(r) in ('b', 'v9b_g20')]

    # ---------------- 주장 1 ----------------
    P = pairs(R, PAIR_SCN)
    cb = [s for r in R.values() if cfg(r) == 'b' for s in snaps(r, 60)]
    c1a = float(np.mean([s['ncrumb'] >= 1 for s in cb])) if cb else float('nan')
    mc = [np.mean([s['ncrumb'] for s in snaps(c, 60)]) for _, c, b in P]; mb = [np.mean([s['ncrumb'] for s in snaps(b, 60)]) for _, c, b in P]
    fc = float(np.mean([s['ncrumb'] >= 1 for _, c, b in P for s in snaps(c, 60)]))
    c1b_c = float(np.mean(mc)); c1b_b = float(np.mean(mb))
    v = OK if (c1a <= 0.05 and c1b_b <= c1b_c) else (NO if (c1a > 0.15 or c1b_b > c1b_c) else NA)
    lone_c = [c['met']['crumb_cells'] for _, c, b in P]; lone_b = [b['met']['crumb_cells'] for _, c, b in P]
    J['1'] = dict(verdict=v, cand_snap_frac_with_crumb=c1a, ctrl_snap_frac_with_crumb=fc, crumbs_per_snap_ctrl=c1b_c, crumbs_per_snap_cand=c1b_b,
                  n_cand_snaps=len(cb), lone_cells_dropped_ctrl_median=float(np.median(lone_c)), lone_cells_dropped_cand_median=float(np.median(lone_b)),
                  per_scn={scn: dict(ctrl=float(np.mean([np.mean([s['ncrumb'] for s in snaps(c, 60)]) for k, c, b in P if k[0] == scn])),
                                     cand=float(np.mean([np.mean([s['ncrumb'] for s in snaps(b, 60)]) for k, c, b in P if k[0] == scn]))) for scn in PAIR_SCN if any(k[0] == scn for k, _, _ in P)})
    say(f"\n[주장 1 부스러기] {v}\n  부스러기 있는 상태 비율(t>=60): 대조 {fmt(fc)} → 후보 {fmt(c1a)} (후보 상태 {len(cb)}개)\n  상태당 부스러기 수: 대조 {fmt(c1b_c)} → 후보 {fmt(c1b_b)}"
        f"\n  외톨이 칸으로 말라 버려진 칸 수(실행당 중앙값): 대조 {np.median(lone_c)} → 후보 {np.median(lone_b)}")
    for scn, d in J['1']['per_scn'].items(): say(f"    {scn}: {fmt(d['ctrl'])} → {fmt(d['cand'])}")

    # ---------------- 주장 2 ----------------
    PL = pairs(R, ('long',)); PM = pairs(R, ('mig',))
    def dbfrac(r, t0, t1): s = snaps(r, t0, t1); return (float(np.mean([x['db'] for x in s])) if s else float('nan')), len(s)
    Lc = [dbfrac(c, 200, None)[0] for _, c, b in PL]
    Lb = []; win_b = []
    for _, c, b in PL:
        ts = b['met']['t_scl']; t1 = ts if ts is not None else None
        f_, n_ = dbfrac(b, 200, t1); Lb.append(f_); win_b.append((ts if ts is not None else b['T']) - 200)
    Lb_all = [dbfrac(b, 200, None)[0] for _, c, b in PL]
    Mc = [dbfrac(c, 100, 400.01)[0] for _, c, b in PM]; Mb = [dbfrac(b, 100, 400.01)[0] for _, c, b in PM]
    Dc = float(np.nanmean(Lc)) if Lc else float('nan'); Db = float(np.nanmean(Lb)) if Lb else float('nan')
    mDc = float(np.mean(Mc)); mDb = float(np.mean(Mb))
    short_win = sum(w < 300 for w in win_b)
    if short_win >= 3 or not np.isfinite(Db): v2l = NA
    elif Dc < 0.10: v2l = NA
    elif Db <= 0.5 * Dc: v2l = OK
    elif Db > 0.8 * Dc: v2l = NO
    else: v2l = NA
    if mDc <= 0.15 and mDb <= 0.15: v2m = OK          # 짧은 이주에서는 둘 다 드물다
    elif mDb > 0.3 or mDc > 0.15: v2m = NO
    else: v2m = NA
    mlc = [float(np.mean([x['multi'] for x in snaps(c, 200)])) for _, c, b in PL]; mlb = [float(np.mean([x['multi'] for x in snaps(b, 200, b['met']['t_scl'])])) if snaps(b, 200, b['met']['t_scl']) else float('nan') for _, c, b in PL]
    J['2'] = dict(verdict=overall([v2l], [v2m]), long=dict(verdict=v2l, ctrl=Lc, cand_pre_scl=Lb, cand_all=Lb_all, mean_ctrl=Dc, mean_cand=Db, cand_window=win_b,
                  multi_ctrl=mlc, multi_cand=mlb), mig=dict(verdict=v2m, ctrl=Mc, cand=Mb, mean_ctrl=mDc, mean_cand=mDb))
    say(f"\n[주장 2 아령] {J['2']['verdict']}\n  long (t>=200, 후보는 균핵 전까지): 아령 상태 비율 대조 {fmt(Dc)} → 후보 {fmt(Db)}  [{v2l}]"
        f"\n    시드별 대조 {[fmt(x, 2) for x in Lc]} / 후보 {[fmt(x, 2) for x in Lb]} (후보 창 길이 {win_b})\n    후보 균핵 뒤까지 넣으면 {[fmt(x, 2) for x in Lb_all]}"
        f"\n    굵은 덩이 둘 이상(이음 폭 무관): 대조 {[fmt(x, 2) for x in mlc]} / 후보 {[fmt(x, 2) for x in mlb]}"
        f"\n  mig (100<=t<=400): 대조 {fmt(mDc)} → 후보 {fmt(mDb)}  [{v2m}]")

    # ---------------- 주장 3 ----------------
    PF = pairs(R, FLOW_SCN); q = str(M.Q_FLOW)
    def fl(r, key, qq=q): s = snaps(r, 60); return float(np.mean([x['flow'][qq][key] for x in s])) if s else 0.0
    out3 = {}
    for qq in [str(x) for x in (M.Q_FLOW,) + M.Q_FLOW_SENS]:
        d = {}
        for key in ('A_cells', 'A_tips', 'B_cells', 'B_tips'):
            sc = sum(fl(c, key, qq) for _, c, b in PF); sb = sum(fl(b, key, qq) for _, c, b in PF); d[key] = dict(ctrl=sc, cand=sb, ratio=ratio(sb, sc))
        d['per_scn'] = {scn: {key: dict(ctrl=sum(fl(c, key, qq) for k, c, b in PF if k[0] == scn), cand=sum(fl(b, key, qq) for k, c, b in PF if k[0] == scn)) for key in ('A_cells', 'A_tips', 'B_cells', 'B_tips')} for scn in FLOW_SCN}
        out3[qq] = d
    d = out3[q]; rAc = d['A_cells']['ratio']; rAt = d['A_tips']['ratio']; rBc = d['B_cells']['ratio']
    if not (np.isfinite(rAc) and np.isfinite(rAt)): vA = NA
    elif rAc <= 0.33 and rAt <= 0.5: vA = OK
    elif rAc > 0.6 or rAt > 1.0: vA = NO
    else: vA = NA
    vB = NA if not np.isfinite(rBc) else (OK if rBc <= 0.8 else (NO if rBc > 1.2 else NA))
    J['3'] = dict(verdict=overall([vA], [vB]), A=vA, B=vB, flow=out3)
    say(f"\n[주장 3 흐름 없는 실·가지 끝] {J['3']['verdict']}  (교환 문턱 {q}: 경계 유량 < {q} x 유효 부피)")
    for key in ('A_cells', 'A_tips', 'B_cells', 'B_tips'): say(f"  {key}: 대조 {fmt(d[key]['ctrl'], 1)} → 후보 {fmt(d[key]['cand'], 1)}  비 {fmt(d[key]['ratio'])}")
    say(f"  A(떨어진 가는 조각 포함) {vA}, B(주 몸만) {vB}")
    for scn in FLOW_SCN:
        e = d['per_scn'][scn]; say(f"    {scn}: A칸 {fmt(e['A_cells']['ctrl'], 1)}→{fmt(e['A_cells']['cand'], 1)}  A끝 {fmt(e['A_tips']['ctrl'], 1)}→{fmt(e['A_tips']['cand'], 1)}  B칸 {fmt(e['B_cells']['ctrl'], 1)}→{fmt(e['B_cells']['cand'], 1)}  B끝 {fmt(e['B_tips']['ctrl'], 1)}→{fmt(e['B_tips']['cand'], 1)}")
    for qq in out3:
        if qq != q: say(f"  민감도 문턱 {qq}: A칸 비 {fmt(out3[qq]['A_cells']['ratio'])}, A끝 비 {fmt(out3[qq]['A_tips']['ratio'])}, B칸 비 {fmt(out3[qq]['B_cells']['ratio'])}")

    # ---------------- 주장 4 ----------------
    PFd = pairs(R, FOOD_SCN)
    nt = lambda r: sum(x is not None for x in r['met']['t_touch'])
    tc = sum(nt(c) for _, c, b in PFd); tb = sum(nt(b) for _, c, b in PFd); nfood = sum(len(c['met']['t_touch']) for _, c, b in PFd)
    v4a = OK if tb >= tc - 2 else NO
    def last(r):
        tt = r['met']['t_touch']; return (max(tt), False) if all(x is not None for x in tt) else (r['T'], True)
    rat = []; cens_b = 0; cens_c = 0; per_food = []
    for k, c, b in PFd:
        lc, cc = last(c); lb, cb_ = last(b); rat.append(lb / lc); cens_b += cb_; cens_c += cc
        for x, y in zip(c['met']['t_touch'], b['met']['t_touch']): per_food.append([k[0], k[1], x, y])
    med4 = float(np.median(rat))
    v4b = NO if med4 > 1.4 else (NA if cens_b > len(rat) / 4 else OK)
    late = [y - x for _, _, x, y in per_food if x is not None and y is not None]
    tm_c = []; tm_b = []; rt = []; rd = []
    for k, c, b in PM:
        a_ = c['met']['t_touch'][0]; b_ = b['met']['t_touch'][0]; a_ = c['T'] if a_ is None else a_; b_ = b['T'] if b_ is None else b_
        tm_c.append(a_); tm_b.append(b_); rt.append(b_ / a_); rd.append(disp_end(b) / max(disp_end(c), 1e-9))
    mrt = float(np.median(rt)); mrd = float(np.median(rd))
    v4c = OK if (mrt <= 1.15 and mrd >= 0.85) else (NO if (mrt > 1.3 or mrd < 0.7) else NA)
    lt = [(k[1], c['met']['t_touch'][0], b['met']['t_touch'][0], round(disp_end(c), 1), round(disp_end(b), 1)) for k, c, b in PL]
    J['4'] = dict(verdict=overall([v4a, v4b, v4c]), a=dict(verdict=v4a, touched_ctrl=tc, touched_cand=tb, foods=nfood),
                  b=dict(verdict=v4b, ratios=rat, median=med4, cens_cand=cens_b, cens_ctrl=cens_c, per_food=per_food, late_ge20=int(sum(x >= 20 for x in late)), late_n=len(late),
                         late_median=float(np.median(late)) if late else None, late_max=float(max(late)) if late else None),
                  c=dict(verdict=v4c, t_touch_ctrl=tm_c, t_touch_cand=tm_b, ratio_t_median=mrt, disp_ctrl=[disp_end(c) for _, c, b in PM], disp_cand=[disp_end(b) for _, c, b in PM], ratio_d_median=mrd),
                  long=lt)
    say(f"\n[주장 4 먹이 찾기·이주] {J['4']['verdict']}\n  (a) 닿은 먹이: 대조 {tc} → 후보 {tb} / {nfood}  [{v4a}]"
        f"\n  (b) 마지막 먹이 시각 비(후보/대조) 중앙값 {fmt(med4)} (짝 {len(rat)}, 후보 못 닿음 {cens_b}, 대조 못 닿음 {cens_c})  [{v4b}]"
        f"\n      먹이별 지연(후보-대조): 중앙값 {fmt(J['4']['b']['late_median'], 1)}, 최대 {fmt(J['4']['b']['late_max'], 1)}, 20 이상 늦은 먹이 {J['4']['b']['late_ge20']}/{len(late)}"
        f"\n  (c) mig: 유인원 닿는 시각 비 중앙값 {fmt(mrt)}, 끝 변위 비 중앙값 {fmt(mrd)}  [{v4c}]\n      닿는 시각 대조 {tm_c}\n                 후보 {tm_b}"
        f"\n      변위 대조 {[round(x, 1) for x in J['4']['c']['disp_ctrl']]}\n           후보 {[round(x, 1) for x in J['4']['c']['disp_cand']]}\n  long (시드, 닿음 대조, 닿음 후보, 변위 대조, 변위 후보): {lt}")

    # ---------------- 주장 5 ----------------
    migseeds = set(r['seed'] for r in R.values() if r['scn'] == 'mig')
    def dirs(c_):
        rs = [r for r in R.values() if cfg(r) == c_ and r['R_init'] == 12.0 and (r['scn'] == 'mig' or (r['scn'] == 'long' and r['seed'] not in migseeds))]
        return sorted([(r['scn'], r['seed']) + direction(r) for r in rs])
    db_ = dirs('b'); dc_ = dirs('c')
    eb = np.array([x[2] for x in db_]); ec = np.array([x[2] for x in dc_])
    npos = int((eb > 0).sum()); nneg = int((eb < 0).sum()); mab = float(np.median(np.abs(eb)))
    v5 = OK if (mab <= 15 and min(npos, nneg) >= 3) else (NO if (mab > 25 or min(npos, nneg) <= 1) else NA)
    J['5'] = dict(verdict=v5, cand=db_, ctrl=dc_, cand_med_abs=mab, cand_mean=float(eb.mean()), cand_pos=npos, cand_neg=nneg,
                  ctrl_med_abs=float(np.median(np.abs(ec))), ctrl_mean=float(ec.mean()), ctrl_pos=int((ec > 0).sum()), ctrl_neg=int((ec < 0).sum()))
    say(f"\n[주장 5 이주 방향] {v5}\n  후보 {len(eb)}개: |오차| 중앙값 {fmt(mab, 1)}°, 평균 {fmt(float(eb.mean()), 1)}°, +{npos} / -{nneg}  {[round(float(x), 1) for x in eb]}"
        f"\n  대조 {len(ec)}개: |오차| 중앙값 {fmt(J['5']['ctrl_med_abs'], 1)}°, 평균 {fmt(J['5']['ctrl_mean'], 1)}°, +{J['5']['ctrl_pos']} / -{J['5']['ctrl_neg']}  {[round(float(x), 1) for x in ec]}")

    # ---------------- 주장 6 ----------------
    def t_first(r): tt = [x for x in r['met']['t_touch'] if x is not None]; return min(tt) if tt else None
    def tails(r, key='tail'):
        t0 = t_first(r)
        if t0 is None: return None
        s = snaps(r, t0); sz = [v for x in s for v in x[key].get('sizes', [])] if key == 'tail' else []
        return dict(n=float(np.mean([x[key]['n'] for x in s])) if s else 0.0, cells=float(np.mean([x[key]['cells'] for x in s])) if s else 0.0, sizes=sz,
                    mx=max([x[key]['max'] for x in s]) if s else 0, ns=len(s))
    tcs = []; tbs = []
    for k, c, b in PFd:
        a_, b_ = tails(c), tails(b)
        if a_ is None or b_ is None: continue
        tcs.append((k, a_, tails(c, 'tail_ext'))); tbs.append((k, b_, tails(b, 'tail_ext')))
    n_c = sum(x[1]['n'] for x in tcs); n_b = sum(x[1]['n'] for x in tbs)
    szc = [v for x in tcs for v in x[1]['sizes']]; szb = [v for x in tbs for v in x[1]['sizes']]
    Lc6 = float(np.mean(szc)) if szc else float('nan'); Lb6 = float(np.mean(szb)) if szb else 0.0
    rn = ratio(n_b, n_c); rl = (Lb6 / Lc6) if (szc and np.isfinite(Lc6)) else float('nan')
    mxr = [x[1]['mx'] / y[1]['mx'] for x, y in zip(tbs, tcs) if y[1]['mx'] > 0]
    ne_c = sum(x[2]['n'] for x in tcs); ne_b = sum(x[2]['n'] for x in tbs); rne = ratio(ne_b, ne_c)
    if not (np.isfinite(rn) and np.isfinite(rl)): v6 = NA
    elif rn <= 0.33 and rl <= 0.7: v6 = OK
    elif rn > 0.6 or rl > 1.0: v6 = NO
    else: v6 = NA
    v6e = NA if not np.isfinite(rne) else (OK if rne <= 0.8 else NO)
    # 이주 판(주장 아님): 참고로 같은 측정
    def tails_all(r, t0): s = snaps(r, t0); return float(np.mean([x['tail']['n'] for x in s])) if s else 0.0
    mig6 = dict(ctrl=float(np.mean([tails_all(c, 60) for _, c, b in PM + PL])), cand=float(np.mean([tails_all(b, 60) for _, c, b in PM + PL])))
    J['6'] = dict(verdict=overall([v6], [v6e]), strict=dict(verdict=v6, n_ctrl=n_c, n_cand=n_b, ratio_n=rn, len_ctrl=Lc6, len_cand=Lb6, ratio_len=rl,
                  max_ratio_median=float(np.median(mxr)) if mxr else None, max_ctrl=[x[1]['mx'] for x in tcs], max_cand=[x[1]['mx'] for x in tbs], pairs=len(tcs)),
                  ext=dict(verdict=v6e, n_ctrl=ne_c, n_cand=ne_b, ratio=rne), migration_reference=mig6)
    say(f"\n[주장 6 막다른 실 꼬리] {J['6']['verdict']}\n  먹이 판 {len(tcs)} 짝, 첫 먹이에 닿은 뒤, 주 몸, 3칸 이상, 어린 칸 없는 꼬리"
        f"\n  상태당 꼬리 수 합: 대조 {fmt(n_c, 2)} → 후보 {fmt(n_b, 2)}  비 {fmt(rn)}\n  꼬리 평균 길이(칸): 대조 {fmt(Lc6, 1)} → 후보 {fmt(Lb6, 1)}  비 {fmt(rl)}  [{v6}]"
        f"\n  실행별 가장 긴 꼬리: 대조 {J['6']['strict']['max_ctrl']} / 후보 {J['6']['strict']['max_cand']}"
        f"\n  계단꼴·2칸 폭 끝 포함: 상태당 수 대조 {fmt(ne_c, 2)} → 후보 {fmt(ne_b, 2)}  비 {fmt(rne)}  [{v6e}]"
        f"\n  (참고, 주장 아님) 이주 판 상태당 꼬리 수: 대조 {fmt(mig6['ctrl'], 2)} → 후보 {fmt(mig6['cand'], 2)}")

    # ---------------- 주장 7 ----------------
    S7 = [r for r in R.values() if cfg(r) == 'b' and r['scn'] == 'slimeall']
    rows = []; untrapped = []
    for r in sorted(S7, key=lambda r: (r['R_init'], r['seed'])):
        s = r.get('scl', {})
        if not s.get('trapped'): untrapped.append(r['name']); continue
        a, b, c, d, e, f = s['a'], s.get('b', {}), s['c'], s['d'], s['e'], s['f']
        nb0 = s['bodies_at_trap']
        pa = (a['n_end'] == nb0) and (a['max_bodies_after'] <= nb0) and (a['tail_max_end'] < M.TAIL_MIN)
        pb = bool(b) and (b['max_area_ratio'] <= 1.05) and (b['outside_union_frac'] <= 0.02)
        pc = (c['rank_mean'] >= 0.7) and (c['peak_dist'] <= 3) and (c['area'] >= c['area_min'] - 1) and (c['disc_iou'] < 0.9)
        pd_core = None if d.get('n_out', 0) < 10 else ((d['dur'] >= 40) and (d['maxwin10'] <= 0.35) and (d['rho'] <= -0.5) and (d['near_med'] >= d['q75']))      # 바깥 칸 10 미만: 따질 수 없음
        pd_fill = True if d.get('n_fill', 0) < 10 or 'fill_dur' not in d else ((d['fill_dur'] >= 20) and (d['fill_maxwin10'] <= 0.5))
        pe_h = e['holes'] == 0; pe_s = e['solidity'] >= 0.85
        pf = (f['ratio'] >= 1.5) and (f['rho'] >= 0.7) and f['mono'] and f['gradual']
        rows.append(dict(name=r['name'], seed=r['seed'], R_init=r['R_init'], t_scl=s['t_scl'], a=pa, b=pb, c=pc, d=(None if pd_core is None else (pd_core and pd_fill)), d_core=pd_core, d_fill=pd_fill, e_holes=pe_h, e_sol=pe_s, f=pf,
                         area=c['area'], V=c['V_lump'], area_min=c['area_min'], rank=c['rank_mean'], peak_dist=c['peak_dist'], disc_iou=c['disc_iou'],
                         dur=d.get('dur'), maxwin10=d.get('maxwin10'), rho_d=d.get('rho'), near_med=d.get('near_med'), q75=d.get('q75'), n_out=d.get('n_out'), n_fill=d.get('n_fill'),
                         fill_dur=d.get('fill_dur'), fill_maxwin10=d.get('fill_maxwin10'), holes=e['holes'], solidity=e['solidity'], f_ratio=f['ratio'], f_rho=f['rho'], f_mono=f['mono'], f_gradual=f['gradual'],
                         n_end=a['n_end'], max_bodies_after=a['max_bodies_after'], tail_max_end=a['tail_max_end'], max_area_ratio=b.get('max_area_ratio'), outside_union=b.get('outside_union_frac'),
                         coords=c['coords']))
    def hard(key): return NA if not rows else (OK if all(x[key] for x in rows) else NO)
    def soft(key):
        v_ = [x[key] for x in rows if x[key] is not None]
        if not v_: return NA
        fr = float(np.mean(v_)); return OK if fr >= 0.8 else (NO if fr <= 0.5 else NA)
    eq = [x for x in rows if x['R_init'] == 12.0]
    areas = [x['area'] for x in eq]; distinct = len(set(areas))
    ious = [M.shape_iou(eq[i]['coords'], eq[j]['coords']) for i in range(len(eq)) for j in range(i + 1, len(eq))]
    iou_med = float(np.median(ious)) if ious else float('nan')
    vc_grp = NA if len(eq) < 4 else (OK if (distinct >= 0.75 * len(eq) and iou_med < 0.85) else (NO if (distinct == 1 or iou_med >= 0.95) else NA))
    sub = dict(a=hard('a'), b=hard('b'), c_run=soft('c'), c_group=vc_grp, d=soft('d'), e_holes=hard('e_holes'), e_sol=soft('e_sol'), f=soft('f'))
    v7 = NA if (len(untrapped) > 2 or not rows) else overall(list(sub.values()))
    for x in rows: x.pop('coords')
    LT = []
    for r in R.values():
        if cfg(r) == 'b' and r['scn'] == 'long' and r.get('scl', {}).get('trapped'):
            s = r['scl']; LT.append(dict(name=r['name'], t_scl=s['t_scl'], n_end=s['a']['n_end'], tail_max_end=s['a']['tail_max_end'], max_area_ratio=s.get('b', {}).get('max_area_ratio'),
                                         holes=s['e']['holes'], solidity=s['e']['solidity'], area=s['c']['area'], area_min=s['c']['area_min'], f_ratio=s['f']['ratio'], f_rho=s['f']['rho'], disc_iou=s['c']['disc_iou']))
    J['7'] = dict(verdict=v7, sub=sub, runs=rows, untrapped=untrapped, distinct_areas=distinct, n_equal_volume=len(eq), areas=areas, pair_iou_median=iou_med, long_trapped=LT)
    say(f"\n[주장 7 균핵] {v7}  (slimeall 후보 {len(rows)}개 갇힘, 안 갇힘 {untrapped})")
    for k_, v_ in sub.items():
        if k_ == 'c_group': continue
        key_ = 'c' if k_ == 'c_run' else k_
        say(f"  ({k_}) {v_}  통과 {sum(bool(x[key_]) for x in rows if x[key_] is not None)} / {sum(x[key_] is not None for x in rows)}")
    say(f"  (c_group) {sub['c_group']}")
    say(f"  (c 무리) 같은 부피 {len(eq)}개의 끝 넓이 {areas} → 서로 다른 값 {distinct}개, 무게중심 맞춘 모양 IoU 중앙값 {fmt(iou_med)}")
    for x in rows:
        say(f"   {x['name']}: t_scl {x['t_scl']}, 넓이 {x['area']} (최소 {fmt(x['area_min'], 1)}), 짙은곳 순위 {fmt(x['rank'], 2)}, 원판 IoU {fmt(x['disc_iou'], 2)}, 걷힘 10→90% {fmt(x['dur'], 0)}h, 10h 최대몫 {fmt(x['maxwin10'], 2)}, "
            f"거리-마름 rho {fmt(x['rho_d'], 2)}, 둘레 중앙 {fmt(x['near_med'], 0)} vs 75% {fmt(x['q75'], 0)}, 메움 {x['n_fill']}칸 {fmt(x['fill_dur'], 0)}h/{fmt(x['fill_maxwin10'], 2)}, 구멍 {x['holes']}, 볼록몫 {fmt(x['solidity'], 2)}, "
            f"두께 가운데/가장자리 {fmt(x['f_ratio'], 2)} rho {fmt(x['f_rho'], 2)} 단조 {x['f_mono']} 완만 {x['f_gradual']}, 덩이 {x['n_end']} (최대 {x['max_bodies_after']}), 꼬리 {x['tail_max_end']}, 다시넓어짐 {fmt(x['max_area_ratio'], 3)}/{fmt(x['outside_union'], 3)}")
    for x in LT: say(f"   (long 후보 갇힘) {x}")

    # ---------------- 주장 8 ----------------
    def health(r):
        m = r['met']; V0 = m['V0']; dv = abs(m['V_end'] - V0 - m['Vinj']) / V0
        ok = (m['stop'] == '') and (m['steps_done'] == r['steps_expected']) and (m['h_min_end_of_step'] >= -1e-9) and (m['mass_err_max'] <= 1e-8) and (dv <= 1e-3)
        return ok, dict(name=r['name'], stop=m['stop'], steps=m['steps_done'], expected=r['steps_expected'], hmin_end=m['h_min_end_of_step'], neg_end_cellsteps=m['neg_end_cellsteps'],
                        mass_err=m['mass_err_max'], vol_loss=dv, V_crumb=m['V_crumb'])
    H = [health(r) for r in cand_all]; Hc = [health(r) for r in R.values() if cfg(r) == 'c']
    v8 = OK if all(h[0] for h in H) else NO
    J['8'] = dict(verdict=v8, n=len(H), failed=[h[1] for h in H if not h[0]], worst=dict(hmin_end=min(h[1]['hmin_end'] for h in H), mass_err=max(h[1]['mass_err'] for h in H),
                  vol_loss=max(h[1]['vol_loss'] for h in H), neg_end_cellsteps=max(h[1]['neg_end_cellsteps'] for h in H)),
                  ctrl=dict(n=len(Hc), failed=[h[1]['name'] for h in Hc if not h[0]], hmin_end=min(h[1]['hmin_end'] for h in Hc), mass_err=max(h[1]['mass_err'] for h in Hc), vol_loss=max(h[1]['vol_loss'] for h in Hc)))
    say(f"\n[주장 8 건강] {v8}\n  후보 {len(H)}개: 실패 {len(J['8']['failed'])}  가장 나쁜 값 {J['8']['worst']}\n  (대조 {len(Hc)}개: 실패 {J['8']['ctrl']['failed']}, 끝 최소 두께 {J['8']['ctrl']['hmin_end']}, 질량 오차 {J['8']['ctrl']['mass_err']}, 부피 손실 {J['8']['ctrl']['vol_loss']})")
    for h in J['8']['failed']: say(f"   실패: {h}")

    # ---------------- 주장 9 ----------------
    PA = pairs(R, PAIR_SCN)
    ec9 = np.array([x for _, c, b in PA for x in c['mg_err_series']]); eb9 = np.array([x for _, c, b in PA for x in b['mg_err_series']])
    st = lambda e: dict(n=int(e.size), median=float(np.median(e)), p90=float(np.percentile(e, 90)), p99=float(np.percentile(e, 99)), max=float(e.max()))
    s_c = st(ec9); s_b = st(eb9); mx_all = max(max(r['mg_err_series']) for r in cand_all if r['mg_err_series'])
    worse = [k for k in ('median', 'p90', 'p99') if s_b[k] > 1.1 * s_c[k]]; bad = [k for k in ('median', 'p90', 'p99') if s_b[k] > 1.25 * s_c[k]]
    v9 = OK if (not worse and mx_all <= 0.6) else (NO if (mx_all > 0.6 or bad) else NA)
    per = {scn: dict(ctrl=st(np.array([x for k, c, b in PA if k[0] == scn for x in c['mg_err_series']])), cand=st(np.array([x for k, c, b in PA if k[0] == scn for x in b['mg_err_series']]))) for scn in PAIR_SCN if any(k[0] == scn for k, _, _ in PA)}
    J['9'] = dict(verdict=v9, ctrl=s_c, cand=s_b, cand_max_all_runs=mx_all, worse_gt10pct=worse, per_scn=per)
    say(f"\n[주장 9 압력 풀이] {v9}\n  유량 오차 대조 {', '.join(f'{k} {fmt(s_c[k], 4)}' for k in ('median', 'p90', 'p99', 'max'))} (n {s_c['n']})"
        f"\n            후보 {', '.join(f'{k} {fmt(s_b[k], 4)}' for k in ('median', 'p90', 'p99', 'max'))} (n {s_b['n']}); 후보 모든 실행의 최대 {fmt(mx_all, 4)}")
    for scn, dd in per.items(): say(f"    {scn}: 대조 med {fmt(dd['ctrl']['median'], 4)} p99 {fmt(dd['ctrl']['p99'], 4)} max {fmt(dd['ctrl']['max'], 4)} | 후보 med {fmt(dd['cand']['median'], 4)} p99 {fmt(dd['cand']['p99'], 4)} max {fmt(dd['cand']['max'], 4)}")

    # ---------------- 결정성 점검 (주장 아님) ----------------
    det = {}
    for c_ in ('c', 'b'):
        a_ = [r for r in R.values() if cfg(r) == c_ and r['scn'] == 'mig' and r['seed'] == 1001]; b_ = [r for r in R.values() if cfg(r) == c_ and r['scn'] == 'long' and r['seed'] == 1001]
        if a_ and b_:
            ta = np.array(a_[0]['met']['traj'], float); tb_ = np.array(b_[0]['met']['traj'], float); n_ = min(len(ta), int((tb_[:, 0] <= 400).sum()))
            det[f'mig_vs_long_s1001_{c_}'] = bool(np.array_equal(ta[:n_], tb_[:n_]))
    try:
        h1 = np.load(os.path.join(RUNS, 'b_slimeall_s1001_v9b', 'h.npy')); h2 = np.load(os.path.join(RUNS, 'b_slimeall_s1001_v9b_g20', 'h.npy'))
        det['slimeall_s1001_gm5_vs_gm20_h_identical'] = bool(np.array_equal(h1, h2))
    except Exception as ex: det['slimeall_gm'] = f'없음 ({ex.__class__.__name__})'
    J['determinism'] = det
    say(f"\n[결정성 점검] {det}")

    # ---------------- 진짜 점균답지 않은 점: 측정 ----------------
    def mean_key(rs, f_): v = [f_(x) for r in rs for x in snaps(r, 60)]; return float(np.mean(v)) if v else float('nan')
    NR = {}
    for c_ in ('c', 'b'):
        fr_ = [r for r in R.values() if cfg(r) == c_ and r['scn'] in FOOD_SCN]; mg_ = [r for r in R.values() if cfg(r) == c_ and r['scn'] in ('mig', 'long')]
        NR[c_] = dict(food_tube_n=mean_key(fr_, lambda x: x['tube']['n']), food_tube_cells=mean_key(fr_, lambda x: x['tube']['cells']), food_tube_max=max([x['tube']['max'] for r in fr_ for x in snaps(r, 60)] or [0]),
                      food_young_n=mean_key(fr_, lambda x: x['tail']['young_n']), food_young_cells=mean_key(fr_, lambda x: x['tail']['young_cells']),
                      food_young_max=max([max(x['tail']['young_sizes'] or [0]) for r in fr_ for x in snaps(r, 60)] or [0]),
                      mig_tube_n=mean_key(mg_, lambda x: x['tube']['n']), mig_tube_cells=mean_key(mg_, lambda x: x['tube']['cells']),
                      counters={k: float(np.median([r['met'][k] or 0 for r in R.values() if cfg(r) == c_])) for k in ('conn_kept_cellsteps', 'fission_runs', 'tiphome_cells', 'neg_fill_cellsteps', 'hang_cellsteps', 'ret_cellsteps', 'sup_updates', 'mg_nadapt', 'mg_nguard', 'lim_steps')})
    J['not_real'] = NR
    say(f"\n[참고: 관·고리, 탐색 가지, 규칙 작동 횟수]")
    for c_ in ('c', 'b'): say(f"  {'대조' if c_ == 'c' else '후보'}: {NR[c_]}")
    json.dump(J, open(PRE + '.json', 'w'), indent=1, ensure_ascii=False, default=float)
    open(PRE + '.txt', 'w').write('\n'.join(T) + '\n')
    print('\n'.join(T))


if __name__ == '__main__':
    main()
