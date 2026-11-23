#!/usr/bin/env python3
"""verify4 측정 (독립 검증자 코드). 실행 폴더 하나를 읽어 스냅숏(20 시간 단위마다)별로 잰 값과 실행 요약을 JSON 으로 쓴다.

usage: measure.py RUN_DIR OUT_JSON

읽는 것: RUN_DIR/vs_t*.npz (wet, h, hmean, Qgross, age, t, cen), RUN_DIR/metrics.json, RUN_DIR/params.json,
         끝 상태 RUN_DIR/h.npy, wet.npy, slime.npy (있으면).
정의는 verify4/CRITERIA.md 에 적은 그대로다. 모든 연결은 토러스 위 8-이웃이다.
"""
import numpy as np, json, sys, os, glob, re
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, maximum_flow

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]                     # 모델의 간선 방향 (ref_model.DIRS 와 같은 순서)
ALL8 = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0)]
SQ3 = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]   # 3x3 정사각형 (가는 부분/막 판별)
D2 = [(dx, dy) for dy in range(-2, 3) for dx in range(-2, 3) if dx * dx + dy * dy <= 5]   # 반지름 2 원반 (21칸, 덩이 판별)
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]

# ---- 기준값 (CRITERIA.md 1절) ----
DEBRIS_SHARE = 0.05      # 부스러기: 전체 부피의 5% 미만인 떨어진 조각
H_THICK = 0.5            # 굵음: 한 주기 평균 두께 >= 0.5 h0
LUMP_SHARE = 0.05        # 덩이: 굵은 몸통(반지름 2 원반 열림) 조각 중 전체 부피의 5% 이상
NECK_MAX = 3             # 아령: 두 덩이 사이 최소 절단 폭 <= 3 칸
H_FILM = 0.3             # 얇은 막: 한 주기 평균 두께 < 0.3 h0 인 칸이 3x3 으로 덮이는 곳
DEAD_FRAC = 0.05         # 흐름 없음: 칸 흐름 < 0.05 x (그 스냅숏 젖은 칸 흐름의 90 백분위)
BRANCH_MIN = 5           # 가지: 가는 칸 덩어리 5칸 이상
FRESH_TRAP = 0.05        # 갇힘: 가장자리 마른 칸 중 한 번도 젖은 적 없는 칸의 비율 < 0.05
# 민감도 (판정에는 쓰지 않고 보고만 한다)
SENS_LUMP = [(0.5, 0.10), (0.7, 0.05)]
SENS_FILM = [0.2, 0.4]
SENS_DEAD = [0.02, 0.10]


def sh(a, dx, dy):
    """a 를 (x+dx, y+dy) 이웃에서 읽은 값 (모델의 nb 와 같은 규약: 배열 축 0 = y, 축 1 = x)"""
    return np.roll(a, (-dy, -dx), (0, 1))


def label8(mask):
    """토러스 8-연결 성분. 0 = 배경, 1..n"""
    n = int(mask.sum()); out = np.zeros(mask.shape, np.int64)
    if n == 0: return out, 0
    idx = -np.ones(mask.shape, np.int64); idx[mask] = np.arange(n)
    r = []; c = []
    for dx, dy in DIRS:
        m = mask & sh(mask, dx, dy); r.append(idx[m]); c.append(sh(idx, dx, dy)[m])
    r = np.concatenate(r); c = np.concatenate(c)
    nc, lab = connected_components(coo_matrix((np.ones(r.size), (r, c)), shape=(n, n)), directed=False)
    out[mask] = lab + 1
    return out, int(nc)


def erode(m, S):
    o = m.copy()
    for dx, dy in S: o &= sh(m, dx, dy)
    return o


def dilate(m, S):
    o = m.copy()
    for dx, dy in S: o |= sh(m, dx, dy)
    return o


def opening(m, S): return dilate(erode(m, S), S) & m


# 고리 위 젖은 이웃 무리 수 (8-연결) 표: 256 가지 무늬
def _ring_tables():
    pos = np.array(RING)
    adj = np.array([[max(abs(pos[i][0] - pos[j][0]), abs(pos[i][1] - pos[j][1])) <= 1 and i != j for j in range(8)] for i in range(8)])
    groups = np.zeros(256, np.int8); count = np.zeros(256, np.int8)
    for pat in range(256):
        on = [i for i in range(8) if pat >> i & 1]; count[pat] = len(on); seen = set(); g = 0
        for s in on:
            if s in seen: continue
            g += 1; st = [s]; seen.add(s)
            while st:
                u = st.pop()
                for v in on:
                    if v not in seen and adj[u, v]: seen.add(v); st.append(v)
        groups[pat] = g
    return groups, count


