#!/usr/bin/env python3
"""verify8 판정 코드 — data/*.json (measure.py 의 출력)을 읽어 주장 1~9 를 CRITERIA.md 의 기준으로 판정한다.

usage: judge.py DATA_DIR OUT_DIR   -> OUT_DIR/JUDGE.json, OUT_DIR/JUDGE.md
꼬리표: v8c = 대조(지금 모델), v8v = 후보
"""
import numpy as np, json, os, sys, glob
from scipy.stats import binomtest

OK, NO, UNK = '맞음', '틀림', '판정 못 함'
TH = dict(
    tmin=60.0,
    c1_ok_mean=0.05, c1_ok_frac=0.05, c1_no_mean=0.20, c1_no_frac=0.15,
    c2_ctrl_min=0.05, c2_ok_ratio=0.5, c2_no_ratio=0.8, c2_pair_ok=0.25,
    c3_ok_ratio=0.5, c3_no_ratio=0.8, c3_pair_ok=0.70, c3_ctrl_min=1.0, c3_film_lo=0.5, c3_film_hi=2.0, c3_q='0.05',
    c4a_def_ok=2, c4b_ok=1.4, c4c_t_ok=1.10, c4c_t_no=1.25, c4c_d_ok=0.90, c4c_d_no=0.75, mig_T=400.0,
    c5_ok_err=15.0, c5_no_err=25.0, c5_p=0.05,
    c6_ok_cells=0.5, c6_ok_len=0.7, c6_no_cells=0.8, c6_no_len=0.9, c6_pair_ok=0.70, c6_ctrl_min=1.0, c6_after_touch=20.0,
    c7_min_after=300.0, c7_b_area=1.15, c7_b_iou=0.8, c7_c_dens=1.1, c7_c_overlap=0.8, c7_c_disc=0.9, c7_c_pair=0.9,
    c7_d_t90=30.0, c7_d_max10=0.35, c7_e_sol=0.9, c7_f_sp=0.5, c7_f_ratio=1.5, c7_f_step=0.5, c7_f_cv=0.15,
    c8_mass=1e-6, c8_hneg=-1e-9,
    c9_tol_ok=1.05, c9_tol_no=1.25, c9_max=0.6,
)
MIG = ('mig', 'long'); FOOD = ('food3', 'asym3', 'food4')


def load(dd):
    R = {}
    for f in sorted(glob.glob(os.path.join(dd, '*.json'))):
        r = json.load(open(f))
        if 'arm' in r: R[(r['scn'], r['seed'], r['arm'])] = r
    return R


def pairs(R, scns=None):
    out = []
    for (s, sd, a), r in sorted(R.items()):
        if a == 'v8c' and (scns is None or s in scns) and (s, sd, 'v8v') in R: out.append((r, R[(s, sd, 'v8v')]))
    return out


def arm(R, a, scns=None): return [r for (s, sd, x), r in sorted(R.items()) if x == a and (scns is None or s in scns)]


def snaps(r, tmin=0.0, tmax=np.inf): return [s for s in r['snaps'] if tmin <= s['t'] < tmax and s.get('n_comp', 0) > 0]


def mean(x): x = [v for v in x if v is not None]; return float(np.mean(x)) if x else None


def rnd(x, k=4): return None if x is None else round(float(x), k)


def tscl(r): return r['metrics'].get('t_scl')


def c1(R):
    res = {}
    for a in ('v8c', 'v8v'):
        per = []; ns = 0; nw = 0; by = {}
        for r in arm(R, a):
            ss = snaps(r, TH['tmin'])
            if not ss: continue
            c = [s['crumbs'] for s in ss]; per.append(np.mean(c)); ns += len(c); nw += sum(x > 0 for x in c)
            by.setdefault(r['scn'], []).append(np.mean(c))
        res[a] = dict(runs=len(per), mean_per_snap=rnd(mean(per)), frac_snaps=rnd(nw / max(ns, 1)), snaps=ns, by_scn={k: rnd(np.mean(v)) for k, v in by.items()},
                      runs_with_crumb=int(sum(p > 0 for p in per)))
    v = res['v8v']
    if v['runs'] == 0: verd = UNK
    elif v['mean_per_snap'] <= TH['c1_ok_mean'] and v['frac_snaps'] <= TH['c1_ok_frac']: verd = OK
    elif v['mean_per_snap'] > TH['c1_no_mean'] or v['frac_snaps'] > TH['c1_no_frac']: verd = NO
    else: verd = UNK
    return dict(verdict=verd, **res)


