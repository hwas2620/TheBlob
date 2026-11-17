#!/usr/bin/env python3
"""N3 - point food as a non-ageing reservoir (optionally injecting volume) on top of the E10 model (copy of round2 e10.py, modified).

usage: python3 n3.py NAME '{"param": value, ...}'
writes runs/NAME/{h.npy, wet.npy, age.npy, sage.npy, C_edges.npy, eage.npy, Qmean.npy, Qgross.npy, theta.npy, slime.npy, twet.npy, food.npy,
                  state_t*.npz, snapshot_*.png, params.json, metrics.json}

E10 rules 1-7 are unchanged (see e10_orig.py docstring).  Changes (N3):
  T torus      : no interior mask, no boundary stop; centroid tracked with minimum image.
  F food field : c(x) = sum_k a_k sum_{3x3 images} exp(-|x-x_k|^2/(2 food_sigma^2)); enters ONLY the wetting threshold (- y_c*c).  No linear gradient.
                 foods = [[angle_deg, dist], ...] relative to the initial disc centre.
  R reservoir  : wet cells inside the food disc (radius food_r) of a live food do not age: senescence age 'sage' is frozen there.
                 h*_i = h0*exp(-sage/tau_a)*[1-(1-h_fill/h0)*exp(-age/tau_f)] + tube   (age = time since wetting, sage = senescence age; equal when reservoir=0)
  I eating     : every wet food cell eats 'eat' per unit time from the food's remaining amount M_k (food_M, 0 = infinite) and gains gain*eat*dt of thickness.
                 M_k = 0 -> food dead: reservoir off, attractant amplitude a_k decays with food_fade.
  B bridge_keep: a drying candidate dries only if its wet 8-neighbours form one 8-connected group in the 3x3 ring (Yokoi number <= 1), or its Cn < bridge_break;
                 only one colour of a 2x2 colouring may dry per step (no simultaneous removal of adjacent cells).  = retreat from dead ends first.
  K tube_keep  : cells with Cn > tube_keep do not dry.
  H h_res      : rest thickness of live-food cells is h_res*h0 instead of h0 (thick reservoir; default 1 = off).
"""
import numpy as np, json, sys, os, time
import scipy.sparse as sp, scipy.sparse.linalg as spl
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
import graphm

HERE = os.path.dirname(os.path.abspath(__file__))

DEF = dict(
    N=192, seed=1, edge_sigma=0.5, R_init=12.0, h_init=3.0, T=300.0, dt=0.1,
    kappa=8.0, h0=1.0, h_old=0.0, tau_a=30.0, beta=0.05, cap=0.5,
    y_sigma=0.05, lam=0.02, y_s=0.5, y_c=0.2, slime_tau=1e9, tau_f=2.0,
    hy0=1.1, Q0_auto=1.0, Q0_floor=1e-4, c_draw=0.0,
    h_fill=0.3, h_min=0.15, grace=2.0,
    gamma=1.5, Q0=0.05, rate=0.5, D0=0.3, D0_noise=0.3, r=0.02, Cmax=1e4,
    phase_mode='osc', eps=0.1, period=4.0, turns=1.0, d_omega=0.1, D_theta=8.8, osc_sub=4, pulse_tube=1,
    tauQ=0.0, reinforce='abs', rate_down=0.0, tube_yield=0, stat_periods=5,
    # --- N3 ---
    foods=[], food_sigma=25.0, food_amp=1.0, food_r=4.0, reservoir=0, eat=0.0, gain=0.0, food_M=0.0, food_fade=10.0,
    bridge_keep=0, bridge_break=1.0, tube_keep=0.0, h_res=1.0,
    gm_every=20.0, nsnap=5, log_every=50,
    # --- N2 (front isotropy) ---
    wet_rho=0.0, curv='n8', curv_sigma=1.5, curv_ref=0.33, curv_gain=8.0, curv_cap=99.0, stop_touch=0,
)
# E7 "sheet front" parameter set = base of every E10 run
BASE = dict(T=400, kappa=20, hy0=1.05, h_fill=0.2, Q0_auto=0.2, tau_a=50, r=0.05, D0=2, rate=0.05, lam=0.06, y_sigma=0.02)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]
WTH = [4 / 6 if (d[0] == 0 or d[1] == 0) else 1 / 6 for d in ALL]
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]     # cyclic order around a cell


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # a at the neighbour in direction d
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))      # edge array of the neighbour at -d (edge arriving here)


