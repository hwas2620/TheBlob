#!/usr/bin/env python3
"""E8-implicit-thickness : semi-implicit thickness model + superlinear edge-conductance reinforcement.

Hypothesis under test
  The old continuum prototype (specs/plasmodium-core/prototype/continuum.py) failed ONLY because the pressure was an
  explicit local elastic-wall pressure whose penetration depth delta = sqrt(2*C*kappa/omega) was << body radius.
  Solving the same thickness model semi-implicitly (screened Poisson) with delta >= body size, plus superlinear
  reinforcement of edge conductances, should give veins + travelling pulsation + mass conservation (+ slime, food).

Model (what this file implements)
  lattice : N x N torus, 8-neighbour edges, dirs (1,0),(0,1),(1,1),(1,-1), weights w = 2/3,2/3,1/6,1/6 (isotropic 9-pt)
  cell    : h (thickness, conserved), phi (phase), s (slime), c (food, static)
  edge    : C_e (conductance), qavg_e (time-averaged |flux density|)
  target thickness   heq = hstar*[(1-eta)*(1-sig_s*s) + eta*v + sig_c*c] - a*hstar*cos(phi)
                     v = min(sqrt(max(Ccell/Ccell0 - 2*Cmin, 0)), vmax)        (stage 1: eta = sig_s = sig_c = 0  ->  heq = hstar - a hstar cos phi)
  pressure           p = kappa*(h - heq)                       (= kappa(h-hstar) + A cos phi with A = kappa*a*hstar)
  edge flux          Q_e = w_e*C_e*(p_i - p_j)                 (i -> j)
  semi-implicit step (1/(kappa*dt) + L_C) p^{n+1} = (h^n - heq^{n+1})/dt        L_C = weighted graph Laplacian  (sparse LU)
                     h^{n+1} = h^n - dt*div Q^{n+1}            (flux form, conservative; donor-cell outflow limiter keeps h>=0)
  flux average       qavg_e <- qavg_e + (dt/T_avg)*(C_e*|dp_e|/L_e - qavg_e)      T_avg >= 1 period
  adaptation         dC_e/dt = rate*( het_e*(qavg_e/Q0)^gamma - C_e ),  Cmin <= C_e <= Cmax
                     (law='sat':  het_e*Fmax*x^gamma/(1+x^gamma), x = qavg/Q0)
  penetration depth  delta0 = sqrt(2*kappa*C0/omega), C0 = 1.  kappa is set from delta0/R.
  phase              'plane'  : phi = k.x - omega t  (lambda = lam_over_D * 2R, direction theta, optional slow rotation)
                     'radial' : phi = k r - omega t
                     'kuramoto': z=exp(i phi) lattice, nsub diffusive coupling sub-steps, omega_i = omega(1 + wf*c + wn*noise)
                     'slime'  : phi = -omega t + ks*s  (phase lag tied to slime age; stage 2)
  stage 2 (free boundary)
     wet set = cells with h >= hdry (dry again below 0.5*hdry).  Unknowns = wet cells.
     gate wet i -> dry j is open iff p_i^n > y_j,  y_j = kappa*hstar*(y0 + ys*s_j - yc*c_j + yn*noise_j);
     open gate: Q = w*Cnew*(p_i - y_j) >= 0 (dry cell = Dirichlet value y_j).  Dry cell accumulates h until h >= hdry.
     new wet cell: all its edges get C = C0*lognormal(sig_new), qavg = Q0 (neutral), phase copied from wet neighbours.
     slime: ds/dt = dep*wet*(1-s) - dec*s.
Initial conditions / noise (no vein path is seeded)
  h = hstar inside the initial disc.  C_e = exp(sig_C0*N(0,1)) white noise.  het_e = exp(sig_het*N(0,1)) static white
  log-normal edge heterogeneity multiplying the reinforcement target (sig_het = 0 -> none).
Outputs: runs/NAME/{body.npy, vein.npy (rendered tubes, value = C^(1/4), render_scale x), body_native.npy, vein_native.npy,
         snapshot_*.png, params.json, metrics.json}
"""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl, json, os, sys, time
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
WGT = [2 / 3, 2 / 3, 1 / 6, 1 / 6]
LEN = [1.0, 1.0, 2 ** .5, 2 ** .5]

