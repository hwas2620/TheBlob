#!/usr/bin/env python3
"""verify6 판정: data/*.json 을 모아 주장 1~8 을 CRITERIA.md 의 기준대로 판정한다.

usage: judge.py            -> ../judge.json, ../judge.txt
"""
import glob, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V6 = os.environ.get('VERIFY6_OUT') or os.path.normpath(os.path.join(HERE, '..'))
DATA = os.environ.get('VERIFY6_DATA') or os.path.join(V6, 'data')
CAND, CTRL = 'v6g', 'v6c'
MIG = ('mig', 'long')
FOODS = ('food3', 'asym3', 'food4')
STRUCT = ('mig', 'long', 'food3', 'asym3', 'food4')       # 대조와 견주는 구조 주장(1·2·3·6)의 시나리오. slimeall 은 갇힘 시험 전용
TRAP = ('slimeall', 'long')


# ---------------------------------------------------------------- 도움 함수 (test_meas.py 가 시험한다)
def wrap180(a): return (a + 180.0) % 360.0 - 180.0


def heading(traj, c0, target_deg, dmin):
    """중심 이동이 처음 dmin 칸을 넘은 때의 방향 - 유인원 방향 (도, +는 반시계). 못 넘으면 None"""
    for t, x, y, _a in traj:
        dx = x - c0; dy = y - c0
        if math.hypot(dx, dy) >= dmin:
            return wrap180(math.degrees(math.atan2(dy, dx)) - target_deg)
    return None


def disp_at(traj, c0, t):
    tr = np.array([r[:3] for r in traj], float)
    i = int(np.argmin(np.abs(tr[:, 0] - t)))
    return float(math.hypot(tr[i, 1] - c0, tr[i, 2] - c0)) if abs(tr[i, 0] - t) <= 5.0 else None


def sign_p(k, n):
    """두쪽 부호 검정: n 개 중 k 개 이상이 한쪽 (k >= n/2)"""
    k = max(k, n - k)
    p = sum(math.comb(n, i) for i in range(k, n + 1)) / 2.0 ** n
    return min(1.0, 2 * p)


def t_form(frames, t_on):
    for f in frames:
        if t_on is not None and f['t'] >= t_on and f['scl_state']:
            return f['t']
    return None


def unravel_frac(frames, tf):
    after = [f for f in frames if f['t'] > tf]
    return (sum(1 for f in after if not f['scl_state']) / len(after)) if after else 0.0


def ratio(a, b):
    return (a / b) if b > 0 else (float('inf') if a > 0 else float('nan'))


def r3(x):
    if x is None: return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)): return str(x)
    return round(float(x), 4)


# ---------------------------------------------------------------- 자료
def load():
    runs = {}
    for f in sorted(glob.glob(os.path.join(DATA, 'b_*.json'))):
        R = json.load(open(f)); runs[(R['scn'], R['seed'], R['tag'])] = R
    return runs


def pairs(runs, scns):
    out = []
    for (s, sd, tg) in sorted(runs):
        if tg == CAND and s in scns and (s, sd, CTRL) in runs:
            out.append(((s, sd), runs[(s, sd, CAND)], runs[(s, sd, CTRL)]))
    return out


def tcut(runs, s, sd):
    c = runs.get((s, sd, CAND)); ts = c['met'].get('t_scl') if c else None
    return ts if ts is not None else 1e18


def win(R, t0, t1=1e18):
    return [f for f in R['frames'] if t0 <= f['t'] < t1 and not f.get('empty')]


def fmean(fr, key, norm=None):
    if not fr: return None
    v = [(f[key] / max(f[norm], 1)) if norm else float(f[key]) for f in fr]
    return float(np.mean(v))


def paired_summary(pp, fn):
    """pp: 짝 목록, fn(R) -> 실행 하나의 값(또는 None). 평균·비·짝 우열"""
    a = []; b = []; lt = gt = eq = 0
    for key, c, k in pp:
        x = fn(c); y = fn(k)
        if x is None or y is None: continue
        a.append(x); b.append(y)
        if abs(x - y) <= 1e-12: eq += 1
        elif x < y: lt += 1
        else: gt += 1
    ma = float(np.mean(a)) if a else None; mb = float(np.mean(b)) if b else None
    nt = lt + gt
    return dict(n=len(a), cand=ma, ctrl=mb, ratio=(ratio(ma, mb) if a else None), cand_lower=lt, cand_higher=gt, tied=eq,
                frac_cand_lower=(lt / nt if nt else None))


