#!/usr/bin/env python3
"""verify8 측정 코드 — 실행 폴더 하나(runs/b_<시나리오>_s<시드>_<꼬리표>)를 읽어 측정값을 JSON 으로 쓴다.

usage: measure.py RUN_DIR OUT_DIR
  -> OUT_DIR/<실행이름>.json, (균핵 분석이 있으면) OUT_DIR/<실행이름>_lump.npz

모든 연결은 토러스 위 8-연결이다. 정의는 verify8/CRITERIA.md 의 '측정 정의' 절과 같다.
모델 코드(ref_model.py 등)는 가져오지 않는다(측정의 독립성).
"""
import numpy as np, json, os, sys, glob, re
from scipy import ndimage as ndi
from scipy.stats import spearmanr

RING8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]      # (dx, dy), 고리 순서
RING16 = ([(x, -2) for x in range(-2, 3)] + [(2, y) for y in range(-1, 3)] + [(x, 2) for x in range(1, -3, -1)]
          + [(-2, y) for y in range(1, -2, -1)])                                      # 체비쇼프 거리 2 의 고리, 순서대로
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]                                             # 모델의 간선 채널 k
SQ3 = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]                           # 3x3 구조 요소
DISK2 = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3) if dx * dx + dy * dy <= 5]   # 반지름 2 원판 (21칸)

T_MIN = 60.0          # 주장 1~3: 이 시각 이후 스냅숏만
CRUMB_FRAC = 0.02     # 부스러기: 가장 큰 덩이가 아닌, 부피가 전체의 2% 미만인 연결 성분
CRUMB_FRAC2 = 0.005
BODY_FRAC = 0.10      # 몸(분열 조각): 부피가 전체의 10% 이상인 성분
BODY3 = 0.03          # 균핵 판정에서 '몸'으로 세는 하한
LUMP_FRAC = 0.10      # 아령: 몸 부피의 10% 이상인 굵은 덩이(열림 성분)가 둘 이상
THICK_H = 0.5         # 두께 기준 덩이(참고)
THREAD_MIN = 4        # 가는 실 성분의 최소 칸 수
AGE_OK = 20.0         # 흐름 창(20 시간)을 다 채운 칸만 흐름을 판단
QTHR = (0.01, 0.05, 0.2)   # 흐름 없음: 칸 흐름 < 비율 x 몸의 칸 흐름 중앙값 (0.05 가 기본)
FILM_H = 0.3          # 넓은 부분(열림 안쪽)의 얇은 막: h < 0.3


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))      # (x+dx, y+dy) 의 값
def mimg(v, N): return (v + N / 2) % N - N / 2


def label8(mask):
    """토러스 8-연결 성분. (lab, n), lab 0 = 바깥"""
    mask = np.asarray(mask, bool)
    lab, n = ndi.label(mask, structure=np.ones((3, 3), int))
    if n == 0: return lab, 0
    par = np.arange(n + 1)

    def find(a):
        r = a
        while par[r] != r: r = par[r]
        while par[a] != r: par[a], a = r, par[a]
        return r
    N0, N1 = mask.shape; pr = []
    for s in (-1, 0, 1):
        a = lab[N0 - 1, :]; b = np.roll(lab[0, :], -s); m = (a > 0) & (b > 0); pr.append(np.stack([a[m], b[m]], 1))
        a = lab[:, N1 - 1]; b = np.roll(lab[:, 0], -s); m = (a > 0) & (b > 0); pr.append(np.stack([a[m], b[m]], 1))
    for a, b in np.concatenate(pr):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb: par[rb] = ra
    roots = np.array([find(i) for i in range(n + 1)])
    u, inv = np.unique(roots, return_inverse=True)
    return inv.reshape(-1)[lab], len(u) - 1


def erode(m, se):
    o = m.copy()
    for d in se: o &= nb(m, d)
    return o


def dilate(m, se):
    o = m.copy()
    for d in se: o |= nb(m, d)
    return o


def opening(m, se): return dilate(erode(m, se), se) & m


def nwet8(w):
    n = np.zeros(w.shape, np.int16)
    for d in RING8: n += nb(w, d)
    return n


