#!/usr/bin/env python3
"""검증자의 측정 도구 (모델의 _torus_label, graphm 을 쓰지 않는다).

tlabel(mask)      토러스 8연결 성분. scipy.ndimage.label + 가장자리 넘어가는 쌍을 작은 그래프로 합친다
ring_groups(wet)  젖은 셀마다, 둘레 8칸 가운데 젖은 칸들이 몇 개의 8연결 무리로 나뉘는지 (3x3 안에서, 가운데 칸 빼고)
step_stats(wet,h) 한 상태의 숫자들 (STAT_KEYS 순서)
"""
import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

S8 = np.ones((3, 3), int)
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]   # (dx, dy)


def tlabel(mask):
    """돌려줌: (lab, n). lab 은 0 = 바깥, 1..n = 토러스 8연결 성분"""
    mask = np.asarray(mask, bool)
    lab, n = ndimage.label(mask, structure=S8)
    if n == 0: return lab, 0
    a_ = []; b_ = []
    top = lab[0]; bot = lab[-1]; lef = lab[:, 0]; rig = lab[:, -1]
    for d in (-1, 0, 1):
        b = np.roll(top, -d); m = (bot > 0) & (b > 0); a_.append(bot[m]); b_.append(b[m])     # (N-1, x) ~ (0, x+d)
        b = np.roll(lef, -d); m = (rig > 0) & (b > 0); a_.append(rig[m]); b_.append(b[m])     # (y, N-1) ~ (y+d, 0)
    a_ = np.concatenate(a_); b_ = np.concatenate(b_)
    if a_.size == 0: return lab, n
    g = coo_matrix((np.ones(a_.size, np.int8), (a_, b_)), shape=(n + 1, n + 1))
    nc, cl = connected_components(g, directed=False)
    # 성분 번호를 1..k 로 다시 매긴다 (0 번 노드 = 바깥은 다른 노드와 이어지지 않는다)
    used = np.unique(cl[1:]); remap = np.zeros(nc, np.int64); remap[used] = np.arange(1, used.size + 1)
    out = remap[cl][lab]; out[~mask] = 0
    return out, int(used.size)


def _ring_lut():
    lut = np.zeros(256, np.int8)
    for code in range(256):
        on = [q for q in range(8) if code >> q & 1]
        if not on: continue
        par = {q: q for q in on}
        def f(q):
            while par[q] != q: q = par[q]
            return q
        for i in on:
            for j in on:
                if i < j and max(abs(RING[i][0] - RING[j][0]), abs(RING[i][1] - RING[j][1])) <= 1:
                    par[f(j)] = f(i)
        lut[code] = len({f(q) for q in on})
    return lut


LUT = _ring_lut()


def nbr(a, d):
    """a 를 (dx, dy) 방향 이웃에서 읽는다 (토러스). 배열 첨자는 [y, x]"""
    return np.roll(a, (-d[1], -d[0]), (0, 1))


def ring_groups(wet):
    code = np.zeros(wet.shape, np.int32)
    for q, d in enumerate(RING): code |= nbr(wet, d).astype(np.int32) << q
    return np.where(wet, LUT[code], 0)


THICK = (0.3, 0.45, 0.6)     # 굵은 셀의 문턱 (주 문턱 0.6)
BIGF = (0.05, 0.1, 0.2)      # 큰 조각 = 부피가 몸 전체의 이 비율 이상 (주 비율 0.1)
STAT_KEYS = ['t', 'area', 'V', 'ncomp', 'vol_out', 'area_out', 'n_neg', 'hmin',
             'thin', 'line', 'line3'] + [f'big_{a}_{b}' for a in THICK for b in BIGF] + [f'npc_{a}' for a in THICK]


def step_stats(wet, h, t):
    wet = np.asarray(wet, bool); h = np.asarray(h, np.float64)
    V = float(h[wet].sum()); area = int(wet.sum())
    row = dict(t=float(t), area=area, V=V)
    lab, n = tlabel(wet)
    if n > 0:
        vol = np.bincount(lab[wet], weights=h[wet], minlength=n + 1); cnt = np.bincount(lab[wet], minlength=n + 1)
        k = int(np.argmax(vol)); row['vol_out'] = 1.0 - float(vol[k]) / V if V > 0 else 0.0; row['area_out'] = int(area - cnt[k])
    else:
        row['vol_out'] = 0.0; row['area_out'] = 0
    row['ncomp'] = n
    row['n_neg'] = int((wet & (h < 0)).sum()); row['hmin'] = float(h[wet].min()) if area else 0.0
    row['thin'] = int((wet & (h < 0.3)).sum())
    rg = ring_groups(wet); row['line'] = int((rg >= 2).sum()); row['line3'] = int((rg >= 3).sum())
    for a in THICK:
        th = wet & (h >= a); lt, nt = tlabel(th)
        vt = np.bincount(lt[th], weights=h[th], minlength=nt + 1)[1:] if nt else np.zeros(0)
        row[f'npc_{a}'] = nt
        for b in BIGF: row[f'big_{a}_{b}'] = int((vt >= b * V).sum()) if V > 0 else 0
    return [row[k] for k in STAT_KEYS]
