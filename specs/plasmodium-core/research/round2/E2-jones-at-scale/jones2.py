#!/usr/bin/env python3
"""E2-jones-at-scale 2차: jones.py(전임자 코드)를 확장한 판. 핵심 motor/sensor/확산 규칙은 jones.py 와 동일.

추가한 것:
  geom='growdisk' : 반지름 R(t)=min(R0+v·t, R) 로 커지는 원반(중심 고정). 전진면 = 테두리.
  geom='movedisk' : 반지름 R 의 원반이 +x 로 v px/스텝 병진(토러스). 전진면 = 앞쪽 반원.
  front_inject=p  : 새로 젖은 칸마다 확률 p 로 입자 1개 생성(방향 균등 무작위). "전진면에서 입자 생성"의 단순형.
  exit_mode       : movedisk 에서 몸 밖에 남은 입자 처리. 'relocate' = 이번에 새로 젖은 칸 중 무작위 빈 칸으로 옮김(입자 수 보존),
                    'delete' = 삭제.
  grow=1          : Jones 성장 규칙(SHAPE15 7.5). Gf 스텝마다, 이번 스텝에 이동에 성공한 입자에 대해
                    Gw×Gw 창의 점유 칸 수 c(자기 포함)가 Gmin<=c<=Gmax 이고 age<=grow_age_max 이면
                    3×3 이웃 중 무작위 한 칸(자기 칸 제외)을 골라 몸 안·빈 칸이면 새 입자(방향 무작위).
  shrink=1        : Jones 수축 규칙. Sf 스텝마다 모든 입자에 대해 Sw×Sw 창 점유 칸 수 c(자기 포함)가
                    c<Smin 또는 c>Smax 이면 삭제(먼저 전부 판정한 뒤 한꺼번에 삭제).
  so_mix=[[so,frac],...] : 입자마다 고정 SO 를 비율대로 무작위 배정(SO 혼합). 없으면 somap(나이 구배) 사용.
초기 조건: 입자는 초기 몸 칸에 균등 무작위(셀당 1개), 방향 균등 무작위, trail=0. 경로를 심지 않는다.
"""
import os, sys, json, time, math, subprocess
import numpy as np
from numba import njit
from PIL import Image
from scipy import ndimage as ndi
import jones as J1
from jones import diffuse, vein_metrics, render, nb_seed, place_nodes

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = J1.EVAL
TWO_PI = 2.0 * math.pi

DEFAULTS = dict(J1.DEFAULTS)
DEFAULTS.update(N=512, R=220.0, steps=8000, SO=7.0,
                R0=60.0, v=0.0, front_inject=0.0, exit_mode='relocate',
                grow=0, Gw=9, Gmin=1, Gmax=10, Gf=3, grow_age_max=1.0,
                shrink=0, Sw=5, Smin=0, Smax=24, Sf=3,
                so_mix=None, sync=0, diff_passes=1, n_eval=20, n_snap=5)

@njit(cache=False)
def particles_step2(n, px, py, hx, hy, sop, mv, order, trail, occ, body, somap, cap, cSA, sSA, cRA, sRA, depT, M):
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
            mv[i] = 1
        else:
            a = np.random.random() * TWO_PI
            hx[i] = math.cos(a); hy[i] = math.sin(a)
            mv[i] = 0
    for i in range(n):
        x = px[i]; y = py[i]; cx = hx[i]; cy = hy[i]
        so = sop[i]
        if so <= 0.0:
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