def ring_runs(bits):
    """고리 위 True 연속 구간의 수 (모두 True 면 1)"""
    r = np.zeros(bits[0].shape, np.int16)
    for i in range(len(bits)): r += (bits[i] & ~bits[i - 1])
    return np.where(np.logical_and.reduce(bits), 1, r)


def tips_claim(wet): return wet & (nwet8(wet) == 1)


def tips_robust(wet):
    """가지 끝: 젖은 이웃 1~3 이 한 구간, 거리 2 고리의 젖은 칸 1~3 이 한 구간 (실이 한쪽으로만 이어진다)"""
    b1 = [nb(wet, d) for d in RING8]; b2 = [nb(wet, d) for d in RING16]
    n1 = sum(b.astype(np.int16) for b in b1); n2 = sum(b.astype(np.int16) for b in b2)
    return wet & (n1 >= 1) & (n1 <= 3) & (ring_runs(b1) == 1) & (n2 >= 1) & (n2 <= 3) & (ring_runs(b2) == 1)


def prune_claim(wet):
    """주장 6 의 정의: 젖은 이웃이 하나뿐인 칸을 더 없을 때까지 깎는다. 깎인 칸"""
    cur = wet.copy(); rem = np.zeros_like(wet)
    for _ in range(20000):
        e = cur & (nwet8(cur) == 1)
        if not e.any(): break
        cur &= ~e; rem |= e
    return rem, cur


def cell_flux(Q):
    """칸 흐름: 칸에 닿는 간선 8개의 |Q| 창 평균 합의 절반"""
    s = np.zeros(Q.shape[1:])
    for k, d in enumerate(DIRS): s += Q[k] + np.roll(Q[k], (d[1], d[0]), (0, 1))
    return 0.5 * s


def thin_classes(wet, hp, lab, vol, se=SQ3):
    """열림(se)에서 빠지는 가는 부분의 성분을 나눈다: tail(몸 한 곳에만 붙은 매달린 실), loop(같은 덩이에 두 곳 이상), head(작은 앞머리 덩이가 달린 가지), tube(덩이 사이), free(덩이 없음)"""
    core = opening(wet, se); thin = wet & ~core
    lc, nc = label8(core); lt, nt = label8(thin)
    out = []
    if nt == 0: return out, core, thin
    far = ~dilate(dilate(core, SQ3), SQ3)      # 덩이에서 체비쇼프 거리 3 이상: 여기에 닿지 못하는 tail/loop 는 덩이 가장자리의 술(fringe)
    cvol = np.bincount(lc.ravel(), weights=np.where(core, hp, 0.0).ravel(), minlength=nc + 1)
    tarea = np.bincount(lt.ravel(), minlength=nt + 1)
    touch = {}                       # thin comp -> {core comp: contact clusters}
    cores_t = {}                     # core comp -> set(thin comps)
    if nc > 0:
        adj = dilate(thin, SQ3) & core
        for c in np.unique(lc[adj]):
            if c == 0: continue
            ct = dilate(lc == c, SQ3) & thin
            l2, n2 = label8(ct)
            if n2 == 0: continue
            tl = np.zeros(n2 + 1, np.int64); tl[l2[ct]] = lt[ct]
            for j in range(1, n2 + 1):
                t = int(tl[j]); touch.setdefault(t, {}); touch[t][int(c)] = touch[t].get(int(c), 0) + 1; cores_t.setdefault(int(c), set()).add(t)
    for t in range(1, nt + 1):
        if tarea[t] < THREAD_MIN: continue
        tm = lt == t; body = int(np.bincount(lab[tm]).argmax()); Vb = float(vol[body])
        tc = touch.get(t, {})
        if not tc: cls = 'free'
        elif len(tc) == 1: cls = 'tail' if list(tc.values())[0] == 1 else 'loop'
        else:
            cs = sorted(tc, key=lambda c: -cvol[c]); small = cs[1:]
            if all(cvol[c] < LUMP_FRAC * Vb and cores_t.get(c, set()) == {t} for c in small): cls = 'head'
            else: cls = 'tube'
        if cls in ('tail', 'loop') and not (tm & far).any(): cls = 'fringe'
        out.append(dict(cls=cls, cells=int(tarea[t]), body=body, mask=tm))
    return out, core, thin


