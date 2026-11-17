#!/usr/bin/env python3
"""E2-jones-at-scale: Jones 2010 입자 모델을 큰 격자에서 돌리는 numba 구현.

사용법:
  python3 jones.py NAME '{"N":1024, ...}'            # 한 번 실행
  python3 jones.py --batch batch.json                 # [{"name":..., 파라미터...}, ...] 순차 실행

규칙 (Jones IJUC10 Fig.2 / AMOE12 부록 그대로):
  motor  : 앞으로 SS(=1px) 이동 시도. 새 칸이 몸 밖이거나(갇힘) 이미 cap 개가 있으면 실패 →
           이동·침착 없이 방향을 균등 무작위로 새로 뽑는다. 성공하면 새 칸 trail += depT.
           입자 갱신 순서는 매 스텝 Fisher-Yates 로 섞는다.
  sensor : F, FL, FR = trail[ pos + SO·dir(θ), dir(θ∓SA) ].
           F>FL&&F>FR 직진 / F<FL&&F<FR 무작위 ±RA / FL<FR 이면 +RA / FR<FL 이면 −RA / 그 외 직진.
  투사   : 고정점 칸에 매 스텝 trail += w  (먹이 노드 3×3, 전진면 띠).
  확산   : trail ← 3×3 평균 × (1−damp).  (토러스, 몸 밖으로도 번지되 몸 밖은 침착이 없어 곧 사라진다.)
  SO 구배: SO(x) = SO + (SO_rear − SO)·age01(x)^so_pow,  age01 = 전진면에서 0, 가장 오래된 곳에서 1.
  이동띠 : 몸 = 토러스 위 폭 W 의 띠(y 주기). 전진면이 v px/스텝으로 +x 이동. 뒤에서 벗어난 입자는
           새로 젖은 전진면 열의 무작위 빈 칸으로 옮긴다(입자 수 보존).
초기 조건: 입자는 몸 칸에 균등 무작위(셀당 1개 제한이 켜져 있으면 서로 다른 칸), 방향 균등 무작위. trail = 0.
"""
import os, sys, json, time, math, subprocess
import numpy as np
from numba import njit, prange
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.morphology import skeletonize, remove_small_objects, remove_small_holes
from skimage.measure import label, euler_number

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(os.path.dirname(HERE), 'common', 'eval_morph.py')
TWO_PI = 2.0 * math.pi

DEFAULTS = dict(
    N=1024, steps=16000, seed=1,
    geom='disk',            # disk | fan | band
    R=420.0,                # disk 반지름 (px)
    fan_R=860.0, fan_half=35.0,   # fan: 꼭짓점(뒤) (N/2, N-70), 위쪽으로 열린 부채꼴
    band_W=640, band_v=0.0, # band: 폭 W(진행 방향 길이), 전진 속도 px/스텝
    dens=0.10,              # 입자 수 / 몸 칸 수
    SA=22.5, RA=45.0, SO=9.0, SO_rear=None, so_pow=1.0,
    depT=5.0, damp=0.1, cap=1,      # cap=0 → 점유 제한 없음
    nodes=0, node_w=5.0, node_supp=1.0, node_sep=60.0,
    front_w=0.0, front_width=3,
    n_eval=24, n_snap=5, acc=40,
)

# ---------------------------------------------------------------- numba kernels
@njit(cache=True)
def nb_seed(s):
    np.random.seed(s)