def frac_snaps(r, key, cond, tmin, scl_cut=True):
    tmax = tscl(r) if (scl_cut and tscl(r) is not None) else np.inf
    ss = snaps(r, tmin, tmax)
    return (float(np.mean([cond(s) for s in ss])) if ss else None), len(ss)


def c2(R):
    P = pairs(R, MIG); rows = []
    for c, v in P:
        row = dict(scn=c['scn'], seed=c['seed'])
        for nm, f in (('db', lambda s: s['nbig_sq3'] >= 2), ('db_d2', lambda s: s['nbig_d2'] >= 2), ('thick', lambda s: s['nbig_thick'] >= 2),
                      ('fis', lambda s: s['n_bodies10'] >= 2), ('split', lambda s: s['nbig_sq3'] >= 2 or s['n_bodies10'] >= 2)):
            row['c_' + nm] = rnd(frac_snaps(c, nm, f, TH['tmin'])[0]); row['v_' + nm] = rnd(frac_snaps(v, nm, f, TH['tmin'])[0])
        rows.append(row)
    agg = {k: rnd(mean([r_[k] for r_ in rows])) for k in rows[0] if k[:2] in ('c_', 'v_')} if rows else {}
    if not rows: return dict(verdict=UNK, note='짝 없음')
    cc, vv = agg['c_db'], agg['v_db']
    worse = sum(r_['v_db'] > r_['c_db'] for r_ in rows if r_['v_db'] is not None and r_['c_db'] is not None)
    nt = sum(r_['v_db'] != r_['c_db'] for r_ in rows if r_['v_db'] is not None and r_['c_db'] is not None)
    if cc < TH['c2_ctrl_min']: verd = UNK; why = '대조에도 아령이 드묾'
    elif vv <= TH['c2_ok_ratio'] * cc and (nt == 0 or worse / nt <= TH['c2_pair_ok']) and agg['v_split'] <= agg['c_split']: verd = OK; why = ''
    elif vv > TH['c2_no_ratio'] * cc: verd = NO; why = '후보가 대조의 0.8배를 넘음'
    else: verd = UNK; why = '중간(0.5~0.8배) 또는 짝 비교·분열 포함 조건 어긋남'
    return dict(verdict=verd, why=why, agg=agg, pairs_worse=worse, pairs_nontie=nt, rows=rows)