def centered_shift(mask, N):
    ys, xs = np.nonzero(mask); a = 2 * np.pi / N
    cx = (np.arctan2(np.sin(xs * a).mean(), np.cos(xs * a).mean()) / a) % N
    cy = (np.arctan2(np.sin(ys * a).mean(), np.cos(ys * a).mean()) / a) % N
    return int(round(N / 2 - cy)), int(round(N / 2 - cx))


def lump_metrics(mask, h, N):
    """한 몸(mask)의 모양·두께: 구멍, 볼록 껍질 대비 넓이, 같은 넓이 원판과의 IoU, 두께-안쪽거리 관계"""
    from skimage.morphology import convex_hull_image
    sy, sx = centered_shift(mask, N)
    m = np.roll(mask, (sy, sx), (0, 1)); hh = np.roll(np.where(mask, np.maximum(h, 0.0), 0.0), (sy, sx), (0, 1))
    ys, xs = np.nonzero(m); A = int(m.sum())
    wraps = bool(m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any())
    filled = ndi.binary_fill_holes(m); holes = int((filled & ~m).sum())
    hull = convex_hull_image(m); sol = A / max(int(hull.sum()), 1)
    cy, cx = ys.mean(), xs.mean(); jj, ii = np.mgrid[0:N, 0:N]; R = np.sqrt(A / np.pi)
    disc = (ii - cx) ** 2 + (jj - cy) ** 2 <= R * R; iou = float((m & disc).sum() / max((m | disc).sum(), 1))
    bd = m & ~erode(m, SQ3); by, bx = np.nonzero(bd); th = np.arctan2(by - cy, bx - cx); rr = np.hypot(by - cy, bx - cx)
    bi = ((th + np.pi) / (2 * np.pi) * 36).astype(int) % 36; rmax = np.zeros(36)
    np.maximum.at(rmax, bi, rr); rmax = rmax[rmax > 0]
    rough = float(rmax.std() / rmax.mean()) if rmax.size > 3 else None
    d = ndi.distance_transform_edt(m); hv = hh[m]; dv = d[m]
    sp = float(spearmanr(hv, dv)[0]) if A >= 8 and hv.std() > 0 and dv.std() > 0 else None
    kk = np.floor(dv).astype(int); prof = []
    for k in range(1, int(kk.max()) + 1):
        s = kk == k
        if s.sum() >= 3: prof.append([k, float(hv[s].mean()), int(s.sum())])
    rim = float(hv[dv < 1.5].mean()) if (dv < 1.5).any() else None
    cen = float(hv[dv >= 0.6 * dv.max()].mean())
    ratio = cen / rim if rim and rim > 0 else None
    pm = np.array([p[1] for p in prof]) if prof else np.zeros(0)
    if pm.size >= 4 and pm.max() - pm[0] > 0:
        step = float(np.max(np.diff(pm)) / (pm.max() - pm[0])); viol = int((pm[1:] < 0.9 * pm[:-1]).sum())
    else: step = None; viol = None
    return dict(area=A, holes=holes, solidity=round(sol, 4), disc_iou=round(iou, 4), rough=None if rough is None else round(rough, 4), wraps=wraps,
                sp_h_d=None if sp is None else round(sp, 4), h_ratio=None if ratio is None else round(ratio, 4), h_cv=round(float(hv.std() / max(hv.mean(), 1e-12)), 4),
                max_step_frac=None if step is None else round(step, 4), mono_viol=viol, dmax=round(float(dv.max()), 2), prof=[[p[0], round(p[1], 4), p[2]] for p in prof]), (sy, sx)


