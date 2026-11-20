#!/usr/bin/env python3
"""[S3 검증, 탐색] 몸 밖 조각을 센다. 판정에 쓰지 않는다.

usage: pieces.py --out FILE   (criteria.json 의 판정 짝 + 탐색 짝 E1 을 모두 본다)
저장 시각마다: 젖은 셀 8연결 성분 수 n, 가장 큰 성분 밖 부피 out, 가장 큰 것 말고 셀 10개 이상인 조각 수 big_pieces
실행마다: out 의 시간 평균, n 의 시간 평균, out ≥ 0.10 인 저장 시각 비율(갈라진 시간)
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'stage0'))
sys.path.insert(0, os.path.join(STAGE0, 'metrics')); import vmet
REF = os.path.join(STAGE0, 'ref', 'runs'); K = json.load(open(os.path.join(HERE, 'criteria.json')))


def run_stats(rd):
    rows = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); N = wet.shape[0]
        src, dst, cc, kk = vmet.edge_list(Z['C'].astype(float), wet); nc, lab = vmet.comps(src, dst, N * N); w = wet.ravel()
        vol = np.bincount(lab[w], weights=h.ravel()[w], minlength=nc); area = np.bincount(lab[w], minlength=nc); big = int(np.argmax(vol))
        n = int((area > 0).sum()); bp = int(((area >= 10) & (np.arange(nc) != big)).sum())
        rows.append(dict(t=float(Z['t']), n=n, out=float(1 - vol[big] / vol.sum()), big_pieces=bp))
    o = [r['out'] for r in rows]
    return dict(rows=rows, out_mean=float(np.mean(o)), n_mean=float(np.mean([r['n'] for r in rows])), split_frac=float(np.mean([x >= 0.10 for x in o])), bp_mean=float(np.mean([r['big_pieces'] for r in rows])))


def main():
    out = sys.argv[sys.argv.index('--out') + 1]; R = {}
    sets = {scn: [(s, 'vcd' if s in d['existing_vcd'] else 'vcdv') for s in d['seeds']] for scn, d in K['seeds'].items()}
    sets['mig'] += [(s, 'vcdv') for s in range(41, 51)]
    for scn, lst in sets.items():
        for s, ct in lst:
            a = os.path.join(REF, f'b_{scn}_s{s}_vthAv'); c = os.path.join(REF, f'b_{scn}_s{s}_{ct}')
            if not (os.path.exists(os.path.join(a, 'metrics.json')) and os.path.exists(os.path.join(c, 'metrics.json'))): continue
            R[f'{scn}_s{s}'] = dict(scn=scn, seed=s, ctrl=run_stats(c), cand=run_stats(a))
    json.dump(R, open(out, 'w'))
    for scn in sets:
        P = [v for v in R.values() if v['scn'] == scn]
        if not P: continue
        f = lambda k, w: [p[w][k] for p in P]
        hi = lambda k: sum(a > c for a, c in zip(f(k, 'cand'), f(k, 'ctrl')))
        print(f"{scn:9s} 짝 {len(P):2d} | out 시간평균 중앙 {np.median(f('out_mean','ctrl')):.4f} → {np.median(f('out_mean','cand')):.4f} (후보가 큼 {hi('out_mean')}/{len(P)})"
              f" | 성분 수 평균 {np.median(f('n_mean','ctrl')):.1f} → {np.median(f('n_mean','cand')):.1f} (큼 {hi('n_mean')})"
              f" | 10셀 넘는 조각 {np.median(f('bp_mean','ctrl')):.2f} → {np.median(f('bp_mean','cand')):.2f} (큼 {hi('bp_mean')})"
              f" | 갈라진 시간 비율 평균 {np.mean(f('split_frac','ctrl')):.3f} → {np.mean(f('split_frac','cand')):.3f}")
    for k, v in R.items():
        if v['scn'] in ('long', 'food4'): print(f"  {k}: 갈라진 시간 비율 {v['ctrl']['split_frac']:.2f} → {v['cand']['split_frac']:.2f}, out 시간평균 {v['ctrl']['out_mean']:.3f} → {v['cand']['out_mean']:.3f}")


if __name__ == '__main__':
    main()