def V(ok, bad):
    return '맞음' if ok else ('틀림' if bad else '판정 못 함')


# ---------------------------------------------------------------- 주장
def claim1(runs):
    allc = [f for (s, sd, tg), R in runs.items() if tg == CAND for f in win(R, 100.0)]
    abs_frac = float(np.mean([f['n_debris'] >= 1 for f in allc])) if allc else None
    per_scn = {}
    for s in sorted({k[0] for k in runs}):
        fr = [f for (ss, sd, tg), R in runs.items() if tg == CAND and ss == s for f in win(R, 100.0)]
        if fr: per_scn[s] = float(np.mean([f['n_debris'] >= 1 for f in fr]))
    pp = pairs(runs, STRUCT)
    fc = []; fk = []
    for (s, sd), c, k in pp:
        tc = tcut(runs, s, sd); fc += win(c, 100.0, tc); fk += win(k, 100.0, tc)
    rc = float(np.mean([f['n_debris'] >= 1 for f in fc])) if fc else None
    rk = float(np.mean([f['n_debris'] >= 1 for f in fk])) if fk else None
    sec = dict(abs_frac_t60=float(np.mean([f['n_debris'] >= 1 for (s, sd, tg), R in runs.items() if tg == CAND for f in win(R, 60.0)])) if allc else None,
               rel_cand_mean_n=float(np.mean([f['n_debris'] for f in fc])) if fc else None, rel_ctrl_mean_n=float(np.mean([f['n_debris'] for f in fk])) if fk else None,
               rel_cand_volfrac=float(np.mean([f['debris_vol_frac'] for f in fc])) if fc else None, rel_ctrl_volfrac=float(np.mean([f['debris_vol_frac'] for f in fk])) if fk else None,
               crumb_cells_cand=int(sum(R['met']['crumb_cells'] or 0 for (s, sd, tg), R in runs.items() if tg == CAND)),
               crumb_cells_ctrl=int(sum(R['met']['crumb_cells'] or 0 for (s, sd, tg), R in runs.items() if tg == CTRL)))
    if abs_frac is None or rc is None:
        return dict(verdict='판정 못 함', why='자료 없음')
    ok = abs_frac <= 0.05 and max(per_scn.values()) <= 0.15 and (rc <= 0.5 * rk or rk <= 0.05)
    bad = abs_frac > 0.15 or (rk > 0.05 and rc >= rk)
    return dict(verdict=V(ok, bad), cand_abs_frac=abs_frac, cand_per_scn=per_scn, rel_cand_frac=rc, rel_ctrl_frac=rk, n_frames_abs=len(allc), n_frames_rel=(len(fc), len(fk)), secondary=sec)


def claim2(runs):
    pp = pairs(runs, MIG)
    def w(R):
        s, sd = R['scn'], R['seed']; return win(R, 60.0, min(tcut(runs, s, sd), 400.0 if s == 'mig' else 1e18))
    D = paired_summary(pp, lambda R: fmean(w(R), 'dumbbell'))
    Dv = paired_summary(pp, lambda R: fmean(w(R), 'divided'))
    D1 = paired_summary(pp, lambda R: fmean(w(R), 'dumbbell_any'))
    Sp = paired_summary(pp, lambda R: fmean(w(R), 'split'))
    food = paired_summary(pairs(runs, FOODS), lambda R: fmean(win(R, 60.0, tcut(runs, R['scn'], R['seed'])), 'dumbbell'))
    if not D['n']:
        return dict(verdict='판정 못 함', why='자료 없음')
    c, k = D['cand'], D['ctrl']
    ok = k >= 0.05 and c <= k / 3.0 and (D['frac_cand_lower'] or 0) >= 0.7 and Dv['cand'] <= Dv['ctrl']
    bad = (k >= 0.05 and c >= 0.67 * k) or (Dv['ctrl'] > 0 and Dv['cand'] > 1.25 * Dv['ctrl'])
    return dict(verdict=V(ok, bad), dumbbell=D, divided=Dv, secondary=dict(dumbbell_any_neck=D1, split=Sp, food_scn_dumbbell=food))