def snap_measure(S, N, scl_lump=False):
    wet = S['wet'].astype(bool); h = S['h'].astype(float); hp = np.where(wet, np.maximum(h, 0.0), 0.0); age = S['age'].astype(float)
    Qg = S['Qgross'].astype(float)
    lab, n = label8(wet)
    vol = np.bincount(lab.ravel(), weights=hp.ravel(), minlength=n + 1); area = np.bincount(lab.ravel(), minlength=n + 1)
    vol[0] = 0.0; Vt = float(vol.sum()); main = int(np.argmax(vol)) if n else 0
    o = dict(t=round(float(S['t']), 2), area=int(wet.sum()), vol=round(Vt, 4), h_min=round(float(h[wet].min()), 6) if wet.any() else None, n_comp=int(n))
    if n == 0: return o, None
    others = [k for k in range(1, n + 1) if k != main]
    o['crumbs'] = int(sum(vol[k] < CRUMB_FRAC * Vt for k in others)); o['crumbs05'] = int(sum(vol[k] < CRUMB_FRAC2 * Vt for k in others))
    o['crumb_cells'] = int(sum(area[k] for k in others if vol[k] < CRUMB_FRAC * Vt))
    bodies = [k for k in range(1, n + 1) if vol[k] >= BODY_FRAC * Vt]; o['n_bodies10'] = len(bodies)
    o['n_bodies3'] = int(sum(vol[k] >= BODY3 * Vt for k in range(1, n + 1)))
    # ---- 주장 2: 아령 (열림 덩이) ----
    for nm, se in (('sq3', SQ3), ('d2', DISK2)):
        core = opening(wet, se); lc, nc = label8(core)
        cv = np.bincount(lc.ravel(), weights=np.where(core, hp, 0.0).ravel(), minlength=nc + 1); cv[0] = 0.0
        cb = np.zeros(nc + 1, np.int64)
        if nc: cb[lc[core]] = lab[core]
        nbig = [int(sum((cb[c] == b) and cv[c] >= LUMP_FRAC * vol[b] for c in range(1, nc + 1))) for b in bodies]
        o['nbig_' + nm] = max(nbig) if nbig else 0
    thick = wet & (h >= THICK_H); lt, ntk = label8(thick); tv = np.bincount(lt.ravel(), weights=np.where(thick, hp, 0.0).ravel(), minlength=ntk + 1); tv[0] = 0
    tb = np.zeros(ntk + 1, np.int64)
    if ntk: tb[lt[thick]] = lab[thick]
    o['nbig_thick'] = max([int(sum((tb[c] == b) and tv[c] >= LUMP_FRAC * vol[b] for c in range(1, ntk + 1))) for b in bodies] or [0])
    # ---- 주장 3: 흐름 없는 가는 실·가지 끝 ----
    q = cell_flux(Qg); ok = wet & (age >= AGE_OK)
    qmed = float(np.median(q[ok])) if ok.sum() >= 10 else None
    cls, core1, thin1 = thin_classes(wet, hp, lab, vol, SQ3)
    thread = np.zeros_like(wet)
    for c in cls:
        if c['cls'] != 'fringe': thread |= c['mask']
    o['thread_cells'] = int(thread.sum()); o['qmed'] = qmed
    tr = tips_robust(wet); tc = tips_claim(wet)
    o['tips_robust'] = label8(tr)[1]; o['tips_claim'] = int(tc.sum())
    for f in QTHR:
        key = f'{f:g}'
        if qmed is None or qmed <= 0:
            o['nf_thread_' + key] = None; o['nf_tipr_' + key] = None; o['nf_tipc_' + key] = None; continue
        nfm = ok & (q < f * qmed)
        o['nf_thread_' + key] = int((thread & nfm).sum()); o['nf_tipr_' + key] = label8(tr & nfm)[1]; o['nf_tipc_' + key] = int((tc & nfm).sum())
    o['film_cells'] = int((core1 & ok & (h < FILM_H)).sum())
    # ---- 주장 6: 막다른 실 꼬리 (주장의 정의: 이웃 하나인 끝 칸을 깎아 들어감) ----
    rem, cur = prune_claim(wet); lr, nr = label8(rem); att = dilate(cur, SQ3)
    sizes = []; free_tr = 0
    for j in range(1, nr + 1):
        m = lr == j
        if (m & att).any(): sizes.append(int(m.sum()))
        else: free_tr += 1
    o['tail_cells'] = int(sum(sizes)); o['tail_n3'] = int(sum(s >= 3 for s in sizes)); o['tail_max'] = int(max(sizes) if sizes else 0); o['tail_free'] = free_tr
    # 굳센 정의: 열림(3x3)에서 빠지고 한 덩이에 한 곳만 붙은 가는 성분
    for k_ in ('tail', 'loop', 'head', 'tube', 'free', 'fringe'):
        cc = [c for c in cls if c['cls'] == k_]
        o['th_' + k_ + '_n'] = len(cc); o['th_' + k_ + '_cells'] = int(sum(c['cells'] for c in cc)); o['th_' + k_ + '_max'] = int(max([c['cells'] for c in cc] or [0]))
    old = [c for c in cls if c['cls'] == 'tail' and float(age[c['mask']].mean()) >= AGE_OK]
    o['th_tail_old_n'] = len(old); o['th_tail_old_cells'] = int(sum(c['cells'] for c in old)); o['th_tail_old_max'] = int(max([c['cells'] for c in old] or [0]))
    # ---- 주 몸의 모양 (주장 7) ----
    mm = lab == main
    if scl_lump:
        lm, _ = lump_metrics(mm, h, N); o['lump'] = lm
        core_m = opening(mm, SQ3); lcm, ncm = label8(core_m); cvm = np.bincount(lcm.ravel(), weights=np.where(core_m, hp, 0.0).ravel(), minlength=ncm + 1); cvm[0] = 0
        o['lump']['n_core10'] = int((cvm >= LUMP_FRAC * vol[main]).sum())
        o['lump']['vol'] = round(float(vol[main]), 4)
    return o, dict(wet=wet, h=h, hp=hp, lab=lab, main=main, vol=vol)


