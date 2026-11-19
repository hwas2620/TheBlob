#!/usr/bin/env python3
"""[verify] 독립 심사자의 지표. 실험자의 graphm.py / summ*.py / phase.py 를 import 하지 않는다.
(5차 검증의 research/round5/H1-emergent-phase/verify/vmet.py 를 그대로 옮긴 사본이다. 관문 B 에서 GPU 실행과 numpy 실행을 똑같이 채점하는 데 쓴다. 고치지 않는다)

저장된 상태(state_t*.npz 또는 vs_t*.npz)와 hfood.npy 에서 직접 계산한다.

간선 규약(f1.py 의 DIRS): 채널 k 의 간선은 셀 (y,x) 에서 (y+DY[k], x+DX[k]) 로 간다(토러스 감김).
지표
  vein(thr)   : C>thr 이고 양 끝이 젖은 간선의 그래프. 최대 성분의 간선 수 비율, 순환 수(E-V+성분 수), 간선 수
  same(thr)   : 두 먹이 원반의 젖은 셀이 같은 정맥 성분에 드는가
  pathminC    : 원반 사이 최소 저항 경로(가중치 L/(G(C+r)), 모든 활성 간선)에서 원반 밖 간선의 최소 C
  bottleneck  : 두 원반이 같은 성분에 드는 가장 높은 문턱(= 최대-최소 경로의 최소 C). 문턱에 의존하지 않는 값
  body        : 젖은 셀의 8연결 성분(토러스) 가운데 부피가 가장 큰 것의 부피 비율, 성분 수
  pulse       : hfood.npy 의 원반 평균 두께에서 느린 성분을 빼고(40스텝 이동 평균) 쌍별 상관, Hilbert 위상차
"""
import numpy as np, json, os, sys, glob
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.signal import hilbert

DX = np.array([1, 0, 1, 1]); DY = np.array([0, 1, 1, -1]); LEN = np.array([1.0, 1.0, 2 ** 0.5, 2 ** 0.5])


def wrapd(v, N): return (v + N / 2.0) % N - N / 2.0


def edge_list(C, wet):
    N = wet.shape[0]; yy, xx = np.indices((N, N)); S = []; D = []; CC = []; KK = []
    for k in range(4):
        y2 = (yy + DY[k]) % N; x2 = (xx + DX[k]) % N
        act = wet & wet[y2, x2]
        S.append((yy * N + xx)[act]); D.append((y2 * N + x2)[act]); CC.append(C[k][act].astype(float)); KK.append(np.full(int(act.sum()), k))
    return np.concatenate(S), np.concatenate(D), np.concatenate(CC), np.concatenate(KK)


def comps(src, dst, n):
    nc, lab = connected_components(coo_matrix((np.ones(src.size, np.int8), (src, dst)), shape=(n, n)), directed=False)
    return nc, lab


def vein_stats(src, dst, cc, n, thr):
    m = cc > thr; E = int(m.sum())
    if E < 3: return dict(E=E, largest=0.0, cycles=0, ncomp=0), None
    nc, lab = comps(src[m], dst[m], n)
    ecount = np.bincount(lab[src[m]], minlength=nc)
    nodes = np.unique(np.concatenate([src[m], dst[m]])); V = nodes.size; ncv = np.unique(lab[nodes]).size
    return dict(E=E, largest=float(ecount.max() / E), cycles=int(E - V + ncv), ncomp=int(ncv)), lab


def disc_mask(N, fx, fy, r):
    yy, xx = np.indices((N, N))
    return np.hypot(wrapd(xx - fx, N), wrapd(yy - fy, N)) < r


def food_positions(P):
    N = P['N']; c0 = N / 2 - 0.5
    return [(c0 + d * np.cos(np.radians(a)), c0 + d * np.sin(np.radians(a))) for a, d in P['foods']]


def body_stats(src, dst, wet, h):
    N = wet.shape[0]; n = N * N
    nc, lab = comps(src, dst, n)
    w = wet.ravel(); vol = np.bincount(lab[w], weights=h.ravel()[w].astype(float), minlength=nc); area = np.bincount(lab[w], minlength=nc)
    big = int(np.argmax(vol)); tot = float(vol.sum())
    return dict(body_largest_vol=float(vol[big] / tot) if tot > 0 else 0.0, body_ncomp=int((area > 0).sum()), body_largest_area=float(area[big] / max(int(w.sum()), 1)))