@njit(cache=True)
def particles_step(px, py, hx, hy, order, trail, occ, body, somap, cap, cSA, sSA, cRA, sRA, depT, M):
    n = px.shape[0]
    N = M + 1
    fN = float(N)
    for i in range(n - 1, 0, -1):
        j = int(np.random.random() * (i + 1))
        t = order[i]; order[i] = order[j]; order[j] = t
    moved = 0
    for k in range(n):
        i = order[k]
        x = px[i]; y = py[i]
        nx = x + hx[i]; ny = y + hy[i]
        if nx < 0.0: nx += fN
        elif nx >= fN: nx -= fN
        if ny < 0.0: ny += fN
        elif ny >= fN: ny -= fN
        ix = int(nx); iy = int(ny); ox = int(x); oy = int(y)
        same = (ix == ox) and (iy == oy)
        ok = body[iy, ix] != 0
        if ok and (not same) and cap > 0 and occ[iy, ix] >= cap:
            ok = False
        if ok:
            if not same:
                occ[oy, ox] -= 1
                occ[iy, ix] += 1
            px[i] = nx; py[i] = ny
            trail[iy, ix] += depT
            moved += 1
        else:
            a = np.random.random() * TWO_PI
            hx[i] = math.cos(a); hy[i] = math.sin(a)
    for i in range(n):
        x = px[i]; y = py[i]; cx = hx[i]; cy = hy[i]
        so = somap[int(y), int(x)]
        lx = cx * cSA + cy * sSA; ly = -cx * sSA + cy * cSA
        rx = cx * cSA - cy * sSA; ry = cx * sSA + cy * cSA
        f = trail[int(y + so * cy + fN) & M, int(x + so * cx + fN) & M]
        fl = trail[int(y + so * ly + fN) & M, int(x + so * lx + fN) & M]
        fr = trail[int(y + so * ry + fN) & M, int(x + so * rx + fN) & M]
        turn = 0
        if f > fl and f > fr:
            turn = 0
        elif f < fl and f < fr:
            turn = 1 if np.random.random() < 0.5 else -1
        elif fl < fr:
            turn = 1
        elif fr < fl:
            turn = -1
        if turn != 0:
            s = sRA * turn
            ax = cx * cRA - cy * s; ay = cx * s + cy * cRA
            nrm = 1.5 - 0.5 * (ax * ax + ay * ay)
            hx[i] = ax * nrm; hy[i] = ay * nrm
    return moved

@njit(cache=True, parallel=True)
def diffuse(trail, tmp, k):
    N = trail.shape[0]
    for y in prange(N):
        row = trail[y]; out = tmp[y]
        out[0] = row[N - 1] + row[0] + row[1]
        for x in range(1, N - 1):
            out[x] = row[x - 1] + row[x] + row[x + 1]
        out[N - 1] = row[N - 2] + row[N - 1] + row[0]
    for y in prange(N):
        ym = y - 1 if y > 0 else N - 1
        yp = y + 1 if y < N - 1 else 0
        a = tmp[ym]; b = tmp[y]; c = tmp[yp]; out = trail[y]
        for x in range(N):
            out[x] = (a[x] + b[x] + c[x]) * k

@njit(cache=True)
def band_advance(xf, W, body, somap, so_lut, use_lut, sx, fwidth, px, py, hx, hy, occ, cap, M):
    """전진면을 +x 로 1칸 옮긴다. 반환: 새 xf."""
    N = M + 1
    xf_new = (xf + 1) & M
    leave = (xf_new - W) & M
    for y in range(N):
        body[y, leave] = 0
        body[y, xf_new] = 1
    if use_lut:
        for c in range(W):
            x = (xf_new - c) & M
            v = so_lut[c]
            for y in range(N):
                somap[y, x] = v
    if sx.shape[0] > 0:
        for j in range(fwidth):
            x = (xf_new - j) & M
            for y in range(N):
                sx[j * N + y] = x
    n = px.shape[0]
    for i in range(n):
        ix = int(px[i]); iy = int(py[i])
        if body[iy, ix] == 0:
            occ[iy, ix] -= 1
            yy = 0
            for tries in range(60):
                yy = int(np.random.random() * N)
                if cap <= 0 or occ[yy, xf_new] < cap:
                    break
            occ[yy, xf_new] += 1
            px[i] = xf_new + np.random.random(); py[i] = yy + np.random.random()
            a = np.random.random() * TWO_PI
            hx[i] = math.cos(a); hy[i] = math.sin(a)
    return xf_new

