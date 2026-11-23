#!/usr/bin/env python3
"""verify2 판정: data/frames/*.json (measure.py) 와 data/runs_summary.json (collect.py) 을 CRITERIA.md 대로 판정한다.
-> data/verdict.json, logs/judge_out.txt (표준 출력과 같음)
"""
import glob, json, os, sys
import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, '..', 'data')
LONG = list(range(311, 327))
LINES = []


def say(*a):
    s = ' '.join(str(x) for x in a); LINES.append(s); print(s)


def rnd(x, n=4):
    if x is None: return None
    if isinstance(x, (list, tuple)): return [rnd(v, n) for v in x]
    return None if not np.isfinite(x) else round(float(x), n)


def wil(diff, alt):
    diff = np.asarray(diff, float)
    if np.all(diff == 0): return 1.0
    try: return float(wilcoxon(diff, alternative=alt, zero_method='wilcox').pvalue)
    except ValueError: return 1.0


def boot(diff, n=10000):
    diff = np.asarray(diff, float); rng = np.random.default_rng(0)
    m = diff[rng.integers(0, diff.size, (n, diff.size))].mean(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def pair_stats(c, g, alt):
    c = np.asarray(c, float); g = np.asarray(g, float); d = g - c
    return dict(ctrl_mean=rnd(c.mean()), cand_mean=rnd(g.mean()), diff_mean=rnd(d.mean()), diff_ci95=rnd(boot(d)), p=rnd(wil(d, alt), 5),
                n_lower=int((d < 0).sum()), n_higher=int((d > 0).sum()), n_equal=int((d == 0).sum()), ctrl=rnd(list(c), 3), cand=rnd(list(g), 3))


F = {}
for f in glob.glob(os.path.join(D, 'frames', '*.json')):
    j = json.load(open(f)); F[j['run']] = j['frames']
S = {d['name']: d for d in json.load(open(os.path.join(D, 'runs_summary.json')))}
name = lambda scn, s, arm: f'b_{scn}_s{s}_' + dict(ctrl='w16c', cand='w16gm', dense='w16gm_dense')[arm]
seeds_long = [s for s in LONG if name('long', s, 'ctrl') in F and name('long', s, 'cand') in F]
V = dict(n_long_pairs=len(seeds_long), seeds_long=seeds_long)
say(f'long 짝: {len(seeds_long)} ({seeds_long[0] if seeds_long else "-"}–{seeds_long[-1] if seeds_long else "-"})')


def win(fr, lo, hi, incl=False):
    return [x for x in fr if lo <= x['t'] < hi or (incl and x['t'] == hi)]


EARLY = (100, 1000, False); LATE = (1000, 2000, True)

# ================= claim 1 =================
say('\n== 주장 1: long 후보는 찢어지지 않는다')
c1 = dict(runs={}); ok = True
for s in seeds_long:
    fr = F[name('long', s, 'cand')]; sm = S.get(name('long', s, 'cand'), {})
    bad = [(x['t'], x['n8'], rnd(x['vout'], 6)) for x in fr if x['n8'] != 1 or x['vout'] > 0]
    n4 = sum(1 for x in fr if x['n4'] > 1)
    r = dict(frames=len(fr), bad_frames=bad[:20], n_bad=len(bad), frames_n4_gt1=n4, V_crumb=sm.get('V_crumb'), crumb_cells=sm.get('crumb_cells'))
    c1['runs'][s] = r
    if bad or sm.get('V_crumb', 1) != 0 or sm.get('crumb_cells', 1) != 0 or len(fr) < 100: ok = False
dense = {}
for s in (311, 312):
    sm = S.get(name('long', s, 'dense'))
    if sm is None: dense[s] = None; ok = False; continue
    dense[s] = dict(n=sm['dense_n'], nbad=sm['dense_nbad'], bad=sm['dense_bad'][:10], h_identical=sm.get('dense_h_identical'), wet_identical=sm.get('dense_wet_identical'), tmin=sm['dense_tmin'], tmax=sm['dense_tmax'])
    if not sm.get('dense_h_identical'): say(f'  촘촘 {s}: h.npy 가 w16gm 과 다름 -> 주장 1 판정에서 뺌')
    elif sm['dense_nbad'] != 0: ok = False
c1['dense'] = dense
ctl = {}
for s in seeds_long:
    fr = F[name('long', s, 'ctrl')]; sm = S.get(name('long', s, 'ctrl'), {})
    ctl[s] = dict(frames_torn=sum(1 for x in fr if x['n8'] > 1), vout_max=rnd(max(x['vout'] for x in fr), 5), V_crumb=rnd(sm.get('V_crumb'), 4), crumb_cells=sm.get('crumb_cells'))
c1['ctrl'] = ctl
c1['verdict'] = '맞음' if ok and seeds_long else '틀림'
nbad = sum(r['n_bad'] for r in c1['runs'].values()); vc = [r['V_crumb'] for r in c1['runs'].values()]
say(f'  후보: 어긴 프레임 {nbad} / {sum(r["frames"] for r in c1["runs"].values())}, V_crumb 최대 {max(vc) if vc else None}, crumb_cells 합 {sum(r["crumb_cells"] or 0 for r in c1["runs"].values())}')
say(f'  4-연결로만 갈라진 프레임(후보): {sum(r["frames_n4_gt1"] for r in c1["runs"].values())}')
say(f'  촘촘: ' + '; '.join(f'{s}: 기록 {d["n"]}개, comps≠1 {d["nbad"]}, h 같음 {d["h_identical"]}' if d else f'{s}: 없음' for s, d in dense.items()))
say(f'  대조: 찢어진 프레임이 있는 실행 {sum(1 for v in ctl.values() if v["frames_torn"] > 0)}/{len(ctl)}, 찢어진 프레임 합 {sum(v["frames_torn"] for v in ctl.values())}, V_crumb 합 {rnd(sum(v["V_crumb"] or 0 for v in ctl.values()), 3)}, 밖 부피 몫 최대 {max(v["vout_max"] for v in ctl.values()) if ctl else None}')
say(f'  판정: {c1["verdict"]}')
V['claim1'] = c1


# ================= claim 2 =================
def dfrac(run, key, w, extra=None):
    fr = win(F[run], *w)
    if not fr: return np.nan
    if extra == 'rel': return float(np.mean([x['db'][key] and x['blob'].get('rel', False) for x in fr]))
    return float(np.mean([x['db'][key] for x in fr]))


def longest(run, key, w):
    fr = win(F[run], *w); best = cur = 0
    for x in fr:
        cur = cur + 1 if x['db'][key] else 0; best = max(best, cur)
    return best * 20


say('\n== 주장 2: 아령이 대조보다 드물다')
PK = 'M=wet|r=3|f=0.10|neck=any'
VK = [f'M={M}|r={r}|f={f:.2f}|neck={n}' for M in ('wet', 'h03') for r in (2, 3, 4) for f in (0.05, 0.10, 0.20) for n in ('any', 'b2')]
c2 = {}
for wn, w in (('early', EARLY), ('late', LATE)):
    c = [dfrac(name('long', s, 'ctrl'), PK, w) for s in seeds_long]; g = [dfrac(name('long', s, 'cand'), PK, w) for s in seeds_long]
    ps = pair_stats(c, g, 'less')
    var = {}
    for k in VK:
        cv = np.mean([dfrac(name('long', s, 'ctrl'), k, w) for s in seeds_long]); gv = np.mean([dfrac(name('long', s, 'cand'), k, w) for s in seeds_long])
        var[k] = [rnd(cv), rnd(gv)]
    nless = sum(1 for v in var.values() if v[1] < v[0]); share = nless / len(var)
    if ps['ctrl_mean'] < 0.02: vd = '판정 못 함'
    elif ps['cand_mean'] >= ps['ctrl_mean']: vd = '틀림'
    elif ps['p'] < 0.05 and share >= 0.75: vd = '맞음'
    else: vd = '판정 못 함'
    rep = {}
    for k2 in ('allpieces_r3_f10', 'torn10', 'bad_db_or_torn10'):      # [CRITERIA_CHANGES 1] report only
        rep[k2] = pair_stats([dfrac(name('long', s, 'ctrl'), k2, w) for s in seeds_long], [dfrac(name('long', s, 'cand'), k2, w) for s in seeds_long], 'less')
    rep['native_h06_f05'] = pair_stats([dfrac(name('long', s, 'ctrl'), 'native_h06_f05', w) for s in seeds_long], [dfrac(name('long', s, 'cand'), 'native_h06_f05', w) for s in seeds_long], 'less')
    rep['rel025'] = pair_stats([dfrac(name('long', s, 'ctrl'), PK, w, 'rel') for s in seeds_long], [dfrac(name('long', s, 'cand'), PK, w, 'rel') for s in seeds_long], 'less')
    w2 = (100, 700, False) if wn == 'early' else (1300, 2000, True)
    rep['window_alt'] = pair_stats([dfrac(name('long', s, 'ctrl'), PK, w2) for s in seeds_long], [dfrac(name('long', s, 'cand'), PK, w2) for s in seeds_long], 'less')
    rep['longest_run_time'] = pair_stats([longest(name('long', s, 'ctrl'), PK, w) for s in seeds_long], [longest(name('long', s, 'cand'), PK, w) for s in seeds_long], 'less')
    rep['narrow_b2_primary'] = pair_stats([dfrac(name('long', s, 'ctrl'), PK.replace('any', 'b2'), w) for s in seeds_long], [dfrac(name('long', s, 'cand'), PK.replace('any', 'b2'), w) for s in seeds_long], 'less')
    c2[wn] = dict(primary=ps, variants=var, variants_cand_lower=nless, variants_n=len(var), share=rnd(share, 3), report_only=rep, verdict=vd)
    say(f'  [{wn}] 기본 D: 대조 {ps["ctrl_mean"]} -> 후보 {ps["cand_mean"]} (차 {ps["diff_mean"]}, 95% {ps["diff_ci95"]}, p={ps["p"]}, 시드 낮음/높음/같음 {ps["n_lower"]}/{ps["n_higher"]}/{ps["n_equal"]})')
    say(f'          변형 {nless}/{len(var)} 에서 후보가 낮음 ({share:.0%}); 판정 {vd}')
    for k, v in rep.items(): say(f'          보고만 {k}: 대조 {v["ctrl_mean"]} -> 후보 {v["cand_mean"]} (p={v["p"]}, 낮음/높음 {v["n_lower"]}/{v["n_higher"]})')
vs = [c2['early']['verdict'], c2['late']['verdict']]
c2['verdict'] = '맞음' if all(v == '맞음' for v in vs) else ('틀림' if '틀림' in vs else '판정 못 함')
say(f'  판정: {c2["verdict"]}')
V['claim2'] = c2


# ================= claim 3 =================
def cmean(run, grp, key, w, norm=False):
    fr = win(F[run], *w)
    if not fr: return np.nan
    return float(np.mean([x[grp][key] / (x['body_area'] if norm else 1.0) for x in fr]))


say('\n== 주장 3: long 늦은 창, 가장 큰 몸 안')
c3 = {}
specs = dict(film=('film', 'h=0.3|a=40|b=3', [f'h={h}|a={a}|b={b}' for h in (0.2, 0.3, 0.4) for a in (20, 40, 80) for b in (3, 2)]),
             dead=('dead', 'line=3|F0.1|smin=4', [f'line={l}|{c}|smin={m}' for l in (3, 2) for c in ('F0.03', 'F0.1', 'F0.3', 'C0.5', 'C1', 'C2') for m in (2, 4, 8)]),
             tip=('tip', 'L=3|cells', [f'L={L}|{m}' for L in (1, 3, 6) for m in ('cells', 'lines')]))
for nm, (grp, pk, vk) in specs.items():
    c = [cmean(name('long', s, 'ctrl'), grp, pk, LATE) for s in seeds_long]; g = [cmean(name('long', s, 'cand'), grp, pk, LATE) for s in seeds_long]
    alt = 'greater' if nm == 'tip' else 'less'
    ps = pair_stats(c, g, alt); var = {}
    for k in vk:
        var[k] = [rnd(np.mean([cmean(name('long', s, 'ctrl'), grp, k, LATE) for s in seeds_long]), 3), rnd(np.mean([cmean(name('long', s, 'cand'), grp, k, LATE) for s in seeds_long]), 3)]
    if nm == 'tip':
        okf = lambda a, b: b <= 1.5 * a + 3
        nok = sum(1 for v in var.values() if okf(*v)); share = nok / len(var)
        if okf(ps['ctrl_mean'], ps['cand_mean']) and share >= 0.75: vd = '맞음'
        elif not okf(ps['ctrl_mean'], ps['cand_mean']) and ps['p'] < 0.05: vd = '틀림'
        else: vd = '판정 못 함'
    else:
        nok = sum(1 for v in var.values() if v[1] < v[0]); share = nok / len(var)
        if ps['ctrl_mean'] < 1 and ps['cand_mean'] < 1: vd = '판정 못 함'
        elif ps['cand_mean'] >= ps['ctrl_mean']: vd = '틀림'
        elif ps['p'] < 0.05 and share >= 0.75: vd = '맞음'
        else: vd = '판정 못 함'
    rep = {}
    rep['per_area'] = pair_stats([cmean(name('long', s, 'ctrl'), grp, pk, LATE, True) for s in seeds_long], [cmean(name('long', s, 'cand'), grp, pk, LATE, True) for s in seeds_long], alt)
    rep['late_1500'] = pair_stats([cmean(name('long', s, 'ctrl'), grp, pk, (1500, 2000, True)) for s in seeds_long], [cmean(name('long', s, 'cand'), grp, pk, (1500, 2000, True)) for s in seeds_long], alt)
    rep['early'] = pair_stats([cmean(name('long', s, 'ctrl'), grp, pk, EARLY) for s in seeds_long], [cmean(name('long', s, 'cand'), grp, pk, EARLY) for s in seeds_long], alt)
    if nm == 'film': rep['novein'] = pair_stats([cmean(name('long', s, 'ctrl'), grp, 'primary_novein', LATE) for s in seeds_long], [cmean(name('long', s, 'cand'), grp, 'primary_novein', LATE) for s in seeds_long], alt)
    if nm == 'tip': rep['maxlen'] = pair_stats([cmean(name('long', s, 'ctrl'), grp, 'maxlen', LATE) for s in seeds_long], [cmean(name('long', s, 'cand'), grp, 'maxlen', LATE) for s in seeds_long], alt)
    c3[nm] = dict(primary=ps, variants=var, variants_ok=nok, variants_n=len(var), share=rnd(share, 3), report_only=rep, verdict=vd)
    say(f'  [{nm}] 기본 ({pk}): 대조 {ps["ctrl_mean"]} -> 후보 {ps["cand_mean"]} (차 {ps["diff_mean"]}, 95% {ps["diff_ci95"]}, p({alt})={ps["p"]}, 낮음/높음/같음 {ps["n_lower"]}/{ps["n_higher"]}/{ps["n_equal"]})')
    say(f'          변형 {nok}/{len(var)} ({share:.0%}) 가 {"기준 안" if nm == "tip" else "후보가 낮음"}; 판정 {vd}')
    for k, v in rep.items(): say(f'          보고만 {k}: 대조 {v["ctrl_mean"]} -> 후보 {v["cand_mean"]} (p={v["p"]}, 낮음/높음 {v["n_lower"]}/{v["n_higher"]})')
vs = [c3[k]['verdict'] for k in ('film', 'dead', 'tip')]
c3['verdict'] = '맞음' if all(v == '맞음' for v in vs) else ('틀림' if '틀림' in vs else '판정 못 함')
say(f'  판정: {c3["verdict"]}')
V['claim3'] = c3

# ================= claim 4 =================
say('\n== 주장 4: 먹이 찾기와 굶은 이주')
c4 = {}; allok = True
for scn, seeds in (('food3', range(311, 318)), ('asym3', range(311, 318)), ('food4', range(311, 316)), ('mig', range(311, 319))):
    pr = [s for s in seeds if name(scn, s, 'ctrl') in S and name(scn, s, 'cand') in S]
    if not pr: c4[scn] = None; allok = False; say(f'  [{scn}] 실행 없음'); continue
    if scn == 'mig':
        c = [S[name(scn, s, 'ctrl')]['disp'] for s in pr]; g = [S[name(scn, s, 'cand')]['disp'] for s in pr]
        tc = sum(1 for s in pr if S[name(scn, s, 'ctrl')]['t_touch'][0] is not None); tg = sum(1 for s in pr if S[name(scn, s, 'cand')]['t_touch'][0] is not None)
        ps = pair_stats(c, g, 'less'); okk = ps['cand_mean'] >= 0.9 * ps['ctrl_mean'] and tg >= tc - 1
        ang = dict(ctrl=[rnd(S[name(scn, s, 'ctrl')].get('disp_angle_deg'), 1) for s in pr], cand=[rnd(S[name(scn, s, 'cand')].get('disp_angle_deg'), 1) for s in pr])
        tt = dict(ctrl=[S[name(scn, s, 'ctrl')]['t_touch'][0] for s in pr], cand=[S[name(scn, s, 'cand')]['t_touch'][0] for s in pr])
        c4[scn] = dict(seeds=pr, disp=ps, touched=[tc, tg], angle_deg=ang, t_touch=tt, ok=bool(okk))
        say(f'  [mig] disp: 대조 {ps["ctrl_mean"]} -> 후보 {ps["cand_mean"]} (p(후보<대조)={ps["p"]}), 닿음 {tc} -> {tg}, 각 대조 {ang["ctrl"]} 후보 {ang["cand"]}; {"나빠지지 않음" if okk else "나빠짐"}')
    else:
        def sc(d):
            T = d['T']; tau = [T if v is None else v for v in d['t_touch']]; return float(np.mean(tau)), sum(1 for v in d['t_touch'] if v is not None)
        c = [sc(S[name(scn, s, 'ctrl')]) for s in pr]; g = [sc(S[name(scn, s, 'cand')]) for s in pr]
        ps = pair_stats([x[0] for x in c], [x[0] for x in g], 'greater'); nc = sum(x[1] for x in c); ng = sum(x[1] for x in g)
        okk = ps['cand_mean'] <= 1.10 * ps['ctrl_mean'] and ng >= nc - 1
        tt = dict(ctrl=[S[name(scn, s, 'ctrl')]['t_touch'] for s in pr], cand=[S[name(scn, s, 'cand')]['t_touch'] for s in pr])
        c4[scn] = dict(seeds=pr, score=ps, touched=[nc, ng], t_touch=tt, ok=bool(okk))
        say(f'  [{scn}] 점수 S(평균 닿은 시각, 못 닿으면 T): 대조 {ps["ctrl_mean"]} -> 후보 {ps["cand_mean"]} (p(후보>대조)={ps["p"]}, 낮음/높음 {ps["n_lower"]}/{ps["n_higher"]}), 닿은 먹이 {nc} -> {ng}; {"나빠지지 않음" if okk else "나빠짐"}')
    allok &= bool(c4[scn]['ok'])
c4['verdict'] = '맞음' if allok else '틀림'
say(f'  판정: {c4["verdict"]}')
V['claim4'] = c4

# ================= claim 5 =================
say('\n== 주장 5: 후보 실행 건강')
c5 = dict(runs=[], fails=[])
for nmn, d in S.items():
    if d['arm'] not in ('cand', 'dense'): continue
    chk = dict(neg=d['neg_end_cellsteps'] == 0, mass=d['mass_err_max'] < 1e-10, crumb=(d['V_crumb'] == 0 and d['crumb_cells'] == 0), comps=d['comps8_end'] == 1, stop=d['stop'] == '' and d['steps_done'] == int(round(d['T'] / 0.1)) + 1)
    c5['runs'].append(dict(name=nmn, neg_end_cellsteps=d['neg_end_cellsteps'], mass_err_max=d['mass_err_max'], V_crumb=d['V_crumb'], crumb_cells=d['crumb_cells'], comps8_end=d['comps8_end'], stop=d['stop'], ok=all(chk.values())))
    if not all(chk.values()): c5['fails'].append(dict(name=nmn, failed=[k for k, v in chk.items() if not v], neg_end_cellsteps=d['neg_end_cellsteps'], mass_err_max=d['mass_err_max'], V_crumb=d['V_crumb'], crumb_cells=d['crumb_cells'], comps8_end=d['comps8_end'], stop=d['stop']))
ctrl = [d for d in S.values() if d['arm'] == 'ctrl']
c5['ctrl_summary'] = dict(n=len(ctrl), neg_end_runs=sum(1 for d in ctrl if d['neg_end_cellsteps'] > 0), mass_err_max=max((d['mass_err_max'] for d in ctrl), default=None),
                          crumb_runs=sum(1 for d in ctrl if d['crumb_cells'] > 0), V_crumb_sum=sum(d['V_crumb'] for d in ctrl), torn_end_runs=sum(1 for d in ctrl if d['comps8_end'] != 1))
c5['n'] = len(c5['runs']); c5['verdict'] = '맞음' if c5['n'] == 45 and not c5['fails'] else '틀림'
say(f'  후보 실행 {c5["n"]}개, 어긴 실행 {len(c5["fails"])}: ' + '; '.join(f'{x["name"]} {x["failed"]}' for x in c5['fails'][:10]))
say(f'  mass_err_max 최대(후보) {max(r["mass_err_max"] for r in c5["runs"]) if c5["runs"] else None}')
say(f'  대조: {c5["ctrl_summary"]}')
say(f'  판정: {c5["verdict"]}')
V['claim5'] = c5


# ================= outside the claims =================
say('\n== 주장 밖 (long, 판정 없음)')
ob = {}
for key, lab in (('area', '넓이'), ('veins', '정맥 간선'), ('front', '앞머리 칸'), ('body_area', '가장 큰 몸 넓이')):
    for wn, w in (('early', EARLY), ('late', LATE)):
        c = [np.mean([x[key] for x in win(F[name('long', s, 'ctrl')], *w)]) for s in seeds_long]; g = [np.mean([x[key] for x in win(F[name('long', s, 'cand')], *w)]) for s in seeds_long]
        ob[f'{key}_{wn}'] = pair_stats(c, g, 'less')
        say(f'  {lab} [{wn}]: 대조 {ob[f"{key}_{wn}"]["ctrl_mean"]} -> 후보 {ob[f"{key}_{wn}"]["cand_mean"]} (p(후보<대조)={ob[f"{key}_{wn}"]["p"]})')


def speed(run, w):
    fr = win(F[run], *w)
    if len(fr) < 2: return np.nan
    a = np.array(fr[0]['cen']); b = np.array(fr[-1]['cen'])
    return float(np.hypot(*(b - a)) / (fr[-1]['t'] - fr[0]['t']))


for wn, w in (('early', EARLY), ('late', LATE)):
    ob[f'speed_{wn}'] = pair_stats([speed(name('long', s, 'ctrl'), w) for s in seeds_long], [speed(name('long', s, 'cand'), w) for s in seeds_long], 'less')
    say(f'  무게중심 이동 속도 [{wn}] (셀/시간, 창 처음과 끝 사이 곧은 거리): 대조 {ob[f"speed_{wn}"]["ctrl_mean"]} -> 후보 {ob[f"speed_{wn}"]["cand_mean"]} (p={ob[f"speed_{wn}"]["p"]})')
rt = {arm: [d['runtime'] for d in S.values() if d['scn'] == 'long' and d['arm'] == arm] for arm in ('ctrl', 'cand')}
ob['runtime_long_mean'] = {k: rnd(np.mean(v), 1) if v else None for k, v in rt.items()}
say(f'  long 실행 시간 평균(초): {ob["runtime_long_mean"]}')
V['outside'] = ob

# ---- worst cases (candidate) ----
worst = {}
def wmax(fn, w=LATE):
    best = None
    for s in seeds_long:
        for x in win(F[name('long', s, 'cand')], *w):
            v = fn(x)
            if best is None or v > best[0]: best = (v, s, x['t'])
    return dict(value=best[0], seed=best[1], t=best[2]) if best else None
worst['film_late'] = wmax(lambda x: x['film']['h=0.3|a=40|b=3'])
worst['dead_late'] = wmax(lambda x: x['dead']['line=3|F0.1|smin=4'])
worst['tip_late'] = wmax(lambda x: x['tip']['L=3|cells'])
worst['dumbbell_late'] = wmax(lambda x: (x['blob']['blob_vol'][1] if x['db'][PK] and len(x['blob'].get('blob_vol', [])) > 1 else -1))
worst['dumbbell_early'] = wmax(lambda x: (x['blob']['blob_vol'][1] if x['db'][PK] and len(x['blob'].get('blob_vol', [])) > 1 else -1), EARLY)
runs_db = {s: dfrac(name('long', s, 'cand'), PK, LATE) - dfrac(name('long', s, 'ctrl'), PK, LATE) for s in seeds_long}
worst['seed_worst_dumbbell_diff_late'] = max(runs_db, key=runs_db.get) if runs_db else None
V['worst'] = worst
say('\n== 후보의 가장 나쁜 프레임 (늦은 창)')
for k, v in worst.items(): say(f'  {k}: {v}')

# ---- report only: extra.py results, mig direction error ----
ex = os.path.join(D, 'extra.json')
if os.path.exists(ex):
    E = json.load(open(ex)); V['extra_report_only'] = {k: v for k, v in E.items() if k != 'frames'}
    say('\n== 보고만 (extra.py, CRITERIA_CHANGES 2)')
    for k, v in V['extra_report_only'].items(): say(f'  {k}: {v}')
if c4.get('mig'):
    dev = {a: [abs(((x - 27.0) + 180) % 360 - 180) for x in c4['mig']['angle_deg'][a]] for a in ('ctrl', 'cand')}
    c4['mig']['angle_err_deg'] = {a: dict(mean=rnd(np.mean(v), 2), max=rnd(max(v), 2)) for a, v in dev.items()}
    say(f'  보고만 mig 이주 방향과 유인원 방향(27°) 사이 각의 평균/최대: 대조 {c4["mig"]["angle_err_deg"]["ctrl"]}, 후보 {c4["mig"]["angle_err_deg"]["cand"]}')
V['verdicts'] = {k: V[k]['verdict'] for k in ('claim1', 'claim2', 'claim3', 'claim4', 'claim5')}
say('\n== 판정 요약: ' + json.dumps(V['verdicts'], ensure_ascii=False))
json.dump(V, open(os.path.join(D, 'verdict.json'), 'w'), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
open(os.path.join(HERE, '..', 'logs', 'judge_out.txt'), 'w').write('\n'.join(LINES) + '\n')