def run(name, over):
    P = dict(DEF); P.update(BASE); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    N = P['N']; dt = P['dt']; kap = P['kappa']
    jj, ii = np.mgrid[0:N, 0:N].astype(float)
    X = ii; Y = jj; c0 = N / 2 - 0.5
    mimg = lambda v: (v + N / 2) % N - N / 2
    Ls = [1.0, 1.0, np.sqrt(2), np.sqrt(2)]
    CDRAW = P['c_draw'] if P['c_draw'] > 0 else max(1.0, 2.0 * P['D0'])    # vein = edge reinforced above 2x fresh-sheet conductance
    G = [np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in DIRS]
    Cinit = [P['D0'] * (1 + P['D0_noise'] * rng.uniform(-1, 1, (N, N))) for _ in DIRS]
    eta = rng.normal(size=(N, N))
    # ---- food: periodic point sources ----
    fpos = [(c0 + d_ * np.cos(np.radians(a_)), c0 + d_ * np.sin(np.radians(a_))) for a_, d_ in P['foods']]
    nf = len(fpos); cfield = []; fdisc = []
    for fx, fy in fpos:
        g = np.zeros((N, N))
        for sx in (-N, 0, N):
            for sy in (-N, 0, N): g += np.exp(-((X - fx - sx) ** 2 + (Y - fy - sy) ** 2) / (2 * P['food_sigma'] ** 2))
        cfield.append(P['food_amp'] * g); fdisc.append(np.hypot(mimg(X - fx), mimg(Y - fy)) < P['food_r'])
    fM = np.full(nf, float(P['food_M']) if P['food_M'] > 0 else np.inf, dtype=float); famp = np.ones(nf); t_exh = np.full(nf, np.nan); t_touch = np.full(nf, np.nan); t_cover = np.full(nf, np.nan)
    Vinj = 0.0

    def food_now():
        f = np.zeros((N, N))
        for k_ in range(nf): f += famp[k_] * cfield[k_]
        return f

    def resmask_now():
        m = np.zeros((N, N), bool)
        if P['reservoir']:
            for k_ in range(nf):
                if fM[k_] > 0: m |= fdisc[k_]
        return m
    food = food_now(); resmask = resmask_now()

    dist = np.hypot(X - c0, Y - c0)
    wet = dist < P['R_init']
    h = np.where(wet, P['h_init'], 0.0)
    age = np.zeros((N, N)); sage = np.zeros((N, N)); slime = np.zeros((N, N)); twet = np.full((N, N), -1.0); twet[wet] = 0.0
    C = [np.zeros((N, N)) for _ in DIRS]; eage = [np.zeros((N, N)) for _ in DIRS]
    act_prev = [np.zeros((N, N), bool) for _ in DIRS]
    p = np.zeros((N, N))
    V0 = h.sum()
    steps = int(round(P['T'] / dt))
    snaps = sorted(set(int(steps * (i + 1) / P['nsnap']) for i in range(P['nsnap'])))
    log = []; t0 = time.time(); snapi = 0; hmin_seen = 0.0; stop = ''
    Q = [np.zeros((N, N)) for _ in DIRS]
    mode = P['phase_mode']; eps = P['eps'] if mode != 'none' else 0.0
    wv = 2 * np.pi / P['period']; nper = max(1, int(round(P['period'] / dt))); nwin = nper * P['stat_periods']
    theta = np.zeros((N, N))
    Qf = [np.zeros((N, N)) for _ in DIRS]; Qs = [np.zeros((N, N)) for _ in DIRS]
    sQ = [np.zeros((N, N)) for _ in DIRS]; sA = [np.zeros((N, N)) for _ in DIRS]; cnt_q = 0
    Qmean_last = [np.zeros((N, N)) for _ in DIRS]; Qgross_last = [np.zeros((N, N)) for _ in DIRS]; qwin_t = -1.0
    hmax_w = np.full((N, N), -np.inf); hmin_w = np.full((N, N), np.inf); hsum_w = np.zeros((N, N)); wet_w = np.ones((N, N), bool); cnt_w = 0
    hamp_last = np.zeros((N, N)); hmean_last = np.zeros((N, N))
    ser_new = np.zeros(steps + 1, np.int32); ser_area = np.zeros(steps + 1, np.int32); ser_dry = np.zeros(steps + 1, np.int32); ser_vol = np.zeros(steps + 1, np.float64)
    mass_err_max = 0.0
    gm_n = max(1, int(round(P['gm_every'] / dt))); gseries = []; newdir = np.zeros(3, np.int64); newdir_series = []
    colour = (X.astype(int) % 2) + 2 * (Y.astype(int) % 2)
    nbridge_kept = 0; ntube_kept = 0

    def node_C():
        Cn = np.zeros((N, N))
        for k, d in enumerate(DIRS): Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d)))
        return Cn

    def render(path, t):
        s = max(1, 1024 // N)
        base = np.zeros((N, N, 3), np.float32); base[:] = (10, 18, 10)
        base += np.clip(food, 0, 1)[..., None] * np.array([0, 22, 60], np.float32)       # attractant field (faint blue)
        sl = np.clip(slime, 0, 1)[..., None]
        base = base * (1 - sl) + np.array([52, 40, 30], np.float32) * sl
        b = np.clip(h / (1.3 * P['h0']), 0, 1)[..., None]
        body = np.array([40, 34, 8], np.float32) * (1 - b) + np.array([215, 185, 40], np.float32) * b
        base = np.where(wet[..., None], body, base)
        im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((N * s, N * s), Image.NEAREST)
        dr = ImageDraw.Draw(im); segs = []
        for k, d in enumerate(DIRS):
            ys, xs = np.nonzero(C[k] > CDRAW)
            for e, a, b_ in zip(C[k][ys, xs], xs, ys):
                if 0 <= a + d[0] < N and 0 <= b_ + d[1] < N: segs.append((e, a, b_, a + d[0], b_ + d[1]))
        segs.sort()
        for e, a, b_, c_, d_ in segs:
            wd = 0.45 * e ** 0.25
            br = min(1.0, 0.55 + 0.25 * wd)
            dr.line([((a + .5) * s, (b_ + .5) * s), ((c_ + .5) * s, (d_ + .5) * s)],
                    fill=(int(255 * br), int(120 * br), int(40 * br)), width=max(1, int(round(wd * s))))
        for k_, (fx, fy) in enumerate(fpos):
            rr = P['food_r'] * s; col = (60, 220, 255) if fM[k_] > 0 else (120, 120, 120)
            dr.ellipse([(fx + .5) * s - rr, (fy + .5) * s - rr, (fx + .5) * s + rr, (fy + .5) * s + rr], outline=col, width=2)
        dr.text((6, 4), f'{name} t={t:.0f}', fill=(255, 255, 255))
        im.save(path)

    def solve(W, hstar):
        idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
        rows = []; cols = []; vals = []
        for k, d in enumerate(DIRS):
            m = W[k] > 0
            a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
            rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
        ar = np.arange(n); rows.append(ar); cols.append(ar); vals.append(np.full(n, 1.0 / (kap * dt)))
        A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
        sol = spl.splu(A, permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0.0, options=dict(SymmetricMode=True)).solve(((h - hstar) / dt)[wet])   # SPD: symmetric-mode sparse LU (direct)
        pp = np.zeros((N, N)); pp[wet] = sol
        return pp

    cen_u = [c0, c0]                                  # unwrapped h-centroid

    def centroid():
        m = h.sum()
        if m <= 0: return tuple(cen_u)
        dx = mimg(X - cen_u[0]); dy = mimg(Y - cen_u[1])
        cen_u[0] += float((h * dx).sum() / m); cen_u[1] += float((h * dy).sum() / m)
        return tuple(cen_u)

    def state(t):
        tr = traj
        i0 = int(len(tr) * 0.6) if len(tr) > 3 else 0
        ddx = cen_u[0] - (tr[i0][1] if tr else c0); ddy = cen_u[1] - (tr[i0][2] if tr else c0)
        if np.hypot(ddx, ddy) < 1.0: ddx, ddy = cen_u[0] - c0, cen_u[1] - c0
        n_ = np.hypot(ddx, ddy); dirv = (ddx / n_, ddy / n_) if n_ > 0.5 else (0.0, 0.0)
        return dict(C=np.array(C, np.float32), wet=wet.copy(), h=h.astype(np.float32), age=age.astype(np.float32), sage=sage.astype(np.float32), eage=np.array(eage, np.float32),
                    Qmean=np.array(Qmean_last, np.float32), Qgross=np.array(Qgross_last, np.float32), G=np.array(G, np.float32),
                    cen=np.array([cen_u[0] % N, cen_u[1] % N]), t=t, foods=np.array(fpos), food_r=P['food_r'], r=P['r'], c0=c0, dirv=np.array(dirv), fM=fM.copy())

    cen0 = centroid(); path_len = 0.0; cen_prev = cen0; traj = []; full_states = {}
    for step in range(steps + 1):
        t = step * dt
        # ---- edges ----
        act = []
        for k, d in enumerate(DIRS):
            a = wet & nb(wet, d); new = a & ~act_prev[k]
            C[k] = np.where(new, Cinit[k], C[k]) * a
            eage[k] = np.where(new, 0.0, eage[k] + dt) * a
            Qf[k] = Qf[k] * (a & ~new); Qs[k] = Qs[k] * (a & ~new)
            act.append(a)
        act_prev = act
        # ---- phase field ----
        if mode == 'osc':
            om = wv * (1 + P['d_omega'] * (1 - np.exp(-sage[wet] / P['tau_a'])))
            ns = max(1, int(P['osc_sub'])); dts = dt / ns
            idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
            rows = []; cols = []; vals = []
            for k, d in enumerate(DIRS):
                a = idx[act[k]]; b = nb(idx, d)[act[k]]; rows += [a, b]; cols += [b, a]; vals += [np.full(2 * a.size, WTH[k])]
            Aw = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
            th = theta[wet]
            for _ in range(ns):
                if P['D_theta'] > 0:
                    sn = np.sin(th); cs = np.cos(th)
                    coup = cs * (Aw @ sn) - sn * (Aw @ cs)        # = sum_j w_j sin(theta_j - theta_i) over wet 8-neighbours
                else: coup = 0.0
                th = th + dts * (om + P['D_theta'] * coup)
            theta = np.zeros((N, N)); theta[wet] = th
        else:
            theta = np.where(wet, wv * t, 0.0)
        # ---- rest thickness ----
        Cn = node_C()
        hstar = P['h_old'] + (P['h0'] * (1.0 + (P['h_res'] - 1.0) * resmask) - P['h_old']) * np.exp(-sage / P['tau_a'])   # h_res>1: thick reservoir on live food (N3 variant)
        if P['tau_f'] > 0: hstar = hstar * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f']))   # new cell inflates gradually
        tube = np.minimum(P['beta'] * np.sqrt(Cn), P['cap'])
        if eps > 0:
            mod = 1 + eps * np.cos(theta)
            hstar = hstar * mod
            if P['pulse_tube']: tube = tube * mod
        hstar = hstar + tube
        # ---- pressure / flux / volume ----
        W = [act[k] * G[k] * (C[k] + P['r']) / Ls[k] for k in range(4)]
        p = solve(W, hstar)
        div = np.zeros((N, N))
        for k, d in enumerate(DIRS):
            Q[k] = W[k] * (p - nb(p, d)); div += Q[k] - rev(Q[k], d)
        h = h - dt * div
        hmin_seen = min(hmin_seen, float(h[wet].min()) if wet.any() else 0.0)
        # ---- eating / injection (N3 I) ----
        if nf:
            changed = False
            for k_ in range(nf):
                m = fdisc[k_] & wet; n_ = int(m.sum())
                if n_ > 0 and np.isnan(t_touch[k_]): t_touch[k_] = t
                if n_ >= 0.5 * fdisc[k_].sum() and np.isnan(t_cover[k_]): t_cover[k_] = t
                if fM[k_] > 0 and n_ > 0 and P['eat'] > 0:
                    amt = min(P['eat'] * n_ * dt, fM[k_]); fM[k_] -= amt
                    if P['gain'] > 0: h[m] += P['gain'] * amt / n_; Vinj += P['gain'] * amt
                    if fM[k_] <= 1e-12: fM[k_] = 0.0; t_exh[k_] = t; changed = True
                if fM[k_] <= 0 and famp[k_] > 1e-4:
                    famp[k_] = np.exp(-(t - t_exh[k_]) / max(P['food_fade'], 1e-6)); changed = True
            if changed: food = food_now(); resmask = resmask_now()
        # ---- reinforcement ----
        if P['tauQ'] > 0:
            a_ = min(1.0, dt / P['tauQ'])
            for k in range(4):
                Qf[k] = (Qf[k] + a_ * (np.abs(Q[k]) - Qf[k])) * act[k]; Qs[k] = (Qs[k] + a_ * (Q[k] - Qs[k])) * act[k]
            F = [np.abs(Qs[k]) for k in range(4)] if P['reinforce'] == 'net' else Qf
        else:
            F = [np.abs(Q[k]) for k in range(4)]
        Q0 = P['Q0']
        if P['Q0_auto'] > 0:                         # scale-free: Q0 = gamma-mean of F over active edges -> mean target C = Q0_auto^-gamma
            nact = sum(int(a.sum()) for a in act)
            if nact > 0:
                Q0 = max(P['Q0_floor'], P['Q0_auto'] * (sum(float((F[k][act[k]] ** P['gamma']).sum()) for k in range(4)) / nact) ** (1 / P['gamma']))
        for k in range(4):
            f = (F[k] / Q0) ** P['gamma']
            rt = P['rate'] if P['rate_down'] <= 0 else np.where(f >= C[k], P['rate'], P['rate_down'])
            C[k] = np.clip(C[k] + dt * rt * (f - C[k]), 0.0, P['Cmax']) * act[k]
        age = np.where(wet, age + dt, 0.0)
        sage = np.where(wet, sage + dt * (1.0 - resmask), 0.0)
        if P['slime_tau'] < 1e8: slime *= np.exp(-dt / P['slime_tau'])
        # ---- rolling statistics ----
        hmax_w = np.maximum(hmax_w, h); hmin_w = np.minimum(hmin_w, h); hsum_w += h; wet_w &= wet; cnt_w += 1
        for k in range(4): sQ[k] += Q[k]; sA[k] += np.abs(Q[k])
        cnt_q += 1
        if cnt_w >= nper:
            hamp_last = np.where(wet_w, 0.5 * (hmax_w - hmin_w), 0.0); hmean_last = np.where(wet_w, hsum_w / cnt_w, 0.0)
            hmax_w[:] = -np.inf; hmin_w[:] = np.inf; hsum_w[:] = 0; wet_w[:] = True; cnt_w = 0
        if cnt_q >= nwin:
            Qmean_last = [sQ[k] / cnt_q for k in range(4)]; Qgross_last = [sA[k] / cnt_q for k in range(4)]; qwin_t = t
            for k in range(4): sQ[k][:] = 0; sA[k][:] = 0
            cnt_q = 0
        # ---- drying ----
        Dm = wet & (h < P['h_min']) & (age > P['grace'])
        if Dm.any():
            if P['tube_keep'] > 0:
                keep = Dm & (Cn > P['tube_keep']); ntube_kept += int(keep.sum()); Dm &= ~keep
            if P['bridge_keep']:
                xb = [~nb(wet, d) for d in RING]
                Nc = np.zeros((N, N), np.int8)
                for q in (0, 2, 4, 6): Nc += xb[q].astype(np.int8) - (xb[q] & xb[q + 1] & xb[(q + 2) % 8]).astype(np.int8)
                ok = ((Nc <= 1) | (Cn < P['bridge_break'])) & (colour == step % 4)
                nbridge_kept += int((Dm & (Nc > 1) & (Cn >= P['bridge_break'])).sum()); Dm &= ok
        if Dm.any():
            stay = wet & ~Dm; ns = np.zeros((N, N))
            for d in ALL: ns += nb(stay, d)
            Dm &= ns > 0
            stay = wet & ~Dm; ns[:] = 0
            for d in ALL: ns += nb(stay, d)
            give = np.where(Dm, h / np.maximum(ns, 1), 0.0)
            for d in ALL: h += np.where(stay, nb(give, d), 0.0)
            h[Dm] = 0.0; wet = stay; slime[Dm] = 1.0; age[Dm] = 0.0; sage[Dm] = 0.0; p[Dm] = 0.0
            ser_dry[step] = int(Dm.sum())
        # ---- wetting (thickness yield) ----
        pw = np.where(wet, (h - tube) if P['tube_yield'] else h, -np.inf)
        pmax = np.full((N, N), -np.inf); arg = np.zeros((N, N), np.int8); nw = np.zeros((N, N))
        for q, d in enumerate(ALL):
            v = nb(pw, d); better = v > pmax
            pmax = np.where(better, v, pmax); arg = np.where(better, q, arg); nw += nb(wet, d)
        # N2: curvature (line tension) term
        if P['curv'] == 'gauss':                      # isotropic: Gaussian-weighted wet fraction around the candidate
            fw = gaussian_filter(wet.astype(float), P['curv_sigma'], mode='wrap', truncate=3.0)
            curv = P['lam'] * P['curv_gain'] * (P['curv_ref'] - fw)
        else:
            curv = P['lam'] * np.maximum(3 - nw, -P['curv_cap'])      # curv_cap limits the bonus of concave (kink) sites; default: no limit
        yld = P['hy0'] * (1 + P['y_sigma'] * eta) + curv + P['y_s'] * slime - P['y_c'] * food
        # N2: donor thickness seen by the dry cell
        if P['wet_rho'] > 0:                          # sample the wet-masked thickness at distance wet_rho along the diagonals (bilinear, renormalised over wet cells)
            a_ = min(1.0, P['wet_rho'] / np.sqrt(2.0)); wA = a_ * (1 - a_); wD = a_ * a_
            hz = np.where(wet, pw, 0.0); wz = wet.astype(float)
            ptest = np.full((N, N), -np.inf)
            for d in ((1, 0), (0, 1), (-1, 0), (0, -1)): ptest = np.maximum(ptest, nb(pw, d))
            for d in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                hA = nb(hz, (d[0], 0)); wAa = nb(wz, (d[0], 0)); hB = nb(hz, (0, d[1])); wB = nb(wz, (0, d[1])); hD = nb(hz, d); wDd = nb(wz, d)
                den = wA * (wAa + wB) + wD * wDd
                ptest = np.maximum(ptest, np.where(wDd > 0, (wA * (hA + hB) + wD * hD) / np.maximum(den, 1e-30), -np.inf))
        else:
            ptest = pmax
        cand = ~wet & (ptest > yld)
        if cand.any():
            ys, xs = np.nonzero(cand); a = arg[ys, xs]
            dx = np.array([d[0] for d in ALL])[a]; dy = np.array([d[1] for d in ALL])[a]
            sy = (ys + dy) % N; sx = (xs + dx) % N; flat = sy * N + sx
            cnt = np.bincount(flat, minlength=N * N)[flat]
            amt = np.minimum(P['h_fill'], 0.5 * np.maximum(h[sy, sx], 0.0) / cnt)
            np.subtract.at(h, (sy, sx), amt)
            h[ys, xs] = amt; wet[ys, xs] = True; age[ys, xs] = 0.0; sage[ys, xs] = 0.0; twet[ys, xs] = t
            p[ys, xs] = p[sy, sx]; theta[ys, xs] = theta[sy, sx]
            ser_new[step] = ys.size
            if nf:                                             # direction of new wetting relative to the food(s), seen from the centroid
                vx = mimg(xs - cen_u[0]); vy = mimg(ys - cen_u[1]); vn = np.maximum(np.hypot(vx, vy), 1e-9); best = np.full(xs.size, -2.0)
                live = [k_ for k_ in range(nf) if np.isnan(t_touch[k_])] or list(range(nf))
                for k_ in live:
                    gx = mimg(fpos[k_][0] - cen_u[0]); gy = mimg(fpos[k_][1] - cen_u[1]); gn = max(np.hypot(gx, gy), 1e-9)
                    best = np.maximum(best, (vx * gx + vy * gy) / (vn * gn))
                newdir += np.array([(best > 0.5).sum(), ((best <= 0.5) & (best >= -0.5)).sum(), (best < -0.5).sum()])
        ser_area[step] = int(wet.sum()); ser_vol[step] = h.sum()
        mass_err_max = max(mass_err_max, abs(float((h.sum() - V0 - Vinj) / V0)))
        if step % 10 == 0: centroid()
        # ---- log / graph series / snapshots ----
        if step % P['log_every'] == 0 or step == steps:
            cen = tuple(cen_u); path_len += np.hypot(cen[0] - cen_prev[0], cen[1] - cen_prev[1]); cen_prev = cen
            traj.append((round(t, 2), round(cen[0], 2), round(cen[1], 2), int(wet.sum())))
            log.append(dict(t=round(t, 2), area=int(wet.sum()), V=float(h.sum()), Vinj=float(Vinj), cx=cen[0], cy=cen[1], Cmax=float(Cn.max()),
                            hmax=float(h.max()), young=int((wet & (age < 5)).sum()), elapsed=round(time.time() - t0, 1)))
            if step % (P['log_every'] * 10) == 0 or step == steps:
                e = log[-1]; print(name, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items()}), flush=True)
        if step > 0 and step % gm_n == 0:
            S = state(t); g = graphm.quick(S); g['fM'] = [None if np.isinf(v) else round(float(v), 2) for v in fM]; g['Vinj'] = round(float(Vinj), 2)
            g['new_dir[toward,side,away]'] = [int(v) for v in newdir]; newdir[:] = 0
            g['h_on_food'] = [round(float(h[fdisc[k_] & wet].mean()), 3) if (fdisc[k_] & wet).any() else None for k_ in range(nf)]
            g['wet_food_cells'] = [int((fdisc[k_] & wet).sum()) for k_ in range(nf)]
            g['hmax'] = round(float(h.max()), 3); g['cen'] = [round(cen_u[0], 2), round(cen_u[1], 2)]
            g['vol3r'] = [round(float(h[np.hypot(mimg(X - fx), mimg(Y - fy)) < 3 * P['food_r']].sum() / h.sum()), 3) for fx, fy in fpos]
            g['vol_on_food'] = [round(float(h[fdisc[k_]].sum() / h.sum()), 3) for k_ in range(nf)]
            gseries.append(g)
        if step in snaps:
            snapi += 1; render(os.path.join(out, f'snapshot_{snapi}_t{int(round(t)):04d}.png'), t)
            S = state(t); np.savez_compressed(os.path.join(out, f'state_t{int(round(t)):04d}.npz'), **S)
            full_states[f't{int(round(t)):04d}'] = graphm.full(S)
        if not wet.any(): stop = 'all dry'; break
    nstep = step + 1

    # ------------------------------ outputs ------------------------------
    Cn = node_C()
    sv = lambda n_, a_: np.save(os.path.join(out, n_), a_)
    sv('h.npy', h.astype(np.float32)); sv('wet.npy', wet); sv('age.npy', np.where(wet, age, -1).astype(np.float32)); sv('sage.npy', np.where(wet, sage, -1).astype(np.float32))
    sv('C_edges.npy', np.array(C, np.float32)); sv('eage.npy', np.array(eage, np.float32)); sv('Qmean.npy', np.array(Qmean_last, np.float32)); sv('Qgross.npy', np.array(Qgross_last, np.float32))
    sv('theta.npy', np.where(wet, theta, np.nan).astype(np.float32)); sv('slime.npy', slime.astype(np.float32)); sv('twet.npy', twet.astype(np.float32)); sv('food.npy', food.astype(np.float32))
    sv('vein_native.npy', (Cn * wet).astype(np.float32)); sv('hamp.npy', hamp_last.astype(np.float32)); sv('hmean.npy', hmean_last.astype(np.float32))
    np.savez_compressed(os.path.join(out, 'series.npz'), new=ser_new[:nstep], area=ser_area[:nstep], dry=ser_dry[:nstep], vol=ser_vol[:nstep], dt=dt)
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    cen = centroid()
    met = dict(name=name, stop=stop, t_end=round(t, 2), runtime=round(time.time() - t0, 1), V0=float(V0), Vinj=float(Vinj), V_end=float(h.sum()),
               mass_err_max=float(mass_err_max), h_min_seen=hmin_seen, disp=round(float(np.hypot(cen[0] - c0, cen[1] - c0)), 2), path_len=round(float(path_len), 2),
               area_end=int(wet.sum()), foods=[[round(a, 2), round(b, 2)] for a, b in fpos],
               t_touch=[None if np.isnan(v) else round(float(v), 1) for v in t_touch], t_cover=[None if np.isnan(v) else round(float(v), 1) for v in t_cover],
               t_exh=[None if np.isnan(v) else round(float(v), 1) for v in t_exh], fM_end=[None if np.isinf(v) else round(float(v), 2) for v in fM],
               bridge_kept_cellsteps=int(nbridge_kept), tube_kept_cellsteps=int(ntube_kept), traj=traj)
    wm = hmean_last > 0
    if wm.any():
        ha = hamp_last[wm]; hm = hmean_last[wm]; sh = hm > 0.5 * P['h0']
        met['hamp'] = dict(mean=round(float(ha.mean()), 4), sheet_rel=round(float((ha[sh] / hm[sh]).mean()), 4) if sh.any() else None)
    met['gseries'] = gseries; met['full'] = full_states; met['log'] = log
    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    last = full_states[sorted(full_states)[-1]] if full_states else {}
    print(name, 'MET', json.dumps({k: met.get(k) for k in ('t_end', 'disp', 'area_end', 'mass_err_max', 'h_min_seen', 't_touch', 't_cover', 't_exh', 'Vinj', 'runtime')}))
    print(name, 'VEIN', json.dumps(last.get('vein')), 'BODY', json.dumps(last.get('body')))
    return met


if __name__ == '__main__':
    name = sys.argv[1]; over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    run(name, over)
