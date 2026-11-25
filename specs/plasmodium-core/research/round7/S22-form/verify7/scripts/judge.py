#!/usr/bin/env python3
"""verify7 판정: verify7/data/*.json 과 verify7/data/replay.json 을 읽어 CRITERIA.md 3절의 기준을 적용한다.

usage: judge.py            -> verify7/judge_out.json, verify7/JUDGE.md
"""
import json, os, sys, glob
import numpy as np
from scipy.stats import binomtest
HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.normpath(os.path.join(HERE, '..'))
DATA = os.environ.get('V7_DATA') or os.path.join(V, 'data')
OUTD = os.environ.get('V7_OUTDIR') or V

MAIN_SCN = ('long', 'mig', 'food3', 'asym3', 'food4', 'slimeall')
MIG_SEEDS = {'long': range(661, 667), 'mig': range(667, 679)}
FOOD_SCN = ('food3', 'asym3', 'food4')
OK, NO, UND, NA = '맞음', '틀림', '판정 못 함', '해당 없음'


def load():
    D = {}
    for f in glob.glob(os.path.join(DATA, 'b_*.json')):
        if f.endswith('.extra.json'): continue          # 보충 측정 파일 (CRITERIA_CHANGES.md 1절)
        r = json.load(open(f)); D[r['name']] = r
    return D


def runs(D, tag, scns):
    return [r for r in D.values() if r['tag'] == tag and r['scn'] in scns]


def frames(r, t0=None, t1=None):
    return [f for f in r['frames'] if (t0 is None or f['t'] >= t0 - 1e-9) and (t1 is None or f['t'] <= t1 + 1e-9)]


def ang_wrap(a):
    return (a + 180.0) % 360.0 - 180.0


def mig_measures(r):
    """주장 4c, 5: 궤적(5 시간마다, 펼친 무게중심)에서. t <= 400 만 쓴다"""
    tr = np.array([[a[0], a[1], a[2]] for a in r['traj'] if a[0] <= 400 + 1e-9])
    c0 = r['c0']; fa = r['foods'][0]
    gx, gy = fa[0] - c0, fa[1] - c0; g_ang = np.degrees(np.arctan2(gy, gx))
    dx = tr[:, 1] - tr[0, 1]; dy = tr[:, 2] - tr[0, 2]; dd = np.hypot(dx, dy)
    out = dict(d400=float(dd[-1]), t_last=float(tr[-1, 0]))
    j = np.nonzero(dd >= 35.0)[0]
    if j.size:
        i = int(j[0]); out['t35'] = float(tr[i, 0]); out['err35'] = float(ang_wrap(np.degrees(np.arctan2(dy[i], dx[i])) - g_ang))
    elif dd[-1] >= 10:
        out['t35'] = None; out['err35'] = float(ang_wrap(np.degrees(np.arctan2(dy[-1], dx[-1])) - g_ang)); out['err_from_end'] = True
    else:
        out['t35'] = None; out['err35'] = None
    tt = r['t_touch'][0] if r['t_touch'] else None
    out['t_touch'] = float(tt) if (tt is not None and tt <= 400 + 1e-9) else None
    if out['t_touch'] is not None:
        k = int(np.argmin(np.abs(tr[:, 0] - out['t_touch'])))
        out['err_touch'] = float(ang_wrap(np.degrees(np.arctan2(dy[k], dx[k])) - g_ang)) if dd[k] >= 5 else None
    return out


def pct(a, q):
    a = np.asarray([x for x in a if x is not None], float)
    return float(np.percentile(a, q)) if a.size else None