def c3(R):
    q = TH['c3_q']; P = pairs(R); rows = []
    for c, v in P:
        row = dict(scn=c['scn'], seed=c['seed'])
        for k in ('nf_thread_' + q, 'nf_tipr_' + q, 'nf_tipc_' + q, 'nf_thread_0.01', 'nf_thread_0.2', 'nf_tipr_0.01', 'nf_tipr_0.2', 'thread_cells', 'tips_robust'):
            row['c_' + k] = rnd(mean([s.get(k) for s in snaps(c, TH['tmin'])])); row['v_' + k] = rnd(mean([s.get(k) for s in snaps(v, TH['tmin'])]))
        if c['scn'] in MIG:
            row['c_film'] = rnd(mean([s['film_cells'] for s in snaps(c, TH['tmin'], tscl(c) or np.inf)])); row['v_film'] = rnd(mean([s['film_cells'] for s in snaps(v, TH['tmin'], tscl(v) or np.inf)]))
        rows.append(row)
    if not rows: return dict(verdict=UNK, note='짝 없음')

    def ratio(k):
        cs = sum(r_['c_' + k] or 0 for r_ in rows); vs = sum(r_['v_' + k] or 0 for r_ in rows)
        lower = sum((r_['v_' + k] or 0) < (r_['c_' + k] or 0) for r_ in rows); nt = sum((r_['v_' + k] or 0) != (r_['c_' + k] or 0) for r_ in rows)
        return dict(ctrl_mean=rnd(cs / len(rows)), cand_mean=rnd(vs / len(rows)), ratio=rnd(vs / cs) if cs > 0 else None, pairs_lower=lower, pairs_nontie=nt)
    out = {k: ratio(k) for k in ('nf_thread_' + q, 'nf_tipr_' + q, 'nf_tipc_' + q, 'nf_thread_0.01', 'nf_thread_0.2', 'nf_tipr_0.01', 'nf_tipr_0.2', 'thread_cells', 'tips_robust')}
    vs = []
    for k in ('nf_thread_' + q, 'nf_tipr_' + q):
        o = out[k]
        if o['ctrl_mean'] is None or o['ctrl_mean'] < TH['c3_ctrl_min'] or o['ratio'] is None: vs.append(UNK)
        elif o['ratio'] <= TH['c3_ok_ratio'] and o['pairs_lower'] >= TH['c3_pair_ok'] * max(o['pairs_nontie'], 1): vs.append(OK)
        elif o['ratio'] > TH['c3_no_ratio'] or o['pairs_lower'] < 0.5 * o['pairs_nontie']: vs.append(NO)
        else: vs.append(UNK)
    verd = NO if NO in vs else (OK if all(x == OK for x in vs) else UNK)
    fr = [r_ for r_ in rows if 'c_film' in r_]; cf = sum(r_['c_film'] or 0 for r_ in fr); vf = sum(r_['v_film'] or 0 for r_ in fr)
    film = dict(ctrl_mean=rnd(cf / max(len(fr), 1)), cand_mean=rnd(vf / max(len(fr), 1)), ratio=rnd(vf / cf) if cf > 0 else None)
    film['verdict'] = UNK if film['ratio'] is None else (OK if TH['c3_film_lo'] <= film['ratio'] <= TH['c3_film_hi'] else NO)
    by = {}
    for r_ in rows:
        b = by.setdefault(r_['scn'], dict(c_thr=0.0, v_thr=0.0, c_tip=0.0, v_tip=0.0, n=0))
        b['c_thr'] += r_['c_nf_thread_' + q] or 0; b['v_thr'] += r_['v_nf_thread_' + q] or 0; b['c_tip'] += r_['c_nf_tipr_' + q] or 0; b['v_tip'] += r_['v_nf_tipr_' + q] or 0; b['n'] += 1
    by = {k: {kk: (rnd(vv / b['n']) if kk != 'n' else vv) for kk, vv in b.items()} for k, b in by.items()}
    return dict(verdict=verd, sub=dict(threads=vs[0], tips=vs[1]), measures=out, film=film, by_scn=by, rows=rows)


def t_last(r):
    tt = r['metrics']['t_touch']
    if not tt: return None, False
    if all(x is not None for x in tt): return max(tt), True
    return r['T'], False