@njit(cache=True)
def run_chunk(nsteps, nacc, acc, px, py, hx, hy, order, trail, tmp, occ, body, somap, cap,
              cSA, sSA, cRA, sRA, depT, M, kdiff, sy, sx, sval, supp,
              band, bstate, W, so_lut, use_lut, fwidth, v):
    moved = 0
    for s in range(nsteps):
        if band:
            bstate[1] += v
            while bstate[1] >= 1.0:
                bstate[1] -= 1.0
                bstate[0] = band_advance(int(bstate[0]), W, body, somap, so_lut, use_lut, sx, fwidth,
                                         px, py, hx, hy, occ, cap, M)
        moved = particles_step(px, py, hx, hy, order, trail, occ, body, somap, cap, cSA, sSA, cRA, sRA, depT, M)
        for j in range(sval.shape[0]):
            val = sval[j]
            if supp < 1.0 and occ[sy[j], sx[j]] > 0:
                val *= supp
            trail[sy[j], sx[j]] += val
        diffuse(trail, tmp, kdiff)
        if s >= nsteps - nacc:
            for y in range(acc.shape[0]):
                for x in range(acc.shape[1]):
                    acc[y, x] += trail[y, x]
    return moved

# ---------------------------------------------------------------- metrics (eval_morph.py 의 정맥 부분과 같은 정의)
def vein_metrics(bm, vein, age=None, rel=0.35):
    out = {}
    area = int(bm.sum())
    vin = vein[bm]
    p99 = float(np.percentile(vin, 99))
    vm = bm & (vein > rel * p99) & (p99 > 0)
    vm = remove_small_objects(vm, 8)
    vm = remove_small_holes(vm, 6)
    va = int(vm.sum())
    out['vein_area_frac'] = round(va / area, 4)
    out['p99'] = round(p99, 3)
    if va < 20:
        out.update(branch_points=0, loops=0, skeleton_len=0, vein_largest_frac=0.0, endpoints=0)
        return out
    vlab = label(vm, connectivity=2)
    sizes = np.bincount(vlab.ravel())[1:]
    out['vein_components'] = int(len(sizes))
    out['vein_largest_frac'] = round(float(sizes.max() / va), 3)
    out['loops'] = int(len(sizes) - euler_number(vm, connectivity=2))
    sk = skeletonize(vm)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - sk
    ends = sk & (nb == 1)
    junc = sk & (nb >= 3)
    jl, nj = ndi.label(ndi.binary_dilation(junc, iterations=1), structure=np.ones((3, 3)))
    out['skeleton_len'] = int(sk.sum())
    out['branch_points'] = int(nj)
    out['endpoints'] = int(ends.sum())
    dt = ndi.distance_transform_edt(vm)
    wmap = 2 * dt
    w = wmap[sk]; w = w[w > 0]
    p10, p50, p90 = [float(v) for v in np.percentile(w, [10, 50, 90])]
    out.update(width_p10=round(p10, 2), width_p50=round(p50, 2), width_p90=round(p90, 2),
               width_ratio_p90_p10=round(p90 / max(p10, 1e-6), 2))
    vs = vein[sk]
    out['strength_ratio_p90_p10'] = round(float(np.percentile(vs, 90) / max(np.percentile(vs, 10), 1e-12)), 2)
    # 구멍(그물눈) 크기: 정맥 마스크의 여집합 중 몸 안 성분
    holes = label(bm & ~vm, connectivity=1)
    hs = np.bincount(holes.ravel())[1:]
    hs = hs[hs >= 12]
    if len(hs):
        out['mesh_count'] = int(len(hs))
        out['mesh_area_median'] = float(np.median(hs))
        out['mesh_area_mean'] = round(float(hs.mean()), 1)
    # 나이(앞→뒤) 3등분별: 뼈대 길이 밀도, 폭 중앙값, 분기점 수
    if age is not None:
        jc = junc
        zones = {}
        for name, lo, hi in (('front', 0.0, 1 / 3), ('mid', 1 / 3, 2 / 3), ('rear', 2 / 3, 1.01)):
            z = bm & (age >= lo) & (age < hi)
            za = int(z.sum())
            if za < 100:
                continue
            zs = sk & z
            ww = wmap[zs]; ww = ww[ww > 0]
            _, znj = ndi.label(ndi.binary_dilation(jc, iterations=1) & z, structure=np.ones((3, 3)))
            zones[name] = dict(area=za, skel_per_1000px=round(float(zs.sum()) / za * 1000, 2),
                               bp_per_1e4px=round(znj / za * 1e4, 2),
                               width_median=round(float(np.median(ww)), 2) if len(ww) else 0.0,
                               width_p90=round(float(np.percentile(ww, 90)), 2) if len(ww) else 0.0,
                               strength_median=round(float(np.median(vein[zs])), 2) if zs.any() else 0.0,
                               vein_frac=round(float((vm & z).sum()) / za, 4))
        out['zones'] = zones
        if 'front' in zones and 'rear' in zones:
            f, r = zones['front'], zones['rear']
            out['rear_over_front_width'] = round(r['width_median'] / max(f['width_median'], 1e-6), 2)
            out['front_over_rear_skel_density'] = round(f['skel_per_1000px'] / max(r['skel_per_1000px'], 1e-6), 2)
            out['rear_over_front_strength'] = round(r['strength_median'] / max(f['strength_median'], 1e-6), 2)
    return out