def claim3(runs):
    pp = pairs(runs, STRUCT)
    wf = lambda R: win(R, 60.0, tcut(runs, R['scn'], R['seed']))
    subs = dict(dead_thread=paired_summary(pp, lambda R: fmean(wf(R), 'dead_thread_cells', 'area')),
                film=paired_summary(pp, lambda R: fmean(wf(R), 'film_cells', 'area')),
                dead_tip=paired_summary(pp, lambda R: fmean(wf(R), 'n_dead_tips')))
    floor = dict(dead_thread=0.001, film=0.001, dead_tip=0.05)
    sv = {}
    for nm, S in subs.items():
        if not S['n'] or S['ctrl'] is None or S['ctrl'] < floor[nm]:
            sv[nm] = '판정 못 함'; continue
        ok = S['ratio'] <= 0.8 and (S['frac_cand_lower'] or 0) >= 0.7
        bad = S['ratio'] >= 1.0 or (S['cand_higher'] >= 0.5 * max(S['cand_lower'] + S['cand_higher'], 1))
        sv[nm] = V(ok, bad)
    overall = '맞음' if all(v == '맞음' for v in sv.values()) else ('틀림' if any(v == '틀림' for v in sv.values()) else '판정 못 함')
    sec = dict(dead_thread_rel02=paired_summary(pp, lambda R: fmean(wf(R), 'dead_thread_cells_rel02', 'area')),
               dead_thread_rel005=paired_summary(pp, lambda R: fmean(wf(R), 'dead_thread_cells_rel005', 'area')),
               film_h025=paired_summary(pp, lambda R: fmean(wf(R), 'film_cells_h0.25', 'area')),
               film_h05=paired_summary(pp, lambda R: fmean(wf(R), 'film_cells_h0.5', 'area')),
               n_dead_threads=paired_summary(pp, lambda R: fmean(wf(R), 'n_dead_threads')),
               n_tips=paired_summary(pp, lambda R: fmean(wf(R), 'n_tips')),
               thread_cells=paired_summary(pp, lambda R: fmean(wf(R), 'thread_cells', 'area')))
    return dict(verdict=overall, sub_verdicts=sv, **subs, secondary=sec)


def claim4(runs):
    # (가) 먹이
    rc = rk = 0; lr = []; per = []
    for (s, sd), c, k in pairs(runs, FOODS):
        for i, (tc, tk) in enumerate(zip(c['met']['t_touch'], k['met']['t_touch'])):
            rc += tc is not None; rk += tk is not None
            if tc is not None and tk is not None: lr.append(math.log(max(tc, 1.0) / max(tk, 1.0)))
            per.append([s, sd, i, tc, tk])
    gm_food = math.exp(float(np.mean(lr))) if lr else None
    # (나) 유인원
    ac = ak = 0; la = []; pa = []
    for (s, sd), c, k in pairs(runs, MIG):
        tc = c['met']['t_touch'][0]; tk = k['met']['t_touch'][0]
        ac += tc is not None; ak += tk is not None
        if tc is not None and tk is not None: la.append(math.log(max(tc, 1.0) / max(tk, 1.0)))
        pa.append([s, sd, tc, tk])
    gm_att = math.exp(float(np.mean(la))) if la else None
    # (다) 옮겨 간 거리
    dc = []; dk = []
    for (s, sd), c, k in pairs(runs, MIG):
        x = disp_at(c['traj'], c['c0'], 200.0); y = disp_at(k['traj'], k['c0'], 200.0)
        if x is not None and y is not None: dc.append(x); dk.append(y)
    dr = float(np.median(dc) / np.median(dk)) if dc else None
    sec = dict(disp400_cand=[disp_at(c['traj'], c['c0'], 400.0) for _, c, _k in pairs(runs, MIG)], disp400_ctrl=[disp_at(k['traj'], k['c0'], 400.0) for _, _c, k in pairs(runs, MIG)],
               food_time_median=(float(np.median([p[3] for p in per if p[3] is not None])) if per else None, float(np.median([p[4] for p in per if p[4] is not None])) if per else None))
    if gm_food is None or gm_att is None or dr is None:
        return dict(verdict='판정 못 함', why='자료 부족', food_reached=(rc, rk), att_reached=(ac, ak))
    ok = rc >= rk - 1 and gm_food <= 1.15 and ac >= ak - 1 and gm_att <= 1.15 and dr >= 0.85
    bad = rc <= rk - 3 or ac <= ak - 3 or gm_food > 1.35 or gm_att > 1.35 or dr < 0.7
    return dict(verdict=V(ok, bad), food_reached=(rc, rk), food_time_gm_ratio=gm_food, food_pairs_both=len(lr), att_reached=(ac, ak), att_time_gm_ratio=gm_att,
                disp200_median=(float(np.median(dc)), float(np.median(dk))), disp200_ratio=dr, per_food=per, per_att=pa, secondary=sec)