def c4(R):
    P = pairs(R, FOOD); rows = []
    for c, v in P:
        tc, fc = t_last(c); tv, fv = t_last(v)
        n_c = sum(x is not None for x in c['metrics']['t_touch']); n_v = sum(x is not None for x in v['metrics']['t_touch'])
        late = [round(b - a, 1) for a, b in zip(c['metrics']['t_touch'], v['metrics']['t_touch']) if a is not None and b is not None]
        rows.append(dict(scn=c['scn'], seed=c['seed'], n_foods=len(c['metrics']['t_touch']), touched_c=n_c, touched_v=n_v, tlast_c=tc, tlast_v=tv, all_c=fc, all_v=fv,
                         ratio=rnd(tv / tc) if tc else None, per_food_delay=late))
    a = dict(ctrl=sum(r_['touched_c'] for r_ in rows), cand=sum(r_['touched_v'] for r_ in rows), foods=sum(r_['n_foods'] for r_ in rows))
    a['deficit'] = a['ctrl'] - a['cand']; a['verdict'] = UNK if not rows else (OK if a['deficit'] <= TH['c4a_def_ok'] else NO)
    rat = [r_['ratio'] for r_ in rows if r_['ratio'] is not None]
    b = dict(median_ratio=rnd(np.median(rat)) if rat else None, n=len(rat), censored_cand=sum(not r_['all_v'] for r_ in rows), censored_ctrl=sum(not r_['all_c'] for r_ in rows),
             delays_over_20=sum(1 for r_ in rows for d in r_['per_food_delay'] if d > 20), max_delay=max([d for r_ in rows for d in r_['per_food_delay']] or [None], key=lambda x: -1e9 if x is None else x))
    b['verdict'] = UNK if not rat else (OK if b['median_ratio'] <= TH['c4b_ok'] else NO)
    if b['verdict'] == OK and b['censored_cand'] > 0:      # 후보가 끝까지 다 닿지 못한 판은 비가 아래 한계라 중앙값이 더 커질 수 있다
        hi = sorted(rat + [])
        b['note'] = '후보 검열 판 있음: 비는 아래 한계'
    # (c) 이주: mig 와 long(앞 400 시간)
    Pm = pairs(R, MIG); mr = []
    for c, v in Pm:
        def tt(r):
            x = r['metrics']['t_touch'][0] if r['metrics']['t_touch'] else None
            return (x, True) if (x is not None and x <= TH['mig_T']) else (TH['mig_T'], False)
        (t1, h1), (t2, h2) = tt(c), tt(v)
        mr.append(dict(scn=c['scn'], seed=c['seed'], t_c=t1, t_v=t2, hit_c=h1, hit_v=h2, d_c=c.get('disp400'), d_v=v.get('disp400'), d200_c=c.get('disp200'), d200_v=v.get('disp200')))
    cc = dict(n=len(mr))
    if mr:
        cc.update(t_med_c=rnd(np.median([m['t_c'] for m in mr]), 2), t_med_v=rnd(np.median([m['t_v'] for m in mr]), 2), hit_c=sum(m['hit_c'] for m in mr), hit_v=sum(m['hit_v'] for m in mr),
                  d_med_c=rnd(np.median([m['d_c'] for m in mr]), 2), d_med_v=rnd(np.median([m['d_v'] for m in mr]), 2),
                  d200_med_c=rnd(np.median([m['d200_c'] for m in mr]), 2), d200_med_v=rnd(np.median([m['d200_v'] for m in mr]), 2))
        tr = cc['t_med_v'] / cc['t_med_c']; dr = cc['d_med_v'] / max(cc['d_med_c'], 1e-9); cc['t_ratio'] = rnd(tr); cc['d_ratio'] = rnd(dr)
        if tr <= TH['c4c_t_ok'] and dr >= TH['c4c_d_ok'] and cc['hit_v'] >= cc['hit_c'] - 1: cc['verdict'] = OK
        elif tr > TH['c4c_t_no'] or dr < TH['c4c_d_no'] or cc['hit_v'] < cc['hit_c'] - 2: cc['verdict'] = NO
        else: cc['verdict'] = UNK
    else: cc['verdict'] = UNK
    vs = [a['verdict'], b['verdict'], cc['verdict']]
    verd = NO if NO in vs else (OK if all(x == OK for x in vs) else UNK)
    return dict(verdict=verd, a=a, b=b, c=cc, rows=rows, mig_rows=mr)


def c5(R):
    out = {}
    for a in ('v8c', 'v8v'):
        e = []; rows = []
        for r in arm(R, a, MIG):
            h = r.get('heading') or {}; x = h.get('35') or h.get('20')
            rows.append(dict(scn=r['scn'], seed=r['seed'], err=None if x is None else x['err'], t=None if x is None else x['t'], at='35' if h.get('35') else ('20' if h.get('20') else None)))
            if x is not None: e.append(x['err'])
        e = np.array(e); npos = int((e > 0).sum()); nneg = int((e < 0).sum())
        p = binomtest(max(npos, nneg), npos + nneg, 0.5).pvalue if npos + nneg > 0 else None
        out[a] = dict(n=int(e.size), med_abs=rnd(np.median(np.abs(e)), 2) if e.size else None, mean_signed=rnd(e.mean(), 2) if e.size else None, n_pos=npos, n_neg=nneg, p_side=rnd(p), rows=rows)
    v = out['v8v']
    if v['n'] < 6: verd = UNK
    elif v['med_abs'] <= TH['c5_ok_err'] and v['p_side'] >= TH['c5_p']: verd = OK
    elif v['p_side'] < TH['c5_p'] or v['med_abs'] > TH['c5_no_err']: verd = NO
    else: verd = UNK
    return dict(verdict=verd, **out)