# ---------------------------------------------------------------- setup
def build_geometry(P, rng):
    N = P['N']
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    g = P['geom']
    info = {}
    if g == 'disk':
        cx = cy = N / 2
        r = np.hypot(xx - cx, yy - cy)
        body = r < P['R']
        age = np.clip(1 - r / P['R'], 0, 1)          # 가장자리(전진면)=0, 중심=1
        front = body & (r >= P['R'] - P['front_width'])
    elif g == 'fan':
        ax, ay = N / 2, N - 70.0
        dx, dy = xx - ax, ay - yy
        d = np.hypot(dx, dy)
        th = np.degrees(np.arctan2(dx, dy))
        body = (d < P['fan_R']) & (np.abs(th) < P['fan_half'])
        age = np.clip(1 - d / P['fan_R'], 0, 1)      # 호(전진면)=0, 꼭짓점=1
        front = body & (d >= P['fan_R'] - P['front_width'])
        info['apex'] = (ax, ay)
    elif g == 'band':
        W = int(P['band_W'])
        xf = W + 20
        dxb = (xf - xx).astype(np.int32)
        body = (dxb >= 0) & (dxb < W)
        age = np.clip(dxb / float(W - 1), 0, 1)
        front = body & (dxb < P['front_width'])
        info['xf0'] = xf
    else:
        raise ValueError(g)
    return body, age.astype(np.float32), front, info

def place_nodes(P, body, age, rng):
    """먹이 노드: 몸 안 균등 무작위, 서로 node_sep 이상, 경계에서 15px 이상. (경로는 심지 않는다.)"""
    k = int(P['nodes'])
    if k <= 0:
        return []
    inner = ndi.binary_erosion(body, iterations=15)
    ys, xs = np.nonzero(inner)
    pts = []
    tries = 0
    while len(pts) < k and tries < 20000:
        tries += 1
        j = rng.integers(len(ys))
        p = (int(xs[j]), int(ys[j]))
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 >= P['node_sep'] ** 2 for q in pts):
            pts.append(p)
    return pts

def render(body, trail, nodes, ref, label_txt, front=None):
    N = body.shape[0]
    img = np.zeros((N, N, 3), np.float32)
    img[body] = (26, 32, 22)
    tv = np.clip(trail / ref, 0, 1) ** 0.6
    img += tv[..., None] * np.array([255, 214, 70], np.float32)
    img = np.clip(img, 0, 255).astype(np.uint8)
    for (x, y) in nodes:
        img[max(y - 3, 0):y + 4, max(x - 3, 0):x + 4] = (80, 220, 255)
    im = Image.fromarray(img)
    if N > 1024:
        im = im.resize((1024, 1024), Image.BILINEAR)
    d = ImageDraw.Draw(im)
    d.text((6, 4), label_txt, fill=(255, 255, 255))
    return im