def dir_stats(ds):
    ds = [d for d in ds if d is not None]
    if not ds: return dict(n=0)
    a = np.array(ds); pos = int((a > 0).sum()); neg = int((a < 0).sum())
    se = float(a.std(ddof=1) / math.sqrt(a.size)) if a.size > 1 else float('inf')
    return dict(n=int(a.size), median_abs=float(np.median(np.abs(a))), mean=float(a.mean()), se=se, t=float(a.mean() / se) if se > 0 else float('inf'),
                pos=pos, neg=neg, sign_p=sign_p(max(pos, neg), pos + neg) if pos + neg else None, values=[round(float(v), 2) for v in a])


def claim5(runs):
    out = {}
    for tg in (CAND, CTRL):
        d25 = []; dto = []
        for (s, sd, t_), R in sorted(runs.items()):
            if t_ != tg or s not in MIG: continue
            tgt = R['P']['foods'][0][0]
            d25.append(heading(R['traj'], R['c0'], tgt, 25.0))
            tt = R['met']['t_touch'][0]
            if tt is not None:
                tr = [r for r in R['traj'] if r[0] <= tt + 1e-9]
                if tr: x, y = tr[-1][1] - R['c0'], tr[-1][2] - R['c0']; dto.append(wrap180(math.degrees(math.atan2(y, x)) - tgt))
        out[tg] = dict(d25=dir_stats(d25), d_touch=dir_stats(dto), n_no25=sum(1 for v in d25 if v is None))
    c = out[CAND]['d25']
    if c.get('n', 0) < 12:
        return dict(verdict='판정 못 함', why='표본 12 미만', **out)
    ok = c['median_abs'] <= 15.0 and c['sign_p'] >= 0.05 and abs(c['t']) < 2.0
    bad = c['median_abs'] > 25.0 or c['sign_p'] < 0.05 or abs(c['t']) >= 2.5
    return dict(verdict=V(ok, bad), **out)


def max_consec(fr, key, thr=1):
    best = cur = 0
    for f in fr:
        cur = cur + 1 if f[key] >= thr else 0; best = max(best, cur)
    return best


