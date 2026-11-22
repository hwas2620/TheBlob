#!/usr/bin/env python3
"""사후 분석 (판정 뒤에 만든 것, 판정에는 쓰지 않는다). → data/post.json 과 화면

1) 주장 2 를 다른 시간 창에서: 스텝별 숫자(data/mon)의 thin, line 평균
2) 주장 2 를 "가장 큰 조각 안" 만으로: 저장 상태(lv, 20 시간마다)에서 가장 큰 젖은 조각 안의 thin, line (대조의 떨어진 부스러기를 뺀다)
3) 주장 1c 를 시간 창별로 (h ≥ 0.6, 10% 와 h ≥ 0.3, 10%)
"""
import glob, json, os, sys
import numpy as np
from scipy.stats import binomtest
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.normpath(os.path.join(HERE, '..', '..', 'model'))
DATA = os.path.join(HERE, '..', 'data')
sys.path.insert(0, HERE)
import monitor

SEEDS = range(201, 213)
WIN = [(200, 500), (500, 1000), (1000, 1500), (1500, 1700), (1700, 2001), (1500, 2001)]


def mon(s, tag):
    Z = np.load(os.path.join(DATA, 'mon', f'b_long_s{s}_{tag}.npz')); A = Z['stats']; k = list(Z['keys'])
    return Z['t'], {n: A[:, i] for i, n in enumerate(k)}


def sign(c, k):
    d = np.asarray(k) - np.asarray(c); lo = int((d < 0).sum()); n = int((d != 0).sum())
    return round(float(binomtest(lo, n, 0.5, alternative='greater').pvalue), 4) if n else 1.0, lo


def largest_piece(s, tag):
    rows = []
    for f in sorted(glob.glob(os.path.join(MODEL, 'runs', f'b_long_s{s}_{tag}', 'lv_t*.npz'))):
        Z = np.load(f); w = Z['wet'].astype(bool); h = Z['h'].astype(float); t = float(Z['t'])
        lab, n = monitor.tlabel(w)
        if n == 0: continue
        vol = np.bincount(lab[w], weights=h[w], minlength=n + 1); big = lab == int(np.argmax(vol))
        rg = monitor.ring_groups(big)
        rows.append((t, int((big & (h < 0.3)).sum()), int((rg >= 2).sum()), int(big.sum())))
    return np.array(rows)


def main():
    out = dict(windows={}, largest={}, big2={})
    M = {(s, tag): mon(s, tag) for s in SEEDS for tag in ('v15c', 'v15k')}
    print('1) 주장 2, 시간 창별 (스텝별 숫자의 평균; 대조 → 후보, 후보가 적은 시드 수/12, 부호 검정 p)')
    for a, b in WIN:
        r = {}
        for key in ('thin', 'line', 'area'):
            c = [M[(s, 'v15c')][1][key][(M[(s, 'v15c')][0] >= a) & (M[(s, 'v15c')][0] < b)].mean() for s in SEEDS]
            k = [M[(s, 'v15k')][1][key][(M[(s, 'v15k')][0] >= a) & (M[(s, 'v15k')][0] < b)].mean() for s in SEEDS]
            p, lo = sign(c, k); r[key] = dict(control=round(float(np.mean(c)), 1), candidate=round(float(np.mean(k)), 1), ratio=round(float(np.mean(k) / np.mean(c)), 3), cand_lower=lo, p=p)
        out['windows'][f'{a}-{b}'] = r
        print(f'  t {a}~{b}:', '  '.join(f"{key} {v['control']:.0f}→{v['candidate']:.0f} ({v['ratio']:.2f}, {v['cand_lower']}/12, p={v['p']})" for key, v in r.items()))
    print('2) 가장 큰 조각 안만 (저장 상태 20 시간마다)')
    L = {(s, tag): largest_piece(s, tag) for s in SEEDS for tag in ('v15c', 'v15k')}
    for a, b in WIN:
        r = {}
        for j, key in ((1, 'thin'), (2, 'line'), (3, 'area')):
            c = [L[(s, 'v15c')][(L[(s, 'v15c')][:, 0] >= a) & (L[(s, 'v15c')][:, 0] < b), j].mean() for s in SEEDS]
            k = [L[(s, 'v15k')][(L[(s, 'v15k')][:, 0] >= a) & (L[(s, 'v15k')][:, 0] < b), j].mean() for s in SEEDS]
            p, lo = sign(c, k); r[key] = dict(control=round(float(np.mean(c)), 1), candidate=round(float(np.mean(k)), 1), ratio=round(float(np.mean(k) / np.mean(c)), 3), cand_lower=lo, p=p)
        out['largest'][f'{a}-{b}'] = r
        print(f'  t {a}~{b}:', '  '.join(f"{key} {v['control']:.0f}→{v['candidate']:.0f} ({v['ratio']:.2f}, {v['cand_lower']}/12, p={v['p']})" for key, v in r.items()))
    print('3) 주장 1c, 시간 창별 (큰 굵은 조각 ≥ 2 인 스텝 비율)')
    for key in ('big_0.6_0.1', 'big_0.45_0.1', 'big_0.3_0.1'):
        r = {}
        for a, b in [(0, 500), (500, 1000), (1000, 1500), (1500, 2001)]:
            c = [(M[(s, 'v15c')][1][key][(M[(s, 'v15c')][0] >= a) & (M[(s, 'v15c')][0] < b)] >= 2).mean() for s in SEEDS]
            k = [(M[(s, 'v15k')][1][key][(M[(s, 'v15k')][0] >= a) & (M[(s, 'v15k')][0] < b)] >= 2).mean() for s in SEEDS]
            p, lo = sign(c, k); r[f'{a}-{b}'] = dict(control=round(float(np.mean(c)), 3), candidate=round(float(np.mean(k)), 3), cand_lower=lo, p=p)
        out['big2'][key] = r
        print(f'  {key}:', '  '.join(f"t{w}: {v['control']:.2f}→{v['candidate']:.2f} ({v['cand_lower']}/12)" for w, v in r.items()))
    json.dump(out, open(os.path.join(DATA, 'post.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