def c6(R):
    P = pairs(R, FOOD); rows = []
    for c, v in P:
        def m(r):
            tt = [x for x in r['metrics']['t_touch'] if x is not None]
            if not tt: return None
            ss = snaps(r, min(tt) + TH['c6_after_touch'])
            if not ss: return None
            g = lambda k: float(np.mean([s[k] for s in ss]))
            return dict(cells=g('tail_cells'), maxlen=g('tail_max'), n3=g('tail_n3'), rob_old=g('th_tail_old_cells'), rob_old_max=g('th_tail_old_max'), rob=g('th_tail_cells'),
                        head_n=g('th_head_n'), head_cells=g('th_head_cells'), head_max=g('th_head_max'), loop_n=g('th_loop_n'), loop_cells=g('th_loop_cells'), loop_max=g('th_loop_max'),
                        tube_n=g('th_tube_n'), tube_cells=g('th_tube_cells'), tube_max=g('th_tube_max'), snaps=len(ss))
        mc, mv = m(c), m(v)
        if mc and mv: rows.append(dict(scn=c['scn'], seed=c['seed'], c=mc, v=mv))
    if not rows: return dict(verdict=UNK, note='짝 없음')
    S = lambda a, k: float(np.mean([r_[a][k] for r_ in rows]))
    agg = {k: dict(ctrl=rnd(S('c', k)), cand=rnd(S('v', k))) for k in rows[0]['c']}
    for k in agg: agg[k]['ratio'] = rnd(agg[k]['cand'] / agg[k]['ctrl']) if agg[k]['ctrl'] else None
    lower = sum(r_['v']['cells'] < r_['c']['cells'] for r_ in rows); nt = sum(r_['v']['cells'] != r_['c']['cells'] for r_ in rows)
    rc, rl = agg['cells']['ratio'], agg['maxlen']['ratio']
    if agg['cells']['ctrl'] < TH['c6_ctrl_min']: verd = UNK; why = '대조에도 꼬리가 드묾'
    elif rc <= TH['c6_ok_cells'] and rl <= TH['c6_ok_len'] and lower >= TH['c6_pair_ok'] * max(nt, 1): verd = OK; why = ''
    elif rc > TH['c6_no_cells'] or rl > TH['c6_no_len']: verd = NO; why = '칸 수 0.8배 또는 길이 0.9배를 넘음'
    else: verd = UNK; why = '중간'
    rob = agg['rob_old']['ratio']
    return dict(verdict=verd, why=why, agg=agg, pairs_lower=lower, pairs_nontie=nt,
                robust_note=None if rob is None else ('굳센 정의(열림 기준 매달린 실, 오래된 것)도 0.5배 이하' if rob <= 0.5 else f'굳센 정의로는 비 {rob}'), rows=rows)


def lump_pair_iou(fa, fb):
    A = np.load(fa)['mask']; B = np.load(fb)['mask']; best = 0.0
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            Bs = np.roll(B, (dy, dx), (0, 1)); best = max(best, float((A & Bs).sum() / max((A | Bs).sum(), 1)))
    return best