DEF = dict(
    stage=1, N=96, R=40.0, seed=1, hstar=1.0,
    period=24.0, spp=24, periods=200,
    delta_over_R=1.0, a=0.15,
    phase='plane', lam_over_D=1.0, theta=0.0, rot_periods=0.0,
    kur_K=0.2, kur_nsub=8, wf=0.0, wn=0.0, ks=3.14159,
    gamma=1.5, law='pow', Fmax=30.0, rate_periods=8.0, Tavg_periods=1.5, Q0='auto', Q0_warm=3,
    Cmin=0.02, Cmax=1e3, sig_C0=0.1, sig_het=0.3, n_adapt=6,
    # stage 2
    eta=0.0, vmax=3.0, sig_s=0.0, sig_c=0.0,
    hdry=0.1, y0=0.03, ys=0.5, yc=0.2, yn=0.01, Cnew=1.0, sig_new=0.3,
    dep_periods=40.0, dec_periods=2000.0,
    foods=[], food_r=0.10, R0=30.0, h0=1.15, c0=[0.5, 0.5],
    snaps=4, render_scale=3,
    solver='lu', jac_k=30, jac_w=0.8,      # solver='jacobi': jac_k warm-started damped-Jacobi sweeps per step instead of sparse LU
)


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # value at the neighbour in direction d
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))      # edge array of the neighbour at -d (edge arriving here)