def claim6(runs):
    cand = [(k, R) for k, R in runs.items() if k[2] == CAND]
    allf = [f for _, R in cand for f in win(R, 60.0)]
    f25 = float(np.mean([f['n_long25'] >= 1 for f in allf])) if allf else None
    f40 = float(np.mean([f['n_long40'] >= 1 for f in allf])) if allf else None
    pers25 = {f'{k[0]}_s{k[1]}': max_consec(win(R, 60.0), 'n_long25') for k, R in cand}
    pers40 = {f'{k[0]}_s{k[1]}': max_consec(win(R, 60.0), 'n_long40') for k, R in cand}
    pp = pairs(runs, STRUCT); fc = []; fk = []
    for (s, sd), c, k in pp:
        tc = tcut(runs, s, sd); fc += win(c, 60.0, tc); fk += win(k, 60.0, tc)
    g = lambda fr, key: float(np.mean([f[key] >= 1 for f in fr])) if fr else None
    rel = dict(cand25=g(fc, 'n_long25'), ctrl25=g(fk, 'n_long25'), cand40=g(fc, 'n_long40'), ctrl40=g(fk, 'n_long40'),
               cand25_tail=g(fc, 'n_long25_tail'), ctrl25_tail=g(fk, 'n_long25_tail'), cand25_bridge=g(fc, 'n_long25_bridge'), ctrl25_bridge=g(fk, 'n_long25_bridge'),
               cand25_w4=g(fc, 'n_long25_w4'), ctrl25_w4=g(fk, 'n_long25_w4'), cand60=g(fc, 'n_long60'), ctrl60=g(fk, 'n_long60'),
               cand_maxlen_mean=float(np.mean([f['thread_maxlen'] for f in fc])) if fc else None, ctrl_maxlen_mean=float(np.mean([f['thread_maxlen'] for f in fk])) if fk else None)
    if f25 is None or rel['ctrl25'] is None:
        return dict(verdict='판정 못 함', why='자료 없음')
    ok = f40 <= 0.01 and max(pers25.values()) < 3 and f25 <= 0.05 and (rel['cand25'] <= rel['ctrl25'] or rel['ctrl25'] <= 0.05)
    bad = f40 > 0.03 or max(pers40.values()) >= 3 or f25 > 0.15
    return dict(verdict=V(ok, bad), cand_abs_f25=f25, cand_abs_f40=f40, max_consec25=max(pers25.values()), max_consec40=max(pers40.values()),
                runs_consec25_ge2={k: v for k, v in pers25.items() if v >= 2}, rel=rel, n_frames=len(allf))


