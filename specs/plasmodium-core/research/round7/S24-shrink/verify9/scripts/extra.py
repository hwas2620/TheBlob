#!/usr/bin/env python3
"""verify9 덧붙임 측정 (판정에 쓰지 않음, 실행 뒤에 씀). 결과: out_extra.json

1. 주장 7 (c) '짙은 곳' 민감도: 갇힐 때 두께를 가우스 흐림(σ 3, 5, 10, 젖은 칸만)으로 잰 몸 안 순위의 덩이 평균, 그리고 덩이 넓이만큼의 가장 짙은 칸과 겹치는 몫
2. 주장 7 (d) 넓이 시계열(스텝마다)에서 갇힌 뒤 10 시간 창 하나의 넓이 감소가 전체 감소에서 차지하는 최대 몫
"""
import json, os, sys, glob
import numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
V9 = os.path.normpath(os.path.join(HERE, '..')); RUNS = os.path.normpath(os.path.join(V9, '..', 'model', 'runs'))
out = {}
for f in sorted(glob.glob(os.path.join(V9, 'out', 'run_b_slimeall_*_v9b.json'))):
    r = json.load(open(f)); s = r['scl']
    if not s.get('trapped'): continue
    t0 = s['t_trap_snap']; Z = np.load(os.path.join(RUNS, r['name'], f'vs_t{int(round(t0)):04d}.npz')); w0 = Z['wet'].astype(bool); h0 = Z['h'].astype(float)
    ZE = np.load(os.path.join(RUNS, r['name'], f"vs_t{int(round(r['T'])):04d}.npz")); wE = ZE['wet'].astype(bool); hE = ZE['h'].astype(float)
    lab, n, vol, area, V = M.components(w0, h0); B = lab == int(np.argmax(vol))
    labE, nE, volE, areaE, VE = M.components(wE, hE); L = labE == int(np.argmax(volE))
    d = {}
    for sg in (3, 5, 10):
        hw = np.where(w0, np.maximum(h0, 0), 0.0); G = gaussian_filter(hw, sg, mode='wrap', truncate=3.0) / np.maximum(gaussian_filter(w0.astype(float), sg, mode='wrap', truncate=3.0), 1e-9)
        Gr = gaussian_filter(hw, sg, mode='wrap', truncate=3.0)      # 흐린 부피 (마른 칸도 0 으로 넣음)
        for nm, F in (('mean', G), ('vol', Gr)):
            bv = F[B]; rk = np.empty(bv.size); rk[np.argsort(bv, kind='stable')] = np.arange(bv.size) / max(bv.size - 1, 1); R_ = np.zeros(w0.shape); R_[B] = rk
            k = int((L & B).sum()); top = np.zeros(w0.shape, bool); idx = np.flatnonzero(B); top.ravel()[idx[np.argsort(-bv, kind='stable')[:k]]] = True
            d[f'{nm}_s{sg}'] = dict(rank=float(R_[L & B].mean()), top_overlap=float((top & L).sum() / max(k, 1)))
    a = np.array(r['area_series'], float); i0 = int(round(s['t_scl'] / r['dt'])); seg = a[i0:i0 + 3000]
    drop = seg[0] - seg.min(); kw = int(round(10 / r['dt']))
    win = float(np.max(seg[:-kw] - seg[kw:]) / max(drop, 1)) if seg.size > kw else float('nan')
    d['area_drop_maxwin10'] = win; d['area_trap'] = float(seg[0]); d['area_min'] = float(seg.min())
    out[r['name']] = d
    print(r['name'], {k: (round(v['rank'], 2), round(v['top_overlap'], 2)) if isinstance(v, dict) else round(v, 3) for k, v in d.items()})
json.dump(out, open(os.path.join(V9, 'out_extra.json'), 'w'), indent=1)