RG, RC = _ring_tables()


def cell_flow(Qg):
    """칸을 지나는 흐름: 0.5 x (칸에 닿는 8 간선의 창 평균 |Q| 합). Qg[k][y,x] 는 (y,x) 에서 DIRS[k] 쪽 이웃으로 가는 간선"""
    q = np.zeros(Qg.shape[1:], np.float64)
    for k, (dx, dy) in enumerate(DIRS): q += Qg[k] + sh(Qg[k], -dx, -dy)
    return 0.5 * q


def min_vertex_cut(body, A, B):
    """body 안에서 A 와 B 를 가르는 데 지워야 하는 최소 칸 수 (A, B 칸은 지울 수 없음). 8-이웃 연결"""
    n = int(body.sum()); idx = -np.ones(body.shape, np.int64); idx[body] = np.arange(n); INF = 10 ** 6
    ar = np.arange(n); vcap = np.where((A | B)[body], INF, 1)
    rows = [2 * ar]; cols = [2 * ar + 1]; caps = [vcap]
    for dx, dy in ALL8:
        m = body & sh(body, dx, dy); u = idx[m]; v = sh(idx, dx, dy)[m]
        rows.append(2 * u + 1); cols.append(2 * v); caps.append(np.full(u.size, INF))
    a = idx[A & body]; b = idx[B & body]; S = 2 * n; T = 2 * n + 1
    rows += [np.full(a.size, S), 2 * b + 1]; cols += [2 * a, np.full(b.size, T)]; caps += [np.full(a.size, INF), np.full(b.size, INF)]
    G = csr_matrix((np.concatenate(caps).astype(np.int32), (np.concatenate(rows), np.concatenate(cols))), shape=(2 * n + 2, 2 * n + 2))
    G.sum_duplicates(); G.sort_indices()
    return int(maximum_flow(G, S, T).flow_value)


def lumps_of(wet, h, heff, lab_b, V, hth, share):
    """굵은 덩이: wet & heff>=hth 를 반지름 2 원반으로 연 뒤의 8-연결 조각 중 부피(h 합) >= share*V. 반환: 덩이 표지 배열, [(표지, 몸 표지, 부피 비율)]"""
    bulk = opening(wet & (heff >= hth), D2)
    ll, nl = label8(bulk)
    if nl == 0: return ll, []
    vol = np.bincount(ll.ravel(), weights=np.where(bulk, h, 0.0).ravel(), minlength=nl + 1)
    out = []
    for k in range(1, nl + 1):
        if vol[k] >= share * V:
            ys, xs = np.nonzero(ll == k); out.append((k, int(lab_b[ys[0], xs[0]]), float(vol[k] / V)))
    return ll, out


def lump_stats(wet, h, heff, lab_b, V, hth, share):
    ll, L = lumps_of(wet, h, heff, lab_b, V, hth, share)
    per_body = {}
    for k, b, s in L: per_body.setdefault(b, []).append(k)
    multi = any(len(v) >= 2 for v in per_body.values())
    cut_min = None
    for b, ks in per_body.items():
        if len(ks) < 2: continue
        body = lab_b == b
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                c = min_vertex_cut(body, ll == ks[i], ll == ks[j])
                cut_min = c if cut_min is None else min(cut_min, c)
    return dict(n_lumps=len(L), multi=bool(multi), dumb=bool(cut_min is not None and cut_min <= NECK_MAX), cut_min=cut_min,
                lump_shares=sorted([round(s, 4) for _, _, s in L], reverse=True)), per_body


def shape_of(mask):
    """K = A / (2 pi Rg^2) (원반 = 1), lam = 작은/큰 2차 모멘트 고유값 비 (원반 = 1). 토러스: 축마다 원형 평균 중심에서 최소 상"""
    N = mask.shape[0]; ys, xs = np.nonzero(mask); A = xs.size
    if A < 3: return None, None
    ang = 2 * np.pi / N
    cx = (np.arctan2(np.sin(xs * ang).sum(), np.cos(xs * ang).sum()) / ang) % N
    cy = (np.arctan2(np.sin(ys * ang).sum(), np.cos(ys * ang).sum()) / ang) % N
    dx = (xs - cx + N / 2) % N - N / 2; dy = (ys - cy + N / 2) % N - N / 2
    dx = dx - dx.mean(); dy = dy - dy.mean()
    sxx = (dx * dx).mean() + 1 / 12; syy = (dy * dy).mean() + 1 / 12; sxy = (dx * dy).mean()
    K = A / (2 * np.pi * (sxx + syy))
    tr = sxx + syy; det = sxx * syy - sxy * sxy; disc = np.sqrt(max(tr * tr / 4 - det, 0.0))
    return float(K), float((tr / 2 - disc) / (tr / 2 + disc))


