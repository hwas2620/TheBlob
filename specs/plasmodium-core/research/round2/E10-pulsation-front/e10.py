#!/usr/bin/env python3
"""E10 - pulsation on top of the E7 flux-driven front model (copy of E7 e7.py = e7_orig.py, extended).

usage: python3 e10.py NAME '{"param": value, ...}'
writes runs/NAME/{body.npy, vein.npy, body_native.npy, vein_native.npy, twet.npy, age.npy, theta.npy, hamp.npy, hmean.npy, C_edges.npy,
                  Qnet.npy, Qgross.npy, series.npz, snapshot_*.png, hamp.png, params.json, metrics.json, eval.json, overlay.png}

E7 MODEL (unchanged; nothing is drawn by hand; initial condition = uniform thick disc, age 0, no direction, no veins)
  cell state : wet, h (thickness = volume), age (time since wetting), slime ;  edge state: C_e (conductance), sq8 lattice
  static noise: G_e = exp(edge_sigma*N(0,1)) per edge, eta_j = N(0,1) per cell (yield), D0 noise per edge.  All white.
  1 rest thickness:  h*_i = h0*exp(-age_i/tau_a)*[1-(1-h_fill/h0)*exp(-age_i/tau_f)] + tube_i ,  tube_i = min(beta*sqrt(Cn_i), cap), Cn_i = max C of adjacent edges
  2 pressure  p_i = kappa*(h_i - h*_i), semi-implicit screened Poisson:  p_i/(kappa*dt) + sum_e W_e (p_i - p_j) = (h_i - h*_i)/dt ,  W_e = G_e*(C_e + r)/L_e
  3 flux-form update  Q_e = W_e (p_i - p_j),  h_i <- h_i - dt*sum_e Q_e
  4 reinforcement  dC_e/dt = rate*((F_e/Q0)^gamma - C_e),  Q0 = Q0_auto*(mean_e F_e^gamma)^(1/gamma) ; new edge C = D0*(1 + D0_noise*U(-1,1))
  5 drying: h_i < h_min and age_i > grace -> dry; volume split among wet neighbours; slime=1
  6 wetting (thickness yield): dry j wets if max over wet 8-neighbours of h_i > hy_j = hy0*(1+y_sigma*eta_j) + lam*(3-n_wet8) + y_s*slime_j - y_c*food_j
        new cell takes min(h_fill, 0.5*h_donor/cnt) from that neighbour; age=0

E10 ADDITIONS
  A pulsation:  h*_i <- h*_i * (1 + eps*cos(theta_i))      (pulse_tube=1: whole h* incl. tube term; 0: only the age term, as E7 g4)
      phase_mode 'uniform': theta_i = w t                    w = 2 pi / period
      phase_mode 'age'    : theta_i = w t + 2 pi turns age_i/age_ref ,  age_ref = 95th percentile of age over wet cells (one global statistic) -> old cells lead
      phase_mode 'osc'    : dtheta_i/dt = w (1 + d_omega (1 - exp(-age_i/tau_a))) + D_theta * sum_{j wet 8-nb} w_j sin(theta_j - theta_i),  w_j = 4/6 (axial), 1/6 (diag)
                            new cell inherits theta of its donor.  osc_sub explicit sub-steps per dt.
      phase_mode 'none'   : no pulsation (theta = w t is still kept as a fictitious clock for the lock statistics = control)
  B reinforcement input F_e:  tauQ=0: F_e = |Q_e| (E7).   tauQ>0, reinforce='abs': F_e low-pass of |Q_e| with time constant tauQ.
                              reinforce='net': F_e = |low-pass of signed Q_e|  (diagnostic: shuttle flow removed)
      rate_down>0: dC/dt uses rate_down instead of rate when the target is below C (slow vein decay / retraction rule)
  C tube_yield=1: the wetting criterion uses h_i - tube_i instead of h_i (so a tube holding volume does not spill sideways)
  D amputation: at t=cut_t remove all wet cells in the rear cut_frac of the body extent along the travel direction (centroid displacement so far)
  E measurements: thickness amplitude map over the last completed period, per-edge net and gross flux over the last completed window of stat_periods periods,
      wetting events vs. local phase of the donor (lock statistics), per-step series (new wet cells, area, tip position after a cut)
"""
import numpy as np, json, sys, os, time, subprocess
import scipy.sparse as sp, scipy.sparse.linalg as spl
from scipy import ndimage as ndi
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(os.path.dirname(HERE), 'common', 'eval_morph.py')

