#!/usr/bin/env python3
"""S16 아령 독립 검증의 지표 (CRITERIA.md 의 정의를 그대로 옮김). 모델 코드를 import 하지 않는다.

간선 규약: 채널 k 의 간선은 셀 (y,x) 에서 (y+DY[k], x+DX[k]) 로 간다 (토러스 감김). DIRS = (1,0), (0,1), (1,1), (1,-1) (dx, dy).
"""
import glob, json, os
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]


def nb(a, d):
    """a 를 방향 d 의 이웃에서 읽은 값"""
    return np.roll(a, (-d[1], -d[0]), (0, 1))


def torus_label(mask):
    """8연결 토러스 성분. (라벨 배열 0=배경, 성분 수)"""
    N0, N1 = mask.shape
    lab, n = ndi.label(mask, structure=np.ones((3, 3), int))
    if n <= 1: return lab, n
    a = []; b = []
    for d in (-1, 0, 1):
        r = np.arange(N0)
        a.append(lab[r, 0]); b.append(lab[(r + d) % N0, N1 - 1])
        c = np.arange(N1)
        a.append(lab[0, c]); b.append(lab[N0 - 1, (c + d) % N1])
    a = np.concatenate(a); b = np.concatenate(b); m = (a > 0) & (b > 0)
    g = coo_matrix((np.ones(int(m.sum()) + n), (np.concatenate([a[m] - 1, np.arange(n)]), np.concatenate([b[m] - 1, np.arange(n)]))), shape=(n, n))
    nc, cl = connected_components(g, directed=False)
    out = np.zeros_like(lab); out[lab > 0] = cl[lab[lab > 0] - 1] + 1
    return out, int(nc)


def dilate8(m):
    o = m.copy()
    for d in ALL: o |= nb(m, d)
    return o


def bfs(src, allowed):
    """src 에서 allowed 칸 안으로 8이웃 BFS. src 에 붙은 allowed 칸 = 1. 닿지 않으면 inf"""
    dist = np.full(src.shape, np.inf); seen = src.copy(); fr = src.copy(); it = 0
    while fr.any():
        it += 1; new = dilate8(fr) & allowed & ~seen
        dist[new] = it; seen |= new; fr = new
    return dist


def bottleneck(A, B, R):
    """CRITERIA 주장 2 의 '이음의 가장 좁은 곳'. R 로 이어지지 않으면 None"""
    dA = bfs(A, R); dB = bfs(B, R); S = dA + dB
    fin = R & np.isfinite(S)
    if not fin.any(): return None, None
    m = float(S[fin].min()); L = int(m) - 1
    cor = fin & (S <= m + 2)
    cnt = [int((cor & (dA == k)).sum()) for k in range(1, L + 1)]
    return (min(cnt) if cnt else None), L


def dumbbell(wet, h, hth=0.5, frac=0.05, do_d2=True, lab_w=None):
    """D1, D2, 큰 덩이 수, 짝마다 (가장 좁은 곳, 길이)"""
    Vb = float(h[wet].sum())
    thick = wet & (h > hth)
    lt, nt = torus_label(thick)
    if nt < 2: return dict(D1=False, D2=False, nbig=int(nt > 0 and Vb > 0 and float(h[thick].sum()) >= frac * Vb), pairs=[])
    vol = np.bincount(lt.ravel(), weights=np.where(thick, h, 0.0).ravel(), minlength=nt + 1); vol[0] = 0
    big = [k for k in range(1, nt + 1) if vol[k] >= frac * Vb]
    if len(big) < 2: return dict(D1=False, D2=False, nbig=len(big), pairs=[])
    if lab_w is None: lab_w, _ = torus_label(wet)
    wc = {k: int(lab_w[lt == k].flat[0]) for k in big}
    groups = {}
    for k in big: groups.setdefault(wc[k], []).append(k)
    D1 = any(len(v) >= 2 for v in groups.values())
    pairs = []; D2 = False
    if D1 and do_d2:
        bigm = np.isin(lt, big); R = wet & ~bigm
        for v in groups.values():
            for i in range(len(v)):
                for j in range(i + 1, len(v)):
                    bn, L = bottleneck(lt == v[i], lt == v[j], R)
                    pairs.append([round(float(vol[v[i]] / Vb), 3), round(float(vol[v[j]] / Vb), 3), bn, L])
                    if bn is not None and bn <= 3: D2 = True
    return dict(D1=bool(D1), D2=bool(D2), nbig=len(big), pairs=pairs)


def block_cover(m):
    """m 의 칸 넷으로 된 2x2 묶음에 드는 칸"""
    b = m & nb(m, (1, 0)) & nb(m, (0, 1)) & nb(m, (1, 1))
    return b | nb(b, (-1, 0)) | nb(b, (0, -1)) | nb(b, (-1, -1))


def active(wet):
    return [wet & nb(wet, d) for d in DIRS]


def incident_max(E, act):
    """간선 값 E[k] (활성 간선만) 의 칸별 최댓값 (닿는 8 간선)"""
    out = np.full(act[0].shape, -np.inf)
    for k, d in enumerate(DIRS):
        e = np.where(act[k], E[k], -np.inf)
        out = np.maximum(out, e); out = np.maximum(out, nb(e, (-d[0], -d[1])))
    return out


_ADJ_PAIRS = [(i, j) for i in range(8) for j in range(i + 1, 8) if max(abs(RING[i][0] - RING[j][0]), abs(RING[i][1] - RING[j][1])) <= 1]


def prune_ends(wet, maxit=400):
    m = wet.copy(); removed = np.zeros_like(wet); it = 0
    for it in range(1, maxit + 1):
        x = [nb(m, d) for d in RING]
        n = np.zeros(m.shape, np.int8)
        for v in x: n += v
        adj = np.zeros(m.shape, bool)
        for i, j in _ADJ_PAIRS: adj |= x[i] & x[j]
        rem = m & ((n == 1) | ((n == 2) & adj))
        if not rem.any(): break
        removed |= rem; m &= ~rem
    return removed, it


def late_cells(S):
    """주장 3 의 세 수와 보조"""
    wet = S['wet'].astype(bool); h = S['h'].astype(float)
    thin = wet & (h < 0.3)
    film = block_cover(thin)
    wide = block_cover(wet); one = wet & ~wide
    act = active(wet)
    Qg = S['Qgross'].astype(float); Cm = S['Cmean'].astype(float)
    vein = [act[k] & (Cm[k] > 4) for k in range(4)]
    qv = np.concatenate([Qg[k][vein[k]] for k in range(4)])
    if qv.size < 10: qv = np.concatenate([Qg[k][act[k]] for k in range(4)]); ref = 'all'
    else: ref = 'vein'
    qref = float(np.percentile(qv, 90)) if qv.size else 0.0
    qc = incident_max(Qg, act); cc = incident_max(Cm, act)
    dead = one & (qc < 0.01 * qref)
    deadC = one & (cc < 0.5)
    ends, _ = prune_ends(wet)
    area = int(wet.sum())
    return dict(t=float(S['t']), area=area, film=int(film.sum()), dead=int(dead.sum()), deadC=int(deadC.sum()), endline=int(ends.sum()), onewide=int(one.sum()),
                qref=qref, qref_from=ref)


def load_vs(run_dir):
    fs = sorted(glob.glob(os.path.join(run_dir, 'vs_t*.npz')))
    for f in fs:
        Z = np.load(f)
        yield {k: Z[k] for k in Z.files}


def run_dir(scn, seed, tag):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'model', 'runs', f'b_{scn}_s{seed}_{tag}')
