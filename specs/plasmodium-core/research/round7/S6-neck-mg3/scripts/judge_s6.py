#!/usr/bin/env python3
"""[7차 S6] 3사이클 결승 시험 판정. 기준은 ../CRITERIA.md (실행 전에 커밋).

usage: judge_s6.py CAND [CAND ...] [--ctrl s6c] [--json FILE]
먼저 bmet.py 로 ref/runs/b_*_s{111..120}_{ctrl,CAND} 를 ../summaries 에 채점해 둔다 (없으면 이 스크립트가 만든다).
"""
import json, os, sys, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'stage0'))
REF = os.path.join(STAGE0, 'ref', 'runs'); SUM = os.path.join(HERE, '..', 'summaries'); MET = os.path.join(STAGE0, 'metrics')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S4-fan2', 'scripts')); from judge_s4 import long_stats
SEEDS = dict(long=range(111, 121), mig=range(111, 115), food3=range(111, 115), asym3=(111, 112), food4=range(111, 117))


def bm(scn, s, tag):
    f = os.path.join(SUM, f'numpy_b_{scn}_s{s}_{tag}.json'); rd = os.path.join(REF, f'b_{scn}_s{s}_{tag}')
    if not os.path.exists(f) and os.path.exists(os.path.join(rd, 'metrics.json')):
        subprocess.run([sys.executable, os.path.join(MET, 'bmet.py'), rd, '--out', SUM], capture_output=True)
    return json.load(open(f)) if os.path.exists(f) else None


def verdict(conf, refu):
    return '확인' if conf else ('반박' if refu else '판정 못 함')