def path_min_c(src, dst, cc, kk, G, r, wet, mA, mB):
    """최소 저항 경로(모든 활성 간선). 돌려줌: (원반 밖 간선의 최소 C, 중앙 C, 간선 수) 또는 None"""
    N = wet.shape[0]; n = N * N
    sa = np.nonzero((mA & wet).ravel())[0]; sb = np.nonzero((mB & wet).ravel())[0]
    if sa.size == 0 or sb.size == 0: return None
    ys, xs = np.divmod(src, N)
    w = LEN[kk] / (G[kk, ys, xs].astype(float) * (cc + r))
    g = csr_matrix((np.concatenate([w, w]), (np.concatenate([src, dst]), np.concatenate([dst, src]))), shape=(n, n))
    dist, pred, _ = dijkstra(g, directed=True, indices=sa, return_predecessors=True, min_only=True)
    tb = sb[np.argmin(dist[sb])]
    if not np.isfinite(dist[tb]): return None
    path = [int(tb)]
    while pred[path[-1]] >= 0: path.append(int(pred[path[-1]]))
    cm = csr_matrix((np.concatenate([cc, cc]) + 1e-30, (np.concatenate([src, dst]), np.concatenate([dst, src]))), shape=(n, n))
    u = np.array(path[:-1]); v = np.array(path[1:])
    if u.size == 0: return dict(n=0, minC=float('nan'), medC=float('nan'))
    pc = np.asarray(cm[u, v]).ravel()
    ind = (mA | mB).ravel(); inside = ind[u] & ind[v]
    po = pc[~inside] if (~inside).sum() >= 3 else pc
    return dict(n=int(po.size), minC=float(po.min()), medC=float(np.median(po)), resist=float(dist[tb]))


def bottleneck(src, dst, cc, n, a_nodes, b_nodes):
    """두 노드 집합이 같은 성분에 드는 가장 높은 문턱 C (최대-최소 경로의 최소 C). 이어지지 않으면 0."""
    if a_nodes.size == 0 or b_nodes.size == 0: return 0.0
    vals = np.unique(cc)

    def conn(thr):
        m = cc >= thr
        if not m.any(): return False
        _, lab = comps(src[m], dst[m], n)
        return np.intersect1d(lab[a_nodes], lab[b_nodes]).size > 0
    if not conn(vals[0]): return 0.0
    lo, hi = 0, vals.size - 1          # conn(vals[lo]) 참
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if conn(vals[mid]): lo = mid
        else: hi = mid - 1
    return float(vals[lo])


def analyse_state(S, G, P, thrs=(4.0, 10.0, 30.0), do_path=True):
    C = S['C'].astype(float); wet = S['wet'].astype(bool); h = S['h'].astype(float); N = wet.shape[0]; n = N * N
    src, dst, cc, kk = edge_list(C, wet)
    out = dict(t=float(S['t']), area=int(wet.sum()), vol=float(h.sum()), hmin=float(h[wet].min()) if wet.any() else 0.0)
    out.update(body_stats(src, dst, wet, h))
    labs = {}
    for thr in thrs:
        vs, lab = vein_stats(src, dst, cc, n, thr); labs[thr] = lab
        for k_, v_ in vs.items(): out[f'vein{thr:g}_{k_}'] = v_
    vm = cc > 4.0
    out['vein_medC'] = float(np.median(cc[vm])) if vm.any() else float('nan'); out['vein_p90C'] = float(np.percentile(cc[vm], 90)) if vm.any() else float('nan')
    fpos = food_positions(P) if P.get('foods') else []
    discs = [disc_mask(N, fx, fy, P['food_r']) for fx, fy in fpos]
    out['wet_food'] = [int((m & wet).sum()) for m in discs]
    pairs = {}
    for i in range(len(discs)):
        for j in range(i + 1, len(discs)):
            a = np.nonzero((discs[i] & wet).ravel())[0]; b = np.nonzero((discs[j] & wet).ravel())[0]; d = {}
            for thr in thrs:
                lab = labs[thr]
                if lab is None or a.size == 0 or b.size == 0: d[f'same{thr:g}'] = False; continue
                # 정맥 간선이 없는 셀은 홑성분이라 두 원반이 겹치지 않는 한 공유될 수 없다
                d[f'same{thr:g}'] = bool(np.intersect1d(lab[a], lab[b]).size > 0)
            if do_path:
                pm = path_min_c(src, dst, cc, kk, G, P['r'], wet, discs[i], discs[j])
                d['path'] = pm
                d['bottleneck'] = bottleneck(src, dst, cc, n, a, b)
            pairs[f'{i}-{j}'] = d
    out['pairs'] = pairs
    return out


