#!/usr/bin/env python3
"""E6 - shuttle (AC) flow, DC front sink, fluctuating sinks and food-pair loads on a FIXED body.
Current reinforcement on sq8 lattice edges, exact sparse solve.  Derived from E1's e1.py (same lattice, edge noise,
adaptation law and tube rendering); the body is a fixed mask and several loads are solved with one factorisation.

usage: python3 e6.py NAME '{"param": value, ...}'
writes runs/NAME/{body.npy, vein.npy, snapshot_*.png, edges_*.npz, params.json, metrics.json, eval.json, overlay.png}

  load     S(t) = f_dc*S_dc + f_ac*S_ac(t) + f_food*S_pair(k),   f_dc = 1 - f_ac - f_food
  pressure sum_e w_e (p_i - p_j) = S_i,  w_e = g_e (C_e + r) / L_e
  adapt    dC_e/dt = rate * ( <|Q_e|>^gamma - C_e )          (Q0 = 1, non-saturating power law)
  <|Q|>    avg='quad': exact cycle average at frozen C (K_phase phases x K_sub sink subsets x food pairs)
           avg='ema' : explicit time stepping, |Q| low-passed with tau = ema_periods * T, adaptation time adapt_periods * T
Nothing is drawn by hand: initial C = D0*(1 + D0_noise*U(-1,1)) on every edge, static lognormal edge factor g_e.
"""
import numpy as np, json, sys, os, time, subprocess, itertools, warnings
warnings.filterwarnings("ignore")
import scipy.sparse as sp, scipy.sparse.linalg as spl
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
from skimage.morphology import remove_small_objects, remove_small_holes
from skimage.measure import label, euler_number

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(os.path.dirname(HERE), 'common', 'eval_morph.py')

DEF = dict(
    N=128, seed=1, edge_sigma=0.5, D0=1.0, D0_noise=0.3, r=1e-3,
    body='disc', R_frac=0.42, front_rough=1.0, fan_angle=110.0,
    f_ac=0.0, f_food=0.0, dc_source='rear',
    ac='radial', ac_origin='rear', lam_frac=1.0, theta0=0.0, rot_turns=0.0, wobble_deg=0.0, K_phase=12, ac_dirs=[],
    avg='quad', spp=12, ema_periods=1.0, adapt_periods=10.0,
    gamma=4.0 / 3.0, rate=1.0, dt=0.2, steps=600,
    p_on=1.0, corr_len=0.0, K_sub=4, avg_power=1.0,
    n_food=0, food_minsep=0.6, food_seed=0,
    init_from='', nsnap=4, render_scale=4, do_eval=1,
)

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALLD = DIRS + [(-d[0], -d[1]) for d in DIRS]


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # a at the neighbour in direction d


def own_metrics(body_r, vein_r, scale):
    """loops = holes of the tube raster; 'big' = holes with area >= 4 cell^2 (lattice-scale gaps between parallel tubes are filled)."""
    bm = body_r > 0; vin = vein_r[bm]; p99 = float(np.percentile(vin, 99)); out = {'w_p99': round(p99, 3)}
    amin = int(4 * scale * scale)
    for rel in (0.2, 0.35, 0.5):
        vm = bm & (vein_r > rel * p99) & (p99 > 0)
        vm = remove_small_objects(vm, 8)
        vmf = remove_small_holes(vm, amin)
        lab = label(vmf, connectivity=2); nc = int(lab.max())
        if nc == 0:
            out[f'r{rel}'] = dict(loops_big=0, comps=0, largest_frac=0.0, vein_frac=0.0); continue
        sizes = np.bincount(lab.ravel())[1:]
        loops = int(nc - euler_number(vmf, connectivity=2))
        holes = ndi.binary_fill_holes(vmf) & ~vmf
        hl, nh = ndi.label(holes)
        ha = np.bincount(hl.ravel())[1:] / (scale * scale) if nh else np.array([0.0])
        # loops of the largest connected vein component only
        big = lab == (1 + int(np.argmax(sizes)))
        loops_main = int(1 - euler_number(big, connectivity=2))
        out[f'r{rel}'] = dict(loops_big=loops, loops_main=loops_main, comps=nc, largest_frac=round(float(sizes.max() / sizes.sum()), 3),
                              vein_frac=round(float(vmf.sum() / bm.sum()), 4), hole_area_med=round(float(np.median(ha)), 1),
                              hole_area_frac=round(float(holes.sum() / bm.sum()), 4))
    return out


