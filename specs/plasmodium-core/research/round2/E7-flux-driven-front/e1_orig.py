#!/usr/bin/env python3
"""E1 - front sink + Poisson pressure + current reinforcement on lattice edges.

usage: python3 e1.py NAME '{"param": value, ...}'
writes runs/NAME/{body.npy, vein.npy, snapshot_*.png, params.json, metrics.json, eval.json, eval_radius.json, overlay.png}

Model (all structure must emerge; nothing is drawn by hand):
  nodes = lattice cells, edges = lattice links (sq4 / sq8 / hex), each edge has conductance C_e >= 0
  wet(t)  : body mask, prescribed kinematically (growing noisy disc, or translating disc / teardrop)
  S       : sink on front cells (wet cells with a dry neighbour), source = point / whole body / retreating rear
  pressure: sum_e w_e (p_i - p_j) = S_i  on wet nodes, w_e = g_e (C_e + r) / L_e   (exact sparse solve or k warm-started Jacobi sweeps)
  flux    : Q_e = w_e (p_i - p_j)
  adapt   : dC_e/dt = rate * ( f(|Q_e|/Q0) - C_e ),  f = x^gamma  (pow)  or  x^gamma/(1+x^gamma)  (sig)
  new edge: C_e = D0 * (1 + D0_noise * U(-1,1))   (static white noise, no spatial structure)
"""
import numpy as np, json, sys, os, time, subprocess
import scipy.sparse as sp, scipy.sparse.linalg as spl
from scipy import ndimage as ndi
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(os.path.dirname(HERE), 'common', 'eval_morph.py')

DEF = dict(
    N=128, seed=1, lattice='sq4', jitter=0.0, edge_sigma=0.0,
    mode='grow', source='point', v=0.5, dt=0.1, R_init=6.0, R_frac=0.42, front_rough=1.0,
    Rb_frac=0.2, travel_frac=0.5, taper=2.5, hold=0.0,
    law='sig', gamma=1.5, Q0=1.0, j0=0.15, r=1e-3, D0=0.1, D0_noise=0.3, rate=1.0,
    solver='exact', k=20, omega=0.9, sink_fluct=0.0, flucT=1.0, check_exact=0,
    front_rule='prescribed', cost=1.0, Dm=0.0, render_scale=4,
    nsnap=4, do_eval=1,
)


