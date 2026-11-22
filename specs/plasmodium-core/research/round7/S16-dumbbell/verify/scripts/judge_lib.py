#!/usr/bin/env python3
"""judge.py 와 같은 통계 (부호 뒤집기, 부트스트랩) 와 먼 먹이 시험의 요약. extra.py 가 쓴다."""
import itertools, json, os
import numpy as np
import vlib as V

OK, BAD, UNK = '맞음', '틀림', '판정 못 함'


def signflip(d):
    d = np.asarray(d, float); n = d.size
    if n == 0: return 1.0, 1.0
    S = np.array(list(itertools.product((-1, 1), repeat=n)))
    m = (S * np.abs(d)).mean(1); o = d.mean(); e = 1e-12
    return float((m <= o + e).mean()), float((m >= o - e).mean())


def boot(d):
    d = np.asarray(d, float); rng = np.random.default_rng(0); idx = rng.integers(0, d.size, (10000, d.size))
    mm = d[idx].mean(1)
    return float(np.percentile(mm, 5)), float(np.percentile(mm, 95))


def noninf(c, g, worse, delta, seeds):
    c = np.asarray(c, float); g = np.asarray(g, float); d = (g - c) * worse
    lo, hi = boot(d); pl, pg = signflip(d)
    if hi < delta: v = OK
    elif d.mean() > delta and pg < 0.05: v = BAD
    else: v = UNK
    return dict(ctrl_mean=float(c.mean()), cand_mean=float(g.mean()), d_worse_mean=float(d.mean()), ci90=[lo, hi], delta=float(delta), p_worse=pg, verdict=v,
                per_seed={int(s): [float(a), float(b)] for s, a, b in zip(seeds, c, g)})


def far_food(VER, seeds=range(271, 277)):
    rows = {}
    for s in seeds:
        for tg in ('v16c_far', 'v16gh_far'):
            d = V.run_dir('food3', s, tg); f = os.path.join(d, 'metrics.json')
            if not os.path.exists(f): return None
            m = json.load(open(f)); P = json.load(open(os.path.join(d, 'params.json'))); tt = m['t_touch']; T = float(P['T'])
            miss = sum(v is None for v in tt); got = [v for v in tt if v is not None]
            rows[(s, tg)] = dict(t_all=T if miss else max(tt), t_first=min(got) if got else T, missed=miss, m=m,
                                 comps_end=V.torus_label(np.load(os.path.join(d, 'wet.npy')))[1])
    S = list(seeds)
    c = [rows[(s, 'v16c_far')]['t_all'] for s in S]; g = [rows[(s, 'v16gh_far')]['t_all'] for s in S]
    out = dict(t_all=noninf(c, g, +1, max(15.0, 0.10 * float(np.mean(c))), S))
    c = [rows[(s, 'v16c_far')]['t_first'] for s in S]; g = [rows[(s, 'v16gh_far')]['t_first'] for s in S]
    out['t_first'] = noninf(c, g, +1, max(10.0, 0.10 * float(np.mean(c))), S)
    out['missed'] = [sum(rows[(s, 'v16c_far')]['missed'] for s in S), sum(rows[(s, 'v16gh_far')]['missed'] for s in S)]
    out['t_touch'] = {s: [rows[(s, 'v16c_far')]['m']['t_touch'], rows[(s, 'v16gh_far')]['m']['t_touch']] for s in S}
    out['activity'] = [[s] + [rows[(s, 'v16gh_far')]['m'][k] for k in ('ret_cellsteps', 'conn_kept_cellsteps', 'hang_cellsteps', 'sup_updates')] for s in S]
    out['health'] = [[s, rows[(s, 'v16gh_far')]['m']['neg_end_cellsteps'], rows[(s, 'v16gh_far')]['m']['mass_err_max'], rows[(s, 'v16gh_far')]['m']['V_crumb'], rows[(s, 'v16gh_far')]['comps_end']] for s in S]
    return out