def claim7(runs):
    trap = []
    for (s, sd, tg), R in sorted(runs.items()):
        if tg != CAND or s not in TRAP: continue
        if s == 'slimeall' or R['met'].get('t_scl') is not None or (R.get('fresh_rim_end') is not None and R['fresh_rim_end'] < 0.05):
            trap.append(((s, sd), R))
    rows = []
    for (s, sd), R in trap:
        fr = R['frames']; ton = R['met'].get('t_scl'); row = dict(run=f'{s}_s{sd}', t_on=ton)
        last3 = [f['scl_state'] for f in fr[-3:]]
        row['a'] = bool(ton is not None and len(last3) == 3 and all(last3))
        tf = t_form(fr, ton); row['t_form'] = tf
        if tf is not None:
            uf = unravel_frac(fr, tf)
            a1 = R['area_1t']; i0 = int(round(tf)); amax = max(a1[i0:]) if i0 < len(a1) else a1[-1]
            row['unravel_frac'] = uf; row['area_regrow'] = amax / max(a1[i0], 1)
            row['b'] = bool(uf <= 0.1 and amax <= 1.25 * a1[i0])
            # (라) 시간을 두고: 형성까지 50 이상, 한 장면 사이 마지막 모양 쪽으로의 IoU 증가가 전체의 절반 이하
            seq = [f for f in fr if (f['t'] >= ton - 20.0) and f['t'] <= tf]
            gains = [b['iou_final'] - a['iou_final'] for a, b in zip(seq[:-1], seq[1:])]
            tot = seq[-1]['iou_final'] - seq[0]['iou_final'] if seq else 0.0
            row['form_dur'] = tf - ton; row['iou_gain_total'] = tot; row['iou_gain_max_step'] = max(gains) if gains else 0.0
            i_on = int(round(ton)); seg = np.array(a1[i_on:i0 + 1], float)
            if seg.size > 11:
                drops = seg[:-10] - seg[10:]; tot_drop = seg[0] - seg.min()
                row['area_drop_max10_share'] = float(drops.max() / tot_drop) if tot_drop > 0 else 0.0
            row['d'] = bool(row['form_dur'] >= 50.0 and (tot <= 0.1 or row['iou_gain_max_step'] <= 0.5 * tot))
        else:
            row['b'] = False; row['d'] = False
        last = fr[-1]; P = last.get('pieces', [])
        if P:
            mp = max(P, key=lambda p: p['vfrac'])
            row['final_main'] = {k: r3(mp.get(k)) for k in ('vfrac', 'area', 'solidity', 'iso', 'aspect', 'radial_cv', 'disc_iou', 'h_cv', 'h_within10', 'h_p10_p90_over_med', 'hole_frac', 'n_lumps', 'thread_comps', 'narrow5_frac')}
            sh = R.get('scl_shape', {})
            row['iou_mass'] = sh.get('iou_mass'); row['overlap_onset'] = sh.get('overlap_onset')
            row['c'] = bool((mp.get('disc_iou', 1) < 0.88 or mp.get('aspect', 1) >= 1.3) and sh.get('iou_mass') is not None and sh['iou_mass'] >= mp.get('disc_iou', 1))
        else:
            row['c'] = False
        row['n_pieces_final'] = len(P)
        rows.append(row)
    # (마) 대조와 견줌: 마지막 장면의 가장 큰 조각
    erows = []
    for (s, sd), c, k in pairs(runs, TRAP):
        if s == 'long' and not ((c['met'].get('t_scl') is not None or (c.get('fresh_rim_end') or 1) < 0.05) and (k.get('fresh_rim_end') or 1) < 0.05):
            continue
        mc = max(c['frames'][-1].get('pieces', []) or [dict(vfrac=0)], key=lambda p: p['vfrac']); mk = max(k['frames'][-1].get('pieces', []) or [dict(vfrac=0)], key=lambda p: p['vfrac'])
        if 'solidity' not in mc or 'solidity' not in mk: continue
        erows.append(dict(run=f'{s}_s{sd}', sol=(r3(mc['solidity']), r3(mk['solidity'])), iso=(r3(mc['iso']), r3(mk['iso'])), hole=(r3(mc['hole_frac']), r3(mk['hole_frac'])),
                          threads=(mc['thread_comps'], mk['thread_comps']), e=bool(mc['solidity'] > mk['solidity'] and mc['iso'] < mk['iso'])))
    n = len(rows)
    frac = {x: (sum(r[x] for r in rows) / n if n else None) for x in 'abcd'}
    fe = (sum(r['e'] for r in erows) / len(erows)) if erows else None
    if n < 5 or fe is None:
        return dict(verdict='판정 못 함', why=f'갇힘 실행 {n} (5 미만) 또는 (마) 짝 없음', rows=rows, erows=erows, frac=frac, frac_e=fe)
    ok = all(frac[x] >= 0.9 for x in 'abcd') and fe >= 0.8
    bad = any(frac[x] < 0.75 for x in 'abcd') or fe < 0.5
    subv = {x: ('맞음' if frac[x] >= 0.9 else ('틀림' if frac[x] < 0.75 else '판정 못 함')) for x in 'abcd'}
    subv['e'] = '맞음' if fe >= 0.8 else ('틀림' if fe < 0.5 else '판정 못 함')
    return dict(verdict=V(ok, bad), sub_verdicts=subv, frac=frac, frac_e=fe, n_trap=n, rows=rows, erows=erows)


def joblog():
    st = {}
    p = os.path.join(DATA, 'joblog.tsv')
    if os.path.exists(p):
        for l in open(p):
            a = l.rstrip('\n').split('\t')
            if len(a) >= 4: st[a[0]] = (a[2], a[3])
    return st