def run(name, **over):
    P = dict(DEF); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    N = P['N']; R = P['R']; hs = P['hstar']; st2 = P['stage'] == 2
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    cx = cy = (N - 1) / 2
    rr = np.hypot(xx - cx, yy - cy)
    dt = P['period'] / P['spp']; omega = 2 * np.pi / P['period']
    delta0 = P['delta_over_R'] * R
    kappa = omega * delta0 ** 2 / 2.0                     # delta0 = sqrt(2 kappa C0 / omega), C0 = 1
    scr = 1.0 / (kappa * dt)
    steps = int(P['periods'] * P['spp'])
    alpha = dt / (P['Tavg_periods'] * P['period'])
    rate = 1.0 / (P['rate_periods'] * P['period'])
    gam = P['gamma']

    if st2:
        act = np.hypot(xx - P['c0'][0] * N, yy - P['c0'][1] * N) < P['R0']
        h = np.where(act, P['h0'] * hs, 0.0)
    else:
        act = rr < R
        h = np.where(act, hs, 0.0)
    C = [np.exp(P['sig_C0'] * rng.normal(size=(N, N))) for _ in DIRS]
    het = [np.exp(P['sig_het'] * rng.normal(size=(N, N))) for _ in DIRS]
    qavg = [np.zeros((N, N)) for _ in DIRS]
    s = np.zeros((N, N))
    c = np.zeros((N, N))
    for fx, fy, amp in P['foods']:
        c += amp * np.exp(-((xx - fx * N) ** 2 + (yy - fy * N) ** 2) / (2 * (P['food_r'] * N) ** 2))
    ynoise = ndi.gaussian_filter(rng.normal(size=(N, N)), 1.5, mode='wrap'); ynoise /= ynoise.std()
    wnoise = ndi.gaussian_filter(rng.normal(size=(N, N)), 4.0, mode='wrap'); wnoise /= wnoise.std()
    z = np.exp(1j * rng.uniform(0, 2 * np.pi, (N, N))) if P['phase'] == 'kuramoto' else None
    p = np.zeros((N, N))
    M0 = h.sum()
    Ccell0 = 2 * sum(WGT)
    Q0 = None if P['Q0'] == 'auto' else float(P['Q0'])
    lam = P['lam_over_D'] * 2 * (R if not st2 else P['R0'] * 1.5)
    kwave = 2 * np.pi / lam

    def phase(t):
        nonlocal z
        ph = P['phase']
        if ph == 'plane':
            th = P['theta'] + (2 * np.pi * t / (P['rot_periods'] * P['period']) if P['rot_periods'] > 0 else 0.0)
            return kwave * ((xx - cx) * np.cos(th) + (yy - cy) * np.sin(th)) - omega * t
        if ph == 'radial':
            return kwave * rr - omega * t
        if ph == 'slime':
            return P['ks'] * s - omega * t
        if ph == 'kuramoto':
            for _ in range(P['kur_nsub']):
                zz = np.where(act, z, 0)
                cnt = sum(nb(act, d).astype(float) + rev(act, d) for d in DIRS[:2])
                sm = sum(nb(zz, d) + rev(zz, d) for d in DIRS[:2])
                z = z + P['kur_K'] * (sm - cnt * z) * act
                z = z / np.maximum(np.abs(z), 1e-9)
            z = z * np.exp(-1j * omega * (1 + P['wf'] * c + P['wn'] * wnoise) * dt)
            return np.angle(z)
        raise ValueError(ph)

    def ccell():
        cc = np.zeros((N, N))
        for k, d in enumerate(DIRS):
            e = C[k] * (act & nb(act, d))
            cc += WGT[k] * (e + rev(e, d))
        return cc

    lu = None; idx = None; G = None; gates = None; dirty = True
    hist = []; log = []; snaps_at = [int(round(steps * (i + 1) / P['snaps'])) for i in range(P['snaps'])]
    snap_i = 0; t0 = time.time(); nfact = 0
    hbuf = []; pbuf = []; front_area = []
    maxdm = 0.0
    yld = None

    for n in range(1, steps + 1):
        t = n * dt
        phi = phase(t)
        if st2:
            v = np.minimum(np.sqrt(np.maximum(ccell() / Ccell0 - 2 * P['Cmin'], 0)), P['vmax'])
            heq = hs * ((1 - P['eta']) * (1 - P['sig_s'] * s) + P['eta'] * v + P['sig_c'] * c) - P['a'] * hs * np.cos(phi)
            heq = np.maximum(heq, 0.0)
            yld = kappa * hs * (P['y0'] + P['ys'] * s - P['yc'] * c + P['yn'] * ynoise)
            # gates from previous pressure
            ng = []
            for k, d in enumerate(DIRS):
                actb = nb(act, d)
                gf = act & ~actb & (p > nb(yld, d))                 # a wet -> b dry
                gb = ~act & actb & (nb(p, d) > yld)                 # b wet -> a dry
                ng.append((gf, gb))
            if gates is None or any((a_[0] != b_[0]).any() or (a_[1] != b_[1]).any() for a_, b_ in zip(ng, gates)):
                dirty = True
            gates = ng
        else:
            heq = hs - P['a'] * hs * np.cos(phi)
        if dirty:
            idx = -np.ones((N, N), int); nact = int(act.sum()); idx[act] = np.arange(nact)
            diag = np.full((N, N), scr)
            rows = []; cols = []; vals = []; G = []
            for k, d in enumerate(DIRS):
                g = WGT[k] * C[k] * (act & nb(act, d)); G.append(g)
                m = g > 0
                a_ = idx[m]; b_ = nb(idx, d)[m]; w = g[m]
                rows += [a_, b_]; cols += [b_, a_]; vals += [-w, -w]
                diag += g + rev(g, d)
                if st2:
                    gf, gb = gates[k]
                    diag += WGT[k] * P['Cnew'] * gf
                    diag += rev(WGT[k] * P['Cnew'] * gb, d)
            diagJ = diag
            if P['solver'] == 'lu':
                rows.append(np.arange(nact)); cols.append(np.arange(nact)); vals.append(diag[act])
                A = sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nact, nact))
                lu = spl.splu(A, permc_spec='MMD_AT_PLUS_A')
            nfact += 1; dirty = False
        rhs = (h - heq) / dt
        if st2:
            for k, d in enumerate(DIRS):
                gf, gb = gates[k]
                rhs = rhs + WGT[k] * P['Cnew'] * gf * nb(yld, d)
                rhs = rhs + rev(WGT[k] * P['Cnew'] * gb * yld, d)
        if P['solver'] == 'lu':
            p = np.zeros((N, N)); p[act] = lu.solve(rhs[act])
        else:
            wj = P['jac_w']
            for _ in range(P['jac_k']):
                acc = rhs.copy()
                for k, d in enumerate(DIRS): acc += G[k] * nb(p, d) + rev(G[k] * p, d)
                p = act * ((1 - wj) * p + wj * acc / diagJ)
        # fluxes
        Q = []; Qg = []
        outv = np.zeros((N, N))
        for k, d in enumerate(DIRS):
            dp = p - nb(p, d)
            q = G[k] * dp; Q.append(q)
            outv += np.maximum(q, 0) + rev(np.maximum(-q, 0), d)
            qi = C[k] * np.abs(dp) / LEN[k] * (G[k] > 0)
            qavg[k] += alpha * (qi - qavg[k])
            if st2:
                gf, gb = gates[k]
                qf = np.maximum(WGT[k] * P['Cnew'] * gf * (p - nb(yld, d)), 0)          # a -> b (b dry)
                qb = np.maximum(WGT[k] * P['Cnew'] * gb * (nb(p, d) - yld), 0)          # b -> a (a dry)
                Qg.append((qf, qb))
                outv += qf + rev(qb, d)
        if st2:
            f = np.minimum(1.0, 0.98 * h / np.maximum(dt * outv, 1e-30))
            for k, d in enumerate(DIRS):
                q = Q[k]; q = np.where(q > 0, q * f, q * nb(f, d)); Q[k] = q
                qf, qb = Qg[k]; Qg[k] = (qf * f, qb * nb(f, d))
        for k, d in enumerate(DIRS):
            q = Q[k]
            if st2: q = q + Qg[k][0] - Qg[k][1]
            h = h - dt * q + dt * rev(q, d)
        maxdm = max(maxdm, abs(h.sum() - M0) / M0)
        if st2:
            newly = (~act) & (h >= P['hdry'] * hs)
            dried = act & (h < 0.5 * P['hdry'] * hs)
            if newly.any() or dried.any():
                if newly.any():
                    q0v = Q0 if Q0 is not None else 0.0
                    for k, d in enumerate(DIRS):
                        e = newly | nb(newly, d)
                        C[k] = np.where(e, np.exp(P['sig_new'] * rng.normal(size=(N, N))), C[k])
                        qavg[k] = np.where(e, q0v, qavg[k])
                    if z is not None:
                        zz = np.where(act, z, 0); sm = sum(nb(zz, d) + rev(zz, d) for d in DIRS)
                        z = np.where(newly & (np.abs(sm) > 0), sm / np.maximum(np.abs(sm), 1e-9), z)
                act = (act | newly) & ~dried
                p = p * act
                dirty = True
            s = s + dt * (act * (1 - s) / (P['dep_periods'] * P['period']) - s / (P['dec_periods'] * P['period']))
        # Q0 auto : median active-edge qavg after warm-up at (nearly) uniform C
        if Q0 is None and n == int(P['Q0_warm'] * P['spp']):
            vals_ = np.concatenate([qavg[k][(act & nb(act, d))] for k, d in enumerate(DIRS)])
            Q0 = float(np.median(vals_)); P['Q0_used'] = Q0
        if Q0 is not None and n % P['n_adapt'] == 0 and n > P['Q0_warm'] * P['spp']:
            dta = dt * P['n_adapt']
            for k, d in enumerate(DIRS):
                x = (qavg[k] / Q0) ** gam
                tgt = het[k] * (x if P['law'] == 'pow' else P['Fmax'] * x / (1 + x))
                C[k] = np.clip(C[k] + (1 - np.exp(-rate * dta)) * (tgt - C[k]), P['Cmin'], P['Cmax'])
            dirty = True
        if n > steps - 2 * P['spp']:
            hbuf.append(h.copy()); pbuf.append(phi.copy() if np.ndim(phi) else None)
        if n % (P['spp'] * max(1, int(P['periods'] // 20))) == 0 or n == steps:
            cc = ccell()[act]
            Fc = sum(WGT[k] * (qavg[k] + rev(qavg[k], d)) for k, d in enumerate(DIRS))[act]
            srt = np.sort(Fc)[::-1]; cs = np.cumsum(srt)
            n80 = float((np.searchsorted(cs, 0.8 * cs[-1]) + 1) / len(srt)) if cs[-1] > 0 else 1.0
            log.append(dict(period=round(t / P['period'], 2), area=int(act.sum()), mass_err=float(abs(h.sum() - M0) / M0),
                            body_mass_frac=float(h[act].sum() / M0), cxy=[round(float((xx * h * act).sum() / max((h * act).sum(), 1e-9)), 2), round(float((yy * h * act).sum() / max((h * act).sum(), 1e-9)), 2)],
                            fresh_frac=float((act & (s < 0.2)).sum() / max(act.sum(), 1)), Cc_p10=float(np.percentile(cc, 10)), Cc_p50=float(np.percentile(cc, 50)),
                            Cc_p99=float(np.percentile(cc, 99)), n80=round(n80, 3), nfact=nfact, wall=round(time.time() - t0, 1)))
            print(name, log[-1], flush=True)
        if snap_i < len(snaps_at) and n >= snaps_at[snap_i]:
            snap_i += 1
            render(os.path.join(out, f'snapshot_{snap_i}.png'), h, ccell(), act, s, c, hs, Ccell0, phi)

    # ---------------- metrics ----------------
    met = dict(name=name, kappa=kappa, delta0=delta0, screen_len_step=float(np.sqrt(kappa * dt)), Q0=Q0, steps=steps, max_mass_err=maxdm,
               runtime=round(time.time() - t0, 1), nfact=nfact, log=log)
    H = np.array(hbuf); nT = len(H)
    tt = (np.arange(steps - nT + 1, steps + 1) * dt)
    ph_ = np.exp(1j * omega * tt)[:, None, None]
    hhat = 2 * (H * ph_).mean(0)                                  # complex amplitude of the omega component
    m = act & (H.min(0) > 0.5 * P['hdry'] * hs)
    if m.sum() > 10:
        amp = np.abs(hhat)[m]
        met['h_amp_mean_over_hstar'] = float(amp.mean() / hs)
        met['h_amp_target'] = P['a']
        met['h_std_time_mean'] = float(H.std(0)[m].mean() / hs)
        # travelling-wave check: plane fit of the phase of hhat  (unwrap-free: fit exp(i*arg) against exp(i k.x))
        ang = np.angle(hhat)
        gx = np.angle((hhat * np.conj(nb(hhat, (1, 0))))[m & nb(m, (1, 0))])
        gy = np.angle((hhat * np.conj(nb(hhat, (0, 1))))[m & nb(m, (0, 1))])
        met['phase_grad_mean_xy'] = [float(gx.mean()), float(gy.mean())]
        met['phase_grad_expected_k'] = float(kwave)
        met['phase_span_rad'] = float(np.ptp(np.unwrap(np.sort(ang[m]))))
        kmag = float(np.hypot(gx.mean(), gy.mean()))
        met['wave_len_measured_cells'] = float(2 * np.pi / kmag) if kmag > 1e-6 else None
        met['wave_speed_cells_per_period'] = met['wave_len_measured_cells']
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    # ---------------- official outputs ----------------
    cc = ccell()
    body = np.where(act, h, 0).astype(np.float32)
    np.save(os.path.join(out, 'body_native.npy'), body); np.save(os.path.join(out, 'vein_native.npy'), (cc * act).astype(np.float32))
    rs_ = P['render_scale']
    imv = Image.new('F', (N * rs_, N * rs_), 0.0); drv = ImageDraw.Draw(imv); segs = []
    for k, d in enumerate(DIRS):
        E = act & nb(act, d) & (C[k] > 1.5 * P['Cmin'])
        ys, xs = np.nonzero(E)
        if abs(d[0]) + abs(d[1]) and len(ys):
            ok = (xs + d[0] >= 0) & (xs + d[0] < N) & (ys + d[1] >= 0) & (ys + d[1] < N)
            for e, x_, y_ in zip(C[k][ys[ok], xs[ok]], xs[ok], ys[ok]): segs.append((float(e), int(x_), int(y_), d[0], d[1]))
    segs.sort()
    for e, x_, y_, dx, dy in segs:
        wd = 0.7 * e ** 0.25
        drv.line([((x_ + .5) * rs_, (y_ + .5) * rs_), ((x_ + dx + .5) * rs_, (y_ + dy + .5) * rs_)], fill=float(wd), width=max(1, int(round(wd * rs_))))
    body_r = np.kron(body, np.ones((rs_, rs_), np.float32))
    np.save(os.path.join(out, 'body.npy'), body_r)
    np.save(os.path.join(out, 'vein.npy'), (np.asarray(imv) * (body_r > 0)).astype(np.float32))
    np.savez_compressed(os.path.join(out, 'state.npz'), h=h.astype(np.float32), C=np.array(C, np.float32), qavg=np.array(qavg, np.float32),
                        act=act, s=s.astype(np.float32), hhat=hhat.astype(np.complex64), p=p.astype(np.float32))
    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    return met


def render(path, h, cc, act, s, c, hs, Ccell0, phi):
    N = h.shape[0]; sc = max(1, 384 // N)
    hv = np.clip(h / (2.0 * hs), 0, 1)
    a = act[..., None].astype(float)
    bg = np.stack([14 + 60 * s + 60 * np.clip(c, 0, 1), 26 + 50 * s + 60 * np.clip(c, 0, 1), 12 + 20 * s], -1)
    fg = np.stack([70 + 185 * hv ** 0.8, 50 + 165 * hv ** 0.8, 5 + 40 * hv], -1)
    im1 = np.clip(bg * (1 - a) + fg * a, 0, 255)
    lv = np.clip((np.log10(np.maximum(cc / Ccell0, 1e-3)) + 2) / 5, 0, 1) * act       # log scale 1e-2 .. 1e3
    im2 = np.stack([255 * lv, 255 * lv ** 1.5, 80 * lv + 20 * act], -1)
    if np.ndim(phi):
        pc = (np.cos(phi) * 0.5 + 0.5) * act
        im3 = np.stack([255 * pc, 60 * act + 0 * pc, 255 * (1 - pc) * act], -1)
        img = np.concatenate([im1, im2, im3], 1)
    else:
        img = np.concatenate([im1, im2], 1)
    img = np.kron(img, np.ones((sc, sc, 1)))
    Image.fromarray(img.astype(np.uint8)).save(path)


if __name__ == '__main__':
    name = sys.argv[1]
    over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    m = run(name, **over)
    print(json.dumps({k: v for k, v in m.items() if k != 'log'}, indent=1))