@njit(cache=False)
def particles_step_sync(n, px, py, hx, hy, sop, mv, prio, cval, cid, trail, occ, body, somap, cSA, sSA, cRA, sRA, depT, M):
    """GPU 식 동기 갱신(2패스 claim, cap=1 전용).
    패스1: 모든 입자가 '이전 상태' 기준으로 목표 칸(pos+dir)을 계산. 목표가 몸 안이고 이전 상태에서 비어 있으면
           무작위 우선순위로 claim (칸마다 최대 우선순위 1개만 남음 = MAX 블렌딩/깊이 테스트).
    패스2: 자기 claim 이 이긴 입자만 이동·침착. 나머지는 제자리 + 방향 무작위. (이번 스텝에 비워지는 칸으로는 못 들어간다.)"""
    N = M + 1
    fN = float(N)
    for i in range(n):
        nx = px[i] + hx[i]; ny = py[i] + hy[i]
        if nx < 0.0: nx += fN
        elif nx >= fN: nx -= fN
        if ny < 0.0: ny += fN
        elif ny >= fN: ny -= fN
        ix = int(nx); iy = int(ny)
        if (ix != int(px[i]) or iy != int(py[i])) and body[iy, ix] != 0 and occ[iy, ix] == 0:
            p = np.float32(np.random.random()) + np.float32(1e-6)
            prio[i] = p
            if p > cval[iy, ix]:
                cval[iy, ix] = p; cid[iy, ix] = i
        else:
            prio[i] = 0.0
    moved = 0
    for i in range(n):
        x = px[i]; y = py[i]
        nx = x + hx[i]; ny = y + hy[i]
        if nx < 0.0: nx += fN
        elif nx >= fN: nx -= fN
        if ny < 0.0: ny += fN
        elif ny >= fN: ny -= fN
        ix = int(nx); iy = int(ny); ox = int(x); oy = int(y)
        same = (ix == ox) and (iy == oy)
        ok = False
        if same:
            ok = body[iy, ix] != 0
        elif prio[i] > 0.0 and cid[iy, ix] == i:
            ok = True
        if ok:
            if not same:
                occ[oy, ox] -= 1
                occ[iy, ix] += 1
            px[i] = nx; py[i] = ny
            trail[iy, ix] += depT
            moved += 1
            mv[i] = 1
        else:
            a = np.random.random() * TWO_PI
            hx[i] = math.cos(a); hy[i] = math.sin(a)
            mv[i] = 0
        if prio[i] > 0.0:
            cval[iy, ix] = 0.0
    for i in range(n):
        x = px[i]; y = py[i]; cx = hx[i]; cy = hy[i]
        so = sop[i]
        if so <= 0.0:
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

@njit(cache=False)
def draw_so(mix_vals, mix_cum):
    if mix_vals.shape[0] == 0:
        return 0.0
    u = np.random.random()
    for k in range(mix_vals.shape[0]):
        if u <= mix_cum[k]:
            return mix_vals[k]
    return mix_vals[-1]

