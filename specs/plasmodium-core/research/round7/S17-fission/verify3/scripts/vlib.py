#!/usr/bin/env python3
"""verify3 측정 도구 (모델의 graphm.py 를 쓰지 않는다). 모두 토러스 감김을 따른다.

간선 규약 (ref_model.py): DIRS = [(1,0),(0,1),(1,1),(1,-1)] 는 (dx, dy). 채널 k 의 간선은 셀 (y,x) 에서 (y+dy, x+dx) 로 간다.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
S8 = np.ones((3, 3), bool)


def nb(a, d):
    return np.roll(a, (-d[1], -d[0]), (0, 1))


def rev(a, d):
    return np.roll(a, (d[1], d[0]), (0, 1))


def tlabel(mask):
    """8연결 성분 번호 (토러스). 0 = 바탕. 번호는 1..n"""
    lab, n = ndi.label(mask, structure=S8)
    if n == 0:
        return lab, 0
    N0, N1 = mask.shape
    a = []; b = []
    for dx in (-1, 0, 1):
        a.append(lab[0, :]); b.append(np.roll(lab[N0 - 1, :], -dx))
        a.append(lab[:, 0]); b.append(np.roll(lab[:, N1 - 1], -dx))
    a = np.concatenate(a); b = np.concatenate(b); m = (a > 0) & (b > 0)
    g = coo_matrix((np.ones(int(m.sum())), (a[m], b[m])), shape=(n + 1, n + 1))
    nc, comp = connected_components(g, directed=False)
    # 바탕(0)을 0 으로 두고 나머지를 1.. 로 다시 매김
    used = np.unique(comp[1:])
    remap = np.zeros(nc, np.int64); remap[used] = np.arange(1, used.size + 1)
    out = np.where(lab > 0, remap[comp[lab]], 0)
    return out, int(used.size)


def _pad(a, p):
    return np.pad(a, p, mode='wrap')


def topen(mask, s):
    """s×s 정사각형으로 열기 (토러스)"""
    p = s + 1
    o = ndi.binary_opening(_pad(mask, p), structure=np.ones((s, s), bool))
    return o[p:-p, p:-p] & mask


def tdt(mask):
    """체스판 거리 변환: 몸 셀에서 가장 가까운 몸 밖 셀까지 (토러스). 1 = 가장자리 셀"""
    p = mask.shape[0] // 2
    d = ndi.distance_transform_cdt(_pad(mask, p), metric='chessboard')
    return d[p:-p, p:-p]


def tskel(mask):
    from skimage.morphology import skeletonize
    p = max(16, mask.shape[0] // 4)
    s = skeletonize(_pad(mask, p))
    return s[p:-p, p:-p] & mask


def nsum8(m):
    m = m.astype(np.int16); s = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                s += np.roll(m, (dy, dx), (0, 1))
    return s


def nmax8(a):
    s = a.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                s = np.maximum(s, np.roll(a, (dy, dx), (0, 1)))
    return s


def dilate_cheb(mask, r):
    p = r + 1
    o = ndi.binary_dilation(_pad(mask, p), structure=np.ones((2 * r + 1, 2 * r + 1), bool))
    return o[p:-p, p:-p]


def cell_flow(Qg):
    """셀에 닿는 8 간선의 Qgross 최댓값"""
    q = np.zeros(Qg.shape[1:], np.float64)
    for k, d in enumerate(DIRS):
        q = np.maximum(q, np.maximum(Qg[k], rev(Qg[k], d)))
    return q


def wconn(body, dt, A, B):
    """A, B 가 {body & dt>=w} ∪ A ∪ B 안에서 이어지는 가장 큰 w (최대-최소 너비). 몸 안이므로 w=1 에서는 늘 이어짐"""
    lo, hi = 1, int(dt[body].max()) if body.any() else 1
    ia = np.flatnonzero(A.ravel())[0]; ib = np.flatnonzero(B.ravel())[0]

    def ok(w):
        lab, _ = tlabel((body & (dt >= w)) | A | B)
        return lab.ravel()[ia] == lab.ravel()[ib] and lab.ravel()[ia] > 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if ok(mid): lo = mid
        else: hi = mid - 1
    return lo
