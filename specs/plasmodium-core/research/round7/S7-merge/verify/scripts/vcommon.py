#!/usr/bin/env python3
"""[S7 독립 검증] 공통 도구. 저장 상태(vs_t*.npz)를 읽고, 덩어리·엽·젖은 칸을 따라 잰 나눔을 낸다.

- 젖은 덩어리 라벨은 ref_model._torus_label (8-연결 토러스)을 쓰고, scipy 그래프로 만든 내 라벨(graph_cc)과 맞춰 볼 수 있게 둘 다 둔다.
- 젖은 칸을 따라 잰 가장 가까운 덩어리 나눔은 규칙 코드를 베끼지 않고 scipy 의 다중 출발 최단 거리(dijkstra, min_only)로 따로 구현했다.
"""
import glob, json, os, sys
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

HERE = os.path.dirname(os.path.abspath(__file__))
VER = os.path.normpath(os.path.join(HERE, '..'))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'stage0'))
REF = os.path.join(STAGE0, 'ref'); RUNS = os.path.join(REF, 'runs')
sys.path.insert(0, REF)
from ref_model import _torus_label  # noqa: E402

TH = 0.3          # 두꺼운 칸 문턱 (규칙의 sup_h)
BIG = 0.1         # 큰 덩어리 문턱 (규칙의 sup_min)
D4 = [(1, 0), (0, 1), (1, 1), (1, -1)]      # (dx, dy): 칸 (y, x) -> (y+dy, x+dx)


def states(rd, tmin=-1.0):
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
    out = []
    for f in fs:
        t = int(os.path.basename(f)[4:-4])
        if t >= tmin: out.append((t, f))
    return out


def load(f, keys=('wet', 'h', 'age', 'sage')):
    Z = np.load(f); d = {k: Z[k] for k in keys if k in Z.files}; d['t'] = float(Z['t'])
    d['wet'] = d['wet'].astype(bool); d['h'] = np.where(d['wet'], d['h'].astype(float), 0.0)
    return d


def graph(wet):
    """젖은 칸의 8-이웃 토러스 그래프 (가중치 1). 반환: 희소 행렬, 칸 번호 배열(-1 = 마름), 젖은 칸의 (y, x)"""
    N = wet.shape[0]; idx = -np.ones(wet.shape, np.int64); ys, xs = np.nonzero(wet); n = ys.size; idx[ys, xs] = np.arange(n)
    S = []; D = []
    for dx, dy in D4:
        j = idx[(ys + dy) % N, (xs + dx) % N]; m = j >= 0
        S.append(np.arange(n)[m]); D.append(j[m])
    S = np.concatenate(S); D = np.concatenate(D)
    G = coo_matrix((np.ones(S.size), (S, D)), shape=(n, n)).tocsr()
    return G, idx, ys, xs


def graph_cc(wet):
    """내 라벨: scipy 그래프 연결 성분 (0 = 마름, 1.. = 덩어리)"""
    G, idx, ys, xs = graph(wet); lab = np.zeros(wet.shape, np.int64)
    if ys.size == 0: return lab
    nc, l = connected_components(G, directed=False); lab[ys, xs] = l + 1
    return lab


def comp_vols(lab, h):
    v = np.bincount(lab.ravel(), weights=h.ravel()); v[0] = 0.0
    return v


def big_parts(wet, h, V=None):
    """큰 두꺼운 덩어리: (라벨 배열, 큰 덩어리 라벨 목록(부피 큰 순), 그 두꺼운 부피 목록)"""
    V = float(h[wet].sum()) if V is None else V
    thk = wet & (h >= TH); lt = _torus_label(thk); vt = comp_vols(lt, np.where(thk, h, 0.0))
    big = [int(k) for k in np.argsort(vt)[::-1] if vt[k] >= BIG * V and k > 0]
    return lt, big, [float(vt[k]) for k in big]


def torus_open(mask, r=2):
    """토러스에서 (2r+1)x(2r+1) 정사각형 열기"""
    p = 3 * r
    m = np.pad(mask, p, mode='wrap')
    o = ndi.binary_opening(m, structure=np.ones((2 * r + 1, 2 * r + 1), bool))
    return o[p:-p, p:-p]


def lobes(wet, h, V=None):
    """큰 엽: 두꺼운 마스크를 5x5 로 연 뒤 8-연결 덩어리 가운데 h 합 >= 0.1 V"""
    V = float(h[wet].sum()) if V is None else V
    o = torus_open(wet & (h >= TH)); lo = _torus_label(o); vo = comp_vols(lo, np.where(o, h, 0.0))
    return int((vo[1:] >= BIG * V).sum())


def torus_dilate(mask, r):
    p = r + 2
    m = np.pad(mask, p, mode='wrap')
    o = ndi.binary_dilation(m, structure=np.ones((2 * r + 1, 2 * r + 1), bool))
    return o[p:-p, p:-p]


def fans(wet, h, V=None, r_open=2, gap=10):
    """[2a′] 큰 부채: 5x5 로 연 두꺼운 마스크의 조각들 가운데 서로 gap 칸 이하로 떨어진 것을 한 부채로 묶고(반지름 gap/2 로 넓혀 이어지면 한 무리),
    무리 안의 (연 마스크) h 합이 0.1 V 이상인 무리 수. 한 전진면이 목에서 끊겨 여러 엽으로 세어지는 것을 막는다."""
    V = float(h[wet].sum()) if V is None else V
    o = torus_open(wet & (h >= TH), r_open)
    if not o.any(): return 0
    g = _torus_label(torus_dilate(o, gap // 2))
    vg = np.bincount(g[o], weights=h[o], minlength=g.max() + 1)
    return int((vg[1:] >= BIG * V).sum())


def lobes_r(wet, h, V, r):
    o = torus_open(wet & (h >= TH), r); lo = _torus_label(o); vo = comp_vols(lo, np.where(o, h, 0.0))
    return int((vo[1:] >= BIG * V).sum())


def partition(wet, seeds_lab):
    """젖은 칸을 따라 잰(8-이웃, 한 걸음 1) 가장 가까운 씨앗의 번호. seeds_lab: 씨앗 칸에 1.., 나머지 0. 닿지 않는 젖은 칸은 0"""
    G, idx, ys, xs = graph(wet); out = np.zeros(wet.shape, np.int64)
    src = idx[(seeds_lab > 0) & wet]
    if src.size == 0: return out
    dist, pred, sources = dijkstra(G, directed=False, indices=src, unweighted=True, min_only=True, return_predecessors=True)
    ok = sources >= 0
    sy, sx = ys[sources[ok]], xs[sources[ok]]
    out[ys[ok], xs[ok]] = seeds_lab[sy, sx]
    return out


def food_field(P):
    """유인장 c(x) (ref_model 과 같은 식). foods 가 없으면 None"""
    N = P['N']; c0 = N / 2 - 0.5; jj, ii = np.mgrid[0:N, 0:N].astype(float)
    if not P.get('foods'): return None
    f = np.zeros((N, N))
    for a_, d_ in P['foods']:
        fx, fy = c0 + d_ * np.cos(np.radians(a_)), c0 + d_ * np.sin(np.radians(a_))
        for sx in (-N, 0, N):
            for sy in (-N, 0, N): f += np.exp(-((ii - fx - sx) ** 2 + (jj - fy - sy) ** 2) / (2 * P['food_sigma'] ** 2))
    return P['food_amp'] * f


def params(rd):
    return json.load(open(os.path.join(rd, 'params.json')))


def rundir(scn, s, tag):
    return os.path.join(RUNS, f'b_{scn}_s{s}_{tag}')