def judge(C, K):
    R = dict(cand=K, ctrl=C, runs={}, G={})
    print(f'\n===== 후보 {K} (대조 {C}) =====')
    # ---- long: G1 갈라진 시간, G2 몸 밖 최대
    P = []
    for s in SEEDS['long']:
        rc, rk = os.path.join(REF, f'b_long_s{s}_{C}'), os.path.join(REF, f'b_long_s{s}_{K}')
        bc, bk = bm('long', s, C), bm('long', s, K)
        if not (bc and bk): print(f'빠짐: long s{s}'); continue
        sf = os.path.join(SUM, f'long_stats_s{s}_{{}}.json')
        def ls(rd, tag):
            f = sf.format(tag)
            if not os.path.exists(f): json.dump(long_stats(rd), open(f, 'w'))
            return json.load(open(f))
        c, k = ls(rc, C), ls(rk, K); c['out_max'] = bc['out_frac']; k['out_max'] = bk['out_frac']; c['area_end'] = bc['area_end']; k['area_end'] = bk['area_end']
        P.append((s, c, k)); R['runs'][f'long_s{s}'] = dict(ctrl=c, cand=k)
        print(f"long s{s}: 갈라진 시간 {c['split_frac']:.2f} → {k['split_frac']:.2f} | 몸 밖 최대 {c['out_max']:.3f} → {k['out_max']:.3f} | 두 부채 최장 {c['two_longest']:.0f} → {k['two_longest']:.0f} | 끝 넓이 {c['area_end']} → {k['area_end']}")
    if len(P) == len(SEEDS['long']):
        cm = float(np.mean([c['split_frac'] for _, c, _ in P])); km = float(np.mean([k['split_frac'] for _, _, k in P]))
        smaller = sum(k['split_frac'] < c['split_frac'] for _, c, k in P); larger = sum(k['split_frac'] > c['split_frac'] for _, c, k in P)
        R['G']['G1'] = dict(ctrl_mean=cm, cand_mean=km, smaller=smaller, larger=larger, verdict=verdict(km <= 0.5 * cm and smaller >= 7, km >= cm or larger >= 6))
        n10 = sum(k['out_max'] < 0.10 for _, _, k in P)
        R['G']['G2'] = dict(cand_lt010=n10, ctrl_lt010=sum(c['out_max'] < 0.10 for _, c, _ in P), verdict=verdict(n10 >= 7, n10 <= 3))
        ac = float(np.mean([c['area_end'] for _, c, _ in P])); ak = float(np.mean([k['area_end'] for _, _, k in P]))
        R['G']['G7'] = dict(ctrl_area=ac, cand_area=ak, ratio=ak / ac, verdict=verdict(ak <= 1.2 * ac, ak > 1.5 * ac))
    else:
        R['G']['G1'] = R['G']['G2'] = R['G']['G7'] = dict(verdict='실행이 모자람')
    # ---- mig: G3
    keys = (('t_touch', +1), ('disp300', -1), ('veinT', -1), ('vein4', -1), ('gross_net', -1))
    val = lambda o, kk: ((o.get(kk) or [None])[0] if isinstance(o.get(kk), list) else o.get(kk))
    M = [(s, bm('mig', s, C), bm('mig', s, K)) for s in SEEDS['mig']]
    if all(c and k for _, c, k in M):
        g = {}; conf = True; refu = False
        for kk, bad in keys:
            cv = [val(c, kk) for _, c, _ in M]; kv = [val(k, kk) for _, _, k in M]
            if any(x is None for x in cv + kv): g[kk] = dict(note='값 없음'); conf = False; continue
            w = max(cv) - min(cv); lo, hi = min(cv) - w / 2, max(cv) + w / 2; inb = sum(lo <= x <= hi for x in kv)
            worse = (np.mean(kv) > np.mean(cv)) if bad > 0 else (np.mean(kv) < np.mean(cv))
            g[kk] = dict(ctrl=cv, cand=kv, band=[lo, hi], inside=inb); conf &= inb >= 3; refu |= (inb == 0 and worse)
            print(f"mig {kk:9s} 대조 {['%.3g' % x for x in cv]} 후보 {['%.3g' % x for x in kv]} 띠 [{lo:.3g}, {hi:.3g}] 안 {inb}/4")
        g['verdict'] = verdict(conf, refu); R['G']['G3'] = g
    else:
        R['G']['G3'] = dict(verdict='실행이 모자람')
    # ---- food3 + asym3: G4
    F = [(scn, s, bm(scn, s, C), bm(scn, s, K)) for scn in ('food3', 'asym3') for s in SEEDS[scn]]
    if all(c and k for *_, c, k in F):
        pc = sum(bool(c['pass']) for *_, c, _ in F); pk = sum(bool(k['pass']) for *_, _, k in F)
        late = [(scn, s, i, a, b) for scn, s, c, k in F for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if a is not None and (b is None or b > a + 50)]
        for scn, s, c, k in F:
            print(f"{scn} s{s}: 통과 {c['pass']} → {k['pass']}, 굵은 쌍 {c['thick']} → {k['thick']}, 닿음 {c['t_touch']} → {k['t_touch']}")
        R['G']['G4'] = dict(ctrl_pass=pc, cand_pass=pk, late=late, verdict=verdict(pk >= pc and len(late) <= 1, pk <= pc - 2 or len(late) >= 3))
    else:
        R['G']['G4'] = dict(verdict='실행이 모자람')
    # ---- food4: G5
    F4 = [(s, bm('food4', s, C), bm('food4', s, K)) for s in SEEDS['food4']]
    if all(c and k for _, c, k in F4):
        rc = sum(bool(c['reached']) for _, c, _ in F4); rk = sum(bool(k['reached']) for _, _, k in F4)
        oc = float(np.mean([c['out_frac'] for _, c, _ in F4])); ok = float(np.mean([k['out_frac'] for _, _, k in F4]))
        for s, c, k in F4:
            print(f"food4 s{s}: 모두 닿음 {c['reached']} → {k['reached']}, 닿음 {c['t_touch']} → {k['t_touch']}, 몸 밖 최대 {c['out_frac']} → {k['out_frac']}")
        R['G']['G5'] = dict(ctrl_reached=rc, cand_reached=rk, ctrl_out=oc, cand_out=ok, verdict=verdict(rk >= rc - 1 and ok <= oc, rk <= rc - 2))
    else:
        R['G']['G5'] = dict(verdict='실행이 모자람')
    # ---- G6: 부피 장부와 스텝 끝 음수
    allk = [bm(scn, s, K) for scn, ss in SEEDS.items() for s in ss]; allc = [bm(scn, s, C) for scn, ss in SEEDS.items() for s in ss]
    if all(allk) and all(allc):
        nk = sum(1 for o in allk if o['neg_end']); nc_ = sum(1 for o in allc if o['neg_end']); mk = max(o['mass_err'] for o in allk)
        print(f"[{K}] 실행 {len(allk)} · 스텝 끝 음수 있는 실행 {nk} (대조 {nc_}) · 스텝 안 최소 {min(o['h_min_in'] for o in allk):.3f} · 부피 오차 최대 {mk:.1e}")
        R['G']['G6'] = dict(cand_neg_runs=nk, ctrl_neg_runs=nc_, mass_err=mk, verdict=verdict(nk <= nc_ and mk < 1e-10, nk > nc_ + 1 or mk >= 1e-10))
    else:
        R['G']['G6'] = dict(verdict='실행이 모자람')
    for g in sorted(R['G']):
        v = R['G'][g]; print(g, v.get('verdict'), {kk: v[kk] for kk in v if kk not in ('verdict',) and not isinstance(v[kk], (dict, list))})
    adv = all(R['G'].get(g, {}).get('verdict') == '확인' for g in ('G1', 'G2')) and all(R['G'].get(g, {}).get('verdict') not in ('반박', '실행이 모자람') for g in ('G3', 'G4', 'G5', 'G6', 'G7'))
    R['advance'] = adv; print('다음 단계(독립 검증)로:', '간다' if adv else '가지 않는다')
    return R


if __name__ == '__main__':
    a = sys.argv[1:]; C = a[a.index('--ctrl') + 1] if '--ctrl' in a else 's6c'; out = a[a.index('--json') + 1] if '--json' in a else None
    cands = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--ctrl', '--json'))]
    res = [judge(C, K) for K in cands]
    if out: json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False, default=float)