def run(name, over):
    P = dict(DEF); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    N = P['N']
    jj, ii = np.mgrid[0:N, 0:N].astype(float); X = ii; Y = jj
    G = [np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in DIRS]
    Cinit = [P['D0'] * (1 + P['D0_noise'] * rng.uniform(-1, 1, (N, N))) for _ in DIRS]
    eta = ndi.gaussian_filter(rng.normal(size=(N, N)), 2.0); eta /= eta.std()
    cx = cy = float(N // 2)
    interior = (ii >= 2) & (ii < N - 2) & (jj >= 2) & (jj < N - 2)

    # ------------------------------ fixed body ------------------------------
    if P['body'] == 'disc':
        R = P['R_frac'] * N; dist = np.hypot(X - cx, Y - cy)
        wet = (dist + P['front_rough'] * eta < R) & interior
        Lbody = 2 * R
        rear = (cx - 0.8 * R, cy)
        src_pt = rear if P['dc_source'] == 'rear' else (cx, cy)
    elif P['body'] == 'fan':
        xa = 0.07 * N; Rf = 0.86 * N; u = X - xa; w_ = Y - cy; rr = np.hypot(u, w_); ang = np.arctan2(w_, u)
        half = np.radians(P['fan_angle'] / 2)
        rear = (xa + 5.0, cy); src_pt = rear
        wet = ((rr + P['front_rough'] * eta < Rf) & (np.abs(ang) < half)) | (np.hypot(X - rear[0], Y - rear[1]) < 3.5)
        wet &= interior; Lbody = Rf
    else: raise ValueError(P['body'])
    lab, nl = ndi.label(wet, structure=np.ones((3, 3)))
    if nl > 1: wet = lab == (1 + np.argmax(np.bincount(lab.ravel())[1:]))
    n = int(wet.sum()); idx = -np.ones((N, N), np.int64); idx[wet] = np.arange(n)
    xs = X[wet]; ys = Y[wet]
    dry_nb = np.zeros((N, N), bool)
    for d in ALLD: dry_nb |= ~nb(wet, d)
    rim = wet & dry_nb
    if P['body'] == 'disc':
        if P['dc_source'] == 'rear':
            cosn = (X - cx) / np.maximum(dist, 1e-6); sinkw = np.where(rim & (cosn > 0), cosn, 0.0)
        else: sinkw = rim.astype(float)
    else: sinkw = (rim & (rr > Rf - 4)).astype(float)
    front = sinkw > 0
    I0 = float(sinkw.sum())
    srcm = (np.hypot(X - src_pt[0], Y - src_pt[1]) < 2.0) & wet
    assert srcm.sum() > 0

    # ------------------------------ edges ------------------------------
    ei = []; ej = []; eg = []; eL = []; ec0 = []; ex1 = []; ey1 = []; ex2 = []; ey2 = []
    for k, d in enumerate(DIRS):
        a = wet & nb(wet, d)
        ei.append(idx[a]); ej.append(nb(idx, d)[a]); eg.append(G[k][a]); eL.append(np.full(int(a.sum()), np.hypot(*d)))
        ec0.append(Cinit[k][a]); ex1.append(X[a]); ey1.append(Y[a]); ex2.append(X[a] + d[0]); ey2.append(Y[a] + d[1])
    ei, ej, eg, eL, C, ex1, ey1, ex2, ey2 = [np.concatenate(v) for v in (ei, ej, eg, eL, ec0, ex1, ey1, ex2, ey2)]
    ne = len(ei)
    B = sp.csr_matrix((np.concatenate([np.ones(ne), -np.ones(ne)]), (np.concatenate([np.arange(ne)] * 2), np.concatenate([ei, ej]))), shape=(ne, n))
    BT = B.T.tocsr(); eye = sp.identity(n, format='csc') * 1e-10
    if P['init_from']:
        z = np.load(os.path.join(HERE, 'runs', P['init_from']))
        assert z['C'].shape == C.shape, 'init_from: edge layout differs (need same N / seed / body)'
        C = z['C'].astype(float)

    def solve(w, S):                               # S: (n, K) -> Q: (ne, K)
        A = (BT @ sp.diags(w) @ B).tocsc() + eye
        lu = spl.splu(A, permc_spec='MMD_AT_PLUS_A', options=dict(SymmetricMode=True), diag_pivot_thresh=0.0)
        Pm = lu.solve(S); Pm = Pm - Pm.mean(0)
        return w[:, None] * (B @ Pm)

    def zero_sum(v): return v - v.mean()

    # ------------------------------ loads ------------------------------
    f_ac = P['f_ac']; f_food = P['f_food']; f_dc = 1.0 - f_ac - f_food
    if abs(f_dc) < 1e-12: f_dc = 0.0
    src_vec = srcm[wet] / srcm.sum(); sink_vec = sinkw[wet]

    def dc_load(sw):                               # total throughput I0
        return zero_sum(I0 * src_vec - I0 * sw / sw.sum())

    def subset_load():
        fld = rng.normal(size=(N, N))
        if P['corr_len'] > 0: fld = ndi.gaussian_filter(fld, P['corr_len'])
        v = fld[wet]; act = sink_vec > 0
        thr = np.quantile(v[act], 1 - P['p_on'])
        sw = np.where(act & (v >= thr), sink_vec, 0.0)
        if sw.sum() <= 0: sw = sink_vec
        return dc_load(sw)

    lam = P['lam_frac'] * Lbody
    org = rear if P['ac_origin'] == 'rear' else (cx, cy)

    def ac_basis(theta):
        if P['ac'] == 'plane': phi = 2 * np.pi * ((xs - cx) * np.cos(theta) + (ys - cy) * np.sin(theta)) / lam
        elif P['ac'] == 'radial':
            if P['ac_origin'] == 'rear' and P['body'] == 'disc' and theta != 0.0:      # pacemaker moves on the circle of radius 0.8R (rear = angle pi)
                o_ = (cx + 0.8 * R * np.cos(np.pi + theta), cy + 0.8 * R * np.sin(np.pi + theta))
            else: o_ = org
            phi = 2 * np.pi * np.hypot(xs - o_[0], ys - o_[1]) / lam
        elif P['ac'] == 'standing': phi = np.where((xs - cx) * np.cos(theta) + (ys - cy) * np.sin(theta) > 0, 0.0, np.pi)
        else: raise ValueError(P['ac'])
        a = zero_sum(np.cos(phi)); b = zero_sum(np.sin(phi))
        th = np.arange(24) * 2 * np.pi / 24
        norm = np.mean([0.5 * np.abs(a * np.cos(t) + b * np.sin(t)).sum() for t in th])   # cycle-mean of the volume rate moved
        return a * I0 / norm, b * I0 / norm

    foods = []
    if P['n_food'] > 0:
        frng = np.random.default_rng(1000 + P['seed'] + P['food_seed'])
        deep = ndi.distance_transform_edt(wet) > 6
        cand = np.argwhere(deep); minsep = P['food_minsep'] * (Lbody / 2)
        for _ in range(20000):
            y_, x_ = cand[frng.integers(len(cand))]
            if all(np.hypot(x_ - fx, y_ - fy) >= minsep for fx, fy in foods): foods.append((float(x_), float(y_)))
            if len(foods) == P['n_food']: break
        assert len(foods) == P['n_food'], 'could not place foods'
        fvec = []
        for fx, fy in foods:
            m = (np.hypot(X - fx, Y - fy) < 2.0)[wet]; fvec.append(m / m.sum())
        food_S = np.stack([zero_sum(I0 * (fvec[i] - fvec[0])) for i in range(1, len(foods))], 1)     # basis: food i -> food 0
        pairs = list(itertools.combinations(range(len(foods)), 2))
    thK = np.arange(P['K_phase']) * 2 * np.pi / P['K_phase']

    # ------------------------------ rendering ------------------------------
    rs_ = P['render_scale']
    body_r = np.kron(wet.astype(np.float32), np.ones((rs_, rs_), np.float32))

    def raster(Cv):
        imv = Image.new('F', (N * rs_, N * rs_), 0.0); drv = ImageDraw.Draw(imv)
        sel = np.nonzero(Cv > 0.008)[0]; sel = sel[np.argsort(Cv[sel])]
        wd = 0.7 * Cv[sel] ** 0.25
        for e, w1 in zip(sel, wd):
            drv.line([((ex1[e] + .5) * rs_, (ey1[e] + .5) * rs_), ((ex2[e] + .5) * rs_, (ey2[e] + .5) * rs_)], fill=float(w1), width=max(1, int(round(w1 * rs_))))
        return (np.asarray(imv) * (body_r > 0)).astype(np.float32)

    def render(path, Cv):
        s = max(1, 1024 // N)
        base = np.zeros((N, N, 3), np.uint8); base[:] = (12, 22, 12); base[wet] = (96, 84, 26)
        if f_dc > 0: base[front] = (150, 132, 40)
        im = Image.fromarray(base).resize((N * s, N * s), Image.NEAREST); dr = ImageDraw.Draw(im)
        sel = np.nonzero(Cv > 0.008)[0]; sel = sel[np.argsort(Cv[sel])]
        for e in sel:
            wd = 0.7 * Cv[e] ** 0.25; br = min(1.0, 0.45 + 0.4 * wd)
            dr.line([((ex1[e] + .5) * s, (ey1[e] + .5) * s), ((ex2[e] + .5) * s, (ey2[e] + .5) * s)],
                    fill=(int(255 * br), int(228 * br), int(70 * br)), width=max(1, int(round(wd * s))))
        if f_dc > 0:
            dr.ellipse([(src_pt[0] + .5 - 2.5) * s, (src_pt[1] + .5 - 2.5) * s, (src_pt[0] + .5 + 2.5) * s, (src_pt[1] + .5 + 2.5) * s], outline=(80, 220, 255), width=2)
        for fx, fy in foods:
            dr.ellipse([(fx + .5 - 3) * s, (fy + .5 - 3) * s, (fx + .5 + 3) * s, (fy + .5 + 3) * s], outline=(255, 70, 70), width=3)
        im.save(path)

    # ------------------------------ main loop ------------------------------
    log = []; t0 = time.time(); m = P['avg_power']
    adapt_total = P['steps'] * P['dt'] * P['rate']              # run length in adaptation times
    if P['avg'] == 'quad':
        nsteps = P['steps']; dts = P['dt'] * P['rate']
    else:
        nsteps = int(round(adapt_total * P['adapt_periods'] * P['spp'])); dts = 1.0 / (P['adapt_periods'] * P['spp'])
        ke = 1.0 / (P['ema_periods'] * P['spp']); qbar = None
    snaps = sorted(set(int(nsteps * (i + 1) / P['nsnap']) for i in range(P['nsnap'])))
    Cprev = C.copy(); kres = None
    for step in range(nsteps + 1):
        w = eg * (C + P['r']) / eL
        if P['wobble_deg'] > 0:                    # direction swings +-wobble_deg around theta0, rot_turns swings per run
            theta = P['theta0'] + np.radians(P['wobble_deg']) * np.sin(2 * np.pi * P['rot_turns'] * step / max(nsteps, 1))
        else: theta = P['theta0'] + 2 * np.pi * P['rot_turns'] * step / max(nsteps, 1)
        if P['avg'] == 'quad':
            cols = []; nd = 0
            if f_dc > 0:
                if P['p_on'] < 1.0:
                    for _ in range(P['K_sub']): cols.append(subset_load())
                    nd = P['K_sub']
                else: cols.append(dc_load(sink_vec)); nd = 1
            thetas = [theta + np.radians(d_) for d_ in P['ac_dirs']] if P['ac_dirs'] else [theta]   # several wave directions in fast alternation
            if f_ac > 0:
                for th_ in thetas:
                    a, b = ac_basis(th_); cols += [a, b]
            if f_food > 0: cols += [food_S[:, i] for i in range(food_S.shape[1])]
            S = np.stack(cols, 1); Q = solve(w, S)
            if step == 0:
                kres = float(np.abs(BT @ Q - S).max() / np.abs(S).max())
            c = 0
            Dl = [f_dc * Q[:, i] for i in range(nd)] if nd else [0.0]; c += nd
            if f_ac > 0:
                Al = [f_ac * (np.cos(t) * Q[:, c + 2 * i_] + np.sin(t) * Q[:, c + 2 * i_ + 1]) for i_ in range(len(thetas)) for t in thK]; c += 2 * len(thetas)
            else: Al = [0.0]
            if f_food > 0:
                Fb = [np.zeros(ne)] + [Q[:, c + i] for i in range(food_S.shape[1])]       # flux for 'food i -> food 0'
                Fl = [f_food * (Fb[i] - Fb[j]) for i, j in pairs]
            else: Fl = [0.0]
            acc = np.zeros(ne); cnt = 0
            for D_ in Dl:
                for A_ in Al:
                    for F_ in Fl:
                        acc += np.abs(D_ + A_ + F_) ** m; cnt += 1
            qm = (acc / cnt) ** (1.0 / m)
        else:                                     # explicit time stepping (validation of the cycle average)
            th = 2 * np.pi * step / P['spp']
            Sdc = f_dc * dc_load(sink_vec) if f_dc > 0 else np.zeros(n)
            a, b = ac_basis(theta) if f_ac > 0 else (np.zeros(n), np.zeros(n))
            S = Sdc + f_ac * (a * np.cos(th) + b * np.sin(th))
            Qi = np.abs(solve(w, S[:, None])[:, 0])
            if qbar is None:                      # initialise the low-pass with the one-period mean at the initial C
                S0 = np.stack([Sdc + f_ac * (a * np.cos(t) + b * np.sin(t)) for t in thK], 1)
                qbar = np.abs(solve(w, S0)).mean(1)
            qbar += ke * (Qi - qbar); qm = qbar
        if step in snaps or step == nsteps:
            k_ = snaps.index(step) + 1 if step in snaps else len(snaps)
            vr = raster(C); om = own_metrics(body_r, vr, rs_)
            chg = float(np.abs(C - Cprev).sum() / max(C.sum(), 1e-30)); Cprev = C.copy()
            entry = dict(step=step, t_adapt=round(step * dts, 2), Cmax=float(C.max()), C_p50=float(np.median(C)), C_p99=float(np.percentile(C, 99)),
                         rel_change_since_prev_snap=round(chg, 4), own=om, elapsed=round(time.time() - t0, 1))
            log.append(entry)
            print(name, json.dumps(dict(step=step, t_adapt=entry['t_adapt'], Cmax=round(entry['Cmax'], 2), chg=entry['rel_change_since_prev_snap'],
                                        loops02=om['r0.2'].get('loops_big'), loops035=om['r0.35'].get('loops_big'), el=entry['elapsed'])), flush=True)
            render(os.path.join(out, f'snapshot_{k_}_t{int(round(step * dts)):04d}.png'), C)
            np.savez_compressed(os.path.join(out, f'edges_{k_}.npz'), C=C.astype(np.float32), qm=qm.astype(np.float32), ex1=ex1.astype(np.float32),
                                ey1=ey1.astype(np.float32), ex2=ex2.astype(np.float32), ey2=ey2.astype(np.float32), wet=wet,
                                foods=np.array(foods), src=np.array(src_pt))
        C = np.maximum(C + dts * (qm ** P['gamma'] - C), 0.0)
        if not np.isfinite(C).all():
            log.append(dict(step=step, error='non-finite conductance')); break

    # ------------------------------ outputs ------------------------------
    vr = raster(C)
    np.save(os.path.join(out, 'body.npy'), body_r); np.save(os.path.join(out, 'vein.npy'), vr)
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    met = dict(name=name, n_nodes=n, n_edges=ne, I0=I0, f_dc=f_dc, kirchhoff_rel_resid_step0=kres, foods=foods, log=log, runtime=round(time.time() - t0, 1))
    # edge-level hierarchy: length-weighted tube-width percentiles over vein edges (width >= 0.35 * p99.5 width)
    wd = 0.7 * C ** 0.25; wref = np.percentile(wd, 99.5); ve = wd >= 0.35 * wref
    if ve.sum() > 10:
        q = np.percentile(wd[ve], [10, 50, 90, 100])
        met['edge_width_p10_p50_p90_max'] = [round(float(x), 3) for x in q]; met['edge_width_ratio_p90_p10'] = round(float(q[2] / q[0]), 2)
        met['vein_edge_frac'] = round(float(ve.mean()), 4)
    if P['do_eval']:
        subprocess.run([sys.executable, EVAL, os.path.join(out, 'body.npy'), os.path.join(out, 'vein.npy'), '--out', os.path.join(out, 'eval.json'),
                        '--png', os.path.join(out, 'overlay.png')], stdout=subprocess.DEVNULL)
        try:
            e = json.load(open(os.path.join(out, 'eval.json')))['primary']; met['eval_primary'] = e
            keys = ('branch_points', 'loops', 'vein_area_frac', 'vein_largest_frac', 'width_ratio_p90_p10', 'strength_ratio_p90_p10', 'endpoints')
            print(name, 'EVAL', {k: e.get(k) for k in keys}, e.get('verdict'))
        except Exception as ex: print('eval failed', ex)
    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    print(name, 'runtime', met['runtime'], 'kres', kres, flush=True)
    return met


if __name__ == '__main__':
    name = sys.argv[1]; over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    run(name, over)