def main():
    D = load()
    J = {}
    mig_runs = {tag: [r for r in D.values() if r['tag'] == tag and r['scn'] in MIG_SEEDS and r['seed'] in MIG_SEEDS[r['scn']]] for tag in ('v7c', 'v7y')}
    food_runs = {tag: runs(D, tag, FOOD_SCN) for tag in ('v7c', 'v7y')}
    main_runs = {tag: runs(D, tag, MAIN_SCN) for tag in ('v7c', 'v7y')}
    J['n_runs'] = {tag: len(main_runs[tag]) for tag in main_runs}

    # ---------------- 주장 1 ----------------
    c1 = {}
    for tag in ('v7c', 'v7y'):
        fr = [f for r in main_runs[tag] for f in frames(r, 60)]
        n = len(fr); k = sum(f.get('n_crumb', 0) >= 1 for f in fr)
        c1[tag] = dict(frames=n, frac_frames_with_crumb=k / max(n, 1), mean_crumbs=float(np.mean([f.get('n_crumb', 0) for f in fr])) if fr else None,
                       mean_crumb_vol=float(np.mean([f.get('crumb_vol', 0) for f in fr])) if fr else None,
                       frac_frames_with_frag=sum(f.get('n_frag', 0) >= 1 for f in fr) / max(n, 1),
                       by_scn={s: sum(f.get('n_crumb', 0) >= 1 for r in main_runs[tag] if r['scn'] == s for f in frames(r, 60)) / max(1, sum(len(frames(r, 60)) for r in main_runs[tag] if r['scn'] == s)) for s in MAIN_SCN},
                       V_crumb_over_V0_max=max((r['V_crumb'] or 0) / r['V0'] for r in main_runs[tag]) if main_runs[tag] else None,
                       crumb_cells_total=int(sum(r['crumb_cells'] or 0 for r in main_runs[tag])))
    y = c1['v7y']; v = OK if (y['frac_frames_with_crumb'] <= 0.05 and y['mean_crumbs'] <= 0.1) else (NO if y['frac_frames_with_crumb'] > 0.15 else UND)
    c1['verdict'] = v; J['claim1'] = c1

    # ---------------- 주장 2 ----------------
    c2 = {}
    for tag in ('v7c', 'v7y'):
        fr = [f for r in mig_runs[tag] for f in frames(r, 40, 400)]
        n = len(fr)
        c2[tag] = dict(frames=n, frac_dumbbell=sum(f.get('n_dumbbell_bodies', 0) >= 1 for f in fr) / max(n, 1),
                       frac_dumbbell_h=sum(f.get('n_dumbbell_h', 0) >= 1 for f in fr) / max(n, 1),
                       per_seed={f"{r['scn']}{r['seed']}": sum(f.get('n_dumbbell_bodies', 0) >= 1 for f in frames(r, 40, 400)) for r in sorted(mig_runs[tag], key=lambda r: r['seed'])})
        lf = []
        for r in runs(D, tag, ('long',)):
            t1 = r['t_scl'] if (tag == 'v7y' and r['t_scl'] is not None) else None
            lf += [f for f in frames(r, 400.1, t1)]
        c2[tag]['long_after400_frames'] = len(lf); c2[tag]['long_after400_frac_dumbbell'] = sum(f.get('n_dumbbell_bodies', 0) >= 1 for f in lf) / max(len(lf), 1)
    fc, fy = c2['v7c']['frac_dumbbell'], c2['v7y']['frac_dumbbell']
    if fc >= 0.10:
        v = OK if fy <= 0.5 * fc else (NO if fy > 0.75 * fc else UND)
    else:
        v = NO if fy > fc + 0.05 else UND
    c2['verdict'] = v; J['claim2'] = c2

    # ---------------- 주장 3 ----------------
    c3 = {}
    groups = {'mig': lambda tag: [f for r in mig_runs[tag] for f in frames(r, 40, 400)], 'food': lambda tag: [f for r in food_runs[tag] for f in frames(r, 40)]}
    meas = (('dead_thread_frac', 0.002), ('film_frac', 0.002), ('dead_tips', 0.2))
    sub = []
    for g, fn in groups.items():
        c3[g] = {}
        for tag in ('v7c', 'v7y'):
            fr = fn(tag)
            c3[g][tag] = {m: float(np.mean([f.get(m, 0) for f in fr])) if fr else None for m, _ in meas}
            c3[g][tag].update({m + s: float(np.mean([f.get(m + s, 0) for f in fr])) if fr else None for m, _ in meas if m != 'film_frac' for s in ('_s05', '_s20')})
            c3[g][tag]['frames'] = len(fr)
        for m, neg in meas:
            a, b = c3[g]['v7c'][m], c3[g]['v7y'][m]
            if a is None or b is None:
                sv = UND
            elif a < neg and b < neg:
                sv = NA
            else:
                rr = b / a if a > 0 else np.inf
                sv = OK if rr <= 0.75 else (NO if rr >= 1.0 else UND)
            c3[g][m + '_verdict'] = sv; sub.append(sv)
    if NO in sub: v = NO
    elif all(s in (OK, NA) for s in sub) and OK in sub: v = OK
    else: v = UND
    c3['verdict'] = v; J['claim3'] = c3

    # ---------------- 주장 4 ----------------
    c4 = {}
    # (a)
    a = {}
    for s in FOOD_SCN:
        a[s] = {tag: int(sum(sum(x is not None for x in r['t_touch']) for r in runs(D, tag, (s,)))) for tag in ('v7c', 'v7y')}
        a[s]['runs'] = {tag: len(runs(D, tag, (s,))) for tag in ('v7c', 'v7y')}
    tot_c = sum(a[s]['v7c'] for s in FOOD_SCN); tot_y = sum(a[s]['v7y'] for s in FOOD_SCN)
    if all(a[s]['v7y'] >= a[s]['v7c'] for s in FOOD_SCN): va = OK
    elif tot_y <= tot_c - 2 or any(a[s]['v7y'] <= a[s]['v7c'] - 2 for s in FOOD_SCN): va = NO
    else: va = UND
    a['total'] = dict(v7c=tot_c, v7y=tot_y); a['verdict'] = va; c4['a'] = a
    # (b)
    b = dict(pairs=[])
    ratios = {}; last_by = {s: [] for s in FOOD_SCN}
    for s in FOOD_SCN:
        for rc in runs(D, 'v7c', (s,)):
            ry = D.get(rc['name'].replace('_v7c', '_v7y'))
            if ry is None: continue
            T = rc['T']; K = len(rc['t_touch'])
            tc = sorted([x if x is not None else T for x in rc['t_touch']]); ty = sorted([x if x is not None else T for x in ry['t_touch']])
            pr = dict(scn=s, seed=rc['seed'], ctrl=tc, cand=ty, ctrl_n=sum(x is not None for x in rc['t_touch']), cand_n=sum(x is not None for x in ry['t_touch']))
            b['pairs'].append(pr)
            for k in range(K):
                rr = ty[k] / max(tc[k], 1e-9)
                ratios.setdefault(k + 1, []).append(rr)
                if k == K - 1: ratios.setdefault('last', []).append(rr); last_by[s].append(rr)
    b['median_ratio'] = {str(k): float(np.median(v_)) for k, v_ in ratios.items()}
    b['median_ratio_last_by_scn'] = {s: float(np.median(v_)) if v_ else None for s, v_ in last_by.items()}
    mr = list(b['median_ratio'].values()); ml = [x for x in b['median_ratio_last_by_scn'].values() if x is not None]
    if mr and all(x <= 1.2 for x in mr) and all(x <= 1.4 for x in ml): vb = OK
    elif any(x > 1.4 for x in mr) or any(x > 1.6 for x in ml): vb = NO
    else: vb = UND
    b['verdict'] = vb; c4['b'] = b
    # (c)
    c = dict(pairs=[])
    rt = []; rd = []; miss = {'v7c': 0, 'v7y': 0}
    for rc in mig_runs['v7c']:
        ry = D.get(rc['name'].replace('_v7c', '_v7y'))
        if ry is None: continue
        mc = mig_measures(rc); my = mig_measures(ry)
        c['pairs'].append(dict(seed=rc['seed'], scn=rc['scn'], ctrl=dict(t_touch=mc['t_touch'], d400=mc['d400']), cand=dict(t_touch=my['t_touch'], d400=my['d400'])))
        tc = mc['t_touch'] if mc['t_touch'] is not None else 400.0; ty = my['t_touch'] if my['t_touch'] is not None else 400.0
        miss['v7c'] += mc['t_touch'] is None; miss['v7y'] += my['t_touch'] is None
        rt.append(ty / tc); rd.append(my['d400'] / max(mc['d400'], 1e-9))
    c['median_ratio_t_touch'] = float(np.median(rt)) if rt else None; c['median_ratio_d400'] = float(np.median(rd)) if rd else None; c['not_touched'] = miss
    c['median_t_touch'] = {tag: pct([mig_measures(r)['t_touch'] if mig_measures(r)['t_touch'] is not None else 400.0 for r in mig_runs[tag]], 50) for tag in ('v7c', 'v7y')}
    c['median_d400'] = {tag: pct([mig_measures(r)['d400'] for r in mig_runs[tag]], 50) for tag in ('v7c', 'v7y')}
    if rt and c['median_ratio_t_touch'] <= 1.10 and c['median_ratio_d400'] >= 0.90 and miss['v7y'] <= miss['v7c']: vc = OK
    elif rt and (c['median_ratio_t_touch'] > 1.25 or c['median_ratio_d400'] < 0.75 or miss['v7y'] >= miss['v7c'] + 2): vc = NO
    else: vc = UND
    c['verdict'] = vc; c4['c'] = c
    sv = [va, vb, vc]
    c4['verdict'] = NO if NO in sv else (OK if all(x == OK for x in sv) else UND); J['claim4'] = c4

    # ---------------- 주장 5 ----------------
    c5 = {}
    for tag in ('v7c', 'v7y'):
        e = [mig_measures(r) for r in sorted(mig_runs[tag], key=lambda r: r['seed'])]
        err = [x['err35'] for x in e if x['err35'] is not None]
        npos = sum(x > 0 for x in err); nneg = sum(x < 0 for x in err)
        c5[tag] = dict(n=len(err), errors=[round(x, 1) for x in err], mean=float(np.mean(err)) if err else None, median_abs=float(np.median(np.abs(err))) if err else None,
                       n_pos=npos, n_neg=nneg, sign_p=float(binomtest(npos, npos + nneg, 0.5).pvalue) if npos + nneg else None,
                       err_touch=[round(x['err_touch'], 1) if x.get('err_touch') is not None else None for x in e])
    y = c5['v7y']
    if y['n'] and y['median_abs'] <= 20 and abs(y['mean']) <= 10 and y['sign_p'] >= 0.05: v = OK
    elif y['n'] and (y['median_abs'] > 35 or y['sign_p'] < 0.01): v = NO
    else: v = UND
    c5['verdict'] = v; J['claim5'] = c5

    # ---------------- 주장 6 ----------------
    c6 = {}
    for tag in ('v7c', 'v7y'):
        fr_all = []; far_by_run = {}
        for r in main_runs[tag]:
            t1 = r['t_scl'] if (tag == 'v7y' and r['t_scl'] is not None) else None
            fr = frames(r, 40, t1); fr_all += fr
            far_by_run[r['name']] = sum(f.get('n_far100', 0) >= 1 for f in fr)
        n = len(fr_all)
        c6[tag] = dict(frames=n, frac_tail30=sum(f.get('n_tail30', 0) >= 1 for f in fr_all) / max(n, 1), far100_frames=int(sum(far_by_run.values())),
                       runs_with_far100_ge2=[k for k, x in far_by_run.items() if x >= 2], max_tail_L=max((f.get('max_tail_L', 0) for f in fr_all), default=0),
                       max_far_L=max((f.get('max_far_L', 0) for f in fr_all), default=0), max_trunk_L=max((f.get('max_trunk_L', 0) for f in fr_all), default=0),
                       frac_trunk100=sum(f.get('n_trunk100', 0) >= 1 for f in fr_all) / max(n, 1),
                       p95_max_tail_L=pct([f.get('max_tail_L', 0) for f in fr_all], 95))
    y = c6['v7y']
    if y['far100_frames'] == 0 and y['frac_tail30'] <= 0.05: v = OK
    elif y['runs_with_far100_ge2'] or y['frac_tail30'] > 0.15: v = NO
    else: v = UND
    c6['verdict'] = v; J['claim6'] = c6

    # ---------------- 주장 7 ----------------
    c7 = dict(runs=[])
    for r in sorted(runs(D, 'v7y', MAIN_SCN), key=lambda r: (r['scn'], r['seed'])):
        if r.get('scl') is None or r['t_scl'] is None: continue
        if r['T'] - r['t_scl'] < 300: continue
        S = r['scl']; tt = S['t_trap_frame']
        fr = [f for f in r['frames'] if f['t'] >= tt - 1e-9]
        f0 = fr[0]; fE = fr[-1]
        nb2 = f0.get('n_ge2', 0)
        breakup = any(f.get('n_ge2', 0) > nb2 for f in fr[1:])
        allc = [all(b['compact'] for b in f.get('bodies', [])) and len(f.get('bodies', [])) > 0 for f in fr]
        a_ok = bool(allc[-1] and not breakup)
        tg = S.get('t90') if S.get('t90') is not None else tt          # 맺힘 = 모임 곡선이 90% 에 닿은 뒤 처음으로 한 덩어리 조건을 채운 장면
        it = next((i for i, x in enumerate(allc) if x and fr[i]['t'] >= tg - 20 + 1e-9), None)
        if it is None:
            b_ok = None; t_f = None
        else:
            t_f = fr[it]['t']; A_f = fr[it]['bodies'][0]['area']
            b_ok = bool(all(allc[it:]) and all(f['bodies'][0]['area'] <= 1.25 * A_f for f in fr[it:]))
        Dr = S.get('D_ratio_s4', [])
        c_ok = bool(Dr and all(x >= 1.2 for x in Dr))
        if S.get('t10') is None or S.get('t90') is None:
            d_ok = None                                               # 갇힐 때 이미 모여 있었다 (모임 곡선 변화 <= 0.05): 판정 못 함
        else:
            d_ok = bool(30 <= (S['t90'] - r['t_scl']) <= 700 and (S['t90'] - S['t10']) >= 30)
        e_vals = []
        for bd in fE.get('bodies', []):
            cv = bd['h_cv_int'] if bd['h_cv_int'] is not None else bd['h_cv']; q = bd['h_p90_p10_int'] if bd['h_p90_p10_int'] is not None else bd['h_p90_p10']
            e_vals.append((cv, q))
        e_ok = bool(e_vals and all(cv >= 0.15 and q >= 1.4 for cv, q in e_vals))
        bE = fE['bodies'][0] if fE.get('bodies') else {}
        c7['runs'].append(dict(name=r['name'], t_scl=r['t_scl'], t_trap_frame=tt, nbodies_trap_ge2=nb2, nbodies_end_ge3=len(fE.get('bodies', [])), breakup=breakup,
                               final_compact=bool(allc[-1]), t_form=t_f, t10=S.get('t10'), t90=S.get('t90'), f_start=S.get('f_start'), f_end=S.get('f_end'),
                               D_ratio_s2=S.get('D_ratio_s2'), D_ratio_s4=Dr, D_ratio_s8=S.get('D_ratio_s8'),
                               end_area=bE.get('area'), end_vol=bE.get('vol'), end_A_over_V=(bE.get('area') / bE['vol']) if bE.get('vol') else None,
                               end_disc_iou=bE.get('disc_iou'), end_solidity=bE.get('solidity'), end_Pn=bE.get('Pn'), end_h_cv_int=bE.get('h_cv_int'), end_h_p90_p10_int=bE.get('h_p90_p10_int'),
                               end_core_share=bE.get('core_share'), end_thin_share=bE.get('thin_share'), end_max_strand_L=bE.get('max_strand_L'),
                               a=a_ok, b=b_ok, c_loc=c_ok, d=d_ok, e=e_ok))
    R = c7['runs']; nR = len(R)

    def runlevel(key):
        vals = [x[key] for x in R]
        nf = sum(v_ is False for v_ in vals); nn = sum(v_ is None for v_ in vals)
        if nR == 0: return UND, nf, nn
        if nf == 0 and nn == 0: return OK, nf, nn
        if nf >= 2 or nf >= 0.2 * nR: return NO, nf, nn
        return UND, nf, nn
    c7['a'] = dict(zip(('verdict', 'fail', 'none'), runlevel('a')))
    c7['b'] = dict(zip(('verdict', 'fail', 'none'), runlevel('b')))
    c7['d'] = dict(zip(('verdict', 'fail', 'none'), runlevel('d')))
    c7['e'] = dict(zip(('verdict', 'fail', 'none'), runlevel('e')))
    vl, nfl, nnl = runlevel('c_loc')
    av = [x['end_A_over_V'] for x in R if x['end_A_over_V'] is not None]; iou = [x['end_disc_iou'] for x in R if x['end_disc_iou'] is not None]
    cvav = float(np.std(av) / np.mean(av)) if len(av) >= 2 else None
    same = max((sum(abs(x - y_) <= 0.02 * y_ for x in av) for y_ in av), default=0)
    medi = float(np.median(iou)) if iou else None
    if vl == OK and cvav is not None and cvav >= 0.10 and same <= len(av) / 2 and medi <= 0.85: vcc = OK
    elif vl == NO or (cvav is not None and cvav < 0.05) or (medi is not None and medi >= 0.92) or sum(x['D_ratio_s4'] and min(x['D_ratio_s4']) < 1.0 for x in R) >= max(1, nR / 2): vcc = NO
    else: vcc = UND
    c7['c'] = dict(verdict=vcc, loc_fail=nfl, cv_A_over_V=cvav, max_same_A_over_V=same, median_disc_iou=medi)
    # (f)
    fp = []
    for rc in runs(D, 'v7c', ('slimeall',)):
        ry = D.get(rc['name'].replace('_v7c', '_v7y'))
        if ry is None: continue
        tl = min(rc['frames'][-1]['t'], ry['frames'][-1]['t'])
        fc_ = [f for f in rc['frames'] if abs(f['t'] - tl) < 1e-6][0]; fy_ = [f for f in ry['frames'] if abs(f['t'] - tl) < 1e-6][0]
        bc = fc_['bodies'][0] if fc_.get('bodies') else None; by = fy_['bodies'][0] if fy_.get('bodies') else None
        if bc is None or by is None: continue
        fp.append(dict(seed=rc['seed'], t=tl, ctrl=dict(solidity=bc['solidity'], Pn=bc['Pn'], thin_share=bc['thin_share'], holes=bc['holes'], area=bc['area']),
                       cand=dict(solidity=by['solidity'], Pn=by['Pn'], thin_share=by['thin_share'], holes=by['holes'], area=by['area']),
                       sol_better=by['solidity'] > bc['solidity'], Pn_better=by['Pn'] < bc['Pn']))
    ns = len(fp); sb = sum(x['sol_better'] for x in fp); pb = sum(x['Pn_better'] for x in fp)
    if ns and sb >= 0.8 * ns and pb >= 0.8 * ns: vf = OK
    elif ns and (ns - sb >= 0.5 * ns or ns - pb >= 0.5 * ns): vf = NO
    else: vf = UND
    c7['f'] = dict(verdict=vf, pairs=fp, n=ns, solidity_better=sb, Pn_better=pb)
    subs = [c7[k]['verdict'] for k in 'abcdef']
    c7['verdict'] = NO if NO in subs else (OK if all(x == OK for x in subs) else UND); c7['n_runs'] = nR
    J['claim7'] = c7

    # ---------------- 주장 8 ----------------
    c8 = dict(runs=[])
    bad_hard = False; bad_soft = False
    for r in sorted([r for r in D.values() if r['tag'].startswith('v7y')], key=lambda r: r['name']):
        fr = r['frames']
        vl = {round(a[0], 1): a[2] for a in r['vlog']}      # 넣은 부피(먹이) Vinj 의 시각별 기록
        dr = [abs(f['Vraw'] - r['V0'] - vl[round(f['t'], 1)]) / r['V0'] for f in fr if round(f['t'], 1) in vl]
        drift = max(dr) if dr else None                      # 저장 상태(float32 두께)의 합으로 다시 잰 부피 어긋남
        hmin_fr = min((f['hmin_wet'] for f in fr), default=None)
        x = dict(name=r['name'], stop=r['stop'], t_end=r['t_end'], T=r['T'], mass_err_max=r['mass_err_max'], h_min_end_of_step=r['h_min_end_of_step'],
                 neg_end_cellsteps=r['neg_end_cellsteps'], V_crumb_rel=(r['V_crumb'] or 0) / r['V0'], frame_hmin=hmin_fr, frame_vol_drift=drift)
        hard = (r['stop'] != '' or abs(r['t_end'] - r['T']) > 0.05 or r['h_min_end_of_step'] < -1e-6 or r['mass_err_max'] > 1e-6 or (hmin_fr is not None and hmin_fr < -1e-6))
        soft = (r['h_min_end_of_step'] < -1e-9 or (r['neg_end_cellsteps'] or 0) > 0 or r['mass_err_max'] > 1e-9 or x['V_crumb_rel'] > 1e-6 or (drift is not None and drift > 1e-5))
        x['hard_fail'] = bool(hard); x['soft_fail'] = bool(soft)
        bad_hard |= hard; bad_soft |= soft
        c8['runs'].append(x)
    exp = sum(1 for ln in open(os.environ.get('V7_JOBS') or os.path.join(V, 'jobs.txt')) if ' v7y' in ln)
    c8['expected_candidate_runs'] = exp; c8['found_candidate_runs'] = len(c8['runs'])
    if len(c8['runs']) < exp: bad_hard = True
    c8['verdict'] = NO if bad_hard else (UND if bad_soft else OK); J['claim8'] = c8

    # ---------------- 주장 9 ----------------
    c9 = dict(inrun={})
    sub = []
    for s in MAIN_SCN:
        st = {}
        for tag in ('v7c', 'v7y'):
            e = np.array([x[1] for r in runs(D, tag, (s,)) for x in r['mg_err_series']], float)
            st[tag] = dict(n=int(e.size), median=float(np.median(e)) if e.size else None, p90=pct(e, 90), p99=pct(e, 99), max=float(e.max()) if e.size else None,
                           n_gt03=int((e > 0.3).sum()), n_gt1=int((e > 1.0).sum()), frac_gt03=float((e > 0.3).mean()) if e.size else None)
        c, y = st['v7c'], st['v7y']
        if not c['n'] or not y['n']: sv = UND
        elif y['median'] > 1.5 * c['median'] or y['p90'] > 1.5 * c['p90'] or y['n_gt1'] > 0: sv = NO
        elif y['median'] <= 1.1 * c['median'] and y['p90'] <= 1.1 * c['p90'] and y['n_gt03'] == 0: sv = OK
        elif y['n_gt03'] > 0 and y['frac_gt03'] > (c['frac_gt03'] or 0): sv = NO
        else: sv = UND
        st['verdict'] = sv; sub.append(sv); c9['inrun'][s] = st
    rp = os.path.join(DATA, 'replay.json')
    if os.path.exists(rp):
        R9 = json.load(open(rp))
        rat = np.array([x['pcg']['e_flux'] / max(x['mg']['e_flux'], 1e-300) for x in R9])
        em = np.array([x['mg']['e_flux'] for x in R9]); ep = np.array([x['pcg']['e_flux'] for x in R9])
        c9['replay'] = dict(n=len(R9), median_ratio_pcg_over_mg=float(np.median(rat)), frac_pcg_better=float((rat < 1).mean()),
                            mg=dict(median=float(np.median(em)), p90=pct(em, 90), max=float(em.max())), pcg=dict(median=float(np.median(ep)), p90=pct(ep, 90), max=float(ep.max())),
                            pcg_n_gt03=int((ep > 0.3).sum()), mg_n_gt03=int((em > 0.3).sum()),
                            dh_mg_max=float(max(x['mg']['e_dh'] for x in R9)), dh_pcg_max=float(max(x['pcg']['e_dh'] for x in R9)),
                            by_run={})
        for x in R9:
            c9['replay']['by_run'].setdefault(x['run'], []).append([x['t'], round(x['mg']['e_flux'], 5), round(x['pcg']['e_flux'], 5), x['scl']])
        rr = c9['replay']
        if rr['median_ratio_pcg_over_mg'] <= 1.0 and rr['pcg_n_gt03'] == 0: sv = OK
        elif rr['median_ratio_pcg_over_mg'] > 1.5 or rr['pcg']['max'] > 1.0: sv = NO
        else: sv = UND
        rr['verdict'] = sv; sub.append(sv)
    else:
        sub.append(UND)
    c9['verdict'] = NO if NO in sub else (OK if all(x == OK for x in sub) else UND); J['claim9'] = c9

    json.dump(J, open(os.path.join(OUTD, 'judge_out.json'), 'w'), indent=1, ensure_ascii=False)
    for k in range(1, 10):
        print(f'claim{k}', J[f'claim{k}']['verdict'])


if __name__ == '__main__':
    main()
