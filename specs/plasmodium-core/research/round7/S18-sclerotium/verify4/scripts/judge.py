#!/usr/bin/env python3
"""verify4 판정: data/runs/*.json (measure.py 출력) 을 짝지어 여섯 주장을 판정한다.

usage: judge.py            -> logs/judge.txt, data/summary.json
판정 규칙은 verify4/CRITERIA.md 3절 그대로다.
"""
import json, glob, os, sys
import numpy as np
from scipy.stats import wilcoxon

V4 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRESH_TRAP = 0.05
MIG_W = 1600.0          # 옮겨 다니는 구간의 끝 (주장 2·3)
POST_LAG = 100.0        # 갇힌 뒤 이만큼 지나서부터 (주장 4)
ALPHA = 0.05
LINES = []


def say(*a):
    s = ' '.join(str(x) for x in a); LINES.append(s); print(s)


def load():
    R = {}
    for f in sorted(glob.glob(os.path.join(V4, 'data', 'runs', '*.json'))):
        r = json.load(open(f)); R[(r['scn'], r['seed'], r['cfg'])] = r
    return R


def complete(r):
    m = r.get('metrics') or {}
    return bool(m) and m.get('stop') == '' and abs(float(m.get('t_end', -1)) - r['T']) < 1e-6 and len(r['snaps']) > 0


def win(r, t0, t1): return [s for s in r['snaps'] if t0 - 1e-6 <= s['t'] <= t1 + 1e-6]


def t_trap(r):
    """처음으로 '그 뒤 모든 스냅숏에서 fresh < 0.05' 가 되는 시각 (없으면 None)"""
    S = r['snaps']; tt = None
    for s in reversed(S):
        if s['fresh'] < FRESH_TRAP: tt = s['t']
        else: break
    return tt


def wil(d, alt):
    d = np.asarray(d, float); d = d[d != 0]
    if d.size == 0: return 1.0
    try: return float(wilcoxon(d, alternative=alt).pvalue)
    except ValueError: return 1.0


def stat(c, w):
    c = np.asarray(c, float); w = np.asarray(w, float); d = w - c
    return dict(n=int(d.size), mean_c=float(c.mean()), mean_w=float(w.mean()), med_c=float(np.median(c)), med_w=float(np.median(w)), mean_d=float(d.mean()), med_d=float(np.median(d)),
                p_less=wil(d, 'less'), p_greater=wil(d, 'greater'), n_w_lower=int((d < 0).sum()), n_w_higher=int((d > 0).sum()), n_tie=int((d == 0).sum()))


def lower_test(c, w, floor):
    """후보(w)가 대조(c)보다 낮다는 주장. 'pass' | 'fail' | 'unclear'"""
    s = stat(c, w)
    if s['n'] < 6: s['verdict'] = 'unclear'; s['why'] = '짝 6 미만'; return s
    if s['mean_c'] < floor:
        s['verdict'] = 'fail' if (s['mean_w'] > s['mean_c'] and s['p_greater'] < ALPHA) else 'unclear'; s['why'] = '대조에서도 드묾'; return s
    if s['mean_d'] < 0 and s['med_d'] <= 0 and s['p_less'] < ALPHA: s['verdict'] = 'pass'
    elif s['mean_d'] >= 0 or s['p_greater'] < ALPHA: s['verdict'] = 'fail'
    else: s['verdict'] = 'unclear'
    return s


def higher_test(c, w):
    s = lower_test(-np.asarray(c, float), -np.asarray(w, float), -np.inf)
    s2 = stat(c, w); s2['verdict'] = s['verdict']; return s2


def noninf(c, w, worse_sign, margin, use_mean=False):
    """후보가 대조보다 '나쁘지 않다'. d = (w - c) * worse_sign 가 양수면 나쁨. 효과 = 중앙값(또는 평균)"""
    c = np.asarray(c, float); w = np.asarray(w, float); d = (w - c) * worse_sign
    eff = float(d.mean() if use_mean else np.median(d)); p = wil(d, 'greater')
    v = 'fail' if (eff > margin and p < ALPHA) else ('pass' if eff <= margin else 'unclear')
    return dict(n=int(d.size), mean_c=float(c.mean()), mean_w=float(w.mean()), med_c=float(np.median(c)), med_w=float(np.median(w)), worse_eff=eff, margin=float(margin), p_worse=p,
                n_w_worse=int((d > 0).sum()), n_w_better=int((d < 0).sum()), verdict=v)