DEF = dict(
    N=192, seed=1, edge_sigma=0.5, R_init=12.0, h_init=3.0, T=300.0, dt=0.1,
    kappa=8.0, h0=1.0, h_old=0.0, tau_a=30.0, beta=0.05, cap=0.5,
    y0=0.8, y_sigma=0.05, lam=0.02, y_s=0.5, y_c=0.0, slime_tau=1e9, y_a=0.0, tau_y=10.0, tau_f=2.0,
    yield_on='h', hy0=1.1, Q0_auto=1.0, Q0_floor=1e-4, lam_R=0, c_draw=0.0,
    h_fill=0.3, h_min=0.15, grace=2.0,
    gamma=1.5, Q0=0.05, rate=0.5, D0=0.3, D0_noise=0.3, r=0.02, Cmax=1e4,
    # --- E10 ---
    phase_mode='none', eps=0.0, period=4.0, turns=1.0, d_omega=0.1, D_theta=8.8, osc_sub=4, pulse_tube=1,
    tauQ=0.0, reinforce='abs', rate_down=0.0, tube_yield=0, stat_periods=5, cut_t=0.0, cut_frac=0.5,
    food=[], food_r=5.0, food_grad=0.0,
    solver='exact', k=20, omega=0.9,
    nsnap=5, render_scale=4, do_eval=1, log_every=50,
)
# E7 "sheet front" parameter set (result.json of E7) = base for every E10 run
BASE = dict(T=400, kappa=20, hy0=1.05, h_fill=0.2, Q0_auto=0.2, tau_a=50, r=0.05, D0=2, rate=0.05, lam=0.06, y_sigma=0.02)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]
WTH = [4 / 6 if (d[0] == 0 or d[1] == 0) else 1 / 6 for d in ALL]


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # a at the neighbour in direction d
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))      # edge array of the neighbour at -d (edge arriving here)