def claim8(runs, expected):
    rows = []; bad = False; skipped = []; jl = joblog()
    for key in expected:
        if key[2] != CAND: continue
        R = runs.get(key); nm = f'b_{key[0]}_s{key[1]}_{key[2]}'
        if R is None:
            if jl.get(nm, ('',))[0].startswith('SKIP'):
                skipped.append(nm); continue          # 멈춤 규칙으로 돌지 않음: 판정에서 빼고 따로 적는다
            rows.append(dict(run=nm, ok=False, why='측정 자료 없음 (돌다 죽음 또는 측정 실패)', joblog=jl.get(nm))); bad = True; continue
        m = R['met']; e = R['mg_err_series']; emax = max((x[1] for x in e), default=0.0)
        vc = (m.get('V_crumb') or 0.0) / m['V0']
        ok = (m['stop'] == '' and m['steps_done'] == R['steps_expected'] and m['neg_end_cellsteps'] == 0 and m['mass_err_max'] <= 1e-6 and vc <= 0.01
              and math.isfinite(emax) and emax < 1.0)
        rows.append(dict(run=f'{key[0]}_s{key[1]}', ok=bool(ok), stop=m['stop'], steps=(m['steps_done'], R['steps_expected']), neg_end_cellsteps=m['neg_end_cellsteps'],
                         mass_err_max=m['mass_err_max'], V_crumb_frac=vc, h_min_seen=m['h_min_seen'], h_min_end=m['h_min_end_of_step'], mg_err_max=emax))
        bad |= not ok
    n = len(rows)
    return dict(verdict=('판정 못 함' if n == 0 else ('틀림' if bad else '맞음')), n=n, n_ok=sum(r['ok'] for r in rows), skipped=skipped,
                worst=dict(mass_err_max=max((r.get('mass_err_max', 0) or 0) for r in rows) if rows else None, V_crumb_frac=max((r.get('V_crumb_frac', 0) or 0) for r in rows) if rows else None,
                           h_min_seen=min((r.get('h_min_seen', 0) or 0) for r in rows) if rows else None),
                rows=[r for r in rows if not r['ok']] or rows[:3])


def solver_acc(runs):
    out = {}
    for s in sorted({k[0] for k in runs}):
        for tg in (CTRL, CAND):
            e = [x for (ss, sd, t_), R in runs.items() if ss == s and t_ == tg for x in R['mg_err_series']]
            if not e: continue
            a = np.array([x[1] for x in e]); b = np.array([x[2] for x in e]); b = b[b > 0]
            out[f'{s}/{tg}'] = dict(n=int(a.size), med=float(np.median(a)), p90=float(np.percentile(a, 90)), p99=float(np.percentile(a, 99)), max=float(a.max()),
                                    thick_med=float(np.median(b)) if b.size else None, thick_p90=float(np.percentile(b, 90)) if b.size else None)
    return out


def scl_thickness(runs):
    out = {}
    for tg in (CAND, CTRL):
        v = []
        for (s, sd, t_), R in runs.items():
            if t_ != tg or s not in TRAP: continue
            P = R['frames'][-1].get('pieces', [])
            if P:
                mp = max(P, key=lambda p: p['vfrac']); v.append((f'{s}_s{sd}', mp.get('h_cv'), mp.get('h_within10'), mp.get('h_p10_p90_over_med')))
        out[tg] = dict(h_cv_median=float(np.median([x[1] for x in v if x[1] is not None])) if v else None,
                       h_within10_median=float(np.median([x[2] for x in v if x[2] is not None])) if v else None,
                       p10p90_median=float(np.median([x[3] for x in v if x[3] is not None])) if v else None, rows=v)
    return out


def main():
    runs = load()
    jobs = [l.split() for l in open(os.environ.get('VERIFY6_JOBS') or os.path.join(HERE, '..', 'jobs.txt')) if l.strip() and not l.startswith('#')]
    expected = [(j[0], int(j[1]), j[2]) for j in jobs]
    J = dict(n_runs=len(runs), n_expected=len(expected), missing=[f'{a}_s{b}_{c}' for a, b, c in expected if (a, b, c) not in runs])
    J['c1'] = claim1(runs); J['c2'] = claim2(runs); J['c3'] = claim3(runs); J['c4'] = claim4(runs)
    J['c5'] = claim5(runs); J['c6'] = claim6(runs); J['c7'] = claim7(runs); J['c8'] = claim8(runs, expected)
    J['solver'] = solver_acc(runs); J['scl_thickness'] = scl_thickness(runs)
    json.dump(J, open(os.path.join(V6, 'judge.json'), 'w'), indent=1, ensure_ascii=False, default=lambda o: str(o))
    with open(os.path.join(V6, 'judge.txt'), 'w') as f:
        f.write(f"실행 {J['n_runs']} / 예정 {J['n_expected']}, 빠진 것 {J['missing']}\n")
        for i in range(1, 9):
            c = J[f'c{i}']; f.write(f"주장 {i}: {c['verdict']}" + (f"  {c.get('sub_verdicts')}" if c.get('sub_verdicts') else '') + '\n')
    print(open(os.path.join(V6, 'judge.txt')).read())


if __name__ == '__main__':
    main()
