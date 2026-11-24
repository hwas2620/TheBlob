#!/usr/bin/env python3
"""verify5: 판정. usage: judge.py [DATA_DIR [OUT_DIR]]   (기본: verify5/data/runs, 출력은 verify5/logs·verify5/data)

verify5/data/runs/b_<scn>_s<seed>_<v5c|v5y>.json 을 모두 읽어, 같은 시드끼리 짝을 지어 CRITERIA.md 의 규칙대로 판정한다.
쓰는 것: verify5/logs/judge.txt (사람이 읽는 판정), verify5/data/judge.json (수치 전부)
"""
import sys, os, json, glob, re
import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__)); V5 = os.path.dirname(HERE)
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(V5, 'data', 'runs')
OUT_TXT = os.path.join(V5, 'logs', 'judge.txt'); OUT_JSON = os.path.join(V5, 'data', 'judge.json')
if len(sys.argv) > 2: OUT_TXT = os.path.join(sys.argv[2], 'judge.txt'); OUT_JSON = os.path.join(sys.argv[2], 'judge.json')      # 시험용 출력 폴더
ALPHA = 0.05
YES, NO, UNK = '맞음', '틀림', '판정 못 함'
LINES = []


def say(*a):
    s = ' '.join(str(x) for x in a); LINES.append(s); print(s)


def load():
    R = {}
    for f in sorted(glob.glob(os.path.join(DATA, 'b_*_s*_v5?.json'))):
        m = re.match(r'b_(\w+?)_s(\d+)_v5([cy])\.json', os.path.basename(f))
        if not m: continue
        R[(m.group(1), int(m.group(2)), m.group(3))] = json.load(open(f))
    return R


def pairs(R, scn):
    seeds = sorted(s for (c, s, a) in R if c == scn and a == 'c' and (c, s, 'y') in R)
    return [(s, R[(scn, s, 'c')], R[(scn, s, 'y')]) for s in seeds]


def p_less(x, y):
    """짝 지은 한쪽 Wilcoxon: x < y 의 p. 차가 모두 0 이면 1"""
    d = np.asarray(x, float) - np.asarray(y, float)
    if d.size == 0 or np.all(d == 0): return 1.0
    return float(wilcoxon(d, alternative='less', zero_method='wilcox').pvalue)


def cmp_lower(ctrl, cand, name, better='lower'):
    """후보가 더 '좋은지'(better='lower': 작을수록 좋음). L: 좋고 유의, N: 평균이 좋지 않음(같거나 나쁨), U: 좋은 쪽이나 유의하지 않음"""
    c = np.asarray(ctrl, float); y = np.asarray(cand, float)
    if better == 'higher': c, y = -c, -y
    if c.size == 0: return dict(name=name, n=0, cls='U', note='짝 없음')
    if np.all(c == 0) and np.all(y == 0): return dict(name=name, n=int(c.size), ctrl_mean=0.0, cand_mean=0.0, mean_diff=0.0, p_one_sided=1.0, cand_better=0, cand_worse=0, cls='U', note='양쪽 모두 0: 견줄 사건 없음')
    p = p_less(y, c); md = float(np.mean(y - c)); nb = int((y < c).sum()); nw = int((y > c).sum())
    cls = 'N' if md >= 0 else ('L' if p < ALPHA else 'U')
    sg = -1 if better == 'higher' else 1
    return dict(name=name, n=int(c.size), ctrl_mean=float(sg * c.mean()), cand_mean=float(sg * y.mean()), mean_diff=float(sg * md), p_one_sided=p, cand_better=nb, cand_worse=nw, cls=cls)


def verdict_all(parts):
    cl = [p['cls'] for p in parts]
    if any(c == 'N' for c in cl): return NO
    if all(c == 'L' for c in cl): return YES
    return UNK