def snap_measures(wet, h, hmean, Qg, U_prev):
    N = wet.shape[0]; h = h.astype(np.float64); wet = wet.astype(bool)
    heff = np.where(wet, np.where(hmean > 0, hmean, h), 0.0)
    V = float(h[wet].sum()); A = int(wet.sum())
    out = dict(area=A, V=round(V, 6), hmin=float(h[wet].min()) if A else 0.0)
    lab_b, nb_ = label8(wet)
    bv = np.bincount(lab_b.ravel(), weights=np.where(wet, h, 0.0).ravel(), minlength=nb_ + 1)
    ba = np.bincount(lab_b.ravel(), minlength=nb_ + 1)
    deb = [k for k in range(1, nb_ + 1) if bv[k] < DEBRIS_SHARE * V]
    big = [k for k in range(1, nb_ + 1) if bv[k] >= DEBRIS_SHARE * V]
    out.update(n_bodies=nb_, n_big=len(big), debris_n=len(deb), debris_cells=int(sum(ba[k] for k in deb)), debris_vol=round(float(sum(bv[k] for k in deb) / max(V, 1e-12)), 6),
               debris_max_share=round(float(max([bv[k] / max(V, 1e-12) for k in deb], default=0.0)), 6),
               body_shares=sorted([round(float(bv[k] / max(V, 1e-12)), 4) for k in big], reverse=True))
    # 덩이 (주 기준 + 민감도)
    ls, per_body = lump_stats(wet, h, heff, lab_b, V, H_THICK, LUMP_SHARE)
    out.update(ls)
    out['n_mass'] = int(sum(max(1, len(per_body.get(k, []))) for k in big))
    for hth, shr in SENS_LUMP:
        s2, _ = lump_stats(wet, h, heff, lab_b, V, hth, shr); out[f'multi_h{hth}_s{shr}'] = s2['multi']; out[f'dumb_h{hth}_s{shr}'] = s2['dumb']
    # 가는 부분, 막, 흐름 없음, 가지 끝
    narrow = wet & ~opening(wet, SQ3)
    out['narrow_cells'] = int(narrow.sum())
    out['film_cells'] = int(opening(wet & (heff < H_FILM), SQ3).sum())
    for hf in SENS_FILM: out[f'film_cells_{hf}'] = int(opening(wet & (heff < hf), SQ3).sum())
    q = cell_flow(Qg.astype(np.float64)) if Qg is not None else None
    pat = np.zeros(wet.shape, np.int64)
    for i, (dx, dy) in enumerate(RING): pat |= sh(wet, dx, dy).astype(np.int64) << i
    tipc = narrow & (RG[pat] == 1) & (RC[pat] >= 1) & (RC[pat] <= 3)
    ln, nn = label8(narrow); nsz = np.bincount(ln.ravel(), minlength=nn + 1); nsz[0] = 0
    tipc &= nsz[ln] >= BRANCH_MIN
    lt, nt = label8(tipc); out['tips'] = nt
    if q is not None and A:
        Fref = float(np.percentile(q[wet], 90)); out['Fref'] = Fref
        tmax = np.zeros(nt + 1); np.maximum.at(tmax, lt.ravel(), q.ravel()) if nt else None
        for th, key in [(DEAD_FRAC, '')] + [(s, f'_{s}') for s in SENS_DEAD]:
            dead = wet & (q < th * Fref)
            out['dead_thread' + key] = int((narrow & dead).sum())
            out['dead_tips' + key] = int((tmax[1:] < th * Fref).sum()) if nt else 0
    # 가장 큰 몸의 모양
    if nb_:
        kb = int(np.argmax(np.where(np.arange(nb_ + 1) > 0, bv, -1.0))); mb = lab_b == kb
        K, lam = shape_of(mb)
        out.update(main_share=round(float(bv[kb] / max(V, 1e-12)), 4), main_area=int(mb.sum()), K=K, lam=lam,
                   main_narrow_share=round(float((narrow & mb).sum() / max(mb.sum(), 1)), 4))
    # 갇힘: 가장자리 마른 칸 중 지금까지 한 번도 젖지 않은 칸의 비율
    rim = dilate(wet, SQ3) & ~wet; nr = int(rim.sum())
    out['fresh'] = round(float((rim & ~U_prev).sum() / max(nr, 1)), 4); out['rim'] = nr
    return out