@njit(cache=False)
def grow_step(n, nmax, px, py, hx, hy, sop, mv, occ, body, agemap, Gw, Gmin, Gmax, grow_age_max, M, mix_vals, mix_cum):
    r = Gw // 2
    n0 = n
    for i in range(n0):
        if mv[i] == 0:
            continue
        ix = int(px[i]); iy = int(py[i])
        if agemap[iy, ix] > grow_age_max:
            continue
        c = 0
        for dy in range(-r, r + 1):
            yy = (iy + dy) & M
            for dx in range(-r, r + 1):
                if occ[yy, (ix + dx) & M] > 0:
                    c += 1
        if c >= Gmin and c <= Gmax and n < nmax:
            k = int(np.random.random() * 8)
            if k >= 4:
                k += 1
            xx = (ix + (k % 3) - 1) & M; yy = (iy + (k // 3) - 1) & M
            if body[yy, xx] != 0 and occ[yy, xx] == 0:
                px[n] = xx + np.random.random(); py[n] = yy + np.random.random()
                a = np.random.random() * TWO_PI
                hx[n] = math.cos(a); hy[n] = math.sin(a)
                sop[n] = draw_so(mix_vals, mix_cum)
                mv[n] = 0
                occ[yy, xx] += 1
                n += 1
    return n

@njit(cache=False)
def remove_tagged(n, tag, px, py, hx, hy, sop, mv, occ):
    i = 0
    while i < n:
        if tag[i] != 0:
            occ[int(py[i]), int(px[i])] -= 1
            n -= 1
            px[i] = px[n]; py[i] = py[n]; hx[i] = hx[n]; hy[i] = hy[n]; sop[i] = sop[n]; mv[i] = mv[n]
            tag[i] = tag[n]; tag[n] = 0
        else:
            i += 1
    return n

@njit(cache=False)
def shrink_step(n, tag, px, py, hx, hy, sop, mv, occ, Sw, Smin, Smax, M):
    r = Sw // 2
    for i in range(n):
        ix = int(px[i]); iy = int(py[i])
        c = 0
        for dy in range(-r, r + 1):
            yy = (iy + dy) & M
            for dx in range(-r, r + 1):
                if occ[yy, (ix + dx) & M] > 0:
                    c += 1
        tag[i] = 1 if (c < Smin or c > Smax) else 0
    return remove_tagged(n, tag, px, py, hx, hy, sop, mv, occ)

@njit(cache=False)
def run_chunk2(nsteps, t0, do_acc, acc, nstate, nmax, px, py, hx, hy, sop, mv, tag, order, trail, tmp, occ, body, somap, agemap,
               sync, prio, cval, cid, dpass,
               cap, cSA, sSA, cRA, sRA, depT, M, kdiff, sy, sx, sval, supp,
               grow, Gw, Gmin, Gmax, Gf, grow_age_max, shrink, Sw, Smin, Smax, Sf, mix_vals, mix_cum):
    n = nstate[0]
    moved = 0
    for s in range(nsteps):
        t = t0 + s + 1
        if sync:
            moved = particles_step_sync(n, px, py, hx, hy, sop, mv, prio, cval, cid, trail, occ, body, somap, cSA, sSA, cRA, sRA, depT, M)
        else:
            moved = particles_step2(n, px, py, hx, hy, sop, mv, order, trail, occ, body, somap, cap, cSA, sSA, cRA, sRA, depT, M)
        n_old = n
        if grow and (t % Gf == 0):
            n = grow_step(n, nmax, px, py, hx, hy, sop, mv, occ, body, agemap, Gw, Gmin, Gmax, grow_age_max, M, mix_vals, mix_cum)
        if shrink and (t % Sf == 0):
            n = shrink_step(n, tag, px, py, hx, hy, sop, mv, occ, Sw, Smin, Smax, M)
        if n != n_old or (shrink and (t % Sf == 0)):
            for i in range(n):
                order[i] = i
        for j in range(sval.shape[0]):
            val = sval[j]
            if supp < 1.0 and occ[sy[j], sx[j]] > 0:
                val *= supp
            trail[sy[j], sx[j]] += val
        for dp in range(dpass - 1):
            diffuse(trail, tmp, np.float32(1.0 / 9.0))
        diffuse(trail, tmp, kdiff)
        if do_acc:
            for y in range(acc.shape[0]):
                for x in range(acc.shape[1]):
                    acc[y, x] += trail[y, x]
    nstate[0] = n
    return moved

# ---------------------------------------------------------------- 기하
def geometry(P, t, grids):
    """현재 시각 t 의 (body bool, age01 float32, front bool)."""
    N = P['N']; xx, yy = grids
    g = P['geom']
    fw = P['front_width']
    if g == 'disk':
        r = np.hypot(xx - N / 2, yy - N / 2); R = P['R']
        return r < R, np.clip(1 - r / R, 0, 1).astype(np.float32), (r < R) & (r >= R - fw)
    if g == 'growdisk':
        r = np.hypot(xx - N / 2, yy - N / 2); R = min(P['R0'] + math.floor(P['v'] * t), P['R'])
        return r < R, np.clip(1 - r / R, 0, 1).astype(np.float32), (r < R) & (r >= R - fw)
    if g == 'movedisk':
        R = P['R']
        cx = (N / 2 + math.floor(P['v'] * t)) % N
        dx = (xx - cx + N / 2) % N - N / 2; dy = yy - N / 2
        r = np.hypot(dx, dy)
        body = r < R
        lead = np.sqrt(np.clip(R * R - dy * dy, 0, None))       # 같은 y 에서 앞 가장자리까지의 x 거리
        behind = lead - dx
        age = np.clip(behind / (2 * R), 0, 1).astype(np.float32)
        front = body & (behind < fw)
        return body, age, front
    if g == 'fan':
        ax, ay = N / 2, N - 40.0
        ddx, ddy = xx - ax, ay - yy
        d = np.hypot(ddx, ddy); th = np.degrees(np.arctan2(ddx, ddy))
        body = (d < P['fan_R']) & (np.abs(th) < P['fan_half'])
        return body, np.clip(1 - d / P['fan_R'], 0, 1).astype(np.float32), body & (d >= P['fan_R'] - fw)
    raise ValueError(g)

def run(name, overrides):
    P = dict(DEFAULTS); P.update(overrides)
    out = os.path.join(HERE, 'runs', name)
    os.makedirs(out, exist_ok=True)
    N = int(P['N']); M = N - 1
    assert N & M == 0
    rng = np.random.default_rng(P['seed'])
    nb_seed(int(P['seed']) * 7919 + 13)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    grids = (xx, yy)
    body_b, age, front = geometry(P, 0, grids)
    body = body_b.astype(np.uint8)
    area0 = int(body_b.sum())
    cap = int(P['cap'])
    n = int(round(P['dens'] * area0))
    flat = np.flatnonzero(body_b)
    cells = rng.choice(flat, n, replace=(cap != 1))
    nmax = int(0.9 * N * N)
    px = np.zeros(nmax); py = np.zeros(nmax); hx = np.zeros(nmax); hy = np.zeros(nmax)
    sop = np.zeros(nmax, np.float32); mv = np.zeros(nmax, np.uint8); tag = np.zeros(nmax, np.uint8)
    order = np.arange(nmax, dtype=np.int64)
    prio = np.zeros(nmax, np.float32); cval = np.zeros((N, N), np.float32); cid = np.zeros((N, N), np.int64)
    if P['sync']:
        assert cap == 1, 'sync 는 cap=1 전용'
    py[:n] = (cells // N) + rng.uniform(0, 1, n); px[:n] = (cells % N) + rng.uniform(0, 1, n)
    a0 = rng.uniform(0, TWO_PI, n); hx[:n] = np.cos(a0); hy[:n] = np.sin(a0)
    if P['so_mix']:
        mix_vals = np.array([m[0] for m in P['so_mix']], np.float32)
        fr = np.array([m[1] for m in P['so_mix']], np.float64); mix_cum = np.cumsum(fr / fr.sum())
        sop[:n] = mix_vals[np.searchsorted(mix_cum, rng.uniform(0, 1, n)).clip(0, len(mix_vals) - 1)]
    else:
        mix_vals = np.zeros(0, np.float32); mix_cum = np.zeros(0, np.float64)
    occ = np.zeros((N, N), np.int32)
    np.add.at(occ, (py[:n].astype(np.int64), px[:n].astype(np.int64)), 1)
    trail = np.zeros((N, N), np.float32); tmp = np.zeros_like(trail); acc = np.zeros_like(trail)
    SO = float(P['SO']); use_grad = P['SO_rear'] is not None
    def make_somap(age):
        if use_grad:
            return (SO + (float(P['SO_rear']) - SO) * age ** P['so_pow']).astype(np.float32)
        return np.full((N, N), SO, np.float32)
    somap = make_somap(age)
    agemap = age.copy()
    nodes = place_nodes(P, body_b, age, rng) if P['geom'] in ('disk', 'fan') else []
    def make_sources(front):
        sy_l, sx_l, sv_l = [], [], []
        if P['front_w'] > 0:
            fy, fx = np.nonzero(front)
            sy_l += fy.tolist(); sx_l += fx.tolist(); sv_l += [P['front_w']] * len(fy)
        for (x, y) in nodes:
            for ddy in (-1, 0, 1):
                for ddx in (-1, 0, 1):
                    sy_l.append(y + ddy); sx_l.append(x + ddx); sv_l.append(P['node_w'])
        return np.array(sy_l, np.int64), np.array(sx_l, np.int64), np.array(sv_l, np.float32)
    sy, sx, sval = make_sources(front)
    cSA, sSA = math.cos(math.radians(P['SA'])), math.sin(math.radians(P['SA']))
    cRA, sRA = math.cos(math.radians(P['RA'])), math.sin(math.radians(P['RA']))
    kdiff = np.float32((1.0 - P['damp']) / 9.0)
    steps = int(P['steps']); nacc = int(P['acc'])
    ev = np.unique(np.round(np.geomspace(max(200, nacc + 10), steps, int(P['n_eval']))).astype(int))
    snap_at = set(int(v) for v in ev[np.linspace(0, len(ev) - 1, int(P['n_snap'])).round().astype(int)])
    dynamic = P['geom'] in ('growdisk', 'movedisk') and P['v'] > 0
    kmax = int(P['R'] - P['R0']) + 1 if P['geom'] == 'growdisk' else 10 ** 12
    v = float(P['v'])
    nstate = np.array([n], np.int64)
    P_out = dict(P); P_out.update(n_particles0=n, body_area0=area0, node_xy=nodes,
                                  init='particles uniform random in initial body cells, random headings, trail=0')
    json.dump(P_out, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    curve = []; ims = []
    t = 0; ref = None; t0w = time.time(); moved = 0
    kfront = 0
    def advance_to(t_target, do_acc):
        nonlocal t, kfront, body_b, age, front, somap, agemap, sy, sx, sval, moved
        while t < t_target:
            if dynamic and kfront < kmax:
                t_next_mask = int(math.ceil((kfront + 1) / v - 1e-9))
                seg = min(t_target, max(t_next_mask, t + 1)) - t
            else:
                seg = t_target - t
            moved = run_chunk2(seg, t, do_acc, acc, nstate, nmax, px, py, hx, hy, sop, mv, tag, order, trail, tmp, occ, body,
                               somap, agemap, int(P['sync']), prio, cval, cid, int(P['diff_passes']), cap, cSA, sSA, cRA, sRA, np.float32(P['depT']), M, kdiff, sy, sx, sval,
                               float(P['node_supp']), int(P['grow']), int(P['Gw']), int(P['Gmin']), int(P['Gmax']), int(P['Gf']),
                               float(P['grow_age_max']), int(P['shrink']), int(P['Sw']), int(P['Smin']), int(P['Smax']),
                               int(P['Sf']), mix_vals, mix_cum)
            t += seg
            if dynamic and kfront < kmax and math.floor(v * t + 1e-9) > kfront:
                kfront = int(math.floor(v * t + 1e-9))
                nb, na, nf = geometry(P, t, grids)
                newc = nb & ~body_b
                body_b = nb; age = na; front = nf
                body[:] = nb
                agemap[:] = na
                somap[:] = make_somap(na)
                if P['front_w'] > 0:
                    sy, sx, sval = make_sources(front)
                nn = int(nstate[0])
                # 몸 밖에 남은 입자
                iy = py[:nn].astype(np.int64); ix = px[:nn].astype(np.int64)
                outside = np.flatnonzero(~nb[iy, ix])
                free = np.flatnonzero(newc.ravel() & (occ.ravel() == 0))
                if len(outside):
                    if P['exit_mode'] == 'relocate' and len(free):
                        rng.shuffle(free)
                        k = min(len(outside), len(free))
                        sel = outside[:k]; dst = free[:k]
                        occ[iy[sel], ix[sel]] -= 1
                        py[sel] = dst // N + rng.uniform(0, 1, k); px[sel] = dst % N + rng.uniform(0, 1, k)
                        aa = rng.uniform(0, TWO_PI, k); hx[sel] = np.cos(aa); hy[sel] = np.sin(aa)
                        occ.ravel()[dst] += 1
                        outside = outside[k:]
                        free = free[k:]
                    if len(outside):
                        tag[:nn] = 0; tag[outside] = 1
                        nn = J2_remove(nn, tag, px, py, hx, hy, sop, mv, occ)
                if P['front_inject'] > 0 and len(free):
                    pick = free[rng.uniform(0, 1, len(free)) < P['front_inject']]
                    k = min(len(pick), nmax - nn)
                    pick = pick[:k]
                    py[nn:nn + k] = pick // N + rng.uniform(0, 1, k); px[nn:nn + k] = pick % N + rng.uniform(0, 1, k)
                    aa = rng.uniform(0, TWO_PI, k); hx[nn:nn + k] = np.cos(aa); hy[nn:nn + k] = np.sin(aa)
                    if len(mix_vals):
                        sop[nn:nn + k] = mix_vals[np.searchsorted(mix_cum, rng.uniform(0, 1, k)).clip(0, len(mix_vals) - 1)]
                    else:
                        sop[nn:nn + k] = 0
                    mv[nn:nn + k] = 0
                    occ.ravel()[pick] += 1
                    nn += k
                order[:nn] = np.arange(nn)
                nstate[0] = nn
    for te in ev:
        te = int(te)
        if te <= t:
            continue
        na_ = min(nacc, te - t)
        advance_to(te - na_, False)
        acc[:] = 0
        advance_to(te, True)
        vein = acc / float(na_)
        bm = body > 0
        nn = int(nstate[0])
        m = vein_metrics(bm, vein, age)
        m['t'] = t; m['moved_frac'] = round(moved / max(nn, 1), 3); m['n'] = nn; m['area'] = int(bm.sum())
        m['dens'] = round(nn / max(int(bm.sum()), 1), 4)
        curve.append(m)
        if t in snap_at:
            if ref is None or dynamic:
                ref = max(float(np.percentile(vein[bm], 99.5)), 1e-6)
            txt = f"{name} t={t} BP={m.get('branch_points')} loops={m.get('loops')} n={nn} dens={m['dens']}"
            im = render(bm, vein, nodes, ref, txt)
            im.save(os.path.join(out, f'snapshot_{t:06d}.png'))
            ims.append(im)
        z = m.get('zones', {})
        print(f"[{name}] t={t} BP={m.get('branch_points')} loops={m.get('loops')} n={nn} dens={m['dens']} "
              f"w50={m.get('width_p50')} r/f_w={m.get('rear_over_front_width')} f/r_sk={m.get('front_over_rear_skel_density')} "
              f"moved={m['moved_frac']} ({time.time() - t0w:.0f}s)", flush=True)
    bm = body > 0
    nn = int(nstate[0])
    dens_map = ndi.uniform_filter((occ > 0).astype(np.float32), 9, mode='wrap')
    np.save(os.path.join(out, 'body.npy'), (bm * (1.0 + dens_map)).astype(np.float32))
    np.save(os.path.join(out, 'vein.npy'), vein.astype(np.float32))
    np.save(os.path.join(out, 'occ.npy'), (occ > 0).astype(np.uint8))
    np.save(os.path.join(out, 'age.npy'), age.astype(np.float32))
    json.dump(dict(curve=curve, wall_s=round(time.time() - t0w, 1), n_particles=nn, body_area=int(bm.sum())),
              open(os.path.join(out, 'curve.json'), 'w'), indent=1)
    k = len(ims)
    if k:
        s = 512
        mont = Image.new('RGB', (s * k, s))
        for i, im in enumerate(ims):
            mont.paste(im.resize((s, s), Image.BILINEAR), (i * s, 0))
        mont.save(os.path.join(out, 'montage.png'))
    r = subprocess.run([sys.executable, EVAL, os.path.join(out, 'body.npy'), os.path.join(out, 'vein.npy'),
                        '--out', os.path.join(out, 'eval.json'), '--png', os.path.join(out, 'overlay.png')],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print('eval failed', r.stderr[-500:])
    print(f"[{name}] done wall={time.time() - t0w:.0f}s n={nn} area={int(bm.sum())}", flush=True)
    return curve

def J2_remove(nn, tag, px, py, hx, hy, sop, mv, occ):
    return int(remove_tagged(nn, tag, px, py, hx, hy, sop, mv, occ))

if __name__ == '__main__':
    if sys.argv[1] == '--batch':
        for job in json.load(open(sys.argv[2])):
            job = dict(job); nm = job.pop('name')
            run(nm, job)
    else:
        run(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
