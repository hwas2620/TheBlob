"""S23 진단 1 보기: 균핵 구멍(slimeall), 먹이 판 자유 꼬리(food4), 풀이(mig 673)를 기준 실행과 견준다.
python3 d1look.py [꼬리표…]   (기본: xh1 xh2 xt1 xg1 xg2)
기준: 같은 시드의 S22 실행(s22y, v7y; 설정과 모델이 비트까지 같다)
"""
import os, sys, glob, json
import numpy as np
from scipy import ndimage as nd
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, '..', 'model', 'runs'); RUNS22 = os.path.join(HERE, '..', '..', 'S22-form', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import nb, RING, _torus_label

def base_dir(scn, s):
    for tag in ('s22y', 'v7y'):
        d = os.path.join(RUNS22, f'b_{scn}_s{s}_{tag}')
        if os.path.exists(os.path.join(d, 'metrics.json')): return d
    return None

def lump(d, t):
    Z = np.load(os.path.join(d, f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); V = h.sum()
    lab = _torus_label(w); vol = nd.sum(h, lab, np.arange(1, lab.max() + 1)); big = lab == (np.argmax(vol) + 1)
    npc = int((vol >= 0.05 * V).sum())
    filled = nd.binary_fill_holes(big); holes = filled & ~big; hl, hn = nd.label(holes)
    opened = nd.binary_opening(big, structure=np.ones((3, 3)))      # 폭 3칸이 안 되는 가는 부분
    narrow = big & ~opened
    ys, xs = np.nonzero(big)
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(np.c_[xs, ys]).volume + 0.5 * len(xs) ** 0.5 * 4
        csol = big.sum() / hull
    except Exception: csol = float('nan')
    hv = h[big]; cv = float(hv.std() / hv.mean())
    return dict(area=int(big.sum()), pieces=npc, holes=int(hn), hole_cells=int(holes.sum()), solid=float(big.sum() / filled.sum()), csolid=float(csol),
                narrow_vol=float(h[narrow].sum() / V), cv=cv, hmax=float(hv.max()))

def strands(w, h):
    nw = np.zeros(w.shape, int)
    for dd in RING: nw += nb(w, dd)
    lab = _torus_label(w & (nw <= 2) & (h < 0.6)); sz = np.bincount(lab.ravel())[1:]
    return (int(sz.max()) if sz.size else 0), int((w & (nw <= 1)).sum())

def tails(d, T):
    out = []
    for t in range(100, T + 1, 50):
        f = os.path.join(d, f'vs_t{t:04d}.npz')
        if not os.path.exists(f): continue
        Z = np.load(f); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); out.append(strands(w, h))
    return out

def main(tags):
    for tag in tags:
        for d in sorted(glob.glob(os.path.join(RUNS, f'b_*_s*_{tag}'))):
            name = os.path.basename(d); scn = name.split('_')[1]; s = int(name.split('_')[2][1:])
            if not os.path.exists(os.path.join(d, 'metrics.json')): continue
            m = json.load(open(os.path.join(d, 'metrics.json'))); b = base_dir(scn, s); mb = json.load(open(os.path.join(b, 'metrics.json'))) if b else None
            if scn == 'slimeall':
                for lab_, dd in (('기준', b), (tag, d)):
                    if dd is None: continue
                    L = lump(dd, 800); print(f"{name:26s} {lab_:5s} 넓이 {L['area']:4d} 조각 {L['pieces']} 구멍 {L['holes']:2d}({L['hole_cells']:3d}칸) solidity {L['solid']:.2f} 볼록 {L['csolid']:.2f} 가는부피 {L['narrow_vol']:.3f} CV {L['cv']:.2f} hmax {L['hmax']:.2f}")
            elif scn in ('food4', 'food3', 'asym3'):
                T = int(m['t_end'])
                tb = tails(b, T) if b else []; tc = tails(d, T)
                f = lambda v: 'x' if v is None else f'{v:.0f}'
                print(f"{name:26s} 닿음 기준 [{' '.join(f(v) for v in mb['t_touch'])}] → [{' '.join(f(v) for v in m['t_touch'])}]")
                print(f"{'':26s} 가장 긴 외가닥 (t 100~{T}, 50마다) 기준 {[a for a, _ in tb]}\n{'':26s}                               후보 {[a for a, _ in tc]}")
                print(f"{'':26s} 자유 끝 기준 {[b_ for _, b_ in tb]}\n{'':26s}         후보 {[b_ for _, b_ in tc]}  되감은 칸 {m.get('tiphome_cells')}, ret {m.get('ret_cellsteps')}")
            elif scn == 'mig':
                print(f"{name:26s} 풀이 오차 [중앙, 90%, 최대] 기준 {np.round(mb['mg_err'][:3], 3).tolist()} → {np.round(m['mg_err'][:3], 3).tolist()}  더 푼 스텝 {m.get('mg_nadapt')} 0 출발 {m.get('mg_nguard')}  닿음 {mb['t_touch']} → {m['t_touch']} 이동 {mb['disp']} → {m['disp']}")
                e = json.load(open(os.path.join(d, 'mg_err_series.json'))); print(f"{'':26s} > 0.2 인 검사: {[(int(x[0]), round(x[1], 2)) for x in e if x[1] > 0.2]}")

if __name__ == '__main__':
    main(sys.argv[1:] or ['xh1', 'xh2', 'xt1', 'xg1', 'xg2'])
