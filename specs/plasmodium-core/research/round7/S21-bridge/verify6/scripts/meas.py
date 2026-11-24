#!/usr/bin/env python3
"""verify6 측정 함수 (한 장면 = vs_t*.npz 하나).

모델 코드와 따로 새로 짠 것이다. 토러스(주기 경계) 위에서 8-이웃 연결로 잰다.
모든 정의는 ../CRITERIA.md 의 '측정 정의' 절과 같다. 값을 바꾸면 기준이 바뀐 것이다.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

# ---- 기준에 묶인 상수 (CRITERIA.md 와 같아야 한다) ----
DEBRIS_VFRAC = 0.01      # 부스러기: 전체 부피의 1% 미만인 떨어진 조각
BODY_VFRAC = 0.20        # 아령 판정 대상 몸: 전체 부피의 20% 이상
SPLIT_VFRAC = 0.10       # 분열: 전체 부피의 10% 이상인 조각이 둘 이상
LUMP_SIGMA = 1.5         # 덩이: 두께를 sigma 1.5 칸으로 흐린 값이
LUMP_REL = 0.5           #       그 몸의 흐린 두께 99백분위의 0.5배 이상인 곳
LUMP_VFRAC = 0.10        #       큰 덩이 = 그 몸 부피의 10% 이상
NECK_OPEN = 5            # 아령의 목: 5x5 열림(폭 4칸 이하 제거) 뒤 두 덩이가 갈라지면 '가는 목'
THREAD_OPEN = 3          # 실: 3x3 열림에서 지워지는 칸(폭 2칸 이하)
THREAD_MIN = 4           # 실 덩어리 최소 칸 수
DEAD_REL = 0.1           # 흐름 없음: 칸 흐름 < 0.1 x (몸의 성숙 칸 흐름 중앙값)
MATURE_AGE = 20.0        # 성숙 칸: age >= 20 (흐름 창 20 시간 내내 젖어 있던 칸)
FILM_H = 0.35            # 얇은 막: 두께 < 0.35 인 성숙한 판 칸(3x3 열림에 남는 칸)이
FILM_MIN = 20            #          20칸 이상 이어진 것
TIP_END = 3              # 가지 끝: 꼬리 실의 붙은 곳에서 가장 먼 3칸
LONG_L = 25.0            # 긴 실: 측지 길이 25칸 이상 (보고용 40, 60)
SCL_VFRAC = 0.05         # 균핵 판정 대상 조각: 전체 부피 5% 이상

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]


def nb(a, d):
    """a 를 방향 d=(dx,dy) 의 이웃에서 읽는다: out[y,x] = a[y+dy, x+dx] (토러스)"""
    return np.roll(a, (-d[1], -d[0]), (0, 1))


def tlabel(mask):
    """토러스 8-연결 라벨. 0 = 배경, 1..n. (라벨 번호, n) 을 돌려준다."""
    mask = np.asarray(mask, bool)
    lab, n = ndi.label(mask, structure=np.ones((3, 3), int))
    if n == 0:
        return lab, 0
    a_ = []; b_ = []
    for d in (-1, 0, 1):
        a = lab[:, 0]; b = np.roll(lab[:, -1], -d)      # (i,0) 와 (i+d, N-1)
        m = (a > 0) & (b > 0); a_.append(a[m]); b_.append(b[m])
        a = lab[0, :]; b = np.roll(lab[-1, :], -d)      # (0,i) 와 (N-1, i+d)
        m = (a > 0) & (b > 0); a_.append(a[m]); b_.append(b[m])
    a_ = np.concatenate(a_); b_ = np.concatenate(b_)
    g = coo_matrix((np.ones(a_.size), (a_, b_)), shape=(n + 1, n + 1))
    nc, cl = connected_components(g, directed=False)
    # 배경(0)이 0 이 되도록 번호를 다시 매긴다
    order = {}
    newid = np.zeros(n + 1, np.int64)
    k = 0
    for i in range(1, n + 1):
        c = cl[i]
        if c not in order:
            k += 1; order[c] = k
        newid[i] = order[c]
    return newid[lab], k


def opening(mask, k):
    """k x k 정사각 열림 (토러스). k x k 블록이 들어가지 않는 폭의 부분이 지워진다."""
    m = np.asarray(mask, np.uint8)
    er = ndi.minimum_filter(m, size=k, mode='wrap')
    return ndi.maximum_filter(er, size=k, mode='wrap').astype(bool) & np.asarray(mask, bool)


def dilate8(mask):
    return ndi.maximum_filter(np.asarray(mask, np.uint8), size=3, mode='wrap').astype(bool)


def cell_flow(Qg, wet):
    """칸의 흐름 = 그 칸에 닿는 8 간선의 창 평균 |Q| (Qgross) 중 최대"""
    fl = np.zeros(wet.shape)
    for k, d in enumerate(DIRS):
        q = np.where(wet & nb(wet, d), Qg[k], 0.0)
        fl = np.maximum(fl, q)
        fl = np.maximum(fl, np.roll(q, (d[1], d[0]), (0, 1)))     # 이웃 (y-dy, x-dx) 에서 들어오는 간선
    return np.where(wet, fl, 0.0)


def _graph(mask):
    """mask 칸들의 8-이웃 그래프 (토러스, 가중치 1 또는 sqrt2). (csr, 칸 번호 배열 idx[N,N], 칸 수)"""
    N0, N1 = mask.shape
    idx = -np.ones(mask.shape, np.int64); n = int(mask.sum()); idx[mask] = np.arange(n)
    rows = []; cols = []; w = []
    for d in DIRS:
        nbi = nb(idx, d); m = mask & (nbi >= 0)
        rows.append(idx[m]); cols.append(nbi[m]); w.append(np.full(int(m.sum()), 1.0 if 0 in d else np.sqrt(2.0)))
    if n == 0:
        return csr_matrix((0, 0)), idx, 0
    r = np.concatenate(rows); c = np.concatenate(cols); ww = np.concatenate(w)
    g = coo_matrix((np.concatenate([ww, ww]), (np.concatenate([r, c]), np.concatenate([c, r]))), shape=(n, n)).tocsr()
    return g, idx, n


def circ_center(mask, wgt=None):
    """토러스 위 원형 평균으로 잰 무게중심 (x, y)"""
    N = mask.shape[0]; ys, xs = np.nonzero(mask)
    w = np.ones(ys.size) if wgt is None else wgt[mask]
    a = 2 * np.pi / N
    cx = (np.arctan2((w * np.sin(xs * a)).sum(), (w * np.cos(xs * a)).sum()) / a) % N
    cy = (np.arctan2((w * np.sin(ys * a)).sum(), (w * np.cos(ys * a)).sum()) / a) % N
    return cx, cy


def centered(mask, cx, cy):
    """(cx, cy) 가 배열 가운데 오도록 굴린다 (조각이 경계에 걸리지 않게)"""
    N = mask.shape[0]
    sx = int(round(N / 2 - cx)); sy = int(round(N / 2 - cy))
    return np.roll(mask, (sy, sx), (0, 1)), (sx, sy)


def shape_measures(cm, h=None):
    """조각 하나(토러스 마스크)의 모양: 넓이, 볼록 껍질 대비 꽉 참(solidity), 둘레 비(=1 원판), 길쭉함, 반지름 변이, 원판 IoU, 두께 CV"""
    from skimage.measure import perimeter_crofton
    from skimage.morphology import convex_hull_image
    N = cm.shape[0]
    cx, cy = circ_center(cm)
    m, _ = centered(cm, cx, cy)
    ys, xs = np.nonzero(m); A = int(m.sum())
    out = dict(area=A)
    if A < 5:
        return out
    wraps = (ys.max() - ys.min() >= N - 2) or (xs.max() - xs.min() >= N - 2)
    out['wraps'] = bool(wraps)
    hull = convex_hull_image(m)
    out['solidity'] = float(A / max(hull.sum(), 1))
    P = float(perimeter_crofton(m, directions=4))
    out['iso'] = float(P / (2 * np.sqrt(np.pi * A)))
    holes = ndi.binary_fill_holes(m) & ~m
    out['hole_frac'] = float(holes.sum() / A)
    mx = xs.mean(); my = ys.mean()
    cov = np.cov(np.vstack([xs - mx, ys - my]))
    ev = np.sort(np.linalg.eigvalsh(cov))
    out['aspect'] = float(np.sqrt(ev[1] / max(ev[0], 1e-9)))
    # 반지름 변이: 무게중심에서 36 방향 칸막이마다 가장 먼 칸의 거리
    ang = np.arctan2(ys - my, xs - mx); rr = np.hypot(ys - my, xs - mx)
    bi = ((ang + np.pi) / (2 * np.pi) * 36).astype(int) % 36
    rmax = np.zeros(36); np.maximum.at(rmax, bi, rr + 0.5)
    out['radial_cv'] = float(rmax.std() / max(rmax.mean(), 1e-9))
    # 같은 넓이·같은 중심 원판과의 IoU
    jj, ii = np.mgrid[0:N, 0:N]
    D = np.hypot(ii - mx, jj - my) <= np.sqrt(A / np.pi)
    out['disc_iou'] = float((m & D).sum() / max((m | D).sum(), 1))
    if h is not None:
        hc = np.roll(h, (int(round(N / 2 - cy)), int(round(N / 2 - cx))), (0, 1))[m]
        out['h_cv'] = float(hc.std() / max(hc.mean(), 1e-12))
        med = float(np.median(hc)); out['h_within10'] = float((np.abs(hc - med) <= 0.1 * med).mean())
        out['h_p10_p90_over_med'] = float((np.percentile(hc, 90) - np.percentile(hc, 10)) / max(med, 1e-12))
    return out


def lumps_of(comp, h, g):
    """몸 하나(comp 마스크)의 큰 덩이 목록: (덩이 마스크, 부피)"""
    gv = g[comp]
    thr = LUMP_REL * np.percentile(gv, 99)
    L = comp & (g >= thr)
    lab, n = tlabel(L)
    Vc = float(h[comp].sum())
    if n == 0:
        return []
    vol = np.bincount(lab.ravel(), weights=np.where(L, h, 0.0).ravel(), minlength=n + 1)
    return [(lab == i, float(vol[i])) for i in range(1, n + 1) if vol[i] >= LUMP_VFRAC * Vc]


def threads(wet, sheet, fl, qdead, k=THREAD_OPEN):
    """폭이 좁은 부분(k x k 열림에서 지워지는 칸)의 덩어리마다: 칸 수, 측지 길이, 붙은 곳 수, 흐름, 끝의 흐름"""
    thr = wet & ~sheet
    lab, n = tlabel(thr)
    res = []
    if n == 0:
        return res, thr
    cnt = np.bincount(lab.ravel(), minlength=n + 1)
    g, idx, nn = _graph(thr)
    for i in range(1, n + 1):
        if cnt[i] < THREAD_MIN:
            continue
        cm = lab == i
        nodes = idx[cm]
        # 측지 길이: 두 번 훑기
        d0 = dijkstra(g, indices=int(nodes[0]))
        far = nodes[np.argmax(np.where(np.isfinite(d0[nodes]), d0[nodes], -1))]
        d1 = dijkstra(g, indices=int(far))
        L = float(np.max(d1[nodes][np.isfinite(d1[nodes])]))
        att = dilate8(cm) & sheet
        _, na = tlabel(att)
        # 실의 흐름
        flc = fl[cm]
        r = dict(cells=int(cnt[i]), length=L, n_attach=int(na), fl_med=float(np.median(flc)), dead=bool(np.median(flc) < qdead))
        if na == 1:
            # 붙은 곳에 닿은 실 칸에서 잰 거리: 가장 먼 TIP_END 칸이 가지 끝
            src = cm & dilate8(att)
            ds = dijkstra(g, indices=idx[src].astype(int), min_only=True)
            dn = ds[nodes]; fin = np.isfinite(dn)
            if fin.any():
                dmax = dn[fin].max()
                endsel = fin & (dn >= dmax - (TIP_END - 1))
                r['tip_fl_max'] = float(flc[endsel].max())
                r['dead_tip'] = bool(r['tip_fl_max'] < qdead)
        res.append(r)
    return res, thr


RING8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]      # 한 칸 둘레를 도는 순서


def crossing(K):
    """8-고리를 한 바퀴 돌며 빈칸→찬칸 넘어감 수 (1 = 끝점, 2 = 줄 위, 3 이상 = 갈림점)"""
    nbv = [nb(K, d) for d in RING8]
    cn = np.zeros(K.shape, np.int8)
    for q in range(8):
        cn += (~nbv[q] & nbv[(q + 1) % 8]).astype(np.int8)
    return np.where(K, cn, 0)


def skeleton_torus(T):
    from skimage.morphology import skeletonize
    p = 12; Tp = np.pad(T, p, mode='wrap')
    return skeletonize(Tp)[p:-p, p:-p] & T


def strands(T, sheet, fl, qdead):
    """[CRITERIA_CHANGES 1] 실 칸(T)의 뼈대를 갈림점에서 끊은 외가닥 조각마다: 길이, 닿는 곳 수(판·갈림점), 끝의 흐름.
    뼈대의 끝점 가운데 판에 닿지 않는 것을 두 번 깎아(2칸 이하 잔가지 없앰) 갈림점(넘어감 수 >= 3)을 찾고,
    깎지 않은 뼈대에서 갈림점 3x3 을 뺀 나머지의 8-연결 덩어리가 외가닥 조각이다."""
    K = skeleton_torus(T)
    near_sheet = dilate8(sheet)
    Kp = K.copy()
    for _ in range(2):
        cn = crossing(Kp); Kp &= ~((cn <= 1) & ~near_sheet)
    J = Kp & (crossing(Kp) >= 3)
    Jd = dilate8(J)
    Sg = K & ~Jd
    lab, n = tlabel(Sg)
    res = []
    if n == 0:
        return res
    cnt = np.bincount(lab.ravel(), minlength=n + 1)
    g, idx, nn = _graph(Sg)
    contact_mask = sheet | (Jd & ~K) | J
    for i in range(1, n + 1):
        if cnt[i] < 2:
            continue
        cm = lab == i; nodes = idx[cm]
        d0 = dijkstra(g, indices=int(nodes[0])); far = nodes[np.argmax(np.where(np.isfinite(d0[nodes]), d0[nodes], -1))]
        d1 = dijkstra(g, indices=int(far)); L = float(np.max(d1[nodes][np.isfinite(d1[nodes])])) + 1.0
        ct = dilate8(cm) & ~cm & (contact_mask | (Jd & K))
        _, nc = tlabel(ct)
        r = dict(length=L, contacts=int(nc))
        if nc == 1:
            src = cm & dilate8(ct)
            ds = dijkstra(g, indices=idx[src].astype(int), min_only=True)
            dn = ds[nodes]; fin = np.isfinite(dn)
            if fin.any():
                endsel = fin & (dn >= dn[fin].max() - (TIP_END - 1))
                r['tip_fl_max'] = float(fl[cm][endsel].max()); r['dead_tip'] = bool(r['tip_fl_max'] < qdead)
        res.append(r)
    return res


def frame_measures(S):
    """S: wet, h, age, Qgross, C (npz 에서 읽은 dict). 한 장면의 측정값 dict"""
    wet = S['wet'].astype(bool); h = S['h'].astype(float); age = S['age'].astype(float)
    N = wet.shape[0]
    out = dict(t=float(S['t']), area=int(wet.sum()))
    if not wet.any():
        out['empty'] = True
        return out
    Vt = float(h[wet].sum()); out['V'] = Vt
    # ---- 몸 조각 ----
    lab, n = tlabel(wet)
    vol = np.bincount(lab.ravel(), weights=np.where(wet, h, 0.0).ravel(), minlength=n + 1)[1:]
    area = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    fr = vol / Vt
    out['n_comp'] = int(n)
    out['n_debris'] = int((fr < DEBRIS_VFRAC).sum())
    out['debris_vol_frac'] = float(fr[fr < DEBRIS_VFRAC].sum())
    out['n_debris_small_area'] = int(((fr < DEBRIS_VFRAC) & (area <= 30)).sum())
    out['n_big_pieces'] = int((fr >= SPLIT_VFRAC).sum())
    out['split'] = bool((fr >= SPLIT_VFRAC).sum() >= 2)
    out['comp_vfrac'] = sorted([round(float(v), 4) for v in fr], reverse=True)[:6]
    # ---- 흐름 ----
    fl = cell_flow(S['Qgross'], wet)
    mat = wet & (age >= MATURE_AGE)
    fref = float(np.median(fl[mat])) if mat.sum() >= 10 else float(np.median(fl[wet]))
    qdead = DEAD_REL * fref
    out['fl_ref'] = fref
    # ---- 덩이 / 아령 ----
    g = ndi.gaussian_filter(np.where(wet, h, 0.0), LUMP_SIGMA, mode='wrap')
    nd1 = 0; nd2 = 0; lumps_max = 0
    for i in range(n):
        if fr[i] < BODY_VFRAC:
            continue
        comp = lab == (i + 1)
        L = lumps_of(comp, h, g)
        lumps_max = max(lumps_max, len(L))
        if len(L) >= 2:
            nd1 += 1
            op = opening(comp, NECK_OPEN); lo, _ = tlabel(op)
            ids = set()
            for lm, _v in L:
                v = lo[lm]; v = v[v > 0]
                if v.size:
                    ids.add(int(np.bincount(v).argmax()))
            if len(ids) >= 2:
                nd2 += 1
    out['n_big_lumps_max'] = int(lumps_max)
    out['dumbbell_any'] = bool(nd1 > 0)
    out['dumbbell'] = bool(nd2 > 0)
    out['divided'] = bool(nd2 > 0 or out['split'])
    # ---- 실 / 막 / 가지 끝 ----
    sheet3 = opening(wet, THREAD_OPEN)
    th3, thr3 = threads(wet, sheet3, fl, qdead, THREAD_OPEN)
    out['thread_cells'] = int(sum(r['cells'] for r in th3))
    out['dead_thread_cells'] = 0
    # 실 덩어리(>= THREAD_MIN 칸)에 속한 칸만 센다
    if th3:
        lab3, _ = tlabel(thr3); cnt3 = np.bincount(lab3.ravel()); keep3 = cnt3 >= THREAD_MIN; keep3[0] = False
        inthr = keep3[lab3]
        out['dead_thread_cells'] = int((inthr & (fl < qdead)).sum())
        out['dead_thread_cells_rel02'] = int((inthr & (fl < 2 * qdead)).sum())
        out['dead_thread_cells_rel005'] = int((inthr & (fl < 0.5 * qdead)).sum())
    else:
        out['dead_thread_cells_rel02'] = 0; out['dead_thread_cells_rel005'] = 0
    out['n_dead_threads'] = int(sum(1 for r in th3 if r['dead'] and r['length'] >= 5))
    out['n_tips'] = int(sum(1 for r in th3 if r['n_attach'] == 1 and r['length'] >= 3))
    out['n_dead_tips'] = int(sum(1 for r in th3 if r.get('dead_tip') and r['length'] >= 3))
    lens = [r['length'] for r in th3]
    out['thread_maxlen'] = float(max(lens)) if lens else 0.0
    out['n_long25'] = int(sum(1 for L in lens if L >= LONG_L))
    out['n_long40'] = int(sum(1 for L in lens if L >= 40))
    out['n_long60'] = int(sum(1 for L in lens if L >= 60))
    out['n_long25_tail'] = int(sum(1 for r in th3 if r['length'] >= LONG_L and r['n_attach'] <= 1))
    out['n_long25_bridge'] = int(sum(1 for r in th3 if r['length'] >= LONG_L and r['n_attach'] >= 2))
    # [CRITERIA_CHANGES 1] 외가닥 조각 (갈림점에서 끊음)
    st = strands(thr3, sheet3, fl, qdead)
    sl = [r['length'] for r in st]
    out['strand_maxlen'] = float(max(sl)) if sl else 0.0
    for L_ in (25, 40, 60, 96):
        out[f'n_strand{L_}'] = int(sum(1 for L in sl if L >= L_))
    out['n_strand25_tail'] = int(sum(1 for r in st if r['length'] >= LONG_L and r['contacts'] <= 1))
    out['n_strand25_bridge'] = int(sum(1 for r in st if r['length'] >= LONG_L and r['contacts'] >= 2))
    out['n_tips2'] = int(sum(1 for r in st if r['contacts'] == 1 and r['length'] >= 3))
    out['n_dead_tips2'] = int(sum(1 for r in st if r.get('dead_tip') and r['length'] >= 3))
    film = wet & sheet3 & (h < FILM_H) & (age >= MATURE_AGE)
    lf, nf_ = tlabel(film)
    if nf_:
        cf = np.bincount(lf.ravel()); kf = cf >= FILM_MIN; kf[0] = False
        out['film_cells'] = int(kf[lf].sum())
    else:
        out['film_cells'] = 0
    for hh in (0.25, 0.5):
        fm = wet & sheet3 & (h < hh) & (age >= MATURE_AGE); lf2, n2 = tlabel(fm)
        if n2:
            c2 = np.bincount(lf2.ravel()); k2 = c2 >= FILM_MIN; k2[0] = False; out[f'film_cells_h{hh}'] = int(k2[lf2].sum())
        else:
            out[f'film_cells_h{hh}'] = 0
    # 폭 4칸 이하 기준 (보고용)
    sheet5 = opening(wet, 5)
    th5, _ = threads(wet, sheet5, fl, qdead, 5)
    out['thread5_maxlen'] = float(max([r['length'] for r in th5])) if th5 else 0.0
    out['n_long25_w4'] = int(sum(1 for r in th5 if r['length'] >= LONG_L))
    # 관 (보고용)
    C = S['C']
    act = [wet & nb(wet, d) for d in DIRS]
    out['vein_edges'] = int(sum(int(((C[k] > 4.0) & act[k]).sum()) for k in range(4)))
    # ---- 균핵 상태(가) 판정용: 부피 5% 이상인 조각마다 ----
    pieces = []
    for i in range(n):
        if fr[i] < SCL_VFRAC:
            continue
        comp = lab == (i + 1)
        L = lumps_of(comp, h, g)
        tc = int((comp & ~sheet3).sum())
        # 이 조각에 속한 실 덩어리 중 THREAD_MIN 칸 이상
        lab3c, n3c = tlabel(comp & ~sheet3)
        big3 = int((np.bincount(lab3c.ravel())[1:] >= THREAD_MIN).sum()) if n3c else 0
        tc5 = int((comp & ~opening(comp, 5)).sum())
        sm = shape_measures(comp, h)
        pieces.append(dict(vfrac=round(float(fr[i]), 4), n_lumps=len(L), thread_cells=tc, thread_comps=big3, narrow5_frac=float(tc5 / max(area[i], 1)), **sm))
    out['pieces'] = pieces
    out['small_vol_frac'] = float(fr[fr < SCL_VFRAC].sum())
    return out


def scl_state(fm):
    """균핵 상태 S (CRITERIA 7-(가)): 부피 5% 이상인 모든 조각이 큰 덩이 하나, 실 덩어리 없음, 폭 4칸 이하 부분 5% 이하, solidity >= 0.7, 작은 조각 부피 1% 미만"""
    P = fm.get('pieces', [])
    if not P:
        return False
    ok = all(p['n_lumps'] == 1 and p['thread_comps'] == 0 and p['narrow5_frac'] <= 0.05 and p.get('solidity', 0) >= 0.7 for p in P)
    return bool(ok and fm.get('small_vol_frac', 1.0) < 0.01)


def fresh_rim_share(wet, slime_now):
    """몸 둘레의 마른 칸 가운데 점액이 없는 칸의 몫 (모델의 '새 땅' 판정과 같은 뜻)"""
    rim = dilate8(wet) & ~wet
    nr = int(rim.sum())
    if nr == 0:
        return float('nan')
    return float((rim & ~slime_now).sum() / nr)
