#!/usr/bin/env python3
"""verify9 측정 라이브러리. 모델 코드를 쓰지 않고 저장된 상태(vs_t*.npz, metrics.json, series.npz, mg_err_series.json)만 읽는다.

배열은 [y, x] 로 놓이고 토러스로 감긴다. 이웃 nb(a, d)[y, x] = a[y + dy, x + dx].
정의는 verify9/CRITERIA.md 의 '측정 정의' 절과 같다.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.stats import spearmanr

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]                 # 간선 채널 (모델과 같은 순서)
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]               # 8 이웃
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]   # 둘레 순서

# ---- 문턱 (CRITERIA.md 와 같아야 한다) ----
MAIN_FRAC = 0.05        # 주 몸: 전체 부피의 5% 이상인 8-연결 덩이
CRUMB_FRAC = 0.02       # 부스러기: 가장 큰 덩이가 아니고 부피가 전체의 2% 미만인 덩이
Q_FLOW = 0.01           # 흐름 없음: 경계 간선 총 유량(Qgross) < Q_FLOW x 유효 부피 (교환 시간 > 100 시간)
Q_FLOW_SENS = (0.003, 0.03)
H_FLOOR = 0.05          # 유효 부피 = sum max(h, H_FLOOR)
AGE_EVAL = 20.0         # 흐름 판정은 나이 20 이상(유량 창 20 시간보다 오래된) 칸만
LUMP_EDT = 3.0          # 굵은 덩이 = EDT >= 3 (폭 5칸 이상) 칸의 8-연결 덩이
NECK_EDT = 2.0          # 이음 판정: EDT >= 2 (폭 3칸 이상) 칸만으로 이어지지 않으면 '가는 실로만' 이어진 것
LUMP_SHARE = 0.15       # 굵은 덩이로 세는 부피 몫 (그 몸의 15% 이상)
TAIL_MIN = 3            # 꼬리로 세는 최소 칸 수
YOUNG_AGE = 10.0        # 꼬리 나무에 나이 10 미만 칸이 있으면 '자라는 탐색 가지'로 따로 센다


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))     # a[y - dy, x - dx]: -d 쪽 이웃이 가진 간선


def nbcount(m):
    c = np.zeros(m.shape, np.int16)
    for d in ALL: c += nb(m, d)
    return c


def label8(mask):
    """토러스 8-연결 꼬리표. (lab, n): lab 은 0(바깥) 또는 1..n"""
    mask = np.asarray(mask, bool); N0, N1 = mask.shape
    lab, n = ndi.label(mask, structure=np.ones((3, 3), int))
    if n == 0: return lab, 0
    a = []; b = []
    for dy in (-1, 0, 1):
        l = lab[:, 0]; r = np.roll(lab[:, N1 - 1], -dy); m = (l > 0) & (r > 0); a.append(l[m]); b.append(r[m])
        t_ = lab[0, :]; bt = np.roll(lab[N0 - 1, :], -dy); m = (t_ > 0) & (bt > 0); a.append(t_[m]); b.append(bt[m])
    a = np.concatenate(a); b = np.concatenate(b)
    g = coo_matrix((np.ones(a.size), (a, b)), shape=(n + 1, n + 1))
    _, cl = connected_components(g, directed=False)
    u, inv = np.unique(cl[1:], return_inverse=True)
    mp = np.concatenate([[0], inv + 1]).astype(np.int64)
    return mp[lab], int(u.size)


def opening3(wet):
    """3x3 이 모두 젖은 칸을 하나라도 덮는 젖은 칸 (넓은 부분). 나머지 젖은 칸 = 가는 칸"""
    full = wet.copy()
    for d in ALL: full &= nb(wet, d)
    op = full.copy()
    for d in ALL: op |= nb(full, d)
    return op & wet


def edt_torus(wet):
    """젖은 칸에서 가장 가까운 마른 칸 중심까지의 유클리드 거리 (토러스). 마른 칸 0"""
    N0, N1 = wet.shape; m0 = N0 // 2; m1 = N1 // 2
    p = np.pad(wet, ((m0, m0), (m1, m1)), mode='wrap')
    d = ndi.distance_transform_edt(p)[m0:m0 + N0, m1:m1 + N1]
    return np.where(wet, d, 0.0)


def geo_assign(mask, seeds):
    """mask 안에서 씨앗 꼬리표(seeds>0)를 8-이웃 걸음으로 퍼뜨린다 (가까운 씨앗이 이김)"""
    lab = np.where(mask, seeds, 0).astype(np.int64); fr = lab > 0
    while True:
        new = np.zeros_like(lab)
        for d in ALL:
            c = nb(lab, d) * nb(fr, d)
            new = np.where((new == 0) & (c > 0), c, new)
        new = np.where(mask & (lab == 0), new, 0)
        if not new.any(): break
        lab = lab + new; fr = new > 0
    return lab


def geo_dist(mask, src):
    """mask 안에서 src 칸들로부터의 길이 (직교 1, 대각 sqrt2). 닿지 않으면 inf"""
    N0, N1 = mask.shape; idx = -np.ones((N0, N1), np.int64); n = int(mask.sum()); idx[mask] = np.arange(n)
    rows = []; cols = []; vals = []
    for d in DIRS:
        m = mask & nb(mask, d); a = idx[m]; b = nb(idx, d)[m]
        rows.append(a); cols.append(b); vals.append(np.full(a.size, np.sqrt(2.0) if (d[0] and d[1]) else 1.0))
    g = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    s = idx[src & mask]
    out = np.full((N0, N1), np.inf)
    if s.size == 0 or n == 0: return out
    dd = dijkstra(g, directed=False, indices=s, min_only=True)
    out[mask] = dd
    return out


def prune_strict(body):
    """젖은 이웃이 꼭 하나인 칸을 거듭 깎는다. (깎인 칸, 남은 칸)"""
    cur = body.copy(); removed = np.zeros_like(body)
    while True:
        e = cur & (nbcount(cur) == 1)
        if not e.any(): break
        cur &= ~e; removed |= e
    return removed, cur


def ring_runs(m):
    x = [nb(m, d) for d in RING]
    runs = np.zeros(m.shape, np.int16); cnt = np.zeros(m.shape, np.int16)
    for q in range(8): runs += x[q] & ~x[(q + 1) % 8]; cnt += x[q]
    return runs, cnt


def prune_ext(body, thin):
    """가는 칸 가운데 젖은 이웃이 1~3개이고 둘레에서 한 줄로 이어진 칸(끝 칸: 계단꼴·2칸 폭 끝 포함)을 거듭 깎는다"""
    cur = body.copy(); removed = np.zeros_like(body)
    while True:
        r, c = ring_runs(cur)
        e = cur & thin & (c >= 1) & (c <= 3) & (r == 1)
        if not e.any(): break
        cur &= ~e; removed |= e
    return removed, cur


def tail_trees(removed, age):
    """깎인 칸의 8-연결 나무들: 크기와 '어린 칸 있음' 여부"""
    lab, n = label8(removed)
    if n == 0: return np.zeros(0, int), np.zeros(0, bool)
    sz = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    amin = np.full(n + 1, np.inf); np.minimum.at(amin, lab[removed], age[removed])
    return sz, amin[1:] < YOUNG_AGE


def dumbbell(body, h, edt):
    """몸 하나: 굵은 덩이 (EDT>=3 덩이, 몸 부피의 15% 이상) 둘 이상이 폭 3칸 이상 길로 이어지지 않으면 아령"""
    core = body & (edt >= LUMP_EDT); lab, n = label8(core)
    if n < 2: return dict(nlump=n, nbig=min(n, 1), multi=False, db=False)
    asg = geo_assign(body, lab)
    vol = np.bincount(asg.ravel(), weights=np.where(body, np.maximum(h, 0.0), 0.0).ravel(), minlength=n + 1)[1:]
    Vb = max(float(vol.sum()), 1e-12); big = [k + 1 for k in range(n) if vol[k] >= LUMP_SHARE * Vb]
    if len(big) < 2: return dict(nlump=n, nbig=len(big), multi=False, db=False)
    lm, _ = label8(body & (edt >= NECK_EDT))
    comps = set(int(lm[lab == k][0]) for k in big)
    return dict(nlump=n, nbig=len(big), multi=True, db=len(comps) >= 2, shares=sorted([round(float(vol[k - 1] / Vb), 3) for k in big], reverse=True))


def components(wet, h):
    lab, n = label8(wet)
    hp = np.where(wet, np.maximum(h, 0.0), 0.0); V = float(hp.sum())
    vol = np.bincount(lab.ravel(), weights=hp.ravel(), minlength=n + 1); vol[0] = 0.0
    area = np.bincount(lab.ravel(), minlength=n + 1); area[0] = 0
    return lab, n, vol, area, V


def snapshot(wet, h, age, Qg, qs=(Q_FLOW,) + Q_FLOW_SENS):
    """한 상태의 일반 측정 (주장 1, 2, 3, 6 과 '진짜 점균답지 않은 점')"""
    wet = np.asarray(wet, bool); h = np.asarray(h, float); age = np.asarray(age, float); Qg = np.asarray(Qg, float)
    lab, n, vol, area, V = components(wet, h)
    out = dict(area=int(wet.sum()), V=V, ncomp=n)
    if n == 0: return out
    big = int(np.argmax(vol))
    main_ids = [k for k in range(1, n + 1) if vol[k] >= MAIN_FRAC * V] or [big]
    main = np.isin(lab, main_ids)
    crumbs = [k for k in range(1, n + 1) if k != big and vol[k] < CRUMB_FRAC * V]
    mids = [k for k in range(1, n + 1) if k != big and CRUMB_FRAC * V <= vol[k] < MAIN_FRAC * V]
    out.update(nmain=len(main_ids), ncrumb=len(crumbs), crumb_cells=int(sum(area[k] for k in crumbs)), crumb_vol=float(sum(vol[k] for k in crumbs)) / max(V, 1e-12),
               nsmall=len(mids), main_vols=sorted([round(float(vol[k] / V), 4) for k in main_ids], reverse=True))
    # ---- 가는 칸, 흐름 ----
    wide = opening3(wet); thin = wet & ~wide
    act = [wet & nb(wet, d) for d in DIRS]
    Qa = [np.where(act[k], Qg[k], 0.0) for k in range(4)]
    inc = np.zeros(wet.shape)
    for k, d in enumerate(DIRS): inc += Qa[k] + rev(Qa[k], d)
    tl, nt = label8(thin & main)
    res = {q: dict(B_cells=0, B_tips=0) for q in qs}
    allthin_bodies = 0
    if nt > 0:
        Fb = np.zeros(nt + 1)
        for k, d in enumerate(DIRS):
            m1 = thin & main & nb(wide, d)               # 주인 칸이 가늘고 이웃이 넓다
            Fb += np.bincount(tl[m1], weights=Qa[k][m1], minlength=nt + 1)
            m2 = wide & nb(thin & main, d)              # 주인 칸이 넓고 이웃이 가늘다
            Fb += np.bincount(nb(tl, d)[m2], weights=Qa[k][m2], minlength=nt + 1)
        ncell = np.bincount(tl.ravel(), minlength=nt + 1)
        Veff = np.bincount(tl.ravel(), weights=np.where(tl > 0, np.maximum(h, H_FLOOR), 0.0).ravel(), minlength=nt + 1)
        medage = np.zeros(nt + 1)
        tlr = tl.ravel(); ag = age.ravel(); o = np.argsort(tlr, kind='stable'); st = np.searchsorted(tlr[o], np.arange(nt + 2))
        for k in range(1, nt + 1): medage[k] = float(np.median(ag[o[st[k]:st[k + 1]]]))
        # 가는 덩이가 넓은 칸과 하나도 닿지 않으면 (몸 전체가 가늘면) 따로 센다
        touch = np.zeros(nt + 1, bool)
        for d in ALL: touch[np.unique(tl[(tl > 0) & nb(wide, d)])] = True
        allthin_bodies = int(((~touch[1:]) & (ncell[1:] >= TAIL_MIN)).sum())
        ev = (ncell >= TAIL_MIN) & (medage >= AGE_EVAL) & touch; ev[0] = False
        for q in qs:
            fl = ev & (Fb < q * Veff)
            res[q]['B_cells'] = int(ncell[fl].sum()); res[q]['B_threads'] = int(fl.sum())
        out['thin_eval'] = int(ev.sum()); out['thin_main_cells'] = int((thin & main).sum())
    out['allthin_bodies'] = allthin_bodies
    nc_ = nbcount(wet)
    tip = wet & (nc_ == 1) & main & (age >= AGE_EVAL)
    for q in qs: res[q]['B_tips'] = int((tip & (inc < q * np.maximum(h, H_FLOOR))).sum())
    out['tips_eval'] = int(tip.sum())
    # 몸에서 떨어진 가는 조각 (주 몸이 아닌 덩이 가운데 가는 칸이 반 이상이고 길이(가로·세로 폭 가운데 큰 것) 4칸 이상)
    det_cells = 0; det_tips = 0
    for k in range(1, n + 1):
        if k in main_ids: continue
        mk = lab == k
        if thin[mk].mean() >= 0.5:
            dx, dy = centred_coords(mk); ext = max(float(dx.max() - dx.min()), float(dy.max() - dy.min())) + 1
            if ext >= 4: det_cells += int(area[k]); det_tips += int((mk & (nc_ == 1)).sum())
    out['det_thin_cells'] = det_cells; out['det_thin_tips'] = det_tips
    for q in qs:
        r = res[q]; r['A_cells'] = r['B_cells'] + det_cells; r['A_tips'] = r['B_tips'] + det_tips
    out['flow'] = {str(q): res[q] for q in qs}
    # ---- 아령 ----
    edt = edt_torus(wet); dbs = []
    for k in main_ids: dbs.append(dumbbell(lab == k, h, edt))
    out['db'] = bool(any(x['db'] for x in dbs)); out['multi'] = bool(any(x['multi'] for x in dbs)); out['db_detail'] = dbs
    # ---- 꼬리 (주 몸에 매달린 것만) ----
    rm, rest = prune_strict(main)
    sz, yg = tail_trees(rm, age)
    old = (sz >= TAIL_MIN) & ~yg; young = (sz >= TAIL_MIN) & yg
    out['tail'] = dict(n=int(old.sum()), cells=int(sz[old].sum()), max=int(sz[old].max()) if old.any() else 0, sizes=[int(v) for v in sz[old]],
                       young_n=int(young.sum()), young_cells=int(sz[young].sum()), young_sizes=[int(v) for v in sz[young]])
    rme, reste = prune_ext(main, thin)
    sze, yge = tail_trees(rme, age)
    olde = (sze >= TAIL_MIN) & ~yge
    out['tail_ext'] = dict(n=int(olde.sum()), cells=int(sze[olde].sum()), max=int(sze[olde].max()) if olde.any() else 0)
    # 넓힌 깎기 뒤에도 남는 가는 칸 = 양 끝이 몸에 이어진 관·고리 (주 몸)
    tube = reste & thin
    lt_, ntb = label8(tube)
    tsz = np.bincount(lt_.ravel(), minlength=ntb + 1)[1:] if ntb else np.zeros(0, int)
    out['tube'] = dict(n=int((tsz >= TAIL_MIN).sum()), cells=int(tsz[tsz >= TAIL_MIN].sum()), max=int(tsz.max()) if tsz.size else 0)
    return out


# ---------------------------------------------------------------- 균핵 (주장 7)
def circ_centroid(m):
    N0, N1 = m.shape; ys, xs = np.nonzero(m)
    ax = 2 * np.pi / N1; ay = 2 * np.pi / N0
    cx = (np.arctan2(np.sin(xs * ax).mean(), np.cos(xs * ax).mean()) / ax) % N1
    cy = (np.arctan2(np.sin(ys * ay).mean(), np.cos(ys * ay).mean()) / ay) % N0
    return cx, cy


def centred_coords(m):
    """mask 칸을 원형 무게중심 기준의 상대 좌표(정수 아님)로 (토러스에서 풀어서)"""
    N0, N1 = m.shape; cx, cy = circ_centroid(m); ys, xs = np.nonzero(m)
    dx = (xs - cx + N1 / 2) % N1 - N1 / 2; dy = (ys - cy + N0 / 2) % N0 - N0 / 2
    return dx, dy


def disc_iou(m):
    """같은 넓이, 같은 무게중심의 원판(칸 중심이 반지름 안)과의 IoU"""
    N0, N1 = m.shape; cx, cy = circ_centroid(m); ys, xs = np.nonzero(m)
    rx = int(np.round(cx)); ry = int(np.round(cy)); ox = cx - rx; oy = cy - ry
    gx = (xs - rx + N1 // 2) % N1 - N1 // 2; gy = (ys - ry + N0 // 2) % N0 - N0 // 2
    R = np.sqrt(xs.size / np.pi); r = int(np.ceil(R)) + 2; Y, X = np.mgrid[-r:r + 1, -r:r + 1]
    dm = np.hypot(X - ox, Y - oy) <= R
    disc = set(zip(Y[dm].tolist(), X[dm].tolist())); cells = set(zip(gy.tolist(), gx.tolist()))
    return len(disc & cells) / max(len(disc | cells), 1)


def shape_iou(c1, c2):
    """두 상대 좌표 묶음 (무게중심 맞춤, 정수 반올림) 의 IoU"""
    a = set(zip(np.round(c1[0]).astype(int).tolist(), np.round(c1[1]).astype(int).tolist()))
    b = set(zip(np.round(c2[0]).astype(int).tolist(), np.round(c2[1]).astype(int).tolist()))
    return len(a & b) / max(len(a | b), 1)


def solidity(m):
    from scipy.spatial import ConvexHull
    dx, dy = centred_coords(m)
    pts = np.concatenate([np.stack([dx + ox, dy + oy], 1) for ox in (-0.5, 0.5) for oy in (-0.5, 0.5)])
    if dx.size < 3: return 1.0
    return float(dx.size / ConvexHull(pts).volume)


def holes(wet):
    """젖은 칸이 둘러싼 마른 칸 수 (가장 큰 마른 덩이에 닿지 않는 마른 칸; 4-연결로 센다: 대각 틈으로는 새지 않는다고 본다)"""
    dry = ~wet
    lab, n = ndi.label(np.pad(dry, 1, mode='wrap'))      # 토러스를 위해 한 칸 감아 붙인 뒤 4-연결
    lab = lab[1:-1, 1:-1]
    # 감김 합치기: 4-연결이므로 가장자리 마주 보는 칸끼리만
    if n == 0: return 0
    a = np.concatenate([lab[:, 0], lab[0, :]]); b = np.concatenate([lab[:, -1], lab[-1, :]]); m = (a > 0) & (b > 0)
    g = coo_matrix((np.ones(int(m.sum())), (a[m], b[m])), shape=(n + 1, n + 1)); _, cl = connected_components(g, directed=False)
    comp = cl[lab]; comp[~dry] = -1
    sz = np.bincount(comp[dry]); bg = int(np.argmax(sz))
    return int((dry & (comp != bg)).sum())


def disk_sum(a, r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]; k = (np.hypot(x, y) <= r).astype(float)
    return ndi.convolve(a, k, mode='wrap')


def profile(L, hm):
    """두께 모양: 덩이 안 EDT 별 평균 두께"""
    e = edt_torus(L); v = hm[L]; ev = e[L]
    rim = L & (e == 1.0); emx = float(ev.max())
    cen = L & (e >= 0.8 * emx)
    ratio = float(hm[cen].mean() / max(hm[rim].mean(), 1e-12)) if rim.any() else float('nan')
    rho = float(spearmanr(ev, v)[0]) if ev.size > 5 and np.std(ev) > 0 and np.std(v) > 0 else float('nan')
    ring = np.floor(ev).astype(int); rings = sorted(set(ring.tolist()))
    means = [float(v[ring == q].mean()) for q in rings]; counts = [int((ring == q).sum()) for q in rings]
    steps = np.diff(means) if len(means) >= 2 else np.zeros(0)
    rise = means[-1] - means[0] if len(means) >= 2 else 0.0
    mono = bool(np.all(steps >= -0.05 * float(np.mean(means)))) if steps.size else True
    gradual = bool(rise > 0 and len(means) >= 3 and float(steps.max()) <= 0.5 * rise)
    return dict(ratio=ratio, rho=rho, rings=rings, means=means, counts=counts, mono=mono, gradual=gradual, emax=emx)


def sclerotium(snaps, t_scl, V_note=None):
    """snaps: [(t, wet, h, hm)] 시간 순. t_scl: 갇힌 시각. 주장 7 의 (a)~(f) 측정"""
    ts = np.array([s[0] for s in snaps]); out = dict(t_scl=t_scl)
    if t_scl is None: out['trapped'] = False; return out
    out['trapped'] = True
    i0 = int(np.nonzero(ts <= t_scl + 1e-9)[0].max()); t0 = ts[i0]; out['t_trap_snap'] = float(t0)
    w0 = snaps[i0][1]; h0_ = snaps[i0][2]
    lab0, n0, vol0, area0, V0 = components(w0, h0_)
    bodies0 = [k for k in range(1, n0 + 1) if vol0[k] >= 0.03 * V0]
    out['bodies_at_trap'] = len(bodies0)
    B = lab0 == int(np.argmax(vol0))
    tE, wE, hE, hmE = snaps[-1]
    labE, nE, volE, areaE, VE = components(wE, hE)
    L = labE == int(np.argmax(volE))
    hmL = np.where(hmE > 0, hmE, hE)
    # (a)
    nb3 = []
    for (t, w, h_, _) in snaps[i0:]:
        l_, n_, v_, a_, V_ = components(w, h_); nb3.append(int(sum(1 for k in range(1, n_ + 1) if v_[k] >= 0.03 * V_)))
    rmE, _ = prune_strict(L); thinE = L & ~opening3(L); szE, _ = tail_trees(rmE, np.full(L.shape, 1e9))
    out['a'] = dict(n_end=int(sum(1 for k in range(1, nE + 1) if volE[k] >= 0.03 * VE)), ncomp_end=nE, max_bodies_after=int(max(nb3)), tail_cells_end=int(rmE.sum()),
                    tail_max_end=int(szE.max()) if szE.size else 0, thin_frac_end=float(thinE.sum() / max(L.sum(), 1)))
    # (b)
    tf = t_scl + 200.0; after = [s for s in snaps if s[0] >= tf]
    if after:
        aE = int(L.sum()); amax = max(int(s[1].sum()) for s in after); uni = np.zeros_like(wE)
        for s in after: uni |= s[1]
        out['b'] = dict(t_f=tf, area_end=aE, max_area_ratio=amax / max(aE, 1), outside_union_frac=float((uni & ~wE).sum() / max(aE, 1)), n_after=len(after))
    # (c)
    D6 = disk_sum(np.where(w0, np.maximum(h0_, 0.0), 0.0), 6)
    bv = D6[B]; rk = np.empty(bv.size); rk[np.argsort(bv, kind='stable')] = np.arange(bv.size) / max(bv.size - 1, 1)
    R = np.zeros(w0.shape); R[B] = rk
    pk = np.unravel_index(np.argmax(np.where(B, D6, -np.inf)), w0.shape)
    N0, N1 = w0.shape; ys, xs = np.nonzero(L)
    dpk = float(np.min(np.hypot((xs - pk[1] + N1 / 2) % N1 - N1 / 2, (ys - pk[0] + N0 / 2) % N0 - N0 / 2))) if ys.size else float('inf')
    VL = float(np.maximum(hE[L], 0).sum())
    dx, dy = centred_coords(L)
    out['c'] = dict(rank_mean=float(R[L & B].mean()) if (L & B).any() else float('nan'), overlap_frac=float((L & B).sum() / max(L.sum(), 1)), peak_dist=dpk,
                    area=int(L.sum()), V_lump=VL, area_min=VL / 3.5, disc_iou=disc_iou(L), coords=[np.round(dx, 3).tolist(), np.round(dy, 3).tolist()])
    # (d) 바깥 칸이 걷히는 차례와 빠르기
    O = B & ~L; nO = int(O.sum()); last_wet = np.full(w0.shape, t0)
    for (t, w, _, _) in snaps[i0:]: last_wet = np.where(w, t, last_wet)
    sn_ts = ts[i0:]
    nxt = {float(sn_ts[j]): float(sn_ts[j + 1]) for j in range(len(sn_ts) - 1)}
    dry_t = np.vectorize(lambda v: nxt.get(float(v), np.inf))(last_wet)
    rem = []
    for (t, w, _, _) in snaps[i0:]: rem.append(1.0 - float((O & w).sum()) / max(nO, 1))
    rem = np.array(rem); d = dict(n_out=nO, n_lump=int(L.sum()), times=sn_ts.tolist(), removed=rem.tolist())
    if nO >= 10:
        t10 = float(sn_ts[np.argmax(rem >= 0.1)]) if (rem >= 0.1).any() else np.inf; t90 = float(sn_ts[np.argmax(rem >= 0.9)]) if (rem >= 0.9).any() else np.inf
        dtsn = float(np.median(np.diff(sn_ts))); kw = max(1, int(round(10.0 / dtsn)))
        win = float(np.max(rem[kw:] - rem[:-kw])) if rem.size > kw else 1.0
        G = geo_dist(B | L, L); dO = G[O]; tO = dry_t[O]; fin = np.isfinite(dO) & np.isfinite(tO)
        rho = float(spearmanr(dO[fin], tO[fin])[0]) if fin.sum() > 5 else float('nan')
        near = O & (G <= 2.0) & np.isfinite(dry_t)
        q75 = float(np.percentile(tO[np.isfinite(tO)], 75)) if np.isfinite(tO).any() else float('nan')
        d.update(t10=t10, t90=t90, dur=t90 - t10, maxwin10=win, rho=rho, near_med=float(np.median(dry_t[near])) if near.any() else float('nan'), q75=q75, n_near=int(near.sum()),
                 dist_max=float(dO[np.isfinite(dO)].max()) if np.isfinite(dO).any() else float('nan'))
    # 구멍 메움
    F = L & ~B; nF = int(F.sum()); first_wet = np.full(w0.shape, np.inf)
    for (t, w, _, _) in snaps[i0 + 1:]: first_wet = np.where(w & ~np.isfinite(first_wet), t, first_wet)
    d['n_fill'] = nF
    if nF >= 10:
        fv = np.sort(first_wet[F]); fv = fv[np.isfinite(fv)]
        if fv.size:
            fr = np.array([float((fv <= t).sum()) / nF for t in sn_ts]); f10 = float(sn_ts[np.argmax(fr >= 0.1)]); f90 = float(sn_ts[np.argmax(fr >= 0.9)]) if (fr >= 0.9).any() else np.inf
            kw = max(1, int(round(10.0 / float(np.median(np.diff(sn_ts))))))
            d.update(fill_dur=f90 - f10, fill_maxwin10=float(np.max(fr[kw:] - fr[:-kw])) if fr.size > kw else 1.0, fill_frac=fr.tolist())
    out['d'] = d
    # (e)
    out['e'] = dict(holes=holes(wE), solidity=solidity(L))
    # (f)
    out['f'] = profile(L, hmL)
    return out