def boot(ctrl, cand, kind, margin, B=20000, seed=20261124):
    """비열등성. kind='rel_up' (클수록 나쁨: 시각), 'rel_down' (작을수록 나쁨: 거리), 'abs_deficit' (적을수록 나쁨: 닿은 수, 절대 단위)
    worse 쪽을 +로 둔 효과 e 와 90% 붓스트랩 구간. NI: 위 끝 < margin. W: 아래 끝 > 0 이고 e > margin. 나머지 U"""
    c = np.asarray(ctrl, float); y = np.asarray(cand, float); n = c.size
    if n == 0: return dict(n=0, cls='U')
    rng = np.random.default_rng(seed); idx = rng.integers(0, n, (B, n))

    def eff(cc, yy):
        if kind == 'rel_up': return (yy - cc).mean(-1) / np.maximum(cc.mean(-1), 1e-12)
        if kind == 'rel_down': return (cc - yy).mean(-1) / np.maximum(cc.mean(-1), 1e-12)
        return (cc - yy).mean(-1)
    e = float(eff(c, y)); eb = eff(c[idx], y[idx]); lo, hi = float(np.percentile(eb, 5)), float(np.percentile(eb, 95))
    cls = 'NI' if hi < margin else ('W' if (lo > 0 and e > margin) else 'U')
    return dict(n=int(n), ctrl_mean=float(c.mean()), cand_mean=float(y.mean()), effect_worse=e, ci90=[lo, hi], margin=margin, cls=cls)


def window_snaps(run, t_end_excl):
    return [s for s in run['snaps'] if 20 <= s['t'] <= 1600 and s['t'] < t_end_excl]


def vw_mean(snaps, key):
    """스냅샷과 몸을 부피 몫으로 가중한 평균. key='n_lumps1' 은 max(덩이 수, 1) (덩이가 없는 그물 몸을 '덩이 0개'로 이득 보지 않게)"""
    num = 0.0; den = 0.0
    for s in snaps:
        for b in s['bodies']:
            v = max(b['n_lumps'], 1) if key == 'n_lumps1' else b.get(key)
            if v is None: continue
            num += b['share'] * float(v); den += b['share']
    return num / den if den > 0 else float('nan')