def load_states(run_dir):
    """(상태 dict 목록, G, P). vs_t*.npz 가 있으면 그것을(20 시간단위 간격), 없으면 state_t*.npz 를 쓴다."""
    P = json.load(open(os.path.join(run_dir, 'params.json')))
    fs = sorted(glob.glob(os.path.join(run_dir, 'vs_t*.npz'))); G = None
    if fs:
        G = np.load(os.path.join(run_dir, 'G_edges.npy'))
    else:
        fs = sorted(glob.glob(os.path.join(run_dir, 'state_t*.npz')))
    out = []
    for f in fs:
        Z = np.load(f, allow_pickle=True); S = {k: Z[k] for k in Z.files}
        if G is None and 'G' in S: G = S['G']
        out.append(S)
    return out, G, P


def touch_times(run_dir, P):
    """hfood.npy 에서 각 원반의 평균 두께가 처음 0 보다 커진 시각(= 처음 닿은 시각)"""
    a = np.load(os.path.join(run_dir, 'hfood.npy')); nf = len(P['foods']); dt = P['dt']; tt = []
    for k in range(nf):
        nz = np.nonzero(a[:, k] > 0)[0]; tt.append(float(nz[0] * dt) if nz.size else None)
    return tt


def pulse_corr(run_dir, P, t0, t1):
    a = np.load(os.path.join(run_dir, 'hfood.npy')).astype(float); nf = len(P['foods']); dt = P['dt']; n = int(round(P['period'] / dt))
    t = np.arange(a.shape[0]) * dt
    hp = []
    for k in range(nf):
        x = a[:, k]; c = np.concatenate([[0.0], np.cumsum(x)])
        mean = np.full(x.size, np.nan); half = n // 2
        idx = np.arange(half, x.size - half)
        mean[idx] = (c[idx + half] - c[idx - half]) / (2 * half)
        hp.append(x - mean)
    hp = np.array(hp); m = (t >= t0) & (t <= t1) & np.isfinite(hp).all(0)
    res = {}
    if m.sum() < 5 * n: return res
    for i in range(nf):
        for j in range(i + 1, nf):
            xi = hp[i, m]; xj = hp[j, m]
            r = float(np.corrcoef(xi, xj)[0, 1])
            zi = hilbert(xi); zj = hilbert(xj); dphi = np.angle(zj * np.conj(zi))[n:-n]
            R = np.exp(1j * dphi).mean()
            res[f'{i}-{j}'] = dict(corr=r, dphi_mean_deg=float(np.degrees(np.angle(R))), dphi_lock=float(abs(R)), amp_i=float(np.sqrt(2) * xi.std()), amp_j=float(np.sqrt(2) * xj.std()))
    return res


