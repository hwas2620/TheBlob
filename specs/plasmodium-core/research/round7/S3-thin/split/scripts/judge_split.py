#!/usr/bin/env python3
"""[S3 덧붙인 확인] 갈라진 시간 비율 판정. 기준은 ../CRITERIA.md.

usage: judge_split.py [--json FILE]
몸 밖 = 1 - (가장 큰 덩어리 부피 / 전체 부피). 덩어리는 정맥 간선으로 이은 젖은 셀의 성분 (독립 검증 pieces.py 와 같은 정의).
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'stage0'))
sys.path.insert(0, os.path.join(STAGE0, 'metrics')); import vmet
REF = os.path.join(STAGE0, 'ref', 'runs')
SEEDS = {'long': range(51, 61), 'food4': range(51, 61)}


def run_stats(rd):
    o = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); N = wet.shape[0]
        src, dst, cc, kk = vmet.edge_list(Z['C'].astype(float), wet); nc, lab = vmet.comps(src, dst, N * N); w = wet.ravel()
        vol = np.bincount(lab[w], weights=h.ravel()[w], minlength=nc)
        o.append(float(1 - vol.max() / vol.sum()))
    M = json.load(open(os.path.join(rd, 'metrics.json')))
    return dict(n_states=len(o), split_frac=float(np.mean([x >= 0.10 for x in o])), out_mean=float(np.mean(o)), out_max_states=float(max(o)),
                h_min_seen=M.get('h_min_seen'), t_touch=M.get('t_touch'))


def bmet(rd):
    """bmet 채점 요약이 있으면 읽는다 (out_frac, reached, thick, pass, neg_end)."""
    name = os.path.basename(rd); f = os.path.join(HERE, '..', 'summaries', f'numpy_{name}.json')
    return json.load(open(f)) if os.path.exists(f) else {}


def main():
    R = {}
    for scn, seeds in SEEDS.items():
        for s in seeds:
            c = os.path.join(REF, f'b_{scn}_s{s}_vcds'); a = os.path.join(REF, f'b_{scn}_s{s}_vthAs')
            if not (os.path.exists(os.path.join(c, 'metrics.json')) and os.path.exists(os.path.join(a, 'metrics.json'))):
                print(f'빠짐: {scn} s{s}'); continue
            R[f'{scn}_s{s}'] = dict(scn=scn, seed=s, ctrl=dict(run_stats(c), **{k: bmet(c).get(k) for k in ('out_frac', 'reached', 'thick', 'pass', 'neg_end')}),
                                    cand=dict(run_stats(a), **{k: bmet(a).get(k) for k in ('out_frac', 'reached', 'thick', 'pass', 'neg_end')}))
    for k, v in R.items():
        c, a = v['ctrl'], v['cand']
        extra = f" | 닿음 {c['reached']}/{a['reached']} 굵은쌍 {c['thick']}/{a['thick']}" if v['scn'] == 'food4' else ''
        print(f"{k:10s} 갈라진 시간 {c['split_frac']:.2f} → {a['split_frac']:.2f} (d {a['split_frac'] - c['split_frac']:+.2f}) | 몸 밖 시간평균 {c['out_mean']:.3f} → {a['out_mean']:.3f}"
              f" | 몸 밖 최대(bmet) {c['out_frac']} → {a['out_frac']} | 스텝 안 최소 {c['h_min_seen']:.4f} → {a['h_min_seen']:.4f} | 스텝 끝 음수 {c['neg_end']} → {a['neg_end']}{extra}")
    out = {}
    for grp, P in (('long', [v for v in R.values() if v['scn'] == 'long']), ('food4', [v for v in R.values() if v['scn'] == 'food4']), ('all', list(R.values()))):
        if not P: continue
        d = np.array([p['cand']['split_frac'] - p['ctrl']['split_frac'] for p in P]); up = int((d > 0).sum()); dn = int((d < 0).sum())
        dm = np.array([p['cand']['out_mean'] - p['ctrl']['out_mean'] for p in P])
        dx = [p['cand']['out_frac'] - p['ctrl']['out_frac'] for p in P if p['cand']['out_frac'] is not None and p['ctrl']['out_frac'] is not None]
        g = dict(pairs=len(P), up=up, down=dn, d_mean=float(d.mean()), d_sem=float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else None,
                 ctrl_mean=float(np.mean([p['ctrl']['split_frac'] for p in P])), cand_mean=float(np.mean([p['cand']['split_frac'] for p in P])),
                 outmean_d=float(dm.mean()), outmean_up=int((dm > 0).sum()), outmax_d=float(np.mean(dx)) if dx else None)
        if grp == 'all':
            if len(P) < 20: g['verdict'] = '짝이 모자람'
            elif up >= 15 and g['d_mean'] >= 0.05: g['verdict'] = '늘어난다'
            elif g['d_mean'] <= 0.03 and up <= 12: g['verdict'] = '늘지 않는다'
            else: g['verdict'] = '판정 못 함'
        out[grp] = g
        print(f"[{grp} {len(P)}짝] 갈라진 시간 평균 {g['ctrl_mean']:.3f} → {g['cand_mean']:.3f}, d 평균 {g['d_mean']:+.3f} ± {g['d_sem'] or 0:.3f}, 후보가 큼 {up} / 작음 {dn}"
              f" | 몸 밖 시간평균 d {g['outmean_d']:+.4f} (큼 {g['outmean_up']}) | 몸 밖 최대 d {g['outmax_d'] if g['outmax_d'] is None else round(g['outmax_d'], 3)}"
              + (f" → 판정: {g['verdict']}" if 'verdict' in g else ''))
    if '--json' in sys.argv:
        json.dump(dict(runs=R, groups=out), open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
