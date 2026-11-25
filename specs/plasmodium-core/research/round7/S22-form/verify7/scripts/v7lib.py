"""verify7 측정 도구 (검증자가 새로 쓴 것. 모델 코드를 가져다 쓰지 않는다).

배열은 모델과 같이 [y, x] 로 놓는다. 이웃 방향 d = (dx, dy).
모든 위상(연결 성분, 열림, 거리)은 토러스(주기 경계)로 잰다.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import ConvexHull

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]                       # 모델의 간선 채널 순서 (Qgross[k] 는 셀에서 d_k 쪽 이웃으로 가는 간선)
ALL8 = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0)]
DISC3 = [(dx, dy) for dy in range(-3, 4) for dx in range(-3, 4) if dx * dx + dy * dy <= 9]

# ---- 기준 문서(CRITERIA.md 2절)의 문턱값. 여기 값이 곧 등록된 정의다 ----
CRUMB_VOL = 0.02        # 부스러기: 가장 큰 몸이 아닌 성분 가운데 부피 < 2% (전체 부피 대비)
FRAG_VOL = 0.10         # 조각: 2% 이상 10% 미만
LOBE_EDT = 3.0          # 굵은 덩이의 속(core): 마른 셀까지 유클리드 거리 >= 3 (폭 5칸 이상)
LOBE_R = 3.0            # 덩이 영역 = 속에서 거리 <= 3 안의 몸 셀
LOBE_MIN = 0.10         # 덩이: 그 몸 부피의 10% 이상
BODY_MIN_LOBE = 0.10    # 아령 판정을 하는 몸: 전체 부피의 10% 이상
CORE_AREA = 20          # 큰 속(3x3 열림 성분): 넓이 >= 20 셀
CORE_VOL = 0.05         #                    그리고 부피 >= 전체의 5%
STRAND_W = 4.0          # 외가닥다움: 넓이 / 길이 <= 4 (평균 폭 4칸 이하)
TAIL_L = 30.0           # 긴 꼬리: 길이 >= 30 셀
FAR_L = 100.0           # 멀리 뻗은 외가닥: 길이 > 100 셀
THIN_COMP = 5           # 실 셀(3x3 열림에서 빠진 셀) 성분 가운데 5 셀 이상만 '실'로 본다 (가장자리 돌기 제외)
DEAD_FRAC = 0.10        # 흐름 없음: 셀 유량 < 0.1 x (큰 속 셀 유량의 중앙값)
FILM_H = 0.3            # 얇은 막: 폭 3 이상 영역에서 한 주기 평균 두께 < 0.3
BODY7 = 0.03            # 균핵 판정 대상 몸: 전체 부피의 3% 이상
BREAK7 = 0.02           # 부서짐 계수: 전체 부피의 2% 이상인 몸의 수
COMPACT_CORE = 0.90     # 한 덩어리: 가장 큰 3x3 열림 성분이 몸 부피의 90% 이상
COMPACT_THIN = 0.05     #            실 셀 부피 <= 5%
COMPACT_TAIL = 10.0     #            몸에 붙은 외가닥 길이 < 10


def nb(a, d):
    """a 의 d=(dx,dy) 쪽 이웃 값: nb(a,d)[y,x] = a[y+dy, x+dx] (토러스)"""
    return np.roll(a, (-d[1], -d[0]), (0, 1))


def rev(a, d):
    """간선 배열에서 -d 쪽 이웃이 가진 간선 (이 셀로 들어오는 간선)"""
    return np.roll(a, (d[1], d[0]), (0, 1))


def mimg(v, N):
    return (v + N / 2) % N - N / 2


def torus_label(mask):
    """8-연결 성분 (토러스). 0 = 바탕, 1..n"""
    mask = np.asarray(mask, bool)
    N0, N1 = mask.shape
    lab, n = ndi.label(mask, structure=np.ones((3, 3), int))
    if n == 0:
        return lab, 0
    pairs = []
    for s in (-1, 0, 1):
        a = lab[0, :]; b = np.roll(lab[N0 - 1, :], -s); m = (a > 0) & (b > 0); pairs.append(np.stack([a[m], b[m]], 1))
        a = lab[:, 0]; b = np.roll(lab[:, N1 - 1], -s); m = (a > 0) & (b > 0); pairs.append(np.stack([a[m], b[m]], 1))
    P = np.concatenate(pairs)
    if P.size == 0:
        return lab, n
    g = coo_matrix((np.ones(len(P)), (P[:, 0], P[:, 1])), shape=(n + 1, n + 1))
    _, cl = connected_components(g, directed=False)
    _, newid = np.unique(cl[1:], return_inverse=True)
    mp = np.concatenate([[0], newid + 1])
    return mp[lab], int(newid.max() + 1)


def open3(mask):
    """3x3 정사각 열림 (토러스): 3x3 이 통째로 들어가는 곳들의 합집합. 폭 2 이하 구조가 빠진다"""
    e = mask.copy()
    for d in ALL8:
        e &= nb(mask, d)
    o = e.copy()
    for d in ALL8:
        o |= nb(e, d)
    return o & mask


def edt_torus(mask, pad=8, return_nearest=False):
    """mask 안의 셀에서 mask 밖(False) 셀까지의 유클리드 거리 (토러스). pad 보다 먼 값은 pad 이상으로만 믿는다.
    return_nearest: 가장 가까운 False 셀의 (y, x) 좌표도 돌려준다 (토러스로 접은 좌표)"""
    N0, N1 = mask.shape
    P = np.pad(mask, pad, mode='wrap')
    if return_nearest:
        d, ind = ndi.distance_transform_edt(P, return_indices=True)
        iy = (ind[0] - pad) % N0; ix = (ind[1] - pad) % N1
        return d[pad:-pad, pad:-pad], iy[pad:-pad, pad:-pad], ix[pad:-pad, pad:-pad]
    d = ndi.distance_transform_edt(P)
    return d[pad:-pad, pad:-pad]


def n_wet_nb(wet):
    c = np.zeros(wet.shape, np.int16)
    for d in ALL8:
        c += nb(wet, d)
    return c


def node_flow(Qg, wet):
    """셀 유량 = 그 셀에 닿은 (양 끝이 젖은) 간선의 한 창(20 시간) 평균 |Q| 가운데 가장 큰 값"""
    F = np.zeros(wet.shape)
    for k, d in enumerate(DIRS):
        act = wet & nb(wet, d)
        q = np.where(act, np.abs(Qg[k]), 0.0)
        F = np.maximum(F, np.maximum(q, rev(q, d)))
    return np.where(wet, F, 0.0)


def geo_diameter(cells, N0, N1):
    """셀 집합(평탄 index)의 측지 지름 (8-이웃, 1 / sqrt2 걸음, 두 번 훑기) + 1 (셀 하나 = 1)"""
    n = cells.size
    if n <= 1:
        return float(n)
    loc = -np.ones(N0 * N1, np.int64); loc[cells] = np.arange(n)
    ys, xs = np.divmod(cells, N1)
    R = []; C = []; W = []
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        nbr = ((ys + dy) % N0) * N1 + (xs + dx) % N1
        j = loc[nbr]; m = j >= 0
        R.append(np.arange(n)[m]); C.append(j[m]); W.append(np.full(m.sum(), np.sqrt(2.0) if dx and dy else 1.0))
    R = np.concatenate(R); C = np.concatenate(C); W = np.concatenate(W)
    g = coo_matrix((W, (R, C)), shape=(n, n)).tocsr()
    d0 = dijkstra(g, directed=False, indices=0)
    d0[~np.isfinite(d0)] = -1
    u = int(np.argmax(d0))
    d1 = dijkstra(g, directed=False, indices=u)
    d1[~np.isfinite(d1)] = -1
    return float(d1.max()) + 1.0


def unwrap_coords(ys, xs, N):
    """몸 셀 좌표를 원형 평균 중심(정수로 반올림) 둘레로 펼친다. 돌려주는 ux, uy 는 정수 오프셋"""
    ang = 2 * np.pi / N
    cx = (np.angle(np.exp(1j * xs * ang).mean()) / ang) % N
    cy = (np.angle(np.exp(1j * ys * ang).mean()) / ang) % N
    cxi = int(round(cx)) % N; cyi = int(round(cy)) % N
    ux = (xs - cxi + N // 2) % N - N // 2; uy = (ys - cyi + N // 2) % N - N // 2
    return ux, uy, cxi, cyi


def shape_desc(bm, h):
    """한 몸(bm: bool 마스크)의 모양: 넓이, 부피, 둘레(4-경계 간선 x pi/4), 정규 둘레 Pn (원판 = 1), 볼록 껍질 대비 넓이(solidity),
    구멍 넓이, 같은 넓이 원판과의 IoU, 펼친 폭(extent)"""
    N0, N1 = bm.shape
    ys, xs = np.nonzero(bm)
    A = int(ys.size)
    out = dict(area=A, vol=float(np.maximum(h[bm], 0).sum()))
    if A == 0:
        return out
    E = 0
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        E += int((bm & ~nb(bm, d)).sum())
    Pc = E * np.pi / 4
    out['Pn'] = float(Pc / (2 * np.sqrt(np.pi * A)))
    ux, uy, cx, cy = unwrap_coords(ys, xs, N0)
    out['extent'] = float(max(ux.max() - ux.min(), uy.max() - uy.min()) + 1)
    out['cen'] = [float((cx + ux.mean()) % N0), float((cy + uy.mean()) % N0)]
    # 펼친 국소 영상
    x0 = int(ux.min()) - 2; y0 = int(uy.min()) - 2
    W_ = int(ux.max()) - x0 + 3; H_ = int(uy.max()) - y0 + 3
    img = np.zeros((H_, W_), bool); img[uy - y0, ux - x0] = True
    filled = ndi.binary_fill_holes(img)
    out['holes'] = int(filled.sum() - img.sum())
    if A >= 3:
        pts = np.concatenate([np.stack([ux + sx, uy + sy], 1) for sx in (-0.5, 0.5) for sy in (-0.5, 0.5)])
        try:
            out['solidity'] = float(A / ConvexHull(pts).volume)
        except Exception:
            out['solidity'] = 1.0
    else:
        out['solidity'] = 1.0
    # 같은 넓이 원판(넓이 중심)과의 IoU
    mx = ux.mean(); my = uy.mean(); r = np.sqrt(A / np.pi)
    gy, gx = np.mgrid[0:H_, 0:W_]; gx = gx + x0; gy = gy + y0
    disc = np.hypot(gx - mx, gy - my) <= r
    out['disc_iou'] = float((disc & img).sum() / max((disc | img).sum(), 1))
    return out


def strands(wet, h, lab, vol_comp, Vtot):
    """외가닥 분석. 큰 속 = 3x3 열림 성분 가운데 넓이 >= 20 이고 부피 >= 전체의 5%. 나머지 젖은 셀의 성분 = '가닥 후보'.
    각 후보: 길이 L(측지 지름), 넓이, 외가닥다움(넓이/L <= 4), 큰 속과의 닿음 묶음 수, 닿은 큰 속 수 -> 종류
      free (안 닿음) / tail (한 곳) / loop (같은 속에 두 곳 이상) / trunk (서로 다른 큰 속 둘 이상: 굵은 부분끼리 잇는 관)"""
    N0, N1 = wet.shape
    o = open3(wet)
    ol, on = torus_label(o)
    hp = np.maximum(h, 0.0)
    oa = np.bincount(ol.ravel(), minlength=on + 1); ov = np.bincount(ol.ravel(), weights=np.where(o, hp, 0).ravel(), minlength=on + 1)
    bigc = (oa >= CORE_AREA) & (ov >= CORE_VOL * Vtot); bigc[0] = False
    core_lab = np.where(bigc[ol], ol, 0)
    core = core_lab > 0
    rest = wet & ~core
    sl, sn = torus_label(rest)
    # 닿음
    touch = np.zeros(wet.shape, bool); touched_ids = []
    for d in ALL8:
        v = nb(core_lab, d)
        m = rest & (v > 0)
        touch |= m
        touched_ids.append((sl[m], v[m]))
    pairs = np.unique(np.concatenate([np.stack(p, 1) for p in touched_ids]), axis=0) if any(p[0].size for p in touched_ids) else np.zeros((0, 2), int)
    tl, tn = torus_label(touch)
    clus = np.unique(np.stack([sl[touch], tl[touch]], 1), axis=0) if tn else np.zeros((0, 2), int)
    ncl = np.bincount(clus[:, 0], minlength=sn + 1) if clus.size else np.zeros(sn + 1, int)
    ncore = np.bincount(pairs[:, 0], minlength=sn + 1) if pairs.size else np.zeros(sn + 1, int)
    area = np.bincount(sl.ravel(), minlength=sn + 1)
    flat = sl.ravel()
    order = np.argsort(flat, kind='stable'); fs = flat[order]; starts = np.searchsorted(fs, np.arange(sn + 2))
    res = []
    for s in range(1, sn + 1):
        a = int(area[s])
        if a < 3:
            continue
        cells = order[starts[s]:starts[s + 1]]
        L = geo_diameter(cells, N0, N1)
        kind = 'free' if ncl[s] == 0 else ('trunk' if ncore[s] >= 2 else ('tail' if ncl[s] == 1 else 'loop'))
        res.append(dict(id=s, area=a, L=L, strand=bool(a / L <= STRAND_W), kind=kind, body=int(lab.ravel()[cells[0]]),
                        vol=float(hp.ravel()[cells].sum())))
    return res, core, o


def frame_measures(wet, h, Qg=None, hmean=None, with_shapes=True):
    """한 장면(저장 상태 하나)의 측정값 모음. CRITERIA.md 2절의 정의를 그대로 따른다"""
    N0, N1 = wet.shape
    wet = np.asarray(wet, bool); h = np.asarray(h, float)
    hp = np.where(wet, np.maximum(h, 0.0), 0.0)
    out = dict(area=int(wet.sum()), V=float(hp.sum()), hmin_wet=float(h[wet].min()) if wet.any() else 0.0, Vraw=float(np.where(wet, h, 0).sum()))
    if not wet.any():
        return out, None
    Vtot = out['V']
    lab, n = torus_label(wet)
    vol = np.bincount(lab.ravel(), weights=hp.ravel(), minlength=n + 1); vol[0] = -1
    area = np.bincount(lab.ravel(), minlength=n + 1)
    big = int(np.argmax(vol))
    others = [k for k in range(1, n + 1) if k != big]
    vf = vol / max(Vtot, 1e-300)
    out['n_comp'] = n
    out['n_crumb'] = int(sum(vf[k] < CRUMB_VOL for k in others))
    out['crumb_area'] = int(sum(area[k] for k in others if vf[k] < CRUMB_VOL))
    out['crumb_vol'] = float(sum(vf[k] for k in others if vf[k] < CRUMB_VOL))
    out['n_frag'] = int(sum(CRUMB_VOL <= vf[k] < FRAG_VOL for k in others))
    out['n_ge10'] = int((vf[1:] >= 0.10).sum()); out['n_ge3'] = int((vf[1:] >= BODY7).sum()); out['n_ge2'] = int((vf[1:] >= BREAK7).sum())
    out['largest_vol'] = float(vf[big])
    # ---- 아령: 폭 기준 덩이 ----
    edt = edt_torus(wet)
    core5 = wet & (edt >= LOBE_EDT)
    cl, cn = torus_label(core5)
    dumb = 0; lobes_all = []
    if cn:
        dist, iy, ix = edt_torus(~core5, return_nearest=True)       # 속까지의 거리와 가장 가까운 속 셀
        near = cl[iy, ix]
        reg = wet & (dist <= LOBE_R)
        lv = np.bincount(np.where(reg, near, 0).ravel(), weights=np.where(reg, hp, 0).ravel(), minlength=cn + 1); lv[0] = 0
        cbody = np.zeros(cn + 1, int); cbody[cl[core5]] = lab[core5]
        for b in range(1, n + 1):
            if vf[b] < BODY_MIN_LOBE:
                continue
            ks = [k for k in range(1, cn + 1) if cbody[k] == b and lv[k] >= LOBE_MIN * vol[b]]
            lobes_all.append(len(ks))
            if len(ks) >= 2:
                dumb += 1
    out['n_dumbbell_bodies'] = dumb; out['lobes'] = lobes_all
    # 두께 기준(참고): h >= 0.6 인 성분 가운데 그 몸 부피의 10% 이상인 것
    th = wet & (h >= 0.6); tl, tn = torus_label(th); dumb_h = 0
    if tn:
        tv = np.bincount(tl.ravel(), weights=np.where(th, hp, 0).ravel(), minlength=tn + 1); tb = np.zeros(tn + 1, int); tb[tl[th]] = lab[th]
        for b in range(1, n + 1):
            if vf[b] < BODY_MIN_LOBE:
                continue
            if sum(1 for k in range(1, tn + 1) if tb[k] == b and tv[k] >= LOBE_MIN * vol[b]) >= 2:
                dumb_h += 1
    out['n_dumbbell_h'] = dumb_h
    # ---- 외가닥 ----
    st, core, o = strands(wet, h, lab, vol, Vtot)
    S_ = [s for s in st if s['strand']]
    tails = [s['L'] for s in S_ if s['kind'] == 'tail']
    far = [s['L'] for s in S_ if s['kind'] in ('tail', 'loop', 'free')]
    trunks = [s['L'] for s in S_ if s['kind'] == 'trunk']
    out['max_tail_L'] = float(max(tails, default=0.0)); out['n_tail30'] = int(sum(L >= TAIL_L for L in tails))
    out['max_far_L'] = float(max(far, default=0.0)); out['n_far100'] = int(sum(L > FAR_L for L in far))
    out['far100_kinds'] = sorted(set(s['kind'] for s in S_ if s['kind'] != 'trunk' and s['L'] > FAR_L))
    out['max_trunk_L'] = float(max(trunks, default=0.0)); out['n_trunk'] = len(trunks); out['n_trunk100'] = int(sum(L > FAR_L for L in trunks))
    # ---- 죽은 구조 ----
    thin = wet & ~o
    thl, thn = torus_label(thin)
    tsz = np.bincount(thl.ravel(), minlength=thn + 1)
    thread = thin & (tsz[thl] >= THIN_COMP)
    nwn = n_wet_nb(wet)
    tips = wet & (nwn == 1)
    hm = np.where(hmean > 0, hmean, h) if hmean is not None else h          # 한 주기 평균 두께 (그 주기 내내 젖어 있지 않던 셀은 지금 두께)
    film = o & (hm < FILM_H)
    out['thread_frac'] = float(thread.sum() / out['area']); out['film_frac'] = float(film.sum() / out['area']); out['n_tips'] = int(tips.sum())
    if Qg is not None:
        F = node_flow(Qg, wet)
        ref_cells = core if core.any() else wet
        Fref = float(np.median(F[ref_cells]))
        out['Fref'] = Fref; out['F_q'] = [float(v) for v in np.percentile(F[wet], [5, 25, 50, 75, 95])]
        for tag, fr in (('', DEAD_FRAC), ('_s05', 0.05), ('_s20', 0.20)):
            dead = F < fr * Fref
            out['dead_thread_frac' + tag] = float((thread & dead).sum() / out['area'])
            out['dead_tips' + tag] = int((tips & dead).sum())
    if with_shapes:
        bods = []
        for b in range(1, n + 1):
            if vf[b] < BODY7:
                continue
            bm = lab == b
            d = shape_desc(bm, h)
            d['vfrac'] = float(vf[b])
            olb, onb = torus_label(o & bm)
            if onb:
                ovb = np.bincount(olb.ravel(), weights=np.where(o & bm, hp, 0).ravel(), minlength=onb + 1); ovb[0] = 0
                d['core_share'] = float(ovb.max() / max(vol[b], 1e-300))
            else:
                d['core_share'] = 0.0
            d['thin_share'] = float(hp[bm & ~o].sum() / max(vol[b], 1e-300))
            d['max_strand_L'] = float(max([s['L'] for s in S_ if s['body'] == b and s['kind'] != 'trunk'], default=0.0))
            d['compact'] = bool(d['core_share'] >= COMPACT_CORE and d['thin_share'] <= COMPACT_THIN and d['max_strand_L'] < COMPACT_TAIL)
            hb = hm[bm]; ei = edt[bm] >= 2
            d['h_cv'] = float(hb.std() / max(hb.mean(), 1e-12)); d['h_p90_p10'] = float(np.percentile(hb, 90) / max(np.percentile(hb, 10), 1e-12))
            if ei.sum() >= 10:
                hi = hb[ei]; d['h_cv_int'] = float(hi.std() / max(hi.mean(), 1e-12)); d['h_p90_p10_int'] = float(np.percentile(hi, 90) / max(np.percentile(hi, 10), 1e-12))
            else:
                d['h_cv_int'] = None; d['h_p90_p10_int'] = None
            bods.append(d)
        out['bodies'] = sorted(bods, key=lambda d: -d['vol'])
    return out, lab