def load_vs(f):
    Z = np.load(f, allow_pickle=True)
    return {k: Z[k] for k in Z.files}


def heading(traj, food, c0, dists=(20.0, 35.0)):
    """무게중심 변위가 처음 d 를 넘는 때의 방향과 먹이 방향의 차(도, 부호 있음: +는 반시계)"""
    tr = np.array([[a[0], a[1], a[2]] for a in traj], float)
    d = tr[:, 1:3] - tr[0, 1:3]; r = np.hypot(d[:, 0], d[:, 1])
    ga = np.degrees(np.arctan2(food[1] - c0, food[0] - c0)); out = {}
    for D in dists:
        i = np.nonzero(r >= D)[0]
        if i.size == 0: out[f'{D:g}'] = None; continue
        a = np.degrees(np.arctan2(d[i[0], 1], d[i[0], 0])); e = (a - ga + 180) % 360 - 180
        out[f'{D:g}'] = dict(t=float(tr[i[0], 0]), err=round(float(e), 2))
    return out


def disp_at(traj, t):
    tr = np.array([[a[0], a[1], a[2]] for a in traj], float); i = int(np.argmin(np.abs(tr[:, 0] - t)))
    return round(float(np.hypot(*(tr[i, 1:3] - tr[0, 1:3]))), 3), float(tr[i, 0])


def area_timing(area, dt, t_scl):
    """균핵 맺힘의 빠르기: t_scl 이후 넓이 변화가 50%, 90% 에 이른 시각과 10 시간 창 하나에 몰린 변화의 최대 몫"""
    i0 = int(round(t_scl / dt)); a = area[i0:].astype(float)
    if a.size < 2: return None
    A0 = a[0]; Ae = a[-1]; dA = A0 - Ae; out = dict(A0=int(A0), A_end=int(Ae), dA=int(dA))
    if abs(dA) < 1: out.update(t50=0.0, t90=0.0, max10=None); return out
    frac = (A0 - a) / dA
    for p in (0.1, 0.5, 0.9):
        j = np.nonzero(frac >= p)[0]; out[f't{int(p * 100)}'] = round(float(j[0] * dt), 2) if j.size else None
    w = int(round(10.0 / dt))
    out['max10'] = round(float(np.max(np.abs(a[w:] - a[:-w])) / abs(dA)), 4) if a.size > w else None
    j90 = int(round(out['t90'] / dt)) if out['t90'] is not None else None
    out['regrow_after_t90'] = round(float(a[j90:].max() / max(a[j90], 1)), 4) if j90 is not None else None
    out['A_min'] = int(a.min()); out['A_max_after'] = int(a.max())
    return out