def run(name, overrides):
    P = dict(DEFAULTS); P.update(overrides)
    out = os.path.join(HERE, 'runs', name)
    os.makedirs(out, exist_ok=True)
    N = int(P['N']); M = N - 1
    assert N & M == 0, 'N 은 2의 거듭제곱'
    rng = np.random.default_rng(P['seed'])
    nb_seed(int(P['seed']) * 7919 + 13)
    body_b, age, front, info = build_geometry(P, rng)
    body = body_b.astype(np.uint8)
    area = int(body_b.sum())
    cap = int(P['cap'])
    n = int(round(P['dens'] * area))
    if cap > 0:
        n = min(n, int(0.95 * area * cap))
    flat = np.flatnonzero(body_b)
    if cap == 1:
        cells = rng.choice(flat, n, replace=False)
    else:
        cells = rng.choice(flat, n, replace=True)
    py = (cells // N).astype(np.float64) + rng.uniform(0, 1, n)
    px = (cells % N).astype(np.float64) + rng.uniform(0, 1, n)
    a0 = rng.uniform(0, TWO_PI, n)
    hx = np.cos(a0); hy = np.sin(a0)
    occ = np.zeros((N, N), np.int32)
    np.add.at(occ, (py.astype(np.int64), px.astype(np.int64)), 1)
    order = np.arange(n, dtype=np.int64)
    trail = np.zeros((N, N), np.float32); tmp = np.zeros_like(trail); acc = np.zeros_like(trail)
    SO = float(P['SO'])
    use_grad = P['SO_rear'] is not None
    if use_grad:
        somap = (SO + (float(P['SO_rear']) - SO) * age ** P['so_pow']).astype(np.float32)
    else:
        somap = np.full((N, N), SO, np.float32)
    band = P['geom'] == 'band'
    W = int(P['band_W']) if band else 1
    so_lut = np.zeros(max(W, 1), np.float32)
    if band:
        c = np.arange(W) / float(W - 1)
        so_lut[:] = SO + ((float(P['SO_rear']) - SO) * c ** P['so_pow'] if use_grad else 0.0)
    # 고정점
    nodes = place_nodes(P, body_b, age, rng)
    sy_l, sx_l, sv_l = [], [], []
    fwidth = int(P['front_width'])
    if P['front_w'] > 0:
        if band:  # 열 단위로 정렬된 배열 (band_advance 가 sx 를 다시 쓴다)
            xf0 = info['xf0']
            for j in range(fwidth):
                sy_l += list(range(N)); sx_l += [(xf0 - j) & M] * N; sv_l += [P['front_w']] * N
        else:
            fy, fx = np.nonzero(front)
            sy_l += fy.tolist(); sx_l += fx.tolist(); sv_l += [P['front_w']] * len(fy)
    for (x, y) in nodes:
        for ddy in (-1, 0, 1):
            for ddx in (-1, 0, 1):
                sy_l.append(y + ddy); sx_l.append(x + ddx); sv_l.append(P['node_w'])
    sy = np.array(sy_l, np.int64); sx = np.array(sx_l, np.int64); sval = np.array(sv_l, np.float32)
    if band and P['front_w'] <= 0:
        sx_band = np.zeros(0, np.int64)
    bstate = np.array([float(info.get('xf0', 0)), 0.0])
    if band and len(nodes) > 0:
        raise ValueError('band + nodes 는 지원하지 않음')
    cSA, sSA = math.cos(math.radians(P['SA'])), math.sin(math.radians(P['SA']))
    cRA, sRA = math.cos(math.radians(P['RA'])), math.sin(math.radians(P['RA']))
    kdiff = np.float32((1.0 - P['damp']) / 9.0)
    steps = int(P['steps']); nacc = int(P['acc'])
    # 평가 시점: 로그 간격 + 마지막
    ev = np.unique(np.round(np.geomspace(max(200, nacc + 10), steps, int(P['n_eval']))).astype(int))
    snap_at = set(int(v) for v in ev[np.linspace(0, len(ev) - 1, int(P['n_snap'])).round().astype(int)])
    P_out = dict(P); P_out.update(n_particles=n, body_area=area, node_xy=nodes,
                                  init='particles uniform random in body cells, random headings, trail=0')
    json.dump(P_out, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    curve = []; ims = []
    t = 0; ref = None; t0 = time.time(); moved = 0
    vein = trail
    for te in ev:
        nst = int(te - t)
        if nst <= 0:
            continue
        acc[:] = 0
        moved = run_chunk(nst, min(nacc, nst), acc, px, py, hx, hy, order, trail, tmp, occ, body, somap, cap,
                          cSA, sSA, cRA, sRA, np.float32(P['depT']), M, kdiff, sy, sx, sval, float(P['node_supp']),
                          band, bstate, W, so_lut, use_grad, fwidth, float(P['band_v']))
        t = int(te)
        vein = acc / float(min(nacc, nst))
        bm = body > 0
        if band:
            xf = int(bstate[0])
            xx = np.arange(N)[None, :]
            age = np.broadcast_to(np.clip(((xf - xx) & M) / float(W - 1), 0, 1), (N, N)).astype(np.float32)
        m = vein_metrics(bm, vein, age)
        m['t'] = t; m['moved_frac'] = round(moved / n, 3)
        curve.append(m)
        if t in snap_at:
            if ref is None:
                ref = max(float(np.percentile(vein[bm], 99.5)), 1e-6)
            txt = f"{name}  t={t}  BP={m.get('branch_points')} loops={m.get('loops')} moved={m['moved_frac']}"
            im = render(bm, vein, nodes, ref, txt)
            im.save(os.path.join(out, f'snapshot_{t:06d}.png'))
            ims.append(im)
        print(f"[{name}] t={t} BP={m.get('branch_points')} loops={m.get('loops')} vfrac={m.get('vein_area_frac')} "
              f"wmed={m.get('width_p50')} moved={m['moved_frac']} ({time.time() - t0:.0f}s)", flush=True)
    # 저장
    bm = body > 0
    # body.npy = 원형질 양: 몸 마스크 × (1 + 국소 입자 밀도). 0 = 몸 밖.
    dens_map = ndi.uniform_filter((occ > 0).astype(np.float32), 9, mode='wrap')
    np.save(os.path.join(out, 'body.npy'), (bm * (1.0 + dens_map)).astype(np.float32))
    np.save(os.path.join(out, 'vein.npy'), vein.astype(np.float32))
    np.save(os.path.join(out, 'occ.npy'), (occ > 0).astype(np.uint8))
    json.dump(dict(curve=curve, wall_s=round(time.time() - t0, 1), n_particles=n, body_area=area),
              open(os.path.join(out, 'curve.json'), 'w'), indent=1)
    # 몽타주
    k = len(ims)
    if k:
        s = 512 if N >= 512 else N
        mont = Image.new('RGB', (s * k, s))
        for i, im in enumerate(ims):
            mont.paste(im.resize((s, s), Image.BILINEAR), (i * s, 0))
        mont.save(os.path.join(out, 'montage.png'))
    r = subprocess.run([sys.executable, EVAL, os.path.join(out, 'body.npy'), os.path.join(out, 'vein.npy'),
                        '--out', os.path.join(out, 'eval.json'), '--png', os.path.join(out, 'overlay.png')],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print('eval failed', r.stderr[-500:])
    print(f"[{name}] done wall={time.time() - t0:.0f}s n={n} area={area}", flush=True)
    return curve

if __name__ == '__main__':
    if sys.argv[1] == '--batch':
        for job in json.load(open(sys.argv[2])):
            job = dict(job); nm = job.pop('name')
            run(nm, job)
    else:
        run(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