def main():
    R = load(); J = {}
    say('# verify5 판정 출력'); say('실행 수:', len(R), ' 시나리오별:', {c: sum(1 for k in R if k[0] == c) for c in sorted(set(k[0] for k in R))})

    # ---------------- 주장 6: 건강 ----------------
    say('\n## 주장 6: 후보 실행의 건강')
    bad = []; rows = []
    for (c, s, a), r in sorted(R.items()):
        m = r['metrics']; Vtot = (m['V0'] or 0) + (m['Vinj'] or 0)
        ok_neg = (m['neg_end_cellsteps'] == 0) and (m['h_min_end_of_step'] >= 0)
        ok_mass = m['mass_err_max'] < 1e-10
        ok_crumb = abs(m['V_crumb']) < 1e-3 * Vtot
        ok_end = (m['stop'] == '') and (m['steps_done'] == r['steps_expected']) and abs(m['t_end'] - r['T']) < 1e-6
        row = dict(scn=c, seed=s, arm=a, neg_end_cellsteps=m['neg_end_cellsteps'], h_min_end=m['h_min_end_of_step'], mass_err=m['mass_err_max'],
                   V_crumb_rel=abs(m['V_crumb']) / max(Vtot, 1e-12), crumb_cells=m['crumb_cells'], stop=m['stop'], steps=m['steps_done'], ok=bool(ok_neg and ok_mass and ok_crumb and ok_end),
                   fails=[k for k, v in (('neg', ok_neg), ('mass', ok_mass), ('crumb', ok_crumb), ('end', ok_end)) if not v])
        rows.append(row)
        if a == 'y' and not row['ok']: bad.append(row)
    ny = sum(1 for r_ in rows if r_['arm'] == 'y'); nc = sum(1 for r_ in rows if r_['arm'] == 'c')
    v6 = (NO if bad else YES) if ny else UNK
    for arm, nm in (('y', '후보'), ('c', '대조')):
        rr = [r_ for r_ in rows if r_['arm'] == arm]
        if rr:
            say(f'{nm} {len(rr)}개: 끝 음수 셀-스텝 최대 {max(r_["neg_end_cellsteps"] for r_ in rr)}, 끝 h 최소 {min(r_["h_min_end"] for r_ in rr):.3g}, 부피 오차 최대 {max(r_["mass_err"] for r_ in rr):.2e}, '
                f'|버린 부피|/몸 부피 최대 {max(r_["V_crumb_rel"] for r_ in rr):.2e}, 끝까지 돈 것 {sum(1 for r_ in rr if "end" not in r_["fails"])}/{len(rr)}, 모두 통과 {sum(r_["ok"] for r_ in rr)}/{len(rr)}')
    for b in bad: say('  후보 실패:', b)
    say('판정 6:', v6); J['claim6'] = dict(verdict=v6, rows=rows, cand_fail=bad)

    # ---------------- 주장 1: 부스러기 ----------------
    say('\n## 주장 1: 부스러기 (몸 부피 5% 미만의 떨어진 조각, t >= 100 스냅샷과 끝 상태)')
    c1 = {}
    for arm in ('y', 'c'):
        st = []
        for (c, s, a), r in sorted(R.items()):
            if a != arm: continue
            ss = [x for x in r['snaps'] if x['t'] >= 100]
            st.append(dict(scn=c, seed=s, debris_snaps=sum(1 for x in ss if x['n_debris'] > 0), debris_piece_snaps=sum(x['n_debris'] for x in ss),
                           debris_new=sum(x['n_debris_new'] for x in ss), final_debris=r['final']['n_debris'], crumb_cells=r['metrics']['crumb_cells'], n_snaps=len(ss)))
        c1[arm] = st
    y = c1['y']; c = c1['c']
    y_any = sum(1 for x in y if x['debris_piece_snaps'] > 0 or x['final_debris'] > 0)
    c_runs_with = sum(1 for x in c if x['debris_piece_snaps'] > 0)
    c_mean = float(np.mean([x['debris_piece_snaps'] for x in c])) if c else float('nan')
    say(f'후보 {len(y)}개: 부스러기가 보인 실행 {y_any}, 부스러기 조각-스냅샷 합 {sum(x["debris_piece_snaps"] for x in y)}, 새 부스러기 합 {sum(x["debris_new"] for x in y)}, 끝 부스러기 합 {sum(x["final_debris"] for x in y)}, 외톨이 셀 말림(crumb_cells, 전 구간) 합 {sum(x["crumb_cells"] for x in y)}')
    say(f'대조 {len(c)}개: 부스러기가 보인 실행 {c_runs_with}, 조각-스냅샷 평균 {c_mean:.2f}/실행, 새 부스러기 합 {sum(x["debris_new"] for x in c)}, 끝 부스러기 합 {sum(x["final_debris"] for x in c)}, crumb_cells 합 {sum(x["crumb_cells"] for x in c)}')
    for scn in sorted(set(x['scn'] for x in c)):
        cc = [x for x in c if x['scn'] == scn]; yy = [x for x in y if x['scn'] == scn]
        say(f'  {scn}: 대조 조각-스냅샷 평균 {np.mean([x["debris_piece_snaps"] for x in cc]):.2f} (실행 {sum(1 for x in cc if x["debris_piece_snaps"] > 0)}/{len(cc)}), 끝 {sum(x["final_debris"] for x in cc)}; '
            f'후보 평균 {np.mean([x["debris_piece_snaps"] for x in yy]) if yy else float("nan"):.2f}, 끝 {sum(x["final_debris"] for x in yy)}')
    partA = (y_any == 0) if y else None
    partB = (c_mean >= 5 and c_runs_with >= 0.5 * len(c)) if c else None
    v1 = UNK if (partA is None or partB is None) else (YES if (partA and partB) else NO)
    say('후보 부분(만들지도 남기지도 않음):', partA, ' 대조 부분(많이 만듦: 평균 >= 5 조각-스냅샷이고 실행 절반 이상):', partB)
    say('판정 1:', v1); J['claim1'] = dict(verdict=v1, partA=partA, partB=partB, cand=y, ctrl=c)

    # ---------------- 갇힘 시각 (long) ----------------
    LP = pairs(R, 'long')
    say('\n## long: 갇힘 시각 (둘레 새 땅 몫 < 0.05 이고 그 뒤 계속 < 0.10), 모델의 t_scl, 점액 어림이 놓친 몫')
    for s, rc, ry in LP:
        say(f'  s{s}: 대조 T_trap={rc["T_trap"]}, 후보 T_trap={ry["T_trap"]}, 후보 t_scl={ry["metrics"]["t_scl"]}, 놓친 점액 몫 c/y={rc["slime_missed"]:.3f}/{ry["slime_missed"]:.3f}, '
            f'끝 판 점액 몫 c/y={rc["board_slime_end"]:.3f}/{ry["board_slime_end"]:.3f}')

    def wend(rc, ry):
        tt = [1e9]
        for x in (rc['T_trap'], ry['T_trap'], ry['metrics']['t_scl']):
            if x is not None: tt.append(float(x))
        return min(tt)

    # ---------------- 주장 2: 덩이 갈림 ----------------
    say('\n## 주장 2: 옮겨 다니는 동안 (long, 20 <= t <= 1600, 짝의 갇힘·후보 균핵 상태 이전) 한 몸 안 굵은 덩이 둘 이상 / 아령')
    rows2 = []; X = {k: ([], []) for k in ('multi', 'dumb', 'multi_0.4', 'dumb_0.4', 'multi_0.6', 'dumb_0.6', 'multi_t100', 'dumb_t100')}
    for s, rc, ry in LP:
        we = wend(rc, ry); sc = window_snaps(rc, we); sy = window_snaps(ry, we)
        if len(sc) < 20 or len(sy) < 20:
            rows2.append(dict(seed=s, used=False, n=len(sc), window_end=we)); continue
        f = lambda ss, key: float(np.mean([x[key] for x in ss]))
        fs = lambda ss, key: float(np.mean([x['sens'][key] for x in ss]))
        row = dict(seed=s, used=True, n=len(sc), window_end=we, c_multi=f(sc, 'any_multi'), y_multi=f(sy, 'any_multi'), c_dumb=f(sc, 'any_dumb'), y_dumb=f(sy, 'any_dumb'))
        rows2.append(row)
        X['multi'][0].append(row['c_multi']); X['multi'][1].append(row['y_multi']); X['dumb'][0].append(row['c_dumb']); X['dumb'][1].append(row['y_dumb'])
        for tr in ('0.4', '0.6'):
            X[f'multi_{tr}'][0].append(fs(sc, f'multi_{tr}')); X[f'multi_{tr}'][1].append(fs(sy, f'multi_{tr}'))
            X[f'dumb_{tr}'][0].append(fs(sc, f'dumb_{tr}')); X[f'dumb_{tr}'][1].append(fs(sy, f'dumb_{tr}'))
        sc1 = [x for x in sc if x['t'] >= 100]; sy1 = [x for x in sy if x['t'] >= 100]
        X['multi_t100'][0].append(f(sc1, 'any_multi')); X['multi_t100'][1].append(f(sy1, 'any_multi'))
        X['dumb_t100'][0].append(f(sc1, 'any_dumb')); X['dumb_t100'][1].append(f(sy1, 'any_dumb'))
    for r_ in rows2:
        say('  s%d' % r_['seed'], '쓰임' if r_['used'] else '안 쓰임', '창 끝 %.0f' % min(r_['window_end'], 1600), ('스냅샷 %d, 여럿 c→y %.3f→%.3f, 아령 c→y %.3f→%.3f' % (r_['n'], r_['c_multi'], r_['y_multi'], r_['c_dumb'], r_['y_dumb'])) if r_['used'] else '')
    p2 = [cmp_lower(X['multi'][0], X['multi'][1], '덩이 둘 이상인 스냅샷 몫'), cmp_lower(X['dumb'][0], X['dumb'][1], '아령인 스냅샷 몫')]
    for p in p2: say('  ', p)
    sens2 = {k: cmp_lower(X[k][0], X[k][1], k) for k in X if k not in ('multi', 'dumb')}
    for k, p in sens2.items(): say('   (민감도)', k, p['cls'], 'c→y %.3f→%.3f p=%.4f' % (p.get('ctrl_mean', np.nan), p.get('cand_mean', np.nan), p.get('p_one_sided', np.nan)) if p['n'] else '')
    nused = sum(1 for r_ in rows2 if r_['used'])
    v2 = verdict_all(p2) if nused >= 4 else UNK
    say('판정 2:', v2, f'(쓰인 짝 {nused})'); J['claim2'] = dict(verdict=v2, rows=rows2, tests=p2, sens=sens2)

    # ---------------- 주장 3: 죽은 구조 ----------------
    say('\n## 주장 3: 옮겨 다니는 동안 얇은 막(몸 넓이 몫), 흐름 없는 실(몸 넓이 몫), 흐름 없는 가지 끝(개수)')
    keys3 = [('film', 'share'), ('deadthread', 'share'), ('deadtips', 'count')]
    sens_keys = ['film_0.25', 'film_0.5', 'deadthread_0.02', 'deadthread_0.1', 'deadtips_0.02', 'deadtips_0.1']
    Y3 = {k: ([], []) for k, _ in keys3}; S3 = {k: ([], []) for k in sens_keys + ['film_abs', 'deadthread_abs', 'thread_share', 'tips_all']}
    rows3 = []
    for s, rc, ry in LP:
        we = wend(rc, ry); sc = window_snaps(rc, we); sy = window_snaps(ry, we)
        if len(sc) < 20 or len(sy) < 20: continue
        def mv(ss, key, kind):
            if kind == 'share': return float(np.mean([x['dead'][key] / max(x['dead']['wet'], 1) for x in ss]))
            return float(np.mean([x['dead'][key] for x in ss]))
        row = dict(seed=s)
        for k, kind in keys3:
            a, b = mv(sc, k, kind), mv(sy, k, kind); Y3[k][0].append(a); Y3[k][1].append(b); row[k] = (a, b)
        for k in sens_keys:
            kind = 'count' if k.startswith('deadtips') else 'share'; S3[k][0].append(mv(sc, k, kind)); S3[k][1].append(mv(sy, k, kind))
        S3['film_abs'][0].append(mv(sc, 'film', 'count')); S3['film_abs'][1].append(mv(sy, 'film', 'count'))
        S3['deadthread_abs'][0].append(mv(sc, 'deadthread', 'count')); S3['deadthread_abs'][1].append(mv(sy, 'deadthread', 'count'))
        S3['thread_share'][0].append(mv(sc, 'thread', 'share')); S3['thread_share'][1].append(mv(sy, 'thread', 'share'))
        S3['tips_all'][0].append(mv(sc, 'tips_all', 'count')); S3['tips_all'][1].append(mv(sy, 'tips_all', 'count'))
        rows3.append(row)
        say('  s%d' % s, ', '.join('%s c→y %.4g→%.4g' % (k, row[k][0], row[k][1]) for k, _ in keys3))
    p3 = [cmp_lower(Y3[k][0], Y3[k][1], k) for k, _ in keys3]
    for p in p3: say('  ', p)
    sens3 = {k: cmp_lower(S3[k][0], S3[k][1], k) for k in S3}
    for k, p in sens3.items(): say('   (민감도/참고)', k, p['cls'], 'c→y %.4g→%.4g p=%.4f' % (p.get('ctrl_mean', np.nan), p.get('cand_mean', np.nan), p.get('p_one_sided', np.nan)) if p['n'] else '')
    v3 = verdict_all(p3) if len(rows3) >= 4 else UNK
    say('판정 3:', v3, f'(쓰인 짝 {len(rows3)})'); J['claim3'] = dict(verdict=v3, rows=rows3, tests=p3, sens=sens3)

    # ---------------- 주장 4: 균핵 ----------------
    say('\n## 주장 4: 갇히면 균핵 (long)')
    LY = [(s, ry) for s, rc, ry in LP]; LC = [(s, rc) for s, rc, ry in LP]
    # 4a, 4b
    qual = [(s, r) for s, r in LY if r['T_trap'] is not None and r['T_trap'] <= 1800]
    bods = [(s, b) for s, r in qual for b in r['final']['bodies']]
    say(f'4a/4b: T_trap <= 1800 인 후보 실행 {len(qual)}개, 끝 상태의 몸 {len(bods)}개')
    for s, b in bods:
        say(f'   s{s} 몸 부피몫 {b["share"]:.3f} 덩이 {b["n_lumps"]} 덩이몫 {b["lump_frac"]:.2f} 축비 {b["ar"]} 볼록채움 {b["solidity"]} κ넓이 {b["kappa_area"]} κ부피 {b["kappa_vol"]} 꼬리 {b["tail"]:.3f} 넓이 {b["area"]} hv {b["hv"]:.2f} → 균핵 {b["scl"]}')
    def frac_rule(k, n, hi=0.9, lo=0.7):
        if n == 0: return UNK
        f = k / n
        return YES if f >= hi else (NO if f < lo else UNK)
    k4a = sum(1 for _, b in bods if b['scl']); k4b = sum(1 for _, b in bods if b['tail'] <= 0.05)
    v4a = frac_rule(k4a, len(bods)) if len(qual) >= 4 else UNK
    v4b = frac_rule(k4b, len(bods)) if len(qual) >= 4 else UNK
    say(f'4a 균핵인 몸 {k4a}/{len(bods)} → {v4a};  4b 꼬리 <= 5% 인 몸 {k4b}/{len(bods)} → {v4b}')
    # 대조 참고
    qc = [(s, r) for s, r in LC if r['T_trap'] is not None and r['T_trap'] <= 1800]; bc = [b for s, r in qc for b in r['final']['bodies']]
    say(f'   (참고) 대조: T_trap <= 1800 실행 {len(qc)}개, 끝의 몸 {len(bc)}개 중 균핵 {sum(b["scl"] for b in bc)}, 꼬리 <= 5% {sum(b["tail"] <= 0.05 for b in bc)}')
    # 4c
    rows4c = []
    for s, r in LY:
        ts = [x for x in (r['T_trap'], r['metrics']['t_scl']) if x is not None]
        if not ts: rows4c.append(dict(seed=s, qual=False, why='갇힘도 t_scl 도 없음')); continue
        t0 = min(ts); sn = [x for x in r['snaps'] if x['t'] >= t0]
        kf = next((i for i, x in enumerate(sn) if x['all_scl']), None)
        if kf is None: rows4c.append(dict(seed=s, qual=False, t0=t0, why='균핵이 맺히지 않음')); continue
        after = sn[kf + 1:]
        if len(after) < 3: rows4c.append(dict(seed=s, qual=False, t0=t0, t_form=sn[kf]['t'], why='맺힌 뒤 스냅샷 < 3')); continue
        A0 = sn[kf]['area']; run2 = 0; unr = False; why = []
        for x in after:
            run2 = run2 + 1 if not x['all_scl'] else 0
            if run2 >= 2: unr = True; why.append(f'균핵 아님 2연속 t={x["t"]}')
            if x['area'] > 1.5 * A0: unr = True; why.append(f'넓이 {x["area"]}>{1.5 * A0:.0f} t={x["t"]}')
        ml = 0
        for x in after:
            ml = ml + 1 if x['any_multi'] else 0
            if ml >= 2: unr = True; why.append(f'덩이 둘 이상 2연속 t={x["t"]}')
        pers = float(np.mean([x['all_scl'] for x in after]))
        rows4c.append(dict(seed=s, qual=True, t0=t0, t_form=sn[kf]['t'], n_after=len(after), persist=pers, unravel=unr, why=sorted(set(why))[:4]))
    for r_ in rows4c: say('   4c', r_)
    q4c = [r_ for r_ in rows4c if r_['qual']]
    v4c = UNK if len(q4c) < 3 else (NO if any(r_['unravel'] for r_ in q4c) else YES)
    say(f'4c 맺힌 실행 {len(q4c)}개, 풀린 실행 {sum(r_["unravel"] for r_ in q4c)} → {v4c}')
    # 4d
    cases = [(s, r['split']) for s, r in LY if r['split'] and r['split']['n_big'] >= 2]
    nb4d = sum(len(sp['bodies']) for _, sp in cases); ok4d = sum(1 for _, sp in cases for b in sp['bodies'] if b['end_scl'] and not b['merged'])
    for s, sp in cases: say(f'   4d s{s}:', sp)
    if nb4d == 0: v4d = UNK
    else:
        f4d = ok4d / nb4d; v4d = YES if f4d >= 0.8 else (NO if f4d < 0.5 else UNK)
    say(f'4d 갇힐 때 10% 넘는 몸이 둘 이상인 실행 {len(cases)}개, 그 몸 {nb4d}개 중 끝에 각자 균핵 {ok4d} → {v4d}')
    # 4e
    say('4e: 짝 모두 T_trap <= 1900, 창 1900 <= t <= 2000, 몸·스냅샷 부피 가중 평균')
    E = {k: ([], []) for k in ('n_lumps1', 'ar', 'kappa_area', 'solidity', 'kappa_vol', 'tail', 'n_bodies')}; rows4e = []
    for s, rc, ry in LP:
        if rc['T_trap'] is None or ry['T_trap'] is None or rc['T_trap'] > 1900 or ry['T_trap'] > 1900: continue
        wc = [x for x in rc['snaps'] if 1900 <= x['t'] <= 2000]; wy = [x for x in ry['snaps'] if 1900 <= x['t'] <= 2000]
        if not wc or not wy: continue
        row = dict(seed=s)
        for k in ('n_lumps1', 'ar', 'kappa_area', 'solidity', 'kappa_vol', 'tail'):
            a, b = vw_mean(wc, k), vw_mean(wy, k); E[k][0].append(a); E[k][1].append(b); row[k] = (round(a, 4), round(b, 4))
        a = float(np.mean([len(x['bodies']) for x in wc])); b = float(np.mean([len(x['bodies']) for x in wy])); E['n_bodies'][0].append(a); E['n_bodies'][1].append(b); row['n_bodies'] = (a, b)
        rows4e.append(row); say('   s%d' % s, row)
    p4e = [cmp_lower(E['n_lumps1'][0], E['n_lumps1'][1], '몸마다 덩이 수 max(n,1) (적을수록)'), cmp_lower(E['ar'][0], E['ar'][1], '축비 (둥글수록)', 'higher'),
           cmp_lower(E['kappa_area'][0], E['kappa_area'][1], 'κ 넓이 (촘촘할수록)', 'higher')]
    for p in p4e: say('  ', p)
    sens4e = [cmp_lower(E['solidity'][0], E['solidity'][1], '볼록채움 (참고)', 'higher'), cmp_lower(E['kappa_vol'][0], E['kappa_vol'][1], 'κ 부피 (참고)', 'higher'),
              cmp_lower(E['tail'][0], E['tail'][1], '꼬리 몫 (참고)')]
    for p in sens4e: say('   (참고)', p)
    v4e = verdict_all(p4e) if len(rows4e) >= 4 else UNK
    say(f'4e 짝 {len(rows4e)}개 → {v4e}')
    subs = dict(a=v4a, b=v4b, c=v4c, d=v4d, e=v4e)
    if any(v == NO for v in subs.values()): v4 = NO
    elif all(subs[k] == YES for k in 'abce') and subs['d'] != NO: v4 = YES
    else: v4 = UNK
    say('판정 4:', v4, subs)
    J['claim4'] = dict(verdict=v4, subs=subs, bodies_4ab=[dict(seed=s, **b) for s, b in bods], rows4c=rows4c, cases4d=[dict(seed=s, **sp) for s, sp in cases], rows4e=rows4e, tests4e=p4e, sens4e=sens4e)

    # ---------------- 주장 5: 먹이 찾기와 이주 ----------------
    say('\n## 주장 5: 먹이 찾기와 이주가 나빠지지 않는다 (비열등: 90% 붓스트랩 구간의 나쁜 쪽 끝 < 여유)')
    p5 = []; rows5 = {}
    for scn in ('food4', 'food3', 'asym3'):
        PP = pairs(R, scn)
        if not PP: p5.append(dict(name=scn, cls='U', n=0)); continue
        T = PP[0][1]['T']
        def cnt(r): return sum(1 for v in r['metrics']['t_touch'] if v is not None)
        def mt(r): return float(np.mean([T if v is None else float(v) for v in r['metrics']['t_touch']]))
        cc = [cnt(rc) for _, rc, _ in PP]; yy = [cnt(ry) for _, _, ry in PP]
        tc = [mt(rc) for _, rc, _ in PP]; ty = [mt(ry) for _, _, ry in PP]
        b1 = boot(cc, yy, 'abs_deficit', 0.25); b1['name'] = f'{scn} 닿은 먹이 수'
        b2 = boot(tc, ty, 'rel_up', 0.15); b2['name'] = f'{scn} 닿는 시각 평균 (못 닿으면 T)'
        p5 += [b1, b2]
        rows5[scn] = [dict(seed=s, c_touch=rc['metrics']['t_touch'], y_touch=ry['metrics']['t_touch']) for s, rc, ry in PP]
        for s, rc, ry in PP: say(f'   {scn} s{s}: 대조 {rc["metrics"]["t_touch"]} / 후보 {ry["metrics"]["t_touch"]}')
        # 참고: 첫 닿음, 마지막 닿음
        fc = [min([v for v in rc['metrics']['t_touch'] if v is not None], default=T) for _, rc, _ in PP]; fy = [min([v for v in ry['metrics']['t_touch'] if v is not None], default=T) for _, _, ry in PP]
        say(f'   (참고) {scn} 첫 닿음 평균 c→y {np.mean(fc):.1f}→{np.mean(fy):.1f}')
    # 이주: mig 짝 + long 의 t <= 400 부분
    def at(traj, t):
        tr = np.asarray(traj, float); i = int(np.argmin(np.abs(tr[:, 0] - t))); return tr[i]
    def mig_stats(r):
        P0 = r['N'] / 2 - 0.5; tr = np.asarray(r['metrics']['traj'], float); tr = tr[tr[:, 0] <= 400 + 1e-6]
        e = at(tr, 400); disp = float(np.hypot(e[1] - P0, e[2] - P0))
        tt = r['metrics']['t_touch'][0]; tt = 400.0 if (tt is None or tt > 400) else float(tt)
        d = np.hypot(tr[:, 1] - P0, tr[:, 2] - P0); k = int(np.argmax(d >= 35)) if (d >= 35).any() else len(tr) - 1
        a_food = np.radians(r['foods_param'][0][0])
        ang = np.degrees(np.angle(np.exp(1j * (np.arctan2(tr[k, 2] - P0, tr[k, 1] - P0) - a_food))))
        proj = float((e[1] - P0) * np.cos(a_food) + (e[2] - P0) * np.sin(a_food))
        return dict(disp=disp, touch=tt, ang=float(ang), t_ang=float(tr[k, 0]), proj=proj)
    MP = [(s, rc, ry, 'mig') for s, rc, ry in pairs(R, 'mig')] + [(s, rc, ry, 'long') for s, rc, ry in LP]
    mc = [mig_stats(rc) for _, rc, _, _ in MP]; my = [mig_stats(ry) for _, _, ry, _ in MP]
    for (s, _, _, src), a, b in zip(MP, mc, my):
        say(f'   이주 {src} s{s}: 거리 c/y {a["disp"]:.1f}/{b["disp"]:.1f}, 닿음 {a["touch"]:.0f}/{b["touch"]:.0f}, 방향 어긋남(도) {a["ang"]:+.1f}/{b["ang"]:+.1f} (t={a["t_ang"]:.0f}/{b["t_ang"]:.0f})')
    b3 = boot([x['disp'] for x in mc], [x['disp'] for x in my], 'rel_down', 0.15); b3['name'] = '이주 거리 (t=400, mig+long 앞부분)'
    b4 = boot([x['touch'] for x in mc], [x['touch'] for x in my], 'rel_up', 0.15); b4['name'] = '유인원에 닿는 시각 (못 닿으면 400, mig+long 앞부분)'
    p5 += [b3, b4]
    only_mig = [(a, b) for (s, _, _, src), a, b in zip(MP, mc, my) if src == 'mig']
    sens5 = [boot([a['disp'] for a, b in only_mig], [b['disp'] for a, b in only_mig], 'rel_down', 0.15), boot([a['touch'] for a, b in only_mig], [b['touch'] for a, b in only_mig], 'rel_up', 0.15)]
    sens5[0]['name'] = '이주 거리 (mig 만)'; sens5[1]['name'] = '닿는 시각 (mig 만)'
    for p in p5: say('  ', p)
    for p in sens5: say('   (참고)', p)
    angc = np.array([x['ang'] for x in mc]); angy = np.array([x['ang'] for x in my])
    dirs = dict(n=int(angc.size), ctrl_mean_signed=float(angc.mean()), cand_mean_signed=float(angy.mean()), ctrl_mean_abs=float(np.abs(angc).mean()), cand_mean_abs=float(np.abs(angy).mean()),
                ctrl_sd=float(angc.std(ddof=1)) if angc.size > 1 else None, cand_sd=float(angy.std(ddof=1)) if angy.size > 1 else None,
                paired_diff_signed=float((angy - angc).mean()), cand_pos=int((angy > 0).sum()), ctrl_pos=int((angc > 0).sum()),
                p_abs_cand_gt_ctrl=p_less(np.abs(angc), np.abs(angy)), proj_c=float(np.mean([x['proj'] for x in mc])), proj_y=float(np.mean([x['proj'] for x in my])))
    say('   이주 방향 (유인원 방향에서 어긋난 각, + 는 각이 커지는 쪽(배열 좌표에서 x 축에서 y 축 쪽); 중심이 출발점에서 35셀 벗어난 때):', dirs)
    cls5 = [p['cls'] for p in p5]
    v5 = NO if 'W' in cls5 else (YES if all(c_ == 'NI' for c_ in cls5) else UNK)
    say('판정 5:', v5, [(p['name'], p['cls']) for p in p5])
    J['claim5'] = dict(verdict=v5, tests=p5, sens=sens5, direction=dirs, rows=rows5, mig=[dict(seed=s, src=src, c=a, y=b) for (s, _, _, src), a, b in zip(MP, mc, my)])

    say('\n## 요약'); V = {k: J[k]['verdict'] for k in ('claim1', 'claim2', 'claim3', 'claim4', 'claim5', 'claim6')}
    for k, v in V.items(): say(f'  {k}: {v}')
    J['summary'] = V
    os.makedirs(os.path.dirname(OUT_TXT), exist_ok=True)
    open(OUT_TXT, 'w').write('\n'.join(LINES) + '\n')
    json.dump(J, open(OUT_JSON, 'w'), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    main()