def c7(R, dd):
    cand = arm(R, 'v8v'); rows = []; trapped_slime = [r for r in cand if r['scn'] == 'slimeall']
    no_scl_slime = [r['seed'] for r in trapped_slime if tscl(r) is None]
    for r in cand:
        if tscl(r) is None or 'scl' not in r: continue
        sc = r['scl']; ts = tscl(r); qual = (r['T'] - ts) >= TH['c7_min_after']
        ss = [s for s in r['snaps'] if s['t'] >= sc['t_trap_snap']]; fin = ss[-1]; L = sc['lump_final']; tm = sc['timing'] or {}
        nb0 = sc['n_bodies3_trap']
        a_ok = all(s['n_bodies3'] <= nb0 for s in ss) and fin['n_comp'] == nb0 and fin['tail_cells'] == 0 and fin['th_tail_n'] == 0 and fin.get('lump', {}).get('n_core10', 1) == 1
        t90 = tm.get('t90'); t_f = ts + (t90 if t90 is not None else 0.0)
        after = [s for s in ss if s['t'] >= t_f]; iou = dict((t, v) for t, v in sc['iou_final'])
        if after:
            A_f = after[0]['area']
            b_ok = all(s['area'] <= TH['c7_b_area'] * A_f for s in after) and all(iou.get(s['t'], 1.0) >= TH['c7_b_iou'] for s in after) and all(s['n_bodies3'] == after[0]['n_bodies3'] for s in after)
        else: b_ok = None
        stayed = r['metrics']['scl_steps'] * 0.1 >= (r['metrics']['t_end'] - ts) - 1.0
        b_ok = (b_ok and stayed) if b_ok is not None else None
        c_ok = sc['dens_ratio'] >= TH['c7_c_dens'] and sc['overlap_trap'] >= TH['c7_c_overlap'] and L['disc_iou'] < TH['c7_c_disc'] and sc['area_final'] >= sc['vol_final'] / 3.5
        d_ok = (t90 is not None and t90 >= TH['c7_d_t90'] and (tm.get('max10') is None or tm['max10'] <= TH['c7_d_max10']))
        e_ok = L['holes'] == 0 and L['solidity'] >= TH['c7_e_sol']
        f_ok = (L['sp_h_d'] is not None and L['sp_h_d'] >= TH['c7_f_sp'] and L['h_ratio'] is not None and L['h_ratio'] >= TH['c7_f_ratio'] and L['h_cv'] >= TH['c7_f_cv']
                and (L['max_step_frac'] is None or L['max_step_frac'] <= TH['c7_f_step']))
        rows.append(dict(run=r['run'], scn=r['scn'], seed=r['seed'], t_scl=ts, qualified=qual, a=a_ok, b=b_ok, c=c_ok, d=d_ok, e=e_ok, f=f_ok, stayed=stayed,
                         n_bodies_trap=nb0, n_comp_final=fin['n_comp'], tail_final=fin['tail_cells'], robust_tail_final=fin['th_tail_n'], n_core10=fin.get('lump', {}).get('n_core10'),
                         dens_ratio=sc['dens_ratio'], overlap=sc['overlap_trap'], disc_iou=L['disc_iou'], solidity=L['solidity'], holes=L['holes'], rough=L['rough'],
                         area_trap=sc['area_trap'], area_final=sc['area_final'], vol_final=sc['vol_final'], amin=sc['amin'], t50=tm.get('t50'), t90=t90, max10=tm.get('max10'),
                         sp=L['sp_h_d'], h_ratio=L['h_ratio'], h_cv=L['h_cv'], max_step=L['max_step_frac'], conc=sc['conc']))
    Q = [x for x in rows if x['qualified']]
    pair = []
    fl = {x['run']: os.path.join(dd, x['run'] + '_lump.npz') for x in Q}
    ks = [k for k in fl if os.path.exists(fl[k])]
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)): pair.append(round(lump_pair_iou(fl[ks[i]], fl[ks[j]]), 4))
    pmed = rnd(np.median(pair)) if pair else None
    sub = {}
    for k in 'abcdef':
        vals = [x[k] for x in Q if x[k] is not None]; nf = sum(not v for v in vals)
        if not vals: sub[k] = UNK
        elif nf == 0: sub[k] = OK
        elif nf >= 2 or nf >= 0.25 * len(vals): sub[k] = NO
        else: sub[k] = UNK
        sub[k + '_fail'] = [x['run'] for x in Q if x[k] is not None and not x[k]]
    if sub['c'] == OK and pmed is not None and pmed >= TH['c7_c_pair']: sub['c'] = NO; sub['c_note'] = '실행끼리 윤곽이 거의 같음'
    if no_scl_slime: verd = NO
    elif not Q: verd = UNK
    else: verd = NO if NO in [sub[k] for k in 'abcdef'] else (OK if all(sub[k] == OK for k in 'abcdef') else UNK)
    same_area = {}
    for x in Q: same_area.setdefault(round(x['vol_final'], 0), []).append(x['area_final'])
    return dict(verdict=verd, sub=sub, qualified=len(Q), slime_without_scl=no_scl_slime, pair_iou_median=pmed, pair_iou=pair,
                at_min_area=sum(x['area_final'] <= x['amin'] for x in Q), rows=rows)