def run(name, over):
    P = dict(DEF); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    N = P['N']; lat = P['lattice']
    if lat == 'sq4': dirs = [(1, 0), (0, 1)]
    elif lat == 'sq8': dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]
    elif lat == 'hex': dirs = [(1, 0), (0, 1), (-1, 1)]
    else: raise ValueError(lat)
    alldirs = dirs + [(-d[0], -d[1]) for d in dirs]
    jj, ii = np.mgrid[0:N, 0:N].astype(float)
    if lat == 'hex': X = ii + 0.5 * jj; Y = jj * np.sqrt(3) / 2; cell_area = np.sqrt(3) / 2
    else: X = ii.copy(); Y = jj.copy(); cell_area = 1.0
    if P['jitter'] > 0:
        X = X + P['jitter'] * rng.uniform(-.5, .5, (N, N)); Y = Y + P['jitter'] * rng.uniform(-.5, .5, (N, N))
    c0 = N // 2
    cx, cy = float(X[c0, c0]), float(Y[c0, c0])
    interior = (ii >= 2) & (ii < N - 2) & (jj >= 2) & (jj < N - 2)

    def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # a at the neighbour in direction d
    def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))      # edge array of the neighbour at -d (edge arriving here)

    Ls = [np.hypot(nb(X, d) - X, nb(Y, d) - Y) for d in dirs]
    Ex = [(nb(X, d) - X) / L for d, L in zip(dirs, Ls)]
    Ey = [(nb(Y, d) - Y) / L for d, L in zip(dirs, Ls)]
    G = [np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in dirs]
    Cinit = [P['D0'] * (1 + P['D0_noise'] * rng.uniform(-1, 1, (N, N))) for _ in dirs]
    eta = ndi.gaussian_filter(rng.normal(size=(N, N)), 2.0); eta /= eta.std()

    Rmax = P['R_frac'] * N * (0.95 if lat == 'hex' else 1.0)
    v = P['v']; dt = P['dt']
    dist = np.hypot(X - cx, Y - cy)
    if P['mode'] == 'grow':
        T = (dist - P['R_init'] + P['front_rough'] * eta) / v
        T[dist < P['R_init']] = -1
        T[~interior | (dist > Rmax + 3)] = np.inf
        steps = int((Rmax - P['R_init']) / v / dt) + int(P['hold'] / dt)
        tgrow = (Rmax - P['R_init']) / v
        def wet_at(t): return T <= min(t, tgrow)
        def centre(t): return cx, cy
        def Rnow(t): return P['R_init'] + v * min(t, tgrow)
    else:
        Rb = P['Rb_frac'] * N; travel = P['travel_frac'] * N
        tail = P['taper'] * Rb if P['mode'] == 'teardrop' else Rb
        x0 = 4 + tail + 2
        steps = int(travel / v / dt)
        def centre(t): return x0 + v * t, cy
        def Rnow(t): return Rb
        def wet_at(t):
            u = X - (x0 + v * t); w = Y - cy
            rr = np.hypot(u, w) + P['front_rough'] * eta
            if P['mode'] == 'translate':
                m = rr < Rb
            else:
                half = Rb * (1 + u / tail)
                m = np.where(u >= 0, rr < Rb, (np.abs(w) + P['front_rough'] * eta < half))
            return m & interior
    src_r = 2.0

    C = [np.zeros((N, N)) for _ in dirs]
    act_prev = [np.zeros((N, N), bool) for _ in dirs]
    p = np.zeros((N, N)); wet_prev = np.zeros((N, N), bool)
    acc = np.zeros((N, N))                      # for flow-coupled front rule
    wet_dyn = None
    snaps = sorted(set(int(steps * (i + 1) / P['nsnap']) for i in range(P['nsnap'])))
    log = []; t0 = time.time(); flux_err = []
    fl = np.zeros((N, N))

    # ---------- image helpers (hex / jitter -> square image by nearest node) ----------
    if lat == 'hex':
        H = int(2 * Rmax + 12); ox = cx - H / 2; oy = cy - H / 2
        py, px = np.mgrid[0:H, 0:H].astype(float)
        jq = np.clip(np.rint((py + oy) / (np.sqrt(3) / 2)).astype(int), 0, N - 1)
        iq = np.clip(np.rint(px + ox - 0.5 * jq).astype(int), 0, N - 1)
        def to_img(a): return a[jq, iq]
        icx, icy = cx - ox, cy - oy
    else:
        H = N; ox = oy = 0.0
        def to_img(a): return a
        icx, icy = cx, cy

    def node_fields(Q):
        Cn = np.zeros((N, N)); qx = np.zeros((N, N)); qy = np.zeros((N, N))
        for k, d in enumerate(dirs):
            Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d)))
            fx = Q[k] * Ex[k] * Ls[k]; fy = Q[k] * Ey[k] * Ls[k]
            qx += 0.5 * (fx + rev(fx, d)); qy += 0.5 * (fy + rev(fy, d))
        return Cn, qx / cell_area, qy / cell_area

    def render(path, wet, front, t):
        s = max(1, 1024 // H)
        base = np.zeros((H, H, 3), np.uint8); base[:] = (12, 22, 12)
        wi = to_img(wet); fi = to_img(front)
        base[wi] = (96, 84, 26); base[fi] = (150, 132, 40)
        im = Image.fromarray(base).resize((H * s, H * s), Image.NEAREST)
        dr = ImageDraw.Draw(im)
        cref = 1.0
        segs = []
        for k, d in enumerate(dirs):
            ys, xs = np.nonzero(C[k] > 0.008 * cref)
            cv = C[k][ys, xs]
            x1 = X[ys, xs]; y1 = Y[ys, xs]
            ys2 = (ys + d[1]) % N; xs2 = (xs + d[0]) % N
            x2 = X[ys2, xs2]; y2 = Y[ys2, xs2]
            for a, b, c_, d_, e in zip(x1, y1, x2, y2, cv): segs.append((e, a, b, c_, d_))
        segs.sort()
        for e, a, b, c_, d_ in segs:
            wd = 0.7 * (e / cref) ** 0.25                      # tube radius ~ C^(1/4), in cells
            wpx = max(1, int(round(wd * s)))
            br = min(1.0, 0.45 + 0.4 * wd)
            col = (int(255 * br), int(228 * br), int(70 * br))
            dr.line([((a - ox + .5) * s, (b - oy + .5) * s), ((c_ - ox + .5) * s, (d_ - oy + .5) * s)], fill=col, width=wpx)
        im.save(path)

    def ring_stats(qm_img, t):
        ccx, ccy = centre(t); ccx -= ox; ccy -= oy; R = Rnow(t); res = {}
        for f in (0.25, 0.5, 0.75, 0.9):
            rho = f * R; n = max(8, int(np.ceil(2 * np.pi * rho)))
            th = np.arange(n) * 2 * np.pi / n
            px_ = np.clip(np.rint(ccx + rho * np.cos(th)).astype(int), 0, H - 1)
            py_ = np.clip(np.rint(ccy + rho * np.sin(th)).astype(int), 0, H - 1)
            q = qm_img[py_, px_]
            if q.sum() <= 0: res[str(f)] = None; continue
            order = np.argsort(-q); cs = np.cumsum(q[order]); n80 = int(np.searchsorted(cs, 0.8 * cs[-1]) + 1)
            top = np.zeros(n, bool); top[order[:n80]] = True
            runs = int(np.sum(top & ~np.roll(top, 1))); runs = max(runs, 1)
            res[str(f)] = dict(n=n, n80_frac=round(n80 / n, 3), veins=runs, PR=round(float(q.sum() ** 2 / (n * (q ** 2).sum())), 3))
        return res

    def aniso(qx, qy, t):
        ccx, ccy = centre(t); R = Rnow(t)
        qxi = ndi.gaussian_filter(to_img(qx), 1.5); qyi = ndi.gaussian_filter(to_img(qy), 1.5)
        py_, px_ = np.mgrid[0:H, 0:H]; rr = np.hypot(px_ + ox - ccx, py_ + oy - ccy)
        m = (rr > 0.3 * R) & (rr < 0.9 * R)
        w = np.hypot(qxi, qyi)[m] ** 2; th = np.arctan2(qyi[m], qxi[m])        # flux^2 weighting -> dominated by veins
        o = {}
        for k in (4, 6, 8):
            z = (w * np.exp(1j * k * th)).sum() / max(w.sum(), 1e-30)
            o[f'A{k}'] = round(float(abs(z)), 3); o[f'A{k}_re'] = round(float(z.real), 3)
        # deviation of flux direction from radial direction (0 = purely radial veins)
        thr = np.arctan2((py_ + oy - ccy)[m], (px_ + ox - ccx)[m])
        dev = np.abs(np.angle(np.exp(1j * (th - thr))))
        o['dev_from_radial_deg'] = round(float(np.degrees((w * dev).sum() / max(w.sum(), 1e-30))), 2)
        return o

    def solve_exact(W, S, wet):
        idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
        rows = []; cols = []; vals = []
        for k, d in enumerate(dirs):
            m = W[k] > 0
            a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
            rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
        A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
        A = A + sp.identity(n, format='csc') * 1e-10
        sol = spl.spsolve(A, S[wet], permc_spec='MMD_AT_PLUS_A')
        pp = np.zeros((N, N)); pp[wet] = sol - sol.mean()
        return pp

    def jacobi(p, W, S, k, omega):
        diag = np.zeros((N, N))
        for kk, d in enumerate(dirs): diag += W[kk] + rev(W[kk], d)
        ok = diag > 0; dsafe = np.where(ok, diag, 1.0)
        for _ in range(k):
            num = S.copy()
            for kk, d in enumerate(dirs):
                num += W[kk] * nb(p, d) + rev(W[kk] * p, d)
            p = np.where(ok, (1 - omega) * p + omega * num / dsafe, 0.0)
        return p

    # ------------------------------ main loop ------------------------------
    for step in range(steps + 1):
        t = step * dt
        if P['front_rule'] == 'prescribed':
            wet = wet_at(t)
        else:                                   # flow-coupled front: a dry cell is wetted when it has received `cost` volume
            if wet_dyn is None: wet_dyn = (dist < P['R_init']) & interior
            wet = wet_dyn
        dry_nb = np.zeros((N, N), bool); ndry = np.zeros((N, N))
        for d in alldirs:
            dn = ~nb(wet, d); dry_nb |= dn; ndry += dn
        front = wet & dry_nb
        newly = wet & ~wet_prev
        if newly.any() and step > 0:                 # warm start for newly wet nodes: mean of already-wet neighbours
            num = np.zeros((N, N)); cnt = np.zeros((N, N))
            for d in alldirs:
                wn = nb(wet_prev, d); num += np.where(wn, nb(p, d), 0); cnt += wn
            p = np.where(newly, num / np.maximum(cnt, 1), p)
        p = np.where(wet, p, 0.0)
        act = []
        for k, d in enumerate(dirs):
            a = wet & nb(wet, d); new = a & ~act_prev[k]
            C[k] = np.where(new, Cinit[k], C[k]) * a
            act.append(a)
        act_prev = act; wet_prev = wet.copy()

        # ---- sources / sinks ----
        S = np.zeros((N, N)); ccx, ccy = centre(t)
        if P['sink_fluct'] > 0:
            if step % max(1, int(P['flucT'] / dt)) == 0:
                fl = np.exp(P['sink_fluct'] * ndi.gaussian_filter(rng.normal(size=(N, N)), 3.0) / 0.094)
        else: fl = 1.0
        if P['mode'] == 'grow':
            S[front] = -P['j0']; S *= fl
            I = -S.sum()
            if P['source'] == 'point':
                sm = (dist < src_r) & wet
            elif P['source'] == 'body':
                sm = wet & ~front
            elif P['source'] == 'ring':                  # annulus source at half radius (control)
                sm = wet & (np.abs(dist - 0.5 * Rnow(t)) < 1.0)
            if sm.sum() == 0: sm = wet & ~front
            S[sm] += I / sm.sum()
        else:
            u = X - ccx; w_ = Y - ccy; rr = np.maximum(np.hypot(u, w_), 1e-6)
            if P['mode'] == 'translate': cosn = u / rr
            else: cosn = np.where(u >= 0, u / rr, -Rb / np.hypot(Rb, tail))     # tapered sides retreat slowly
            S[front & (cosn > 0)] = -P['j0'] * cosn[front & (cosn > 0)]
            S *= fl
            I = -S.sum()
            if P['source'] == 'rear':
                sm = front & (cosn <= 0); wgt = np.where(sm, -cosn + 1e-3, 0.0)
                S += I * wgt / wgt.sum()
            elif P['source'] == 'tail':
                tx = ccx - (0.8 * Rb if P['mode'] == 'translate' else 0.85 * tail)
                sm = (np.hypot(X - tx, Y - ccy) < src_r + 0.5) & wet
                S[sm] += I / sm.sum()
            elif P['source'] == 'body':
                sm = wet & ~front; S[sm] += I / sm.sum()
        S[wet] -= S[wet].sum() / wet.sum()           # exact compatibility

        W = [act[k] * G[k] * (C[k] + P['r']) / Ls[k] for k in range(len(dirs))]
        if P['solver'] == 'exact':
            p = solve_exact(W, S, wet)
        else:
            p = jacobi(p, W, S, P['k'], P['omega'])
        Q = [W[k] * (p - nb(p, dirs[k])) for k in range(len(dirs))]
        if P['solver'] != 'exact' and P['check_exact'] and step % P['check_exact'] == 0 and step > 0:
            pe = solve_exact(W, S, wet)
            Qe = [W[k] * (pe - nb(pe, dirs[k])) for k in range(len(dirs))]
            num = sum(((Q[k] - Qe[k]) ** 2).sum() for k in range(len(dirs))); den = sum((Qe[k] ** 2).sum() for k in range(len(dirs)))
            flux_err.append((round(t, 2), round(float(np.sqrt(num / max(den, 1e-30))), 4)))
        # ---- adaptation ----
        for k in range(len(dirs)):
            x = np.abs(Q[k]) / P['Q0']
            f = x ** P['gamma']
            if P['law'] == 'sig': f = f / (1 + f)
            dC = P['rate'] * (f - C[k])
            if P['Dm'] > 0:                      # lateral diffusion between same-orientation edges (Hu-Cai D^2 Lap c^k)
                lapc = np.zeros((N, N))
                for d in alldirs: lapc += np.where(nb(act[k], d), nb(C[k], d) - C[k], 0.0)
                dC = dC + P['Dm'] * lapc * (4.0 / len(alldirs))
            C[k] = np.maximum(C[k] + dt * dC, 0.0) * act[k]
            if not np.isfinite(C[k]).all():
                log.append(dict(step=step, error='non-finite conductance')); break
        if log and 'error' in log[-1]: break
        # ---- flow-coupled front rule (optional) ----
        if P['front_rule'] != 'prescribed':
            # volume arriving at a front cell is passed on, equally, to its dry neighbours; a dry cell wets at acc >= cost
            give = np.where(front, -S * dt / np.maximum(ndry, 1), 0.0)
            for d in alldirs:
                acc += np.where(~wet & interior & (dist < Rmax), nb(give, d), 0.0)
            noise_cost = P['cost'] * (1 + 0.3 * eta)
            wet_dyn = wet | (acc >= noise_cost)
        if step in snaps or step == steps:
            Cn, qx, qy = node_fields(Q)
            qm = np.hypot(qx, qy)
            rs = ring_stats(to_img(qm), t); an = aniso(qx, qy, t)
            kres = max(abs(sum(Q[k] - rev(Q[k], dirs[k]) for k in range(len(dirs))) - S)[wet].max(), 0) / max(np.abs(S).max(), 1e-30)
            entry = dict(step=step, t=round(t, 2), area=int(wet.sum()), front=int(front.sum()), I=round(float(I), 3),
                         Cmax=float(Cn.max()), kirchhoff_rel_resid=float(kres), rings=rs, aniso=an, elapsed=round(time.time() - t0, 1))
            log.append(entry)
            print(name, json.dumps({k: entry[k] for k in ('step', 't', 'area', 'I', 'Cmax', 'kirchhoff_rel_resid', 'elapsed')}), flush=True)
            if step in snaps:
                render(os.path.join(out, f'snapshot_{snaps.index(step) + 1}_t{int(t):04d}.png'), wet, front, t)
                # edge-level dump for graph analysis (analyze.py); added by the continuing session
                np.savez_compressed(os.path.join(out, f'edges_{snaps.index(step) + 1}.npz'), C=np.array(C, np.float32), Q=np.array(Q, np.float32),
                                    wet=wet, S=S.astype(np.float32), X=X.astype(np.float32), Y=Y.astype(np.float32), dirs=np.array(dirs),
                                    t=t, centre=np.array(centre(t)), R=Rnow(t))
    # ------------------------------ outputs ------------------------------
    Cn, qx, qy = node_fields(Q)
    body = to_img(wet).astype(np.float32); vein = to_img(Cn * wet).astype(np.float32)
    np.save(os.path.join(out, 'body_native.npy'), body); np.save(os.path.join(out, 'vein_native.npy'), vein)
    np.save(os.path.join(out, 'flux_native.npy'), to_img(np.hypot(qx, qy) * wet).astype(np.float32))
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    # OFFICIAL body.npy / vein.npy = rendered tubes: every edge is a tube of diameter 0.7*C^(1/4) cells (Poiseuille D ~ r^4),
    # rasterised at render_scale x.  (native 1-cell-wide diagonal veins are deleted by the 4-connected small-object filter of eval_morph.py)
    rs_ = P['render_scale']
    imv = Image.new('F', (H * rs_, H * rs_), 0.0); drv = ImageDraw.Draw(imv); segs = []
    for k, d in enumerate(dirs):
        ys, xs = np.nonzero(C[k] > 0.008)
        ys2 = (ys + d[1]) % N; xs2 = (xs + d[0]) % N
        for e, a, b, c_, d_ in zip(C[k][ys, xs], X[ys, xs], Y[ys, xs], X[ys2, xs2], Y[ys2, xs2]): segs.append((e, a, b, c_, d_))
    segs.sort()
    for e, a, b, c_, d_ in segs:
        wd = 0.7 * e ** 0.25
        drv.line([((a - ox + .5) * rs_, (b - oy + .5) * rs_), ((c_ - ox + .5) * rs_, (d_ - oy + .5) * rs_)], fill=float(wd), width=max(1, int(round(wd * rs_))))
    body_r = np.kron(body, np.ones((rs_, rs_), np.float32))
    np.save(os.path.join(out, 'body.npy'), body_r); np.save(os.path.join(out, 'vein.npy'), (np.asarray(imv) * (body_r > 0)).astype(np.float32))
    met = dict(name=name, steps=steps, log=log, flux_err=flux_err, runtime=round(time.time() - t0, 1))
    # conductance dynamic range over vein edges (edges carrying more than one front cell's flux)
    allC = np.concatenate([C[k][act[k]] for k in range(len(dirs))]); vc = allC[allC > 1.0] if P['law'] == 'pow' else allC[allC > 0.3]
    if vc.size > 10: met['veinC_p5_p50_p95_max'] = [float(x) for x in np.percentile(vc, [5, 50, 95, 100])]
    if P['do_eval']:
        for bn, vn, en, pn in (('body.npy', 'vein.npy', 'eval.json', 'overlay.png'), ('body_native.npy', 'vein_native.npy', 'eval_native.json', 'overlay_native.png')):
            subprocess.run([sys.executable, EVAL, os.path.join(out, bn), os.path.join(out, vn), '--out', os.path.join(out, en),
                            '--png', os.path.join(out, pn)], stdout=subprocess.DEVNULL)
        try:
            e = json.load(open(os.path.join(out, 'eval.json')))['primary']; er = json.load(open(os.path.join(out, 'eval_native.json')))['primary']
            met['eval_primary'] = e; met['eval_native_primary'] = er
            keys = ('branch_points', 'loops', 'vein_area_frac', 'vein_largest_frac', 'width_ratio_p90_p10', 'strength_ratio_p90_p10', 'endpoints')
            print(name, 'EVAL render', {k: e.get(k) for k in keys}, e.get('verdict'))
            print(name, 'EVAL native', {k: er.get(k) for k in keys}, er.get('verdict'))
        except Exception as ex: print('eval failed', ex)
    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    last = log[-1] if log else {}
    print(name, 'RINGS', json.dumps(last.get('rings')), 'ANISO', json.dumps(last.get('aniso')), 'runtime', met['runtime'], flush=True)
    return met


if __name__ == '__main__':
    name = sys.argv[1]; over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    run(name, over)