def main(rd, od):
    name = os.path.basename(rd.rstrip('/'))
    mt = re.match(r'b_(.+)_s(\d+)_(v8[cv])$', name)
    scn, seed, tag = mt.group(1), int(mt.group(2)), mt.group(3)
    P = json.load(open(os.path.join(rd, 'params.json'))); M = json.load(open(os.path.join(rd, 'metrics.json')))
    N = int(P['N']); T = float(P['T']); dt = float(P['dt']); c0 = N / 2 - 0.5
    res = dict(run=name, scn=scn, seed=seed, arm=tag, N=N, T=T)
    keys = ('stop', 't_end', 'steps_done', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step', 'neg_end_cellsteps', 'neg_end_steps', 't_touch', 't_cover', 't_exh',
            'foods', 't_scl', 'scl_steps', 'fission_runs', 'V0', 'Vinj', 'V_end', 'V_crumb', 'crumb_cells', 'runtime', 'mg_err', 'mg_nadapt', 'mg_nguard', 'disp', 'area_end')
    res['metrics'] = {k: M.get(k) for k in keys}
    res['steps_expected'] = int(round(T / dt)) + 1
    errs = json.load(open(os.path.join(rd, 'mg_err_series.json')))
    res['mg_err_list'] = [round(float(e[1]), 6) for e in errs]
    traj = M['traj']; res['traj'] = traj
    if P.get('foods'):
        fp = M['foods']; res['heading'] = heading(traj, fp[0], c0); res['disp400'] = disp_at(traj, min(400.0, T))[0]; res['disp200'] = disp_at(traj, min(200.0, T))[0]
    t_scl = M.get('t_scl')
    vs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    snaps = []; keep = {}
    for f in vs:
        S = load_vs(f); t = float(S['t'])
        o, aux = snap_measure(S, N, scl_lump=(t_scl is not None and t >= t_scl - 20.0))
        snaps.append(o); keep[round(t, 2)] = aux
    res['snaps'] = snaps
    ser = np.load(os.path.join(rd, 'series.npz')); vol = ser['vol']
    res['vol_rel_dev_max'] = round(float(np.max(np.abs(vol - vol[0])) / vol[0]), 8) if P.get('eat', 0) == 0 else None
    if t_scl is not None and snaps:
        sc = dict(t_scl=t_scl, timing=area_timing(ser['area'], dt, t_scl))
        tt = sorted(keep); tr_ = [t for t in tt if t <= t_scl]; t_tr = tr_[-1] if tr_ else tt[0]; t_end = tt[-1]
        A = keep[t_tr]; B = keep[t_end]
        Mf = B['lab'] == B['main']; Mt = A['lab'] == A['main']
        G = ndi.gaussian_filter(A['hp'], 4.0, mode='wrap')
        sc['t_trap_snap'] = t_tr; sc['t_final'] = t_end
        sc['dens_ratio'] = round(float(G[Mf].mean() / max(G[Mt].mean(), 1e-12)), 4)
        sc['dense_frac'] = round(float((G[Mf] > np.median(G[Mt])).mean()), 4)
        sc['overlap_trap'] = round(float(A['wet'][Mf].mean()), 4)
        sc['area_final'] = int(Mf.sum()); sc['vol_final'] = round(float(B['vol'][B['main']]), 4); sc['amin'] = int(sc['vol_final'] / 3.5) + 1
        sc['area_trap'] = int(Mt.sum()); sc['n_bodies3_trap'] = next(s['n_bodies3'] for s in snaps if abs(s['t'] - t_tr) < 1e-6)
        conc = []; ious = []
        for t in tt:
            if t < t_tr: continue
            X = keep[t]; Mx = X['lab'] == X['main']
            conc.append([t, round(float(X['hp'][Mf].sum() / max(X['hp'].sum(), 1e-12)), 4)])
            ious.append([t, round(float((Mx & Mf).sum() / max((Mx | Mf).sum(), 1)), 4)])
        sc['conc'] = conc; sc['iou_final'] = ious
        lm, (sy, sx) = lump_metrics(Mf, B['h'], N); sc['lump_final'] = lm
        mr = np.roll(Mf, (sy, sx), (0, 1)); hr = np.roll(B['hp'], (sy, sx), (0, 1)); c = N // 2; w = min(48, N // 2)
        np.savez_compressed(os.path.join(od, name + '_lump.npz'), mask=mr[c - w:c + w, c - w:c + w], h=hr[c - w:c + w, c - w:c + w].astype(np.float32),
                            mask_abs=Mf, trap_wet=A['wet'], trap_G=G.astype(np.float32))
        res['scl'] = sc
    json.dump(res, open(os.path.join(od, name + '.json'), 'w'))
    print(name, 'snaps', len(snaps), 'scl', t_scl)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