def main():
    rd, outp = sys.argv[1], sys.argv[2]
    name = os.path.basename(os.path.normpath(rd))
    m = re.match(r'b_(\w+?)_s(\d+)_(v4c|v4w)$', name)
    scn, seed, cfg = m.group(1), int(m.group(2)), m.group(3)
    res = dict(name=name, scn=scn, seed=seed, cfg=cfg)
    P = json.load(open(os.path.join(rd, 'params.json'))) if os.path.exists(os.path.join(rd, 'params.json')) else None
    M = json.load(open(os.path.join(rd, 'metrics.json'))) if os.path.exists(os.path.join(rd, 'metrics.json')) else None
    files = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
    N = int(P['N']) if P else int(np.load(files[0])['wet'].shape[0])
    c0 = N / 2 - 0.5; R0 = float(P['R_init']) if P else 12.0
    jj, ii = np.mgrid[0:N, 0:N]
    U = np.hypot(ii - c0, jj - c0) < R0          # 처음 원반 (ref_model 과 같은 식)
    snaps = []; hmin_snap = 0.0
    for f in files:
        Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h']; t = float(Z['t'])
        s = snap_measures(wet, h, Z['hmean'], Z['Qgross'], U)
        s['t'] = round(t, 2); s['cen'] = [round(float(v), 3) for v in Z['cen']]
        U = U | wet; s['cover'] = round(float(U.sum() / U.size), 4)
        if P and P.get('foods'):
            fr = float(P['food_r']); fw = []
            for a_, d_ in P['foods']:
                fx = c0 + d_ * np.cos(np.radians(a_)); fy = c0 + d_ * np.sin(np.radians(a_))
                dd = np.hypot((ii - fx + N / 2) % N - N / 2, (jj - fy + N / 2) % N - N / 2) < fr
                fw.append(int((dd & wet).sum()))
            s['food_wet'] = fw
        hmin_snap = min(hmin_snap, s['hmin']); snaps.append(s)
    res['snaps'] = snaps; res['hmin_snapshots'] = hmin_snap
    # 끝 상태와 모델 기록
    if P: res.update(N=N, T=float(P['T']), dt=float(P['dt']), foods=P.get('foods'), food_r=P.get('food_r'), c0=c0)
    if M:
        keys = ('stop', 't_end', 'steps_done', 'V0', 'Vinj', 'V_end', 'V_crumb', 'crumb_cells', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step', 'neg_end_cellsteps',
                'neg_end_steps', 'neg_cellsteps', 't_touch', 't_cover', 't_exh', 't_scl', 'scl_steps', 'fission_runs', 'conn_kept_cellsteps', 'ret_cellsteps', 'runtime', 'disp', 'path_len')
        res['metrics'] = {k: M.get(k) for k in keys}
        res['traj'] = [[a[0], a[1], a[2]] for a in M['traj']]
    if os.path.exists(os.path.join(rd, 'h.npy')) and M:
        he = np.load(os.path.join(rd, 'h.npy')).astype(np.float64); we = np.load(os.path.join(rd, 'wet.npy'))
        Vexp = M['V0'] + M['Vinj'] - M['V_crumb']
        res['end_check'] = dict(hmin_wet=float(he[we].min()) if we.any() else 0.0, vol_rel_err=float(abs(he[we].sum() - Vexp) / M['V0']),
                                same_as_last_snap=bool(len(files) > 0 and np.array_equal(np.load(files[-1])['wet'], we)))
        if os.path.exists(os.path.join(rd, 'slime.npy')):
            sl = np.load(os.path.join(rd, 'slime.npy')) > 0.5
            res['end_check']['slime_cover'] = round(float(sl.mean()), 4)
            res['end_check']['U_captures_slime'] = round(float((sl & U).sum() / max(sl.sum(), 1)), 4)    # 스냅숏 합집합이 실제 점액을 얼마나 잡았나
    json.dump(res, open(outp, 'w'), separators=(',', ':'))
    print(name, 'snaps', len(snaps), 'ok')


if __name__ == '__main__':
    main()