def combine(vs):
    if any(v == 'fail' for v in vs): return 'fail'
    if all(v == 'pass' for v in vs): return 'pass'
    return 'unclear'


KO = {'pass': '맞음', 'fail': '틀림', 'unclear': '판정 못 함'}


def fmt(s, keys=('n', 'mean_c', 'mean_w', 'med_d', 'p_less', 'p_greater', 'verdict')):
    return ', '.join(f"{k}={s[k]:.4g}" if isinstance(s.get(k), float) else f"{k}={s.get(k)}" for k in keys if k in s)


def cen_at(r, t):
    tr = np.array(r['traj'], float); i = int(np.argmin(np.abs(tr[:, 0] - t))); return tr[i, 1:3]


def main():
    R = load(); OUT = dict()
    say('# verify4 판정 출력 (judge.py)')
    say('실행 수:', len(R), ' 끝까지 돈 실행:', sum(complete(r) for r in R.values()))
    seeds = lambda scn: sorted({k[1] for k in R if k[0] == scn})
    pairs = lambda scn: [s for s in seeds(scn) if (scn, s, 'v4c') in R and (scn, s, 'v4w') in R and complete(R[(scn, s, 'v4c')]) and complete(R[(scn, s, 'v4w')])]

    # ---------------- 주장 6: 건강 ----------------
    say('\n## 주장 6: 후보 실행은 모두 건강하다')
    h6 = []
    for k in sorted(R):
        r = R[k]; m = r.get('metrics') or {}; e = r.get('end_check') or {}
        Vb = (m.get('V0') or 0) + (m.get('Vinj') or 0)
        # [CRITERIA_CHANGES 1] 버린 부피는 절댓값으로 본다 (음수 외톨이 칸을 버리면 V_crumb 가 음수가 된다)
        chk = dict(run=r['name'], complete=complete(r), neg_end=(m.get('neg_end_cellsteps') == 0 and (m.get('h_min_end_of_step') or 0) >= 0 and r['hmin_snapshots'] >= 0 and e.get('hmin_wet', -1) >= 0),
                   mass=(m.get('mass_err_max') is not None and m['mass_err_max'] < 1e-10), crumb=(m.get('V_crumb') is not None and abs(m['V_crumb']) < 1e-3 * Vb),
                   endvol=(e.get('vol_rel_err', 1) < 1e-5), mass_err_max=m.get('mass_err_max'), V_crumb_rel=(abs(m.get('V_crumb', 0)) / Vb if Vb else None), V_crumb=m.get('V_crumb'),
                   neg_end_cellsteps=m.get('neg_end_cellsteps'), h_min_end=m.get('h_min_end_of_step'), crumb_cells=m.get('crumb_cells'), t_end=m.get('t_end'), stop=m.get('stop'))
        chk['ok'] = all(chk[x] for x in ('complete', 'neg_end', 'mass', 'crumb', 'endvol'))
        h6.append((k, chk))
    for cfg in ('v4w', 'v4c'):
        rows = [c for k, c in h6 if k[2] == cfg]; bad = [c for c in rows if not c['ok']]
        say(f"{cfg}: 실행 {len(rows)}, 건강 {len(rows) - len(bad)}, 안 건강 {len(bad)}")
        mx = max([c['mass_err_max'] or 0 for c in rows], default=0); cr = max([c['V_crumb_rel'] or 0 for c in rows], default=0)
        say(f"   mass_err_max 최대 {mx:.3g}, 버린 부피/몸 부피 최대 {cr:.3g}, 음수 끝 칸-스텝 합 {sum((c['neg_end_cellsteps'] or 0) for c in rows)}")
        for c in bad: say('   안 건강:', json.dumps({x: c[x] for x in c if x != 'run'}), c['run'])
    cand_runs = [c for k, c in h6 if k[2] == 'v4w']
    v6 = 'pass' if cand_runs and all(c['ok'] for c in cand_runs) else 'fail'
    say('주장 6 판정:', KO[v6]); OUT['claim6'] = dict(verdict=v6, runs=[c for k, c in h6])

    # ---------------- 주장 1: 부스러기 ----------------
    say('\n## 주장 1: 부스러기가 없다 (t >= 100 과 끝)')
    d1 = []
    for k in sorted(R):
        r = R[k]; S = win(r, 100, 1e9)
        ds = [s for s in S if s['debris_n'] > 0]
        d1.append(dict(run=r['name'], scn=k[0], cfg=k[2], snaps=len(S), debris_snaps=len(ds), debris_end=r['snaps'][-1]['debris_n'] if r['snaps'] else None,
                       debris_max_n=max([s['debris_n'] for s in S], default=0), debris_max_share=max([s['debris_max_share'] for s in S], default=0.0),
                       first_t=ds[0]['t'] if ds else None, crumb_cells=(r.get('metrics') or {}).get('crumb_cells'), fission_runs=(r.get('metrics') or {}).get('fission_runs')))
    for cfg in ('v4c', 'v4w'):
        rows = [x for x in d1 if x['cfg'] == cfg]
        say(f"{cfg}: 실행 {len(rows)}, 부스러기 있는 실행 {sum(x['debris_snaps'] > 0 or (x['debris_end'] or 0) > 0 for x in rows)}, "
            f"부스러기 스냅숏 합 {sum(x['debris_snaps'] for x in rows)} / {sum(x['snaps'] for x in rows)}, 끝에 남은 실행 {sum((x['debris_end'] or 0) > 0 for x in rows)}, "
            f"외톨이 셀 마름(crumb) 있는 실행 {sum((x['crumb_cells'] or 0) > 0 for x in rows)}")
        for scn in sorted({x['scn'] for x in rows}):
            rr = [x for x in rows if x['scn'] == scn]
            say(f"   {scn}: 부스러기 실행 {sum(x['debris_snaps'] > 0 or (x['debris_end'] or 0) > 0 for x in rr)}/{len(rr)}, 스냅숏 {sum(x['debris_snaps'] for x in rr)}/{sum(x['snaps'] for x in rr)}, 끝 {sum((x['debris_end'] or 0) > 0 for x in rr)}")
    viol = [x for x in d1 if x['cfg'] == 'v4w' and (x['debris_snaps'] > 0 or (x['debris_end'] or 0) > 0)]
    for x in viol: say('   후보 부스러기:', x['run'], json.dumps({k: x[k] for k in ('debris_snaps', 'debris_end', 'debris_max_n', 'debris_max_share', 'first_t', 'crumb_cells', 'fission_runs')}))
    ctrl = [x for x in d1 if x['cfg'] == 'v4c']; ctrl_frac = sum(x['debris_snaps'] > 0 for x in ctrl) / max(len(ctrl), 1)
    v1a = 'pass' if not viol and any(x['cfg'] == 'v4w' for x in d1) else 'fail'
    v1b = 'pass' if ctrl_frac >= 0.5 else 'fail'
    v1 = combine([v1a, v1b])
    say(f"1a 후보에 부스러기 없음: {KO[v1a]} (부스러기 낸 후보 실행 {len(viol)})  1b 대조는 많이 만든다 (실행의 50% 이상): {KO[v1b]} ({ctrl_frac:.2f})")
    say('주장 1 판정:', KO[v1]); OUT['claim1'] = dict(verdict=v1, v1a=v1a, v1b=v1b, ctrl_frac=ctrl_frac, rows=d1)

    # ---------------- long: 갇힘 시각과 창 ----------------
    say('\n## long: 갇힘 시각 (내 측정: 가장자리의 새 땅 비율 < 0.05 가 끝까지)')
    LP = pairs('long'); info = {}
    for s in LP:
        c = R[('long', s, 'v4c')]; w = R[('long', s, 'v4w')]
        tc = t_trap(c); tw = t_trap(w); tscl = (w.get('metrics') or {}).get('t_scl')
        W = min([MIG_W] + [x for x in (tc, tw, tscl) if x is not None])
        info[s] = dict(T_trap_c=tc, T_trap_w=tw, t_scl_w=tscl, W=W, slime_c=(c.get('end_check') or {}).get('U_captures_slime'), slime_w=(w.get('end_check') or {}).get('U_captures_slime'))
        say(f"   s{s}: T_trap 대조 {tc}, 후보 {tw}, 후보 t_scl {tscl}, 이주 창 끝 {W}, 점액 포착률 c {info[s]['slime_c']} w {info[s]['slime_w']}")
    OUT['long_windows'] = info

    # ---------------- 주장 2 ----------------
    say('\n## 주장 2: 옮겨 다니는 동안 덩이가 갈리지 않는다 (long, 100 <= t <= 창 끝)')
    M2 = {k: ([], []) for k in ('multi', 'dumb', 'multi_h0.5_s0.1', 'dumb_h0.5_s0.1', 'multi_h0.7_s0.05', 'dumb_h0.7_s0.05')}; used2 = []
    for s in LP:
        W = info[s]['W']; Sc = win(R[('long', s, 'v4c')], 100, W); Sw = win(R[('long', s, 'v4w')], 100, W)
        if len(Sc) < 10 or len(Sw) < 10: say(f"   s{s}: 창 스냅숏 {len(Sc)}/{len(Sw)} < 10, 뺌"); continue
        used2.append(s)
        for key in M2:
            M2[key][0].append(np.mean([x[key] for x in Sc])); M2[key][1].append(np.mean([x[key] for x in Sw]))
    r2 = {}
    for key in M2:
        r2[key] = lower_test(M2[key][0], M2[key][1], floor=0.05); r2[key]['c'] = M2[key][0]; r2[key]['w'] = M2[key][1]
        say(f"   {key:18s}", ('(주) ' if key in ('multi', 'dumb') else '(민감도) ') + fmt(r2[key]))
    v2 = combine([r2['multi']['verdict'], r2['dumb']['verdict']])
    say('주장 2 판정:', KO[v2], ' 짝:', used2); OUT['claim2'] = dict(verdict=v2, pairs=used2, tests=r2)

    # ---------------- 주장 3 ----------------
    say('\n## 주장 3: 죽은 구조가 적다 (같은 창)')
    keys3 = ['film_cells', 'dead_thread', 'dead_tips', 'film_cells_0.2', 'film_cells_0.4', 'dead_thread_0.02', 'dead_thread_0.1', 'dead_tips_0.02', 'dead_tips_0.1', 'narrow_cells', 'tips', 'area']
    M3 = {k: ([], []) for k in keys3}
    for s in used2:
        W = info[s]['W']; Sc = win(R[('long', s, 'v4c')], 100, W); Sw = win(R[('long', s, 'v4w')], 100, W)
        for key in keys3:
            M3[key][0].append(np.mean([x.get(key, 0) for x in Sc])); M3[key][1].append(np.mean([x.get(key, 0) for x in Sw]))
    r3 = {}
    for key in keys3:
        r3[key] = lower_test(M3[key][0], M3[key][1], floor=1.0); r3[key]['c'] = M3[key][0]; r3[key]['w'] = M3[key][1]
        tag = '(주) ' if key in ('film_cells', 'dead_thread', 'dead_tips') else ('(참고) ' if key in ('narrow_cells', 'tips', 'area') else '(민감도) ')
        say(f"   {key:18s}", tag + fmt(r3[key]))
    v3 = combine([r3[k]['verdict'] for k in ('film_cells', 'dead_thread', 'dead_tips')])
    say('주장 3 판정:', KO[v3]); OUT['claim3'] = dict(verdict=v3, pairs=used2, tests=r3)

    # ---------------- 주장 4 ----------------
    say('\n## 주장 4: 갇히면 균핵이 된다 (long, 각 실행의 [T_trap + 100, 2000])')
    keys4 = ['n_mass', 'K', 'lam', 'main_narrow_share', 'n_lumps', 'n_big']
    M4 = {k: ([], []) for k in keys4}; used4 = []
    for s in LP:
        tc, tw = info[s]['T_trap_c'], info[s]['T_trap_w']
        if tc is None or tw is None: say(f"   s{s}: 갇힘 없음 (대조 {tc}, 후보 {tw}), 뺌"); continue
        Sc = win(R[('long', s, 'v4c')], tc + POST_LAG, 1e9); Sw = win(R[('long', s, 'v4w')], tw + POST_LAG, 1e9)
        if len(Sc) < 3 or len(Sw) < 3: say(f"   s{s}: 갇힌 뒤 스냅숏 {len(Sc)}/{len(Sw)} < 3, 뺌"); continue
        used4.append(s)
        for key in keys4:
            M4[key][0].append(np.mean([x[key] if x.get(key) is not None else np.nan for x in Sc])); M4[key][1].append(np.mean([x[key] if x.get(key) is not None else np.nan for x in Sw]))
    r4 = {}
    r4['n_mass'] = lower_test(M4['n_mass'][0], M4['n_mass'][1], floor=-np.inf)
    r4['K'] = higher_test(M4['K'][0], M4['K'][1]); r4['lam'] = higher_test(M4['lam'][0], M4['lam'][1])
    r4['main_narrow_share'] = lower_test(M4['main_narrow_share'][0], M4['main_narrow_share'][1], floor=-np.inf)
    for key in ('n_lumps', 'n_big'): r4[key] = stat(M4[key][0], M4[key][1]) if used4 else {}
    for key in keys4:
        if used4: r4[key]['c'] = M4[key][0]; r4[key]['w'] = M4[key][1]
        say(f"   {key:18s}", fmt(r4[key], ('n', 'mean_c', 'mean_w', 'med_d', 'p_less', 'p_greater', 'verdict')) if used4 else '-')
    # 절대 조건: 갇힌 후보 실행의 끝 상태
    ab = []
    for s in LP:
        w = R[('long', s, 'v4w')]; tw = info[s]['T_trap_w']
        if tw is None or len(win(w, tw + POST_LAG, 1e9)) < 3: continue
        e = w['snaps'][-1]; ok = (e['n_mass'] == 1 and e['n_big'] == 1 and (e['K'] or 0) >= 0.75 and (e['lam'] or 0) >= 0.5)
        ab.append(dict(seed=s, ok=ok, n_mass=e['n_mass'], n_big=e['n_big'], K=e['K'], lam=e['lam']))
        say(f"   끝 상태 후보 s{s}: 덩이 {e['n_mass']}, 몸 {e['n_big']}, K {e['K']:.3f}, lam {e['lam']:.3f} -> {'균핵' if ok else '아님'}")
    fr = sum(a['ok'] for a in ab) / len(ab) if ab else None
    va = 'unclear' if (fr is None or len(ab) < 6) else ('pass' if fr >= 0.8 else ('fail' if fr < 0.5 else 'unclear'))
    vr = 'unclear' if len(used4) < 6 else combine([r4[k]['verdict'] for k in ('n_mass', 'K', 'lam', 'main_narrow_share')])
    v4 = 'fail' if 'fail' in (va, vr) else ('pass' if (va == 'pass' and vr == 'pass') else 'unclear')
    say(f"절대(끝 상태 균핵 비율 >= 0.8): {KO[va]} ({fr}, 실행 {len(ab)})  상대(대조와 비교, 짝 {len(used4)}): {KO[vr]}")
    # 참고: 고정 창 [1800, 2000]
    F4 = {k: ([], []) for k in ('n_mass', 'K', 'lam', 'main_narrow_share')}
    for s in LP:
        Sc = win(R[('long', s, 'v4c')], 1800, 2000); Sw = win(R[('long', s, 'v4w')], 1800, 2000)
        for key in F4: F4[key][0].append(np.nanmean([x[key] if x.get(key) is not None else np.nan for x in Sc])); F4[key][1].append(np.nanmean([x[key] if x.get(key) is not None else np.nan for x in Sw]))
    rf = {k: stat(*F4[k]) for k in F4} if LP else {}
    for k in rf: say(f"   (참고, 고정 창 1800~2000) {k:18s}", fmt(rf[k], ('n', 'mean_c', 'mean_w', 'med_d', 'p_less', 'p_greater')))
    say('주장 4 판정:', KO[v4]); OUT['claim4'] = dict(verdict=v4, absolute=va, relative=vr, frac_scl=fr, end_states=ab, pairs=used4, tests=r4, fixed_window=rf)

    # ---------------- 주장 5 ----------------
    say('\n## 주장 5: 먹이 찾기와 이주는 나빠지지 않는다')
    r5 = {}; vs5 = []; pooled = dict(dn=[], dtau_rel=[])
    for scn in ('food4', 'food3', 'asym3'):
        P = pairs(scn)
        if not P: say(f"   {scn}: 짝 없음"); vs5.append('unclear'); continue
        nt = ([], []); tau = ([], []); tf = ([], [])
        for s in P:
            for j, cfg in enumerate(('v4c', 'v4w')):
                r = R[(scn, s, cfg)]; tt = r['metrics']['t_touch']; T = r['T']
                nt[j].append(sum(x is not None for x in tt)); tau[j].append(np.mean([x if x is not None else T for x in tt])); tf[j].append(min([x if x is not None else T for x in tt]))
        cmed = float(np.median(tau[0]))
        a = noninf(nt[0], nt[1], -1, 0.25, use_mean=True); b = noninf(tau[0], tau[1], +1, 0.10 * cmed); c_ = noninf(tf[0], tf[1], +1, 0.10 * float(np.median(tf[0])))
        a['c'], a['w'] = nt; b['c'], b['w'] = tau; c_['c'], c_['w'] = tf
        r5[scn] = dict(n_touched=a, tau=b, t_first_info=c_); vs5 += [a['verdict'], b['verdict']]
        pooled['dn'] += list(np.array(nt[1]) - np.array(nt[0])); pooled['dtau_rel'] += list((np.array(tau[1]) - np.array(tau[0])) / cmed)
        say(f"   {scn} 닿은 수      ", fmt(a, ('n', 'mean_c', 'mean_w', 'worse_eff', 'margin', 'p_worse', 'verdict')))
        say(f"   {scn} 닿는 시각 평균", fmt(b, ('n', 'med_c', 'med_w', 'worse_eff', 'margin', 'p_worse', 'verdict')))
        say(f"   {scn} 첫 닿음(참고)  ", fmt(c_, ('n', 'med_c', 'med_w', 'worse_eff', 'margin', 'p_worse', 'verdict')))
    if pooled['dn']:
        pa = noninf(np.zeros(len(pooled['dn'])), -np.array(pooled['dn']), 1, 0.25, use_mean=True)
        pb = noninf(np.zeros(len(pooled['dtau_rel'])), np.array(pooled['dtau_rel']), 1, 0.10)
        r5['pooled'] = dict(n_touched=pa, tau_rel=pb); vs5 += [pa['verdict'], pb['verdict']]
        say('   먹이 셋 묶음 닿은 수 (후보-대조 줄어듦)', fmt(pa, ('n', 'worse_eff', 'margin', 'p_worse', 'verdict')))
        say('   먹이 셋 묶음 닿는 시각 (상대)        ', fmt(pb, ('n', 'worse_eff', 'margin', 'p_worse', 'verdict')))
    # mig: mig 413~420 + long 401~412 (t <= 400 은 mig 와 같은 실행)
    rows = []
    for scn in ('mig', 'long'):
        for s in pairs(scn):
            row = []
            for cfg in ('v4c', 'v4w'):
                r = R[(scn, s, cfg)]; c0 = r['c0']; a_, d_ = r['foods'][0]; u = np.array([np.cos(np.radians(a_)), np.sin(np.radians(a_))])
                tt = r['metrics']['t_touch'][0]; tt = tt if (tt is not None and tt <= 400) else 400.0
                v200 = cen_at(r, 200.0) - c0; te = min(tt, 200.0); ve = cen_at(r, te) - c0
                head = float(np.degrees(np.arccos(np.clip(ve @ u / np.linalg.norm(ve), -1, 1)))) if np.linalg.norm(ve) >= 5 else 90.0
                row.append((tt, float(v200 @ u), head))
            rows.append((scn, s, row))
    if rows:
        tc = [x[2][0][0] for x in rows]; tw = [x[2][1][0] for x in rows]; pc = [x[2][0][1] for x in rows]; pw = [x[2][1][1] for x in rows]
        hc = [x[2][0][2] for x in rows]; hw = [x[2][1][2] for x in rows]
        a = noninf(tc, tw, +1, 0.10 * float(np.median(tc))); b = noninf(pc, pw, -1, 0.10 * float(np.median(pc))); c_ = noninf(hc, hw, +1, 10.0)
        a['c'], a['w'] = tc, tw; b['c'], b['w'] = pc, pw; c_['c'], c_['w'] = hc, hw
        r5['mig'] = dict(t_touch=a, P200=b, heading=c_, seeds=[(x[0], x[1]) for x in rows]); vs5 += [a['verdict'], b['verdict'], c_['verdict']]
        say(f"   mig 유인원 닿는 시각 (400 에서 자름)", fmt(a, ('n', 'med_c', 'med_w', 'worse_eff', 'margin', 'p_worse', 'verdict')))
        say(f"   mig t=200 유인원 쪽 이동 거리       ", fmt(b, ('n', 'med_c', 'med_w', 'worse_eff', 'margin', 'p_worse', 'verdict')))
        say(f"   mig 방향 오차(도)                    ", fmt(c_, ('n', 'med_c', 'med_w', 'worse_eff', 'margin', 'p_worse', 'verdict')))
    v5 = combine(vs5) if vs5 else 'unclear'
    say('주장 5 판정:', KO[v5]); OUT['claim5'] = dict(verdict=v5, tests=r5)

    say('\n## 요약')
    for i in (1, 2, 3, 4, 5, 6): say(f"주장 {i}: {KO[OUT[f'claim{i}']['verdict']]}")
    os.makedirs(os.path.join(V4, 'logs'), exist_ok=True); os.makedirs(os.path.join(V4, 'data'), exist_ok=True)
    open(os.path.join(V4, 'logs', 'judge.txt'), 'w').write('\n'.join(LINES) + '\n')
    json.dump(OUT, open(os.path.join(V4, 'data', 'summary.json'), 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    main()