def c8(R):
    rows = []; bad = []
    for r in arm(R, 'v8v'):
        m = r['metrics']; hmin = min([s['h_min'] for s in r['snaps'] if s.get('h_min') is not None] or [0.0])
        ok = (m['stop'] == '' and m['steps_done'] == r['steps_expected'] and m['neg_end_cellsteps'] == 0 and m['h_min_end_of_step'] >= TH['c8_hneg']
              and m['mass_err_max'] <= TH['c8_mass'] and hmin >= TH['c8_hneg'])
        rows.append(dict(run=r['run'], ok=ok, stop=m['stop'], steps=m['steps_done'], steps_expected=r['steps_expected'], neg_end_cellsteps=m['neg_end_cellsteps'],
                         h_min_end_of_step=m['h_min_end_of_step'], h_min_seen=m['h_min_seen'], mass_err_max=m['mass_err_max'], h_min_snap=hmin, V_crumb=m.get('V_crumb')))
        if not ok: bad.append(r['run'])
    n_expected = None
    return dict(verdict=(UNK if not rows else (OK if not bad else NO)), n=len(rows), bad=bad,
                worst=dict(mass_err_max=max([x['mass_err_max'] for x in rows] or [None]), h_min_end=min([x['h_min_end_of_step'] for x in rows] or [None]),
                           h_min_seen=min([x['h_min_seen'] for x in rows] or [None]), V_crumb_max=max([x['V_crumb'] or 0 for x in rows] or [None])), rows=rows)


def c9(R):
    out = {}
    for a in ('v8c', 'v8v'):
        e = np.array([x for r in arm(R, a) for x in r['mg_err_list']])
        out[a] = dict(n=int(e.size), median=rnd(np.median(e), 5), p90=rnd(np.percentile(e, 90), 5), p99=rnd(np.percentile(e, 99), 5), max=rnd(e.max(), 5)) if e.size else dict(n=0)
        by = {}
        for r in arm(R, a):
            by.setdefault(r['scn'], []).extend(r['mg_err_list'])
        out[a + '_by'] = {k: dict(n=len(v), median=rnd(np.median(v), 5), p99=rnd(np.percentile(v, 99), 5), max=rnd(max(v), 5)) for k, v in by.items() if v}
    c, v = out['v8c'], out['v8v']
    if not c.get('n') or not v.get('n'): verd = UNK
    else:
        rs = [v[k] / c[k] for k in ('median', 'p90', 'p99')]; out['ratios'] = [rnd(x) for x in rs]
        if all(x <= TH['c9_tol_ok'] for x in rs) and v['max'] <= TH['c9_max']: verd = OK
        elif any(x > TH['c9_tol_no'] for x in rs) or v['max'] > TH['c9_max']: verd = NO
        else: verd = UNK
    return dict(verdict=verd, **out)


def md(J):
    L = ['# verify8 판정 출력 (judge.py 자동 생성)', '', '| 주장 | 판정 |', '|---|---|']
    for k in sorted(J):
        if k.startswith('c'): L.append(f"| {k} | {J[k]['verdict']} |")
    L += ['', '```', json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ('rows', 'mig_rows', 'pair_iou')} for k, v in J.items() if k.startswith('c')}, ensure_ascii=False, indent=1), '```']
    return '\n'.join(L)


def main(dd, od):
    R = load(dd); os.makedirs(od, exist_ok=True)
    J = dict(c1=c1(R), c2=c2(R), c3=c3(R), c4=c4(R), c5=c5(R), c6=c6(R), c7=c7(R, dd), c8=c8(R), c9=c9(R), n_runs=len(R), TH=TH)
    json.dump(J, open(os.path.join(od, 'JUDGE.json'), 'w'), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    open(os.path.join(od, 'JUDGE.md'), 'w').write(md(J))
    for k in sorted(J):
        if k.startswith('c'): print(k, J[k]['verdict'])
    return J


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