def run(name, over):
    P = dict(DEF); P.update(BASE); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    N = P['N']; dt = P['dt']; kap = P['kappa']
    jj, ii = np.mgrid[0:N, 0:N].astype(float)
    X = ii; Y = jj; c0 = N / 2 - 0.5
    interior = (ii >= 3) & (ii < N - 3) & (jj >= 3) & (jj < N - 3)
    Ls = [1.0, 1.0, np.sqrt(2), np.sqrt(2)]
    CDRAW = P['c_draw'] if P['c_draw'] > 0 else max(1.0, 2.0 * P['D0'])    # vein = edge reinforced above 2x fresh-sheet conductance
    K20 = np.array([[0,1,1,1,0],[1,1,1,1,1],[1,1,0,1,1],[1,1,1,1,1],[0,1,1,1,0]], float)
    G = [np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in DIRS]
    Cinit = [P['D0'] * (1 + P['D0_noise'] * rng.uniform(-1, 1, (N, N))) for _ in DIRS]
    eta = rng.normal(size=(N, N))
    food = np.zeros((N, N))
    for (fx, fy) in P['food']:
        food = np.maximum(food, (np.hypot(X - fx, Y - fy) < P['food_r']).astype(float))
    if P['food_grad'] > 0:                       # optional smooth attractant gradient along +x (lowers yield)
        food = food + P['food_grad'] * (X - c0) / N

    dist = np.hypot(X - c0, Y - c0)
    wet = dist < P['R_init']
    h = np.where(wet, P['h_init'], 0.0)
    age = np.zeros((N, N)); slime = np.zeros((N, N)); twet = np.full((N, N), -1.0); twet[wet] = 0.0
    C = [np.zeros((N, N)) for _ in DIRS]
    act_prev = [np.zeros((N, N), bool) for _ in DIRS]
    p = np.zeros((N, N))
    V0 = h.sum()
    steps = int(P['T'] / dt)
    snaps = sorted(set(int(steps * (i + 1) / P['nsnap']) for i in range(P['nsnap'])))
    log = []; t0 = time.time(); snapi = 0; hmin_seen = 0.0; stop = ''
    Q = [np.zeros((N, N)) for _ in DIRS]
    # --- E10 state ---
    mode = P['phase_mode']; eps = P['eps'] if mode != 'none' else 0.0
    wv = 2 * np.pi / P['period']; nper = max(1, int(round(P['period'] / dt))); nwin = nper * P['stat_periods']
    theta = np.zeros((N, N)); age_ref = 1.0
    Qf = [np.zeros((N, N)) for _ in DIRS]; Qs = [np.zeros((N, N)) for _ in DIRS]
    hmax_w = np.full((N, N), -np.inf); hmin_w = np.full((N, N), np.inf); hsum_w = np.zeros((N, N)); wet_w = np.ones((N, N), bool); cnt_w = 0
    hamp_last = np.zeros((N, N)); hmean_last = np.zeros((N, N)); hamp_t = -1.0
    sQ = [np.zeros((N, N)) for _ in DIRS]; sA = [np.zeros((N, N)) for _ in DIRS]; cnt_q = 0
    Qnet_last = [np.zeros((N, N)) for _ in DIRS]; Qgross_last = [np.zeros((N, N)) for _ in DIRS]; qwin_t = -1.0
    lock_hist = np.zeros(24); lock_sum = 0j; lock_n = 0
    ser_new = np.zeros(steps + 1, np.int32); ser_area = np.zeros(steps + 1, np.int32); ser_dry = np.zeros(steps + 1, np.int32)
    ser_tip = np.full(steps + 1, np.nan, np.float32); ser_vol = np.zeros(steps + 1, np.float32)
    cut_step = int(round(P['cut_t'] / dt)) if P['cut_t'] > 0 else -1; cut_info = None; cut_dir = None
    mass_err_max = 0.0

    def node_C():
        Cn = np.zeros((N, N))
        for k, d in enumerate(DIRS): Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d)))
        return Cn

    def render(path, t):
        s = max(1, 1024 // N)
        base = np.zeros((N, N, 3), np.float32); base[:] = (10, 18, 10)
        sl = np.clip(slime, 0, 1)[..., None]
        base = base * (1 - sl) + np.array([52, 40, 30], np.float32) * sl
        b = np.clip(h / (1.3 * P['h0']), 0, 1)[..., None]
        body = np.array([40, 34, 8], np.float32) * (1 - b) + np.array([215, 185, 40], np.float32) * b
        base = np.where(wet[..., None], body, base)
        if food.max() > 0:
            fm = (food > 0.5) & ~wet; base[fm] = (30, 70, 110)
        im = Image.fromarray(base.astype(np.uint8)).resize((N * s, N * s), Image.NEAREST)
        dr = ImageDraw.Draw(im); segs = []
        for k, d in enumerate(DIRS):
            ys, xs = np.nonzero(C[k] > CDRAW)
            for e, a, b_ in zip(C[k][ys, xs], xs, ys): segs.append((e, a, b_, a + d[0], b_ + d[1]))
        segs.sort()
        for e, a, b_, c_, d_ in segs:
            wd = 0.45 * e ** 0.25
            br = min(1.0, 0.55 + 0.25 * wd)
            dr.line([((a + .5) * s, (b_ + .5) * s), ((c_ + .5) * s, (d_ + .5) * s)],
                    fill=(int(255 * br), int(120 * br), int(40 * br)), width=max(1, int(round(wd * s))))
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
        sol = spl.spsolve(A, ((h - hstar) / dt)[wet], permc_spec='MMD_AT_PLUS_A')
        pp = np.zeros((N, N)); pp[wet] = sol
        return pp

    def jacobi(p, W, hstar, k, omega):
        diag = np.full((N, N), 1.0 / (kap * dt)); b = (h - hstar) / dt
        for kk, d in enumerate(DIRS): diag += W[kk] + rev(W[kk], d)
        for _ in range(k):
            num = b.copy()
            for kk, d in enumerate(DIRS): num += W[kk] * nb(p, d) + rev(W[kk] * p, d)
            p = np.where(wet, (1 - omega) * p + omega * num / diag, 0.0)
        return p

    def centroid():
        m = h.sum()
        return (float((h * X).sum() / m), float((h * Y).sum() / m)) if m > 0 else (c0, c0)

    cen0 = centroid(); path_len = 0.0; cen_prev = cen0; traj = []
    for step in range(steps + 1):
        t = step * dt
        # ---- amputation (E10 D) ----
        if step == cut_step and wet.any():
            cen = centroid(); ddx, ddy = cen[0] - cen0[0], cen[1] - cen0[1]; nrm = np.hypot(ddx, ddy)
            if nrm < 1e-6: ddx, ddy, nrm = 1.0, 0.0, 1.0
            cut_dir = (ddx / nrm, ddy / nrm)
            s_ = X * cut_dir[0] + Y * cut_dir[1]; smin, smax = s_[wet].min(), s_[wet].max()
            rm = wet & (s_ < smin + P['cut_frac'] * (smax - smin))
            Vb = float(h.sum()); Ab = int(wet.sum())
            h[rm] = 0.0; wet = wet & ~rm; slime[rm] = 1.0; age[rm] = 0.0; p[rm] = 0.0; theta[rm] = 0.0
            cut_info = dict(t=round(t, 2), dir=[round(cut_dir[0], 3), round(cut_dir[1], 3)], V_before=Vb, V_after=float(h.sum()), area_before=Ab, area_after=int(wet.sum()),
                            disp_at_cut=round(float(nrm), 2), s_cut=float(smin + P['cut_frac'] * (smax - smin)), s_tip=float(smax))
            V0 = h.sum(); print(name, 'CUT', json.dumps(cut_info), flush=True)
        # ---- edges ----
        act = []
        for k, d in enumerate(DIRS):
            a = wet & nb(wet, d); new = a & ~act_prev[k]
            C[k] = np.where(new, Cinit[k], C[k]) * a
            Qf[k] = Qf[k] * (a & ~new); Qs[k] = Qs[k] * (a & ~new)
            act.append(a)
        act_prev = act
        # ---- phase field (E10 A) ----
        if mode == 'osc':
            om = wv * (1 + P['d_omega'] * (1 - np.exp(-age / P['tau_a'])))
            ns = max(1, int(P['osc_sub'])); dts = dt / ns
            for _ in range(ns):
                coup = np.zeros((N, N))
                if P['D_theta'] > 0:
                    for d, wt in zip(ALL, WTH): coup += wt * nb(wet, d) * np.sin(nb(theta, d) - theta)
                theta = np.where(wet, theta + dts * (om + P['D_theta'] * coup), 0.0)
        elif mode == 'age':
            if wet.any(): age_ref = max(float(np.percentile(age[wet], 95)), 1.0)
            theta = np.where(wet, wv * t + 2 * np.pi * P['turns'] * np.minimum(age / age_ref, 1.5), 0.0)
        else:
            theta = np.where(wet, wv * t, 0.0)
        # ---- rest thickness ----
        Cn = node_C()
        hstar = P['h_old'] + (P['h0'] - P['h_old']) * np.exp(-age / P['tau_a'])
        if P['tau_f'] > 0: hstar = hstar * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f']))   # new cell inflates gradually
        tube = np.minimum(P['beta'] * np.sqrt(Cn), P['cap'])
        if eps > 0:
            mod = 1 + eps * np.cos(theta)
            hstar = hstar * mod
            if P['pulse_tube']: tube = tube * mod
        hstar = hstar + tube
        # ---- pressure / flux / volume ----
        W = [act[k] * G[k] * (C[k] + P['r']) / Ls[k] for k in range(4)]
        if P['solver'] == 'exact': p = solve(W, hstar)
        else: p = jacobi(np.where(wet, p, 0.0), W, hstar, P['k'], P['omega'])
        div = np.zeros((N, N))
        for k, d in enumerate(DIRS):
            Q[k] = W[k] * (p - nb(p, d)); div += Q[k] - rev(Q[k], d)
        h = h - dt * div
        hmin_seen = min(hmin_seen, float(h[wet].min()) if wet.any() else 0.0)
        # ---- reinforcement (E10 B) ----
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
        age = np.where(wet, age + dt * (1.0 - np.clip(food, 0, 1) if P['food'] else 1.0), 0.0)
        if P['slime_tau'] < 1e8: slime *= np.exp(-dt / P['slime_tau'])
        # ---- E10 E: rolling statistics (thickness amplitude over one period, net/gross flux over stat_periods periods) ----
        hmax_w = np.maximum(hmax_w, h); hmin_w = np.minimum(hmin_w, h); hsum_w += h; wet_w &= wet; cnt_w += 1
        for k in range(4): sQ[k] += Q[k]; sA[k] += np.abs(Q[k])
        cnt_q += 1
        if cnt_w >= nper:
            hamp_last = np.where(wet_w, 0.5 * (hmax_w - hmin_w), 0.0); hmean_last = np.where(wet_w, hsum_w / cnt_w, 0.0); hamp_t = t
            hmax_w[:] = -np.inf; hmin_w[:] = np.inf; hsum_w[:] = 0; wet_w[:] = True; cnt_w = 0
        if cnt_q >= nwin:
            Qnet_last = [np.abs(sQ[k]) / cnt_q for k in range(4)]; Qgross_last = [sA[k] / cnt_q for k in range(4)]; qwin_t = t
            for k in range(4): sQ[k][:] = 0; sA[k][:] = 0
            cnt_q = 0
        # ---- drying ----
        Dm = wet & (h < P['h_min']) & (age > P['grace'])
        if Dm.any():
            stay = wet & ~Dm; ns = np.zeros((N, N))
            for d in ALL: ns += nb(stay, d)
            Dm &= ns > 0
            stay = wet & ~Dm; ns[:] = 0
            for d in ALL: ns += nb(stay, d)
            give = np.where(Dm, h / np.maximum(ns, 1), 0.0)
            for d in ALL: h += np.where(stay, nb(give, d), 0.0)
            h[Dm] = 0.0; wet = stay; slime[Dm] = 1.0; age[Dm] = 0.0; p[Dm] = 0.0
            ser_dry[step] = int(Dm.sum())
        # ---- wetting (yield) ----
        pw = np.where(wet, kap * (h - hstar), -np.inf)       # pressure after the update
        if P['y_a'] > 0: pw = pw - P['y_a'] * (1 - np.exp(-age / P['tau_y']))     # stalled (old) boundary hardens
        ybase = P['y0']
        if P['yield_on'] == 'h':                              # thickness criterion: spill when h_i > hy_j
            pw = np.where(wet, (h - tube) if P['tube_yield'] else h, -np.inf); ybase = P['hy0']
        pmax = np.full((N, N), -np.inf); arg = np.zeros((N, N), np.int8); nw = np.zeros((N, N))
        for q, d in enumerate(ALL):
            v = nb(pw, d); better = v > pmax
            pmax = np.where(better, v, pmax); arg = np.where(better, q, arg); nw += nb(wet, d)
        curv = (3 - nw) if P['lam_R'] == 0 else (8 - ndi.convolve(wet.astype(float), K20, mode='constant')) * 3.0 / 8.0   # lam_R=2: radius-2.2 disc (20 cells), flat front = 8
        yld = ybase * (1 + P['y_sigma'] * eta) + P['lam'] * curv + P['y_s'] * slime - P['y_c'] * food
        cand = ~wet & interior & (pmax > yld)
        if cand.any():
            ys, xs = np.nonzero(cand); a = arg[ys, xs]
            dx = np.array([d[0] for d in ALL])[a]; dy = np.array([d[1] for d in ALL])[a]
            sy = ys + dy; sx = xs + dx; flat = sy * N + sx
            cnt = np.bincount(flat, minlength=N * N)[flat]
            amt = np.minimum(P['h_fill'], 0.5 * np.maximum(h[sy, sx], 0.0) / cnt)
            np.subtract.at(h, (sy, sx), amt)
            h[ys, xs] = amt; wet[ys, xs] = True; age[ys, xs] = 0.0; twet[ys, xs] = t
            p[ys, xs] = p[sy, sx]; theta[ys, xs] = theta[sy, sx]
            ser_new[step] = ys.size
            if step > steps // 2:                             # lock statistics: local phase of the donor at the moment of wetting
                psi = np.mod(theta[sy, sx], 2 * np.pi)
                lock_hist += np.histogram(psi, bins=24, range=(0, 2 * np.pi))[0]; lock_sum += np.exp(1j * psi).sum(); lock_n += psi.size
        ser_area[step] = int(wet.sum()); ser_vol[step] = h.sum()
        if cut_dir is not None and wet.any():
            sm_ = wet & (h > 0.5 * P['h0'])
            if sm_.any(): ser_tip[step] = float((X * cut_dir[0] + Y * cut_dir[1])[sm_].max())
        mass_err_max = max(mass_err_max, abs(float((h.sum() - V0) / V0)))
        # ---- log / snapshots ----
        if step % P['log_every'] == 0 or step == steps:
            cen = centroid(); path_len += np.hypot(cen[0] - cen_prev[0], cen[1] - cen_prev[1]); cen_prev = cen
            V = h.sum(); qa = np.concatenate([np.abs(Q[k][act[k]]) for k in range(4)]) if wet.any() else np.zeros(1)
            traj.append((round(t, 2), round(cen[0], 2), round(cen[1], 2), int(wet.sum())))
            log.append(dict(t=round(t, 2), area=int(wet.sum()), V_err=float((V - V0) / V0), cx=cen[0], cy=cen[1],
                            pmax=float(pw[wet].max()) if wet.any() else 0, Cmax=float(Cn.max()),
                            Qp50=float(np.percentile(qa, 50)), Qp99=float(np.percentile(qa, 99)), Qmax=float(qa.max()),
                            young=int((wet & (age < 5)).sum()), elapsed=round(time.time() - t0, 1)))
            if step % (P['log_every'] * 10) == 0 or step == steps:
                e = log[-1]; print(name, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items()}), flush=True)
        if step in snaps:
            snapi += 1; render(os.path.join(out, f'snapshot_{snapi}_t{int(t):04d}.png'), t)
        if not wet.any(): stop = 'all dry'; break
        edge = wet & ~ndi.binary_erosion(interior, iterations=2)
        if edge.any(): stop = f'reached boundary at t={t:.1f}'; break
    if stop:
        snapi += 1; render(os.path.join(out, f'snapshot_{snapi}_t{int(t):04d}_stop.png'), t); print(name, 'STOP', stop)
    nstep = step + 1

    # ------------------------------ outputs ------------------------------
    Cn = node_C()
    np.save(os.path.join(out, 'body_native.npy'), h.astype(np.float32)); np.save(os.path.join(out, 'vein_native.npy'), (Cn * wet).astype(np.float32))
    np.save(os.path.join(out, 'twet.npy'), twet.astype(np.float32)); np.save(os.path.join(out, 'age.npy'), np.where(wet, age, -1).astype(np.float32))
    np.save(os.path.join(out, 'theta.npy'), np.where(wet, theta, np.nan).astype(np.float32))
    np.save(os.path.join(out, 'hamp.npy'), hamp_last.astype(np.float32)); np.save(os.path.join(out, 'hmean.npy'), hmean_last.astype(np.float32))
    np.save(os.path.join(out, 'C_edges.npy'), np.array(C, np.float32)); np.save(os.path.join(out, 'slime.npy'), slime.astype(np.float32))
    np.save(os.path.join(out, 'Qnet.npy'), np.array(Qnet_last, np.float32)); np.save(os.path.join(out, 'Qgross.npy'), np.array(Qgross_last, np.float32))
    np.savez_compressed(os.path.join(out, 'series.npz'), new=ser_new[:nstep], area=ser_area[:nstep], dry=ser_dry[:nstep], tip=ser_tip[:nstep], vol=ser_vol[:nstep], dt=dt)
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    # thickness amplitude map (PNG): left = amplitude (0 .. 0.2 h0), right = relative amplitude hamp/hmean (0 .. 0.3)
    try:
        s = 3
        def cmap(v):
            v = np.clip(v, 0, 1)[..., None]
            lo = np.array([20, 20, 60], np.float32); mid = np.array([230, 80, 40], np.float32); hi = np.array([255, 255, 160], np.float32)
            return np.where(v < 0.5, lo + (mid - lo) * (v * 2), mid + (hi - mid) * (v * 2 - 1))
        wm = hmean_last > 0
        a1 = np.where(wm[..., None], cmap(hamp_last / (0.2 * P['h0'])), 8); a2 = np.where(wm[..., None], cmap(hamp_last / np.maximum(hmean_last, 1e-6) / 0.3), 8)
        im = Image.fromarray(np.concatenate([a1, a2], 1).astype(np.uint8)).resize((2 * N * s, N * s), Image.NEAREST)
        dr = ImageDraw.Draw(im); dr.text((6, 4), f'{name} thickness amplitude over one period ending t={hamp_t:.1f}: left abs (white=0.2), right relative (white=0.3)', fill=(255, 255, 255))
        im.save(os.path.join(out, 'hamp.png'))
    except Exception as ex: print('hamp png failed', ex)
    rs_ = P['render_scale']
    imv = Image.new('F', (N * rs_, N * rs_), 0.0); drv = ImageDraw.Draw(imv); segs = []
    for k, d in enumerate(DIRS):
        ys, xs = np.nonzero(C[k] > CDRAW)
        for e, a, b_ in zip(C[k][ys, xs], xs, ys): segs.append((e, a, b_, a + d[0], b_ + d[1]))
    segs.sort()
    for e, a, b_, c_, d_ in segs:
        wd = 0.45 * e ** 0.25
        drv.line([((a + .5) * rs_, (b_ + .5) * rs_), ((c_ + .5) * rs_, (d_ + .5) * rs_)], fill=float(wd), width=max(1, int(round(wd * rs_))))
    body_r = np.kron(wet.astype(np.float32) * np.maximum(h, 1e-3).astype(np.float32), np.ones((rs_, rs_), np.float32))
    np.save(os.path.join(out, 'body.npy'), body_r); np.save(os.path.join(out, 'vein.npy'), (np.asarray(imv) * (body_r > 0)).astype(np.float32))

    met = dict(name=name, stop=stop, t_end=round(t, 2), runtime=round(time.time() - t0, 1), V0=float(V0),
               mass_err_max=float(max(mass_err_max, max(abs(e['V_err']) for e in log))), h_min_seen=hmin_seen, traj=traj)
    cen = centroid(); met['disp'] = round(float(np.hypot(cen[0] - cen0[0], cen[1] - cen0[1])), 2); met['path_len'] = round(float(path_len), 2)
    met['area_end'] = int(wet.sum())
    if cut_info: met['cut'] = cut_info
    # ---- E10 metrics ----
    wm = hmean_last > 0
    if wm.any():
        ha = hamp_last[wm]; hm = hmean_last[wm]
        met['hamp'] = dict(t=round(hamp_t, 2), mean=round(float(ha.mean()), 4), p50=round(float(np.percentile(ha, 50)), 4), p90=round(float(np.percentile(ha, 90)), 4), max=round(float(ha.max()), 4),
                           rel_mean=round(float((ha / np.maximum(hm, 1e-6)).mean()), 4), sheet_mean=round(float(ha[hm > 0.5 * P['h0']].mean()), 4) if (hm > 0.5 * P['h0']).any() else None,
                           thin_mean=round(float(ha[hm <= 0.5 * P['h0']].mean()), 4) if (hm <= 0.5 * P['h0']).any() else None)
    if qwin_t > 0:
        gn = np.array(Qnet_last); gg = np.array(Qgross_last); Ce = np.array(C); am = np.array(act) & (gg > 0)
        vm = am & (Ce > CDRAW)
        met['flux'] = dict(t=round(qwin_t, 2), window=P['stat_periods'] * P['period'],
                           gross_over_net_all=round(float(gg[am].sum() / max(gn[am].sum(), 1e-12)), 3),
                           gross_over_net_vein=round(float(gg[vm].sum() / max(gn[vm].sum(), 1e-12)), 3) if vm.any() else None,
                           shuttle_over_net_vein=round(float((gg[vm].sum() - gn[vm].sum()) / max(gn[vm].sum(), 1e-12)), 3) if vm.any() else None,
                           median_edge_ratio_vein=round(float(np.median(gg[vm] / np.maximum(gn[vm], 1e-12))), 3) if vm.any() else None,
                           frac_vein_edges_reversing=round(float((gg[vm] > 1.05 * gn[vm]).mean()), 3) if vm.any() else None)
    if lock_n > 0:
        met['lock'] = dict(n=int(lock_n), R=round(float(abs(lock_sum) / lock_n), 3), phase_deg=round(float(np.degrees(np.angle(lock_sum)) % 360), 1), hist=[int(x) for x in lock_hist])
    i0 = nstep // 2; sn = ser_new[i0:nstep].astype(float)
    if sn.sum() > 0:
        tt = np.arange(i0, nstep) * dt
        met['new_mod_index'] = round(float(abs((sn * np.exp(-1j * wv * tt)).sum()) / sn.sum()), 3)       # 0 = steady advance, ->1 = advance in one burst per period (clock w)
        met['new_rate_late'] = round(float(sn.sum() / (tt[-1] - tt[0] + dt)), 3)
    if wet.sum() > 20 and mode != 'none':
        aw = age[wet]; th = theta[wet]; o = np.argsort(aw); n10 = max(3, aw.size // 10)
        met['phase_lead_old_minus_young_turns'] = round(float((th[o[-n10:]].mean() - th[o[:n10]].mean()) / (2 * np.pi)), 3)
        met['phase_age_corr'] = round(float(np.corrcoef(aw, th)[0, 1]), 3) if th.std() > 1e-9 else 0.0
        if mode == 'age': met['age_ref'] = round(age_ref, 1)
    if wet.sum() > 30:
        lab, nl = ndi.label(wet, structure=np.ones((3, 3))); sizes = np.bincount(lab.ravel())[1:]
        met['body_components'] = int(nl); met['body_largest_frac'] = round(float(sizes.max() / wet.sum()), 3)
        big = lab == (np.argmax(sizes) + 1); met['vol_frac_largest'] = round(float(h[big].sum() / h.sum()), 3)
        # polarisation of recent growth: mean unit vector from centroid to cells wetted in the last 15% of the run
        ym = wet & (twet > t - max(0.15 * t, 5 * dt))
        if ym.sum() > 5:
            ux = X[ym] - cen[0]; uy = Y[ym] - cen[1]; rr = np.maximum(np.hypot(ux, uy), 1e-6)
            mx, my = float((ux / rr).mean()), float((uy / rr).mean())
            met['growth_polarisation'] = round(float(np.hypot(mx, my)), 3)
            ang = np.arctan2(uy, ux); hist = np.histogram(ang, bins=36, range=(-np.pi, np.pi))[0]
            met['growth_sector_frac'] = round(float((hist > 0).mean()), 3)          # fraction of 10-degree sectors with recent growth
            gl, gn_ = ndi.label(ndi.binary_dilation(ym, iterations=2)); met['active_front_patches'] = int(gn_)
        # travel direction: centroid displacement over the last 40% of logged time
        i0 = int(len(traj) * 0.6); ddx = traj[-1][1] - traj[i0][1]; ddy = traj[-1][2] - traj[i0][2]
        if np.hypot(ddx, ddy) < 1.0: ddx, ddy = cen[0] - cen0[0], cen[1] - cen0[1]
        nrm = np.hypot(ddx, ddy)
        met['late_speed'] = round(float(np.hypot(traj[-1][1] - traj[i0][1], traj[-1][2] - traj[i0][2]) / max(traj[-1][0] - traj[i0][0], 1e-9)), 4)
        if nrm > 0.5:
            ux, uy = ddx / nrm, ddy / nrm
            s = (X[big] - cen[0]) * ux + (Y[big] - cen[1]) * uy; w = -(X[big] - cen[0]) * uy + (Y[big] - cen[1]) * ux
            smin, smax = s.min(), s.max(); L = smax - smin
            fr = s > smax - 0.3 * L; re = s < smin + 0.3 * L
            ext = lambda q: float(np.percentile(q, 97.5) - np.percentile(q, 2.5)) + 1 if q.size > 3 else 1.0
            met['len_along'] = round(float(L + 1), 1)
            met['front_width_ext'] = round(ext(w[fr]), 1); met['rear_width_ext'] = round(ext(w[re]), 1)
            met['front_rear_ext_ratio'] = round(ext(w[fr]) / ext(w[re]), 2)
            met['front_rear_area_ratio'] = round(float(fr.sum() / max(re.sum(), 1)), 2)   # = occupied width ratio (same band length)
            met['dir'] = [round(ux, 3), round(uy, 3)]
        # sheet (thick part) solidity
        sm = wet & (h > 0.5 * P['h0'])
        if sm.sum() > 30:
            from skimage.measure import label as sklabel, regionprops
            pr = sorted(regionprops(sklabel(sm, connectivity=2)), key=lambda r_: -r_.area)[0]
            met['sheet_area_frac'] = round(float(sm.sum() / wet.sum()), 3); met['sheet_solidity'] = round(float(pr.solidity), 3)
            met['sheet_largest_frac'] = round(float(pr.area / sm.sum()), 3)
    if P['do_eval'] and wet.sum() > 50:
        for bn, vn, en, pn in (('body.npy', 'vein.npy', 'eval.json', 'overlay.png'), ('body_native.npy', 'vein_native.npy', 'eval_native.json', 'overlay_native.png')):
            subprocess.run([sys.executable, EVAL, os.path.join(out, bn), os.path.join(out, vn), '--out', os.path.join(out, en),
                            '--png', os.path.join(out, pn)], stdout=subprocess.DEVNULL)
        try:
            e = json.load(open(os.path.join(out, 'eval.json')))['primary']; er = json.load(open(os.path.join(out, 'eval_native.json')))['primary']
            met['eval_primary'] = e; met['eval_native_primary'] = er
        except Exception as ex: print('eval failed', ex)
    met['log'] = log
    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    keys = ('disp', 'path_len', 'late_speed', 'area_end', 'mass_err_max', 'h_min_seen', 'growth_polarisation', 'growth_sector_frac', 'active_front_patches',
            'front_rear_ext_ratio', 'front_rear_area_ratio', 'sheet_solidity', 'sheet_area_frac', 'body_components', 'runtime')
    print(name, 'MET', json.dumps({k: met.get(k) for k in keys}))
    print(name, 'E10', json.dumps({k: met.get(k) for k in ('hamp', 'flux', 'new_mod_index', 'phase_lead_old_minus_young_turns', 'phase_age_corr')}), 'lock', {k: v for k, v in met.get('lock', {}).items() if k != 'hist'})
    e = met.get('eval_primary', {})
    print(name, 'EVAL', {k: e.get(k) for k in ('body_solidity', 'branch_points', 'loops', 'vein_area_frac', 'vein_largest_frac', 'width_ratio_p90_p10', 'strength_ratio_p90_p10')}, e.get('verdict'))
    return met


if __name__ == '__main__':
    name = sys.argv[1]; over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    run(name, over)
