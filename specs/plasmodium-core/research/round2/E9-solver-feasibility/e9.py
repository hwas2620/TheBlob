#!/usr/bin/env python3
"""E9 - solver feasibility: E1 model (grow mode, sq8 edge conductances) with GPU-style approximate pressure solvers.

usage: python3 e9.py NAME '{"param": value, ...}'
writes runs/NAME/{body.npy, vein.npy, snapshot_*.png, params.json, metrics.json, eval.json, overlay.png}

Model = e1.py (grow, sq8, pow law).  Edge channels k: 0=E (j,i+1), 1=N (j+1,i), 2=NE (j+1,i+1), 3=SE (j-1,i+1).
Solvers (all are 9-point stencil passes on padded arrays; 'exact' = scipy sparse direct, baseline only):
  exact | jac | hb | gs4 | mg | pcg | vpipe      (see REPORT.md section 2)
"""
import numpy as np, json, sys, os, time, subprocess
import scipy.sparse as sp, scipy.sparse.linalg as spl
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
from numba import njit, prange

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.join(os.path.dirname(HERE), 'common', 'eval_morph.py')

DEF = dict(
    N=256, seed=1, edge_sigma=0.5, v=1.0, dt=0.2, R_init=6.0, R_frac=0.42, front_rough=1.0, hold=0.0,
    gamma=1.5, Q0=1.0, j0=1.0, r=1e-3, D0=1.0, D0_noise=0.3, rate=1.0, Ccap=0.0, Dm=0.0,
    solver='exact', k=20, omega=0.8, beta=0.9,
    ncyc=1, nu1=2, nu2=2, nu1_0=-1, nu2_0=-1, nc=20, nmin=4, mg_omega=0.8, mg_scale=2.0,
    solve_every=1, adapt_every=1, tol=1e-8, maxit=200, vp_a=0.1, vp_b=1.0,
    coarse_p=0, interp='nearest', post=0,
    islands='drop', dtype='f8', check_every=50, render_scale=0, nsnap=3, do_eval=1, save_edges=0,
)

# ----------------------------------------------------------------------------------------------------
# stencil kernels.  All arrays padded: shape (n+2, n+2), halo cells are zero (no edges into the halo).
# ----------------------------------------------------------------------------------------------------

@njit(cache=True, parallel=True)
def k_diag(W, D):
    n0 = D.shape[0]; n1 = D.shape[1]
    for j in prange(1, n0 - 1):
        for i in range(1, n1 - 1):
            D[j, i] = (W[0, j, i] + W[0, j, i - 1] + W[1, j, i] + W[1, j - 1, i]
                       + W[2, j, i] + W[2, j - 1, i - 1] + W[3, j, i] + W[3, j + 1, i - 1])


@njit(cache=True, parallel=True)
def k_resid(p, W, S, D, R):
    n0 = D.shape[0]; n1 = D.shape[1]
    for j in prange(1, n0 - 1):
        for i in range(1, n1 - 1):
            if D[j, i] > 0:
                nbr = (W[0, j, i] * p[j, i + 1] + W[0, j, i - 1] * p[j, i - 1] + W[1, j, i] * p[j + 1, i] + W[1, j - 1, i] * p[j - 1, i]
                       + W[2, j, i] * p[j + 1, i + 1] + W[2, j - 1, i - 1] * p[j - 1, i - 1]
                       + W[3, j, i] * p[j - 1, i + 1] + W[3, j + 1, i - 1] * p[j + 1, i - 1])
                R[j, i] = S[j, i] - (D[j, i] * p[j, i] - nbr)
            else:
                R[j, i] = 0


@njit(cache=True, parallel=True)
def _jac1(p, W, S, D, om, out):
    n0 = D.shape[0]; n1 = D.shape[1]
    for j in prange(1, n0 - 1):
        for i in range(1, n1 - 1):
            if D[j, i] > 0:
                nbr = (W[0, j, i] * p[j, i + 1] + W[0, j, i - 1] * p[j, i - 1] + W[1, j, i] * p[j + 1, i] + W[1, j - 1, i] * p[j - 1, i]
                       + W[2, j, i] * p[j + 1, i + 1] + W[2, j - 1, i - 1] * p[j - 1, i - 1]
                       + W[3, j, i] * p[j - 1, i + 1] + W[3, j + 1, i - 1] * p[j + 1, i - 1])
                out[j, i] = (1 - om) * p[j, i] + om * (S[j, i] + nbr) / D[j, i]
            else:
                out[j, i] = 0