def summarise(run_dir, kind='food', window=None, verbose=False, do_path=True):
    """kind='food': 창 = [max(닿은 시각)+20, min(떨어진 시각)]; kind='mig': 창 = t>=200"""
    states, G, P = load_states(run_dir)
    met = json.load(open(os.path.join(run_dir, 'metrics.json'))) if os.path.exists(os.path.join(run_dir, 'metrics.json')) else {}
    rows = [analyse_state(S, G, P, do_path=(do_path and kind == 'food')) for S in states]
    out = dict(run=os.path.basename(run_dir.rstrip('/')), n_states=len(rows))
    if kind == 'food':
        tt = touch_times(run_dir, P); out['t_touch'] = tt
        ex = [v for v in (met.get('t_exh') or []) if v is not None]; t1 = min(ex) if ex else 1e9
        out['t_exh_first'] = None if t1 > 1e8 else t1
        if any(v is None for v in tt): out['note'] = '모든 먹이에 닿지 못함'; t0 = 1e9
        else: t0 = max(tt) + 20
        if window: t0, t1 = window
        W = [r for r in rows if t0 <= r['t'] <= t1 + 1e-6]
        out['window'] = [t0, t1, len(W)]
        if W:
            pk = sorted(W[0]['pairs'])
            for thr in (4, 10, 30):
                out[f'same{thr}'] = {k: round(float(np.mean([r['pairs'][k][f'same{thr}'] for r in W])), 2) for k in pk}
                out[f'vein{thr}_largest_med'] = round(float(np.median([r[f'vein{thr}_largest'] for r in W])), 3)
                out[f'vein{thr}_largest_min'] = round(float(np.min([r[f'vein{thr}_largest'] for r in W])), 3)
            if do_path:
                out['pathminC_med'] = {k: round(float(np.median([(r['pairs'][k]['path'] or {}).get('minC', 0.0) for r in W])), 1) for k in pk}
                out['bottleneck_med'] = {k: round(float(np.median([r['pairs'][k]['bottleneck'] for r in W])), 1) for k in pk}
                out['bottleneck_min'] = {k: round(float(np.min([r['pairs'][k]['bottleneck'] for r in W])), 1) for k in pk}
            out['vein_medC_med'] = round(float(np.median([r['vein_medC'] for r in W])), 1)
            out['body_largest_vol_min'] = round(float(min(r['body_largest_vol'] for r in W)), 3)
            out['cycles4_med'] = float(np.median([r['vein4_cycles'] for r in W]))
            if t1 < 1e8 and t0 < 1e8: out['pulse'] = {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in pulse_corr(run_dir, P, t0, t1).items()}
        allr = rows
        out['body_largest_vol_min_all'] = round(float(min(r['body_largest_vol'] for r in allr)), 3) if allr else None
        out['body_largest_vol_end'] = round(float(allr[-1]['body_largest_vol']), 3) if allr else None
    else:
        W = [r for r in rows if r['t'] >= (window[0] if window else 200)]
        out['window'] = [W[0]['t'], W[-1]['t'], len(W)] if W else None
        for thr in (4, 10, 30):
            out[f'vein{thr}_largest_med'] = round(float(np.median([r[f'vein{thr}_largest'] for r in W])), 3)
            out[f'vein{thr}_largest_min'] = round(float(np.min([r[f'vein{thr}_largest'] for r in W])), 3)
            out[f'vein{thr}_E_med'] = float(np.median([r[f'vein{thr}_E'] for r in W]))
        out['cycles4_med'] = float(np.median([r['vein4_cycles'] for r in W]))
        out['body_largest_vol_min'] = round(float(min(r['body_largest_vol'] for r in W)), 3)
        out['body_ncomp_end'] = W[-1]['body_ncomp']
    # 공통: 무게중심 이동. 저장된 상태를 시간순으로 따라가며 직전 무게중심 기준 최소 상(minimum image)으로 갱신한다(몸이 격자 절반을 넘게 퍼지면 정의가 흐려진다 -> span 으로 표시)
    N = P['N']; c0 = N / 2 - 0.5
    if states:
        yy, xx = np.indices((N, N)); cx = cy = c0
        for S in states:
            h = S['h'].astype(float); m_ = h.sum()
            for _ in range(4):
                cx += float((h * wrapd(xx - cx, N)).sum() / m_); cy += float((h * wrapd(yy - cy, N)).sum() / m_)
        out['disp_track'] = round(float(np.hypot(cx - c0, cy - c0)), 1); out['disp_dir_deg'] = round(float(np.degrees(np.arctan2(cy - c0, cx - c0))), 1)
        w = states[-1]['wet'].astype(bool); out['area_end'] = int(w.sum())
        colx = w.any(0); rowy = w.any(1); out['span_xy'] = [int(colx.sum()), int(rowy.sum())]      # 젖은 셀이 있는 열·행의 수 (N/2 를 넘으면 무게중심이 모호)
    for k in ('disp', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step', 'neg_end_cellsteps', 'neg_cellsteps', 'mg_err', 't_exh', 'runtime'):
        if k in met: out['m_' + k] = met[k]
    if 'hamp' in met: out['m_sheet_amp'] = met['hamp'].get('sheet_rel')
    out['rows'] = rows if verbose else None
    return out


if __name__ == '__main__':
    kind = sys.argv[1]
    for rd in sys.argv[2:]:
        o = summarise(rd, kind); o.pop('rows', None)
        print(json.dumps(o, ensure_ascii=False))