# 3. 탐색 가지와 관·고리 (주장 6 에서 뺀 것): 주 몸의 넓힌 깎기 뒤 남는 가는 덩이를, 닿는 넓은 덩이(3x3 열림의 8-연결 덩이)로 나눈다.
#    앞머리 = 나이 중앙값 15 미만이고 몸 넓이의 20% 미만인 넓은 덩이. 탐색 가지 = 앞머리와 다른 넓은 덩이에 함께 닿는 가는 덩이(줄기).
#    관 = 앞머리 아닌 넓은 덩이 둘 이상에 닿는 가는 덩이. 고리 = 넓은 덩이 하나에만 닿는데도 깎이지 않은 가는 덩이(제 몸으로 도는 고리).
def branches(rd):
    res = []
    for fz in sorted(glob.glob(os.path.join(RUNS, rd, 'vs_t*.npz'))):
        Z = np.load(fz); t = float(Z['t'])
        if int(round(t)) % 20 or t < 60: continue
        w = Z['wet'].astype(bool); h = Z['h'].astype(float); age = Z['age'].astype(float)
        lab, n, vol, area, V = M.components(w, h); mids = [k for k in range(1, n + 1) if vol[k] >= M.MAIN_FRAC * V] or [int(np.argmax(vol))]
        main = np.isin(lab, mids); wide = M.opening3(w) & main; thin = main & ~wide
        _, rest = M.prune_ext(main, thin); tube = rest & thin
        lw, nw = M.label8(wide); lt, nt = M.label8(tube)
        if nt == 0: res.append(dict(t=t, br=[], tube=[], loop=[])); continue
        aw = np.bincount(lw.ravel(), minlength=nw + 1); head = np.zeros(nw + 1, bool)
        for k in range(1, nw + 1):
            m_ = lw == k; head[k] = (np.median(age[m_]) < 15) and (aw[k] < 0.2 * main.sum())
        touch = [set() for _ in range(nt + 1)]
        for d in M.ALL:
            nbw = M.nb(lw, d); m_ = (lt > 0) & (nbw > 0)
            for a_, b_ in set(zip(lt[m_].tolist(), nbw[m_].tolist())): touch[a_].add(b_)
        sz = np.bincount(lt.ravel(), minlength=nt + 1); br = []; tb = []; lp = []
        for k in range(1, nt + 1):
            if sz[k] < M.TAIL_MIN: continue
            hs = [x for x in touch[k] if head[x]]; nh = [x for x in touch[k] if not head[x]]
            if hs and nh: br.append(int(sz[k]))
            elif len(nh) >= 2: tb.append(int(sz[k]))
            else: lp.append(int(sz[k]))
        res.append(dict(t=t, br=br, tube=tb, loop=lp))
    return rd, res


if __name__ == '__main__':
    from multiprocessing import Pool
    names = [os.path.basename(p) for p in sorted(glob.glob(os.path.join(RUNS, 'b_*_v9[bc]'))) if p.split('_')[1] in ('food3', 'asym3', 'food4', 'mig', 'long')]
    with Pool(4) as pool: BR = dict(pool.map(branches, names))
    summ = {}
    for g, scns in (('food', ('food3', 'asym3', 'food4')), ('migr', ('mig', 'long'))):
        for tag in ('v9c', 'v9b'):
            ss = [s for nm, v in BR.items() if nm.split('_')[1] in scns and nm.endswith(tag) for s in v]
            def stat(key):
                L = [x for s in ss for x in s[key]]
                return dict(per_snap=round(len(L) / max(len(ss), 1), 3), median_len=float(np.median(L)) if L else None, p90_len=float(np.percentile(L, 90)) if L else None, max_len=max(L) if L else 0)
            summ[f'{g}_{tag}'] = dict(snaps=len(ss), branch=stat('br'), tube=stat('tube'), loop=stat('loop'))
            print(g, tag, summ[f'{g}_{tag}'])
    out['branches'] = summ
    json.dump(out, open(os.path.join(V9, 'out_extra.json'), 'w'), indent=1)