@njit(cache=True)
def k_jac_n(p, W, S, D, om, k, tmp):
    """k damped-Jacobi sweeps, result in p (tmp is scratch)."""
    for _ in range(k // 2):
        _jac1(p, W, S, D, om, tmp); _jac1(tmp, W, S, D, om, p)
    if k % 2:
        _jac1(p, W, S, D, om, tmp); p[:, :] = tmp


@njit(cache=True, parallel=True)
def _hb1(p, pm, W, S, D, om, beta, out):
    n0 = D.shape[0]; n1 = D.shape[1]
    for j in prange(1, n0 - 1):
        for i in range(1, n1 - 1):
            if D[j, i] > 0:
                nbr = (W[0, j, i] * p[j, i + 1] + W[0, j, i - 1] * p[j, i - 1] + W[1, j, i] * p[j + 1, i] + W[1, j - 1, i] * p[j - 1, i]
                       + W[2, j, i] * p[j + 1, i + 1] + W[2, j - 1, i - 1] * p[j - 1, i - 1]
                       + W[3, j, i] * p[j - 1, i + 1] + W[3, j + 1, i - 1] * p[j + 1, i - 1])
                out[j, i] = p[j, i] + om * ((S[j, i] + nbr) / D[j, i] - p[j, i]) + beta * (p[j, i] - pm[j, i])
            else:
                out[j, i] = 0


@njit(cache=True)
def k_hb_n(p, pm, W, S, D, om, beta, k, tmp):
    """heavy ball: p+ = p + om*D^-1(S - A p) + beta*(p - p-).  p, pm updated in place."""
    for _ in range(k):
        _hb1(p, pm, W, S, D, om, beta, tmp)
        pm[:, :] = p; p[:, :] = tmp


@njit(cache=True, parallel=True)
def _gs_colour(p, W, S, D, om, cj, ci):
    n0 = D.shape[0]; n1 = D.shape[1]
    for j in prange(1, n0 - 1):
        if (j & 1) != cj: continue
        for i in range(1, n1 - 1):
            if (i & 1) != ci: continue
            if D[j, i] > 0:
                nbr = (W[0, j, i] * p[j, i + 1] + W[0, j, i - 1] * p[j, i - 1] + W[1, j, i] * p[j + 1, i] + W[1, j - 1, i] * p[j - 1, i]
                       + W[2, j, i] * p[j + 1, i + 1] + W[2, j - 1, i - 1] * p[j - 1, i - 1]
                       + W[3, j, i] * p[j - 1, i + 1] + W[3, j + 1, i - 1] * p[j + 1, i - 1])
                p[j, i] = (1 - om) * p[j, i] + om * (S[j, i] + nbr) / D[j, i]


@njit(cache=True)
def k_gs4_n(p, W, S, D, om, k):
    for _ in range(k):
        for c in range(4):
            _gs_colour(p, W, S, D, om, c // 2, c % 2)


@njit(cache=True, parallel=True)
def k_coarsen(W, Wc, f):
    """coarse operator = f * P^T A P (P = piecewise constant on 2x2 aggregates; f = 1/mg_scale); keeps the sq8 4-channel structure."""
    nc0 = Wc.shape[1]; nc1 = Wc.shape[2]
    for J in prange(1, nc0 - 1):
        j = 2 * J - 1
        for I in range(1, nc1 - 1):
            i = 2 * I - 1
            Wc[0, J, I] = f * (W[0, j, i + 1] + W[0, j + 1, i + 1] + W[2, j, i + 1] + W[3, j + 1, i + 1])
            Wc[1, J, I] = f * (W[1, j + 1, i] + W[1, j + 1, i + 1] + W[2, j + 1, i] + W[3, j + 2, i])
            Wc[2, J, I] = f * W[2, j + 1, i + 1]
            Wc[3, J, I] = f * W[3, j, i + 1]


@njit(cache=True, parallel=True)
def k_restrict(R, Sc):
    nc0 = Sc.shape[0]; nc1 = Sc.shape[1]
    for J in prange(1, nc0 - 1):
        j = 2 * J - 1
        for I in range(1, nc1 - 1):
            i = 2 * I - 1
            Sc[J, I] = R[j, i] + R[j, i + 1] + R[j + 1, i] + R[j + 1, i + 1]


@njit(cache=True, parallel=True)
def k_prolong_add(p, e, D, scale):
    nc0 = e.shape[0]; nc1 = e.shape[1]
    for J in prange(1, nc0 - 1):
        j = 2 * J - 1
        for I in range(1, nc1 - 1):
            i = 2 * I - 1
            c = scale * e[J, I]
            if D[j, i] > 0: p[j, i] += c
            if D[j, i + 1] > 0: p[j, i + 1] += c
            if D[j + 1, i] > 0: p[j + 1, i] += c
            if D[j + 1, i + 1] > 0: p[j + 1, i + 1] += c


@njit(cache=True, parallel=True)
def k_prolong_bilin(p, e, D, Dc):
    """cell-centred bilinear x2 (9/16, 3/16, 3/16, 1/16), normalised over active coarse cells; overwrites p."""
    nc0 = e.shape[0]; nc1 = e.shape[1]
    for J in prange(1, nc0 - 1):
        for I in range(1, nc1 - 1):
            for a in range(2):
                for b in range(2):
                    j = 2 * J - 1 + a; i = 2 * I - 1 + b
                    if D[j, i] <= 0:
                        p[j, i] = 0; continue
                    dj = 2 * a - 1; di = 2 * b - 1
                    num = 0.0; den = 0.0
                    if Dc[J, I] > 0: num += 9 * e[J, I]; den += 9
                    if Dc[J + dj, I] > 0: num += 3 * e[J + dj, I]; den += 3
                    if Dc[J, I + di] > 0: num += 3 * e[J, I + di]; den += 3
                    if Dc[J + dj, I + di] > 0: num += e[J + dj, I + di]; den += 1
                    p[j, i] = num / den if den > 0 else 0.0


@njit(cache=True, parallel=True)
def k_vpipe(p, Q, W, S, D, a, b, k):
    """virtual-pipe style local update: edge flux is state (relaxes to Darcy with inertia), pressure integrates the net divergence."""
    n0 = D.shape[0]; n1 = D.shape[1]
    for _ in range(k):
        for j in prange(1, n0 - 1):
            for i in range(1, n1 - 1):
                Q[0, j, i] += a * (W[0, j, i] * (p[j, i] - p[j, i + 1]) - Q[0, j, i])
                Q[1, j, i] += a * (W[1, j, i] * (p[j, i] - p[j + 1, i]) - Q[1, j, i])
                Q[2, j, i] += a * (W[2, j, i] * (p[j, i] - p[j + 1, i + 1]) - Q[2, j, i])
                Q[3, j, i] += a * (W[3, j, i] * (p[j, i] - p[j - 1, i + 1]) - Q[3, j, i])
        for j in prange(1, n0 - 1):
            for i in range(1, n1 - 1):
                if D[j, i] > 0:
                    div = (Q[0, j, i] - Q[0, j, i - 1] + Q[1, j, i] - Q[1, j - 1, i]
                           + Q[2, j, i] - Q[2, j - 1, i - 1] + Q[3, j, i] - Q[3, j + 1, i - 1])
                    p[j, i] += b * (S[j, i] - div) / D[j, i]
                else:
                    p[j, i] = 0


class MG:
    def __init__(self, N, nmin, dt, scale=2.0):
        self.f = 1.0 / scale
        sizes = [N]
        while sizes[-1] > nmin and sizes[-1] % 2 == 0: sizes.append(sizes[-1] // 2)
        self.sizes = sizes; self.L = len(sizes); z = lambda n: np.zeros((n + 2, n + 2), dt)
        self.W = [np.zeros((4, n + 2, n + 2), dt) for n in sizes]
        self.D = [z(n) for n in sizes]; self.p = [z(n) for n in sizes]; self.S = [z(n) for n in sizes]
        self.R = [z(n) for n in sizes]; self.T = [z(n) for n in sizes]

    def build(self, W0, coarse=True):
        self.W[0][...] = W0; k_diag(self.W[0], self.D[0])
        for l in range(1, self.L if coarse else 1):
            k_coarsen(self.W[l - 1], self.W[l], self.f); k_diag(self.W[l], self.D[l])

    def vcycle(self, l, P):
        p, S, W, D = self.p[l], self.S[l], self.W[l], self.D[l]; om = P['mg_omega']
        if l == self.L - 1:
            k_jac_n(p, W, S, D, om, P['nc'], self.T[l]); return
        a1 = P['nu1_0'] if (l == 0 and P['nu1_0'] >= 0) else P['nu1']
        a2 = P['nu2_0'] if (l == 0 and P['nu2_0'] >= 0) else P['nu2']
        if a1 > 0: k_jac_n(p, W, S, D, om, a1, self.T[l])
        k_resid(p, W, S, D, self.R[l]); k_restrict(self.R[l], self.S[l + 1]); self.p[l + 1][...] = 0
        self.vcycle(l + 1, P)
        k_prolong_add(p, self.p[l + 1], D, 1.0)
        if a2 > 0: k_jac_n(p, W, S, D, om, a2, self.T[l])

    def cost(self, P, start=0):
        """(fine-pass equivalents, draw calls) of one V-cycle started at level `start`, + operator rebuild."""
        fe = 0.0; dc = 0
        for l in range(start, self.L - 1):
            a1 = P['nu1_0'] if (l == 0 and P['nu1_0'] >= 0) else P['nu1']
            a2 = P['nu2_0'] if (l == 0 and P['nu2_0'] >= 0) else P['nu2']
            n = a1 + a2 + 2; fe += n / 4.0 ** l; dc += n
        fe += P['nc'] / 4.0 ** (self.L - 1); dc += P['nc']
        rb_fe = sum(1 / 4.0 ** l for l in range(1, self.L)); rb_dc = self.L - 1
        return fe, dc, rb_fe, rb_dc

    def pcg(self, P, tol, maxit):
        """MG-preconditioned CG on level 0 (warm start self.p[0], rhs self.S[0]).  Returns iterations."""
        W, D = self.W[0], self.D[0]; x = self.p[0].copy(); b = self.S[0].copy()
        r = np.zeros_like(x); k_resid(x, W, b, D, r)
        bn = float(np.sqrt((b * b).sum())) + 1e-300
        if np.sqrt((r * r).sum()) <= tol * bn:
            return 0
        zero = np.zeros_like(x)
        def prec(rr):
            self.S[0][...] = rr; self.p[0][...] = 0; self.vcycle(0, P); return self.p[0].copy()
        z = prec(r); d = z.copy(); rz = float((r * z).sum()); Ad = np.zeros_like(x); it = 0
        for it in range(1, maxit + 1):
            k_resid(d, W, zero, D, Ad); Ad *= -1
            al = rz / float((d * Ad).sum()); x += al * d; r -= al * Ad
            if np.sqrt((r * r).sum()) <= tol * bn: break
            z = prec(r); rz2 = float((r * z).sum()); d = z + (rz2 / rz) * d; rz = rz2
        self.p[0][...] = x; self.S[0][...] = b
        return it


def run(name, over):
    P = dict(DEF); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    N = P['N']; dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]
    alldirs = dirs + [(-d[0], -d[1]) for d in dirs]
    FT = np.float32 if P['dtype'] == 'f4' else np.float64
    jj, ii = np.mgrid[0:N, 0:N].astype(float)
    X = ii.copy(); Y = jj.copy()
    c0 = N // 2; cx, cy = float(X[c0, c0]), float(Y[c0, c0])
    interior = (ii >= 2) & (ii < N - 2) & (jj >= 2) & (jj < N - 2)

    def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))
    def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))

    Ls = [np.hypot(d[0], d[1]) for d in dirs]
    G = [np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in dirs]                 # same RNG order as e1.py
    Cinit = [P['D0'] * (1 + P['D0_noise'] * rng.uniform(-1, 1, (N, N))) for _ in dirs]
    eta = ndi.gaussian_filter(rng.normal(size=(N, N)), 2.0); eta /= eta.std()

    Rmax = P['R_frac'] * N; v = P['v']; dt = P['dt']
    dist = np.hypot(X - cx, Y - cy)
    T = (dist - P['R_init'] + P['front_rough'] * eta) / v
    T[dist < P['R_init']] = -1
    T[~interior | (dist > Rmax + 3)] = np.inf
    steps = int((Rmax - P['R_init']) / v / dt) + int(P['hold'] / dt)
    tgrow = (Rmax - P['R_init']) / v
    def wet_at(t): return T <= min(t, tgrow)
    def Rnow(t): return P['R_init'] + v * min(t, tgrow)
    src_r = 2.0

    C = [np.zeros((N, N)) for _ in dirs]
    act_prev = [np.zeros((N, N), bool) for _ in dirs]
    p = np.zeros((N, N)); wet_prev = np.zeros((N, N), bool)
    snaps = sorted(set(int(steps * (i + 1) / P['nsnap']) for i in range(P['nsnap'])))
    log = []; t0 = time.time(); flux_err = []; kres_log = []; its_log = []
    solver = P['solver']; t_solve = 0.0; diverged = None

    # ---- solver state (padded) ----
    mg = MG(N, P['nmin'], FT, P['mg_scale']) if solver != 'exact' else None
    pm = np.zeros((N + 2, N + 2), FT)                         # heavy-ball previous iterate
    Qs = np.zeros((4, N + 2, N + 2), FT)                      # vpipe flux state
    pc_lvl = P['coarse_p']
    Wp = np.zeros((4, N + 2, N + 2), FT)

    def render(path, wet, front):
        s = max(1, 1024 // N)
        base = np.zeros((N, N, 3), np.uint8); base[:] = (12, 22, 12)
        base[wet] = (96, 84, 26); base[front] = (150, 132, 40)
        im = Image.fromarray(base).resize((N * s, N * s), Image.NEAREST)
        dr = ImageDraw.Draw(im); segs = []
        for k, d in enumerate(dirs):
            ys, xs = np.nonzero(C[k] > 0.03)
            cv = C[k][ys, xs]
            for e, a, b, c_, d_ in zip(cv, xs, ys, xs + d[0], ys + d[1]): segs.append((e, a, b, c_, d_))
        segs.sort()
        for e, a, b, c_, d_ in segs:
            wd = 0.7 * e ** 0.25; wpx = max(1, int(round(wd * s))); br = min(1.0, 0.45 + 0.4 * wd)
            col = (int(255 * br), int(228 * br), int(70 * br))
            dr.line([((a + .5) * s, (b + .5) * s), ((c_ + .5) * s, (d_ + .5) * s)], fill=col, width=wpx)
        im.save(path)

    def node_fields(Q):
        Cn = np.zeros((N, N)); qx = np.zeros((N, N)); qy = np.zeros((N, N))
        for k, d in enumerate(dirs):
            Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d)))
            fx = Q[k] * d[0]; fy = Q[k] * d[1]
            qx += 0.5 * (fx + rev(fx, d)); qy += 0.5 * (fy + rev(fy, d))
        return Cn, qx, qy

    def ring_stats(qm, t):
        R = Rnow(t); res = {}
        for f in (0.25, 0.5, 0.75, 0.9):
            rho = f * R; n = max(8, int(np.ceil(2 * np.pi * rho)))
            th = np.arange(n) * 2 * np.pi / n
            px_ = np.clip(np.rint(cx + rho * np.cos(th)).astype(int), 0, N - 1)
            py_ = np.clip(np.rint(cy + rho * np.sin(th)).astype(int), 0, N - 1)
            q = qm[py_, px_]
            if q.sum() <= 0: res[str(f)] = None; continue
            order = np.argsort(-q); cs = np.cumsum(q[order]); n80 = int(np.searchsorted(cs, 0.8 * cs[-1]) + 1)
            top = np.zeros(n, bool); top[order[:n80]] = True
            runs = max(int(np.sum(top & ~np.roll(top, 1))), 1)
            res[str(f)] = dict(n=n, n80_frac=round(n80 / n, 3), veins=runs, PR=round(float(q.sum() ** 2 / (n * (q ** 2).sum())), 3))
        return res

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

    def fluxes(W, pp): return [W[k] * (pp - nb(pp, dirs[k])) for k in range(4)]

    for step in range(steps + 1):
        t = step * dt
        wet = wet_at(t)
        if P['islands'] == 'drop':                    # keep only the component connected to the source (detached islands have net sink and no source)
            lab, nl = ndi.label(wet, structure=np.ones((3, 3)))
            if nl > 1: wet = lab == lab[c0, c0]
        dry_nb = np.zeros((N, N), bool)
        for d in alldirs: dry_nb |= ~nb(wet, d)
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

        S = np.zeros((N, N)); S[front] = -P['j0']; I = -S.sum()
        sm = (dist < src_r) & wet
        S[sm] += I / sm.sum()
        S[wet] -= S[wet].sum() / wet.sum()

        W = [act[k] * G[k] * (C[k] + P['r']) / Ls[k] for k in range(4)]
        do_solve = (step % P['solve_every'] == 0)
        ts = time.time(); Qvp = None
        if solver == 'exact':
            p = solve_exact(W, S, wet)
        else:
            for k in range(4): Wp[k, 1:-1, 1:-1] = W[k]
            mg.build(Wp, solver in ('mg', 'pcg'))             # level-0 copy + diag (+ coarse operators)
            D0 = mg.D[0]; W0 = mg.W[0]
            mg.S[0][1:-1, 1:-1] = S
            if pc_lvl == 0: mg.p[0][1:-1, 1:-1] = p
            if do_solve:
                if solver == 'jac':
                    k_jac_n(mg.p[0], W0, mg.S[0], D0, P['omega'], P['k'], mg.T[0])
                elif solver == 'hb':
                    pm[1:-1, 1:-1] = np.where(newly, p, pm[1:-1, 1:-1]) * wet      # new cells start with zero velocity
                    k_hb_n(mg.p[0], pm, W0, mg.S[0], D0, P['omega'], P['beta'], P['k'], mg.T[0])
                elif solver == 'gs4':
                    k_gs4_n(mg.p[0], W0, mg.S[0], D0, P['omega'], P['k'])
                elif solver == 'mg' and pc_lvl == 0:
                    for _ in range(P['ncyc']): mg.vcycle(0, P)
                elif solver == 'mg':                           # pressure lives on level pc_lvl only (warm start there)
                    for l in range(pc_lvl): k_restrict(mg.S[l], mg.S[l + 1])
                    for _ in range(P['ncyc']): mg.vcycle(pc_lvl, P)
                    for l in range(pc_lvl, 0, -1):
                        if P['interp'] == 'bilinear': k_prolong_bilin(mg.p[l - 1], mg.p[l], mg.D[l - 1], mg.D[l])
                        else:
                            mg.p[l - 1][...] = 0; k_prolong_add(mg.p[l - 1], mg.p[l], mg.D[l - 1], 1.0)
                    if P['post'] > 0: k_jac_n(mg.p[0], W0, mg.S[0], D0, P['mg_omega'], P['post'], mg.T[0])
                elif solver == 'pcg':
                    its_log.append(mg.pcg(P, P['tol'], P['maxit']))
                elif solver == 'vpipe':
                    Qs *= (Wp > 0)
                    k_vpipe(mg.p[0], Qs, W0, mg.S[0], D0, P['vp_a'], P['vp_b'], P['k'])
                else: raise ValueError(solver)
            if solver == 'vpipe': Qvp = [Qs[k, 1:-1, 1:-1].astype(float) for k in range(4)]
            if pc_lvl == 0 or do_solve: p = mg.p[0][1:-1, 1:-1].astype(float)
            if not np.isfinite(p).all() or np.abs(p).max() > 1e12:
                diverged = dict(step=step, what='pressure non-finite / > 1e12'); break
        t_solve += time.time() - ts
        Q = Qvp if Qvp is not None else fluxes(W, p)
        chk = solver != 'exact' and P['check_every'] and step > 0 and (step % P['check_every'] == 0 or step == steps)
        if chk:
            pe = solve_exact(W, S, wet); Qe = fluxes(W, pe)
            num = sum(((Q[k] - Qe[k]) ** 2).sum() for k in range(4)); den = sum((Qe[k] ** 2).sum() for k in range(4))
            div = sum(Q[k] - rev(Q[k], dirs[k]) for k in range(4))
            kr = float(np.abs(div - S)[wet].sum() / np.abs(S).sum())
            flux_err.append((step, round(float(np.sqrt(num / max(den, 1e-300))), 4))); kres_log.append((step, round(kr, 4)))
        # ---- adaptation ----
        if step % P['adapt_every'] == 0:
            am = 1 - (1 - P['rate'] * dt) ** P['adapt_every']
            for k in range(4):
                f = (np.abs(Q[k]) / P['Q0']) ** P['gamma']
                dC = am * (f - C[k])
                if P['Dm'] > 0:
                    lapc = np.zeros((N, N))
                    for d in alldirs: lapc += np.where(nb(act[k], d), nb(C[k], d) - C[k], 0.0)
                    dC = dC + dt * P['adapt_every'] * P['Dm'] * lapc * 0.5
                C[k] = np.maximum(C[k] + dC, 0.0) * act[k]
                if P['Ccap'] > 0: C[k] = np.minimum(C[k], P['Ccap'])
            if not all(np.isfinite(C[k]).all() for k in range(4)) or max(C[k].max() for k in range(4)) > 1e12:
                diverged = dict(step=step, what='conductance non-finite / > 1e12'); break
        if step in snaps or step == steps:
            Cn, qx, qy = node_fields(Q); qm = np.hypot(qx, qy)
            entry = dict(step=step, t=round(t, 2), area=int(wet.sum()), front=int(front.sum()), I=round(float(I), 3), Cmax=float(Cn.max()),
                         rings=ring_stats(qm, t), elapsed=round(time.time() - t0, 1))
            log.append(entry)
            print(name, json.dumps({k: entry[k] for k in ('step', 't', 'area', 'I', 'Cmax', 'elapsed')}), 'ferr', flux_err[-1:] , flush=True)
            if step in snaps:
                render(os.path.join(out, f'snapshot_{snaps.index(step) + 1}_t{int(t):04d}.png'), wet, front)
                if P['save_edges']:
                    np.savez_compressed(os.path.join(out, f'edges_{snaps.index(step) + 1}.npz'), C=np.array(C, np.float32), wet=wet,
                                        S=S.astype(np.float32), G=np.array(G, np.float32), t=t, R=Rnow(t))
    # ------------------------------ outputs ------------------------------
    Cn, qx, qy = node_fields(Q)
    body = wet.astype(np.float32); vein = (Cn * wet).astype(np.float32)
    np.save(os.path.join(out, 'vein_native.npy'), vein); np.save(os.path.join(out, 'body_native.npy'), body)
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    rs_ = P['render_scale'] or (4 if N <= 256 else 3 if N <= 384 else 2)
    imv = Image.new('F', (N * rs_, N * rs_), 0.0); drv = ImageDraw.Draw(imv); segs = []
    for k, d in enumerate(dirs):
        ys, xs = np.nonzero(C[k] > 0.008)
        for e, a, b, c_, d_ in zip(C[k][ys, xs], xs, ys, xs + d[0], ys + d[1]): segs.append((e, a, b, c_, d_))
    segs.sort()
    for e, a, b, c_, d_ in segs:
        wd = 0.7 * e ** 0.25
        drv.line([((a + .5) * rs_, (b + .5) * rs_), ((c_ + .5) * rs_, (d_ + .5) * rs_)], fill=float(wd), width=max(1, int(round(wd * rs_))))
    body_r = np.kron(body, np.ones((rs_, rs_), np.float32))
    np.save(os.path.join(out, 'body.npy'), body_r); np.save(os.path.join(out, 'vein.npy'), (np.asarray(imv) * (body_r > 0)).astype(np.float32))
    if diverged: diverged['R'] = round(Rnow(diverged['step'] * dt), 1)
    met = dict(name=name, steps=steps, R_final=round(Rnow(steps * dt), 1), log=log, flux_err=flux_err, kirchhoff_l1=kres_log, runtime=round(time.time() - t0, 1),
               t_solve=round(t_solve, 1), diverged=diverged, render_scale=rs_)
    if flux_err:
        fe = np.array([e for _, e in flux_err]); h = len(fe) // 2
        met['flux_err_mean'] = round(float(fe.mean()), 4); met['flux_err_late'] = round(float(fe[h:].mean()), 4); met['flux_err_max'] = round(float(fe.max()), 4)
    if its_log: met['pcg_its_mean'] = round(float(np.mean(its_log)), 2); met['pcg_its_max'] = int(np.max(its_log))
    if mg is not None:
        fe_, dc_, rfe, rdc = mg.cost(P, pc_lvl); m_ = P['solve_every']
        if solver in ('jac', 'hb', 'vpipe'): c = dict(fine_eq=P['k'] * (2 if solver == 'vpipe' else 1) / m_, draws=P['k'] * (2 if solver == 'vpipe' else 1) / m_)
        elif solver == 'gs4': c = dict(fine_eq=P['k'] / m_, draws=4 * P['k'] / m_)
        elif solver == 'mg':
            extra = (P['post'] + sum(1 / 4.0 ** l for l in range(pc_lvl)) * 2) if pc_lvl else 0      # restrict S + prolong p per level, post sweeps
            c = dict(fine_eq=(P['ncyc'] * fe_ + extra) / m_ + rfe, draws=(P['ncyc'] * dc_ + (P['post'] + 2 * pc_lvl if pc_lvl else 0)) / m_ + rdc, levels=mg.L)
        elif solver == 'pcg':
            it = met.get('pcg_its_mean', 0); c = dict(fine_eq=it * (fe_ + 6) + rfe, draws=it * (dc_ + 8) + rdc, levels=mg.L)
        met['gpu_cost_per_step'] = {k_: round(float(v_), 2) for k_, v_ in c.items()}
    allC = np.concatenate([C[k][act[k]] for k in range(4)]); vc = allC[allC > 1.0]
    if vc.size > 10: met['veinC_p5_p50_p95_max'] = [float(x) for x in np.percentile(vc, [5, 50, 95, 100])]
    met['n_vein_edges_C_gt1'] = int(vc.size); met['rings_final'] = log[-1]['rings'] if log else None
    if P['do_eval']:
        subprocess.run([sys.executable, EVAL, os.path.join(out, 'body.npy'), os.path.join(out, 'vein.npy'), '--out', os.path.join(out, 'eval.json'),
                        '--png', os.path.join(out, 'overlay.png')], stdout=subprocess.DEVNULL)
        try:
            e = json.load(open(os.path.join(out, 'eval.json')))['primary']; met['eval_primary'] = e
            keys = ('branch_points', 'loops', 'vein_area_frac', 'vein_largest_frac', 'width_ratio_p90_p10', 'strength_ratio_p90_p10', 'endpoints')
            print(name, 'EVAL', {k: e.get(k) for k in keys}, e.get('verdict'))
        except Exception as ex: print('eval failed', ex)
    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    print(name, 'DONE runtime', met['runtime'], 't_solve', met['t_solve'], 'ferr_late', met.get('flux_err_late'), 'cost', met.get('gpu_cost_per_step'),
          'diverged', diverged, 'rings', json.dumps({k: (v_ or {}).get('veins') for k, v_ in (met['rings_final'] or {}).items()}), flush=True)
    return met


if __name__ == '__main__':
    name = sys.argv[1]; over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    run(name, over)
