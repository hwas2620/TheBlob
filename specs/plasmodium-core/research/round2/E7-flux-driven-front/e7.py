#!/usr/bin/env python3
"""E7 - flux-driven front: volume ledger + yield front + flux-reinforced edge conductance.
(derived from E1 e1.py = e1_orig.py: sq8 edge lattice, static log-normal edge noise, tube render, common eval)

usage: python3 e7.py NAME '{"param": value, ...}'
writes runs/NAME/{body.npy, vein.npy, body_native.npy, vein_native.npy, twet.npy, snapshot_*.png, params.json, metrics.json, eval.json, overlay.png}

HYPOTHESIS: if the front is advanced only by volume delivered through the vein network and total volume is conserved
(the rear becomes the source), the competition "thick vein feeds part of the front" vs. stabilisers (yield threshold,
line tension, sheet permeability) gives a migrating fan with a branching vein tree behind it.

MODEL (nothing is drawn by hand; initial condition = uniform thick disc, age 0, no direction, no veins)
  cell state : wet, h (thickness = volume), age (time since wetting), slime ;  edge state: C_e (conductance), sq8 lattice
  static noise: G_e = exp(edge_sigma*N(0,1)) per edge, eta_j = N(0,1) per cell (yield), D0 noise per edge.  All white.
  1 rest thickness (active contraction grows with age -> sources are NOT hand placed):
        h*_i = h_old + (h0-h_old)*exp(-age_i/tau_a) + min(beta*sqrt(Cn_i), cap)      Cn_i = max C of adjacent edges (tube volume ~ sqrt(C))
        (optional pulsation: h*_i *= 1 + amp*sin(2 pi t/period - kwave . x))    (age does not advance on food)
  2 pressure  p_i = kappa*(h_i - h*_i), semi-implicit (screened Poisson, global):
        p_i/(kappa*dt) + sum_e W_e (p_i - p_j) = (h_i^n - h*_i)/dt ,   W_e = G_e*(C_e + r)/L_e
  3 flux-form update  Q_e = W_e (p_i - p_j),  h_i <- h_i - dt*sum_e Q_e     (total volume conserved to round-off even for inexact solves)
  4 reinforcement  dC_e/dt = rate*((|Q_e|/Q0)^gamma - C_e) ;  new edge C = D0*(1 + D0_noise*U(-1,1))
  5 drying: h_i < h_min and age_i > grace -> dry; remaining volume split equally among wet neighbours; slime=1
  6 wetting (yield): for dry j: pmax_j = max p over wet 8-neighbours,
        y_j = y0*(1 + y_sigma*eta_j) + lam*(3 - n_wet8(j)) + y_s*slime_j - y_c*food_j ;  wet if pmax_j > y_j
        new cell takes h_fill (<= half of donor) from the max-pressure neighbour (conservative); age=0
     DEFAULT since batch c (yield_on='h'): thickness criterion  h_i > hy_j = hy0*(1+y_sigma*eta_j) + lam*(3-n_wet8) + y_s*slime_j - y_c*food_j
        (pressure criterion let old thin cells (h*->0, p=kappa*h) creep forward as a film without any network flux: batch b)
     DEFAULT since batch c (Q0_auto>0): Q0(t) = Q0_auto * (mean_e |Q_e|^gamma)^(1/gamma) over active edges (scale-free; one global mean = mip reduce on GPU)
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
    amp=0.0, period=10.0, wavelen=0.0,
    food=[], food_r=5.0, food_grad=0.0,
    solver='exact', k=20, omega=0.9,
    nsnap=5, render_scale=4, do_eval=1, log_every=50,
)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # a at the neighbour in direction d
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))      # edge array of the neighbour at -d (edge arriving here)


def run(name, over):
    P = dict(DEF); P.update(over)
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
        # ---- edges ----
        act = []
        for k, d in enumerate(DIRS):
            a = wet & nb(wet, d); new = a & ~act_prev[k]
            C[k] = np.where(new, Cinit[k], C[k]) * a
            act.append(a)
        act_prev = act
        # ---- rest thickness ----
        Cn = node_C()
        hstar = P['h_old'] + (P['h0'] - P['h_old']) * np.exp(-age / P['tau_a'])
        if P['tau_f'] > 0: hstar = hstar * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f']))   # new cell inflates gradually
        if P['amp'] > 0:
            ph = 2 * np.pi * t / P['period'] - (2 * np.pi * dist / P['wavelen'] if P['wavelen'] > 0 else 0.0)
            hstar = hstar * (1 + P['amp'] * np.sin(ph))
        hstar = hstar + np.minimum(P['beta'] * np.sqrt(Cn), P['cap'])
        # ---- pressure / flux / volume ----
        W = [act[k] * G[k] * (C[k] + P['r']) / Ls[k] for k in range(4)]
        if P['solver'] == 'exact': p = solve(W, hstar)
        else: p = jacobi(np.where(wet, p, 0.0), W, hstar, P['k'], P['omega'])
        div = np.zeros((N, N))
        for k, d in enumerate(DIRS):
            Q[k] = W[k] * (p - nb(p, d)); div += Q[k] - rev(Q[k], d)
        h = h - dt * div
        hmin_seen = min(hmin_seen, float(h[wet].min()) if wet.any() else 0.0)
        # ---- reinforcement ----
        Q0 = P['Q0']
        if P['Q0_auto'] > 0:                         # scale-free: Q0 = gamma-mean of |Q| over active edges -> mean target C = Q0_auto^-gamma
            nact = sum(int(a.sum()) for a in act)
            if nact > 0:
                Q0 = max(P['Q0_floor'], P['Q0_auto'] * (sum(float((np.abs(Q[k][act[k]]) ** P['gamma']).sum()) for k in range(4)) / nact) ** (1 / P['gamma']))
        for k in range(4):
            f = (np.abs(Q[k]) / Q0) ** P['gamma']
            C[k] = np.clip(C[k] + dt * P['rate'] * (f - C[k]), 0.0, P['Cmax']) * act[k]
        age = np.where(wet, age + dt * (1.0 - np.clip(food, 0, 1) if P['food'] else 1.0), 0.0)
        if P['slime_tau'] < 1e8: slime *= np.exp(-dt / P['slime_tau'])
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
        # ---- wetting (yield) ----
        pw = np.where(wet, kap * (h - hstar), -np.inf)       # pressure after the update
        if P['y_a'] > 0: pw = pw - P['y_a'] * (1 - np.exp(-age / P['tau_y']))     # stalled (old) boundary hardens
        ybase = P['y0']
        if P['yield_on'] == 'h': pw = np.where(wet, h, -np.inf); ybase = P['hy0']      # thickness criterion: spill when h_i > hy_j
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
            amt = np.minimum(P['h_fill'], 0.5 * h[sy, sx] / cnt)
            np.subtract.at(h, (sy, sx), amt)
            h[ys, xs] = amt; wet[ys, xs] = True; age[ys, xs] = 0.0; twet[ys, xs] = t
            p[ys, xs] = p[sy, sx]
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

    # ------------------------------ outputs ------------------------------
    Cn = node_C()
    np.save(os.path.join(out, 'body_native.npy'), h.astype(np.float32)); np.save(os.path.join(out, 'vein_native.npy'), (Cn * wet).astype(np.float32))
    np.save(os.path.join(out, 'twet.npy'), twet.astype(np.float32)); np.save(os.path.join(out, 'age.npy'), np.where(wet, age, -1).astype(np.float32))
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
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
               mass_err_max=float(max(abs(e['V_err']) for e in log)), h_min_seen=hmin_seen, traj=traj)
    cen = centroid(); met['disp'] = round(float(np.hypot(cen[0] - cen0[0], cen[1] - cen0[1])), 2); met['path_len'] = round(float(path_len), 2)
    met['area_end'] = int(wet.sum())
    if wet.sum() > 30:
        lab, nl = ndi.label(wet, structure=np.ones((3, 3))); sizes = np.bincount(lab.ravel())[1:]
        met['body_components'] = int(nl); met['body_largest_frac'] = round(float(sizes.max() / wet.sum()), 3)
        # polarisation of recent growth: mean unit vector from centroid to cells wetted in the last 15% of the run
        ym = wet & (twet > t - max(0.15 * t, 5 * dt))
        if ym.sum() > 5:
            ux = X[ym] - cen[0]; uy = Y[ym] - cen[1]; rr = np.maximum(np.hypot(ux, uy), 1e-6)
            mx, my = float((ux / rr).mean()), float((uy / rr).mean())
            met['growth_polarisation'] = round(float(np.hypot(mx, my)), 3)
            ang = np.arctan2(uy, ux); hist = np.histogram(ang, bins=36, range=(-np.pi, np.pi))[0]
            met['growth_sector_frac'] = round(float((hist > 0).mean()), 3)          # fraction of 10-degree sectors with recent growth
            gl, gn = ndi.label(ndi.binary_dilation(ym, iterations=2)); met['active_front_patches'] = int(gn)
        # travel direction: centroid displacement over the last 40% of logged time
        i0 = int(len(traj) * 0.6); ddx = traj[-1][1] - traj[i0][1]; ddy = traj[-1][2] - traj[i0][2]
        if np.hypot(ddx, ddy) < 1.0: ddx, ddy = cen[0] - cen0[0], cen[1] - cen0[1]
        nrm = np.hypot(ddx, ddy)
        met['late_speed'] = round(float(np.hypot(traj[-1][1] - traj[i0][1], traj[-1][2] - traj[i0][2]) / max(traj[-1][0] - traj[i0][0], 1e-9)), 4)
        if nrm > 0.5:
            ux, uy = ddx / nrm, ddy / nrm
            big = lab == (np.argmax(sizes) + 1)
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
    e = met.get('eval_primary', {})
    print(name, 'EVAL', {k: e.get(k) for k in ('body_solidity', 'branch_points', 'loops', 'vein_area_frac', 'vein_largest_frac', 'width_ratio_p90_p10', 'strength_ratio_p90_p10')}, e.get('verdict'))
    return met


if __name__ == '__main__':
    name = sys.argv[1]; over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    run(name, over)
