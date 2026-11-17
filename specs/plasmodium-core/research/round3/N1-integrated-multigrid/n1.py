#!/usr/bin/env python3
"""N1 - E10 integrated model (copy of round2/E10-pulsation-front/e10.py) with the E9 multigrid (copy of the kernels of
round2/E9-solver-feasibility/e9.py, adapted to the screened operator) as pressure solver.

usage: python3 n1.py NAME '{"param": value, ...}'
writes runs/NAME/{h.npy, wet.npy, age.npy, theta.npy, slime.npy, twet.npy, C_edges.npy, Qnet.npy, Qgross.npy, hamp.npy, hmean.npy,
                  snapshot_*.png, params.json, metrics.json, checks.npy, ckpt_*.npz}

MODEL: identical to e10.py (see its docstring).  Changes that do not alter the model:
  * every per-cell array op of the step runs on a window (bounding box of the wet set + margin) of the full arrays -> same numbers, faster
  * solver = 'exact' (scipy sparse direct, baseline) | 'mg' | 'jac'
  * every check_every steps the same state (W, h, h*) is ALSO solved exactly and the flux error of the approximate solve is logged
  * optional positivity-preserving outflow limiter (limit=1), reinforcement with pre- or post-limit flux
  * dtype f4: all state arrays and the MG arrays are float32

MG (screened operator A = M + L_W, M_ii = 1/(kappa dt) on wet cells, dry cells inactive):
  smoother damped Jacobi (mg_omega), restriction = sum over the 2x2 children, prolongation = piecewise constant (nearest) onto wet children,
  coarse operator rebuilt every step:  W_c = (sum of fine edges crossing the aggregates)/mg_scale,
      M_c = sum of children M            (mg_mass='exact')    or   M_c = sum/mg_scale   (mg_mass='scaled' = plain P^T A P / mg_scale)
  V(nu1,nu2), nc Jacobi sweeps on the coarsest grid, ncyc cycles per step, warm start = previous p (new cell: p of its donor; dried cell: 0)
"""
import numpy as np, json, sys, os, time
import scipy.sparse as sp, scipy.sparse.linalg as spl
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from scipy.sparse.csgraph import connected_components
from PIL import Image, ImageDraw
from numba import njit, prange
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))

DEF = dict(
    N=192, seed=1, edge_sigma=0.5, R_init=12.0, h_init=3.0, T=300.0, dt=0.1,
    kappa=8.0, h0=1.0, h_old=0.0, tau_a=30.0, beta=0.05, cap=0.5,
    y_sigma=0.05, lam=0.02, y_s=0.5, y_c=0.0, slime_tau=1e9, tau_f=2.0,
    hy0=1.1, Q0_auto=1.0, Q0_floor=1e-4, c_draw=0.0,
    h_fill=0.3, h_min=0.15, grace=2.0,
    gamma=1.5, Q0=0.05, rate=0.5, D0=0.3, D0_noise=0.3, r=0.02, Cmax=1e4,
    phase_mode='none', eps=0.0, period=4.0, d_omega=0.1, D_theta=8.8, osc_sub=4, pulse_tube=1,
    tauQ=0.0, stat_periods=5,
    food_grad=0.0,
    nsnap=4, log_every=50,
    # --- N1 ---
    solver='exact', ncyc=1, nu1=2, nu2=2, nc=20, nmin=4, mg_omega=0.8, mg_scale=1.5, mg_mass='exact',
    k=40, omega=0.9,
    limit=0, limit_reinforce='pre', dtype='f8', check_every=10, ckpt_steps=[], crop_every=8, perturb=0.0, extrap=0.0,
)
BASE = dict(T=400, kappa=20, hy0=1.05, h_fill=0.2, Q0_auto=0.2, tau_a=50, r=0.05, D0=2, rate=0.05, lam=0.06, y_sigma=0.02)
REP = dict(phase_mode='osc', eps=0.1, period=4, y_c=0.2, food_grad=1.0)      # E10 representative setting (gradient, coupled oscillators)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]
WTH = [4 / 6 if (d[0] == 0 or d[1] == 0) else 1 / 6 for d in ALL]
LS = [1.0, 1.0, np.sqrt(2), np.sqrt(2)]


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # a at the neighbour in direction d
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))      # edge array of the neighbour at -d (edge arriving here)


# ----------------------------------------------------------------------------------------------------
# stencil kernels (copied from e9.py; + screening term M).  Arrays padded (n+2, n+2), halo = 0.
# channel k: 0=E (j,i+1), 1=N (j+1,i), 2=NE (j+1,i+1), 3=SE (j-1,i+1)
# ----------------------------------------------------------------------------------------------------
@njit(cache=True, parallel=True)
def k_diag(W, M, D):
    n0 = D.shape[0]; n1 = D.shape[1]
    for j in prange(1, n0 - 1):
        for i in range(1, n1 - 1):
            if M[j, i] > 0:
                D[j, i] = M[j, i] + (W[0, j, i] + W[0, j, i - 1] + W[1, j, i] + W[1, j - 1, i]
                                     + W[2, j, i] + W[2, j - 1, i - 1] + W[3, j, i] + W[3, j + 1, i - 1])
            else:
                D[j, i] = 0


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
    for _ in range(k // 2):
        _jac1(p, W, S, D, om, tmp); _jac1(tmp, W, S, D, om, p)
    if k % 2:
        _jac1(p, W, S, D, om, tmp); p[:, :] = tmp


@njit(cache=True, parallel=True)
def k_coarsen(W, M, Wc, Mc, f, fm):
    """coarse operator: Wc = f * (P^T L P) (P = piecewise constant on 2x2 aggregates), Mc = fm * (P^T M P) = fm * sum of children."""
    nc0 = Wc.shape[1]; nc1 = Wc.shape[2]
    for J in prange(1, nc0 - 1):
        j = 2 * J - 1
        for I in range(1, nc1 - 1):
            i = 2 * I - 1
            Wc[0, J, I] = f * (W[0, j, i + 1] + W[0, j + 1, i + 1] + W[2, j, i + 1] + W[3, j + 1, i + 1])
            Wc[1, J, I] = f * (W[1, j + 1, i] + W[1, j + 1, i + 1] + W[2, j + 1, i] + W[3, j + 2, i])
            Wc[2, J, I] = f * W[2, j + 1, i + 1]
            Wc[3, J, I] = f * W[3, j, i + 1]
            Mc[J, I] = fm * (M[j, i] + M[j, i + 1] + M[j + 1, i] + M[j + 1, i + 1])


@njit(cache=True, parallel=True)
def k_restrict(R, Sc):
    nc0 = Sc.shape[0]; nc1 = Sc.shape[1]
    for J in prange(1, nc0 - 1):
        j = 2 * J - 1
        for I in range(1, nc1 - 1):
            i = 2 * I - 1
            Sc[J, I] = R[j, i] + R[j, i + 1] + R[j + 1, i] + R[j + 1, i + 1]


@njit(cache=True, parallel=True)
def k_prolong_add(p, e, D):
    nc0 = e.shape[0]; nc1 = e.shape[1]
    for J in prange(1, nc0 - 1):
        j = 2 * J - 1
        for I in range(1, nc1 - 1):
            i = 2 * I - 1
            c = e[J, I]
            if D[j, i] > 0: p[j, i] += c
            if D[j, i + 1] > 0: p[j, i + 1] += c
            if D[j + 1, i] > 0: p[j + 1, i] += c
            if D[j + 1, i + 1] > 0: p[j + 1, i + 1] += c


class MG:
    def __init__(self, N, nmin, FT, scale=1.5, mass='exact'):
        self.f = 1.0 / scale; self.fm = 1.0 if mass == 'exact' else 1.0 / scale
        sizes = [N]
        while sizes[-1] > nmin and sizes[-1] % 2 == 0: sizes.append(sizes[-1] // 2)
        self.sizes = sizes; self.L = len(sizes); z = lambda n: np.zeros((n + 2, n + 2), FT)
        self.W = [np.zeros((4, n + 2, n + 2), FT) for n in sizes]
        self.M = [z(n) for n in sizes]; self.D = [z(n) for n in sizes]; self.p = [z(n) for n in sizes]; self.S = [z(n) for n in sizes]
        self.R = [z(n) for n in sizes]; self.T = [z(n) for n in sizes]

    def build(self, coarse=True):
        """level-0 W and M must be set by the caller."""
        k_diag(self.W[0], self.M[0], self.D[0])
        for l in range(1, self.L if coarse else 1):
            k_coarsen(self.W[l - 1], self.M[l - 1], self.W[l], self.M[l], self.f, self.fm); k_diag(self.W[l], self.M[l], self.D[l])

    def vcycle(self, l, nu1, nu2, nc, om):
        p, S, W, D = self.p[l], self.S[l], self.W[l], self.D[l]
        if l == self.L - 1:
            k_jac_n(p, W, S, D, om, nc, self.T[l]); return
        if nu1 > 0: k_jac_n(p, W, S, D, om, nu1, self.T[l])
        k_resid(p, W, S, D, self.R[l]); k_restrict(self.R[l], self.S[l + 1]); self.p[l + 1][...] = 0
        self.vcycle(l + 1, nu1, nu2, nc, om)
        k_prolong_add(p, self.p[l + 1], D)
        if nu2 > 0: k_jac_n(p, W, S, D, om, nu2, self.T[l])


def gpu_cost(N, nmin=4, nu1=2, nu2=2, nc=20, ncyc=1):
    """draw calls and fine-grid fullscreen-pass equivalents per step, counted from the structure of the code above.
    per level below the coarsest: nu1 Jacobi + 1 residual + 1 restrict(+clear coarse p) + 1 prolong-add + nu2 Jacobi; coarsest: nc Jacobi.
    rebuild: 1 pass per coarse level (W_c and M_c with 2 render targets; D is recomputed inside each smoother pass from W and M)."""
    sizes = [N]
    while sizes[-1] > nmin and sizes[-1] % 2 == 0: sizes.append(sizes[-1] // 2)
    L = len(sizes); dc = 0; fe = 0.0
    for l in range(L - 1):
        n = nu1 + nu2 + 3
        dc += n; fe += (nu1 + nu2 + 1 + 1) / 4.0 ** l + 1 / 4.0 ** (l + 1)     # restrict pass is rendered at the coarse size
    dc += nc; fe += nc / 4.0 ** (L - 1)
    rb_dc = L - 1; rb_fe = sum(1 / 4.0 ** l for l in range(1, L))
    return dict(levels=L, sizes=sizes, vcycle_drawcalls=dc, vcycle_fine_equiv=round(fe, 2), rebuild_drawcalls=rb_dc, rebuild_fine_equiv=round(rb_fe, 2),
                solver_drawcalls=ncyc * dc + rb_dc, solver_fine_equiv=round(ncyc * fe + rb_fe, 2))


# ----------------------------------------------------------------------------------------------------
# native edge-graph metrics (adapted from E10 verify/indep.py; arrays instead of files)
# ----------------------------------------------------------------------------------------------------
def graph_metrics(C, h, wet, age, dr, Qnet=None, Qgross=None, cthr=4.0):
    N = h.shape[0]; jj, ii = np.mgrid[0:N, 0:N]; out = {}
    ea = []; eb = []; ec = []; ek = []
    for k, d in enumerate(DIRS):
        ys, xs = np.nonzero(C[k] > cthr)
        ea.append(ys * N + xs); eb.append((ys + d[1]) * N + (xs + d[0])); ec.append(C[k][ys, xs]); ek.append(np.full(ys.size, k))
    ea = np.concatenate(ea); eb = np.concatenate(eb); ec = np.concatenate(ec).astype(float); ek = np.concatenate(ek)
    E = ea.size; out['vein_edges'] = int(E)
    if E < 10: return out
    nodes, inv = np.unique(np.concatenate([ea, eb]), return_inverse=True); V_ = nodes.size
    a = inv[:E]; b = inv[E:]
    g = sp.coo_matrix((np.ones(E), (a, b)), shape=(V_, V_))
    nc, lab = connected_components(g, directed=False)
    deg = np.bincount(np.concatenate([a, b]), minlength=V_)
    elab = lab[a]; csize = np.bincount(elab, minlength=nc)
    out.update(vein_nodes=int(V_), vein_components=int(nc), vein_largest_frac=round(float(csize.max() / E), 3), vein_comp_ge10=int((csize >= 10).sum()),
               cycles=int(E - V_ + nc), endpoints=int((deg == 1).sum()), junctions=int((deg >= 3).sum()))
    Lk = np.array(LS)[ek]
    out['orient_len_frac_x_y_d+_d-'] = [round(float(Lk[ek == k].sum() / Lk.sum()), 3) for k in range(4)]
    ya, xa = np.divmod(ea, N)
    s = (xa + 0.5 * np.array([d[0] for d in DIRS])[ek]) * dr[0] + (ya + 0.5 * np.array([d[1] for d in DIRS])[ek]) * dr[1]
    sw = (ii * dr[0] + jj * dr[1])[wet]; smin, smax = sw.min(), sw.max()
    u = (s - smin) / max(smax - smin, 1e-9)                      # 0 = rear, 1 = front
    out['spearman_logC_pos'] = round(float(spearmanr(u, np.log(ec))[0]), 3)
    out['spearman_logC_age'] = round(float(spearmanr(np.maximum(age[ya, xa], 0), np.log(ec))[0]), 3)
    bands = np.clip((u * 6).astype(int), 0, 5)
    out['bands_C_med_rear_to_front'] = [round(float(np.median(ec[bands == q])), 1) if (bands == q).sum() >= 3 else None for q in range(6)]
    thick = ec > 100
    out['n_thick_C>100'] = int(thick.sum()); out['thick_frac_rear_half'] = round(float((thick & (u < 0.5)).sum() / max(thick.sum(), 1)), 3)
    out['C_p50_p90_p99_max'] = [round(float(x), 1) for x in np.percentile(ec, [50, 90, 99, 100])]
    out['r_ratio_p90_p10'] = round(float((np.percentile(ec, 90) / np.percentile(ec, 10)) ** 0.25), 2)
    # top 5% C edges inside the largest component?
    top = ec >= np.percentile(ec, 95)
    out['top5pct_in_largest'] = round(float((elab[top] == np.argmax(csize)).mean()), 3)
    if Qnet is not None and Qgross is not None:
        qn = np.concatenate([Qnet[k][C[k] > cthr] for k in range(4)]).astype(float); qg = np.concatenate([Qgross[k][C[k] > cthr] for k in range(4)]).astype(float)
        ok = qg > 0
        if ok.any(): out['vein_gross_over_net'] = round(float(qg[ok].sum() / max(qn[ok].sum(), 1e-12)), 2)
    # chord orientation: paths between non-degree-2 nodes, cut into pieces of <= 10 edges (>= 5 edges); length-weighted fraction of chords
    # within +-7.5 deg of a lattice direction (0/45/90/135); isotropic expectation 0.333
    try:
        nbrs = [[] for _ in range(V_)]
        for e in range(E): nbrs[a[e]].append((b[e], e)); nbrs[b[e]].append((a[e], e))
        used = np.zeros(E, bool); chx = []; chy = []; ny_, nx_ = np.divmod(nodes, N)
        for v in np.nonzero(deg != 2)[0]:
            for (w, e) in nbrs[v]:
                if used[e]: continue
                path = [v, w]; used[e] = True; cur = w; pe = e
                while deg[cur] == 2:
                    (n1, e1), (n2, e2) = nbrs[cur]
                    nxt, ne = (n1, e1) if e1 != pe else (n2, e2)
                    if used[ne]: break
                    used[ne] = True; path.append(nxt); cur = nxt; pe = ne
                for s0 in range(0, len(path) - 1, 10):
                    seg = path[s0:s0 + 11]
                    if len(seg) >= 6: chx.append(nx_[seg[-1]] - nx_[seg[0]]); chy.append(ny_[seg[-1]] - ny_[seg[0]])
        if len(chx) >= 5:
            chx = np.array(chx, float); chy = np.array(chy, float); ln = np.hypot(chx, chy); ang = np.degrees(np.arctan2(chy, chx)) % 45.0; dev = np.minimum(ang, 45 - ang)
            out['chords'] = int(len(chx)); out['chord_lattice_frac_7p5'] = round(float(ln[dev < 7.5].sum() / max(ln.sum(), 1e-9)), 3)
    except Exception as ex: out['chord_err'] = repr(ex)
    # Strahler order of the largest component treated as an undirected graph after iteratively pruning cycles is ambiguous;
    # use the leaf-peeling (Horton-Strahler on the spanning forest by descending C) instead: maximum order over all components
    try:
        order = np.argsort(-ec); parent = np.arange(V_)
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        adj = [[] for _ in range(V_)]
        for e in order:                                           # maximum-C spanning forest (Kruskal)
            ra, rb = find(a[e]), find(b[e])
            if ra != rb:
                parent[ra] = rb; adj[a[e]].append(b[e]); adj[b[e]].append(a[e])
        smax_ = 0; seen = np.zeros(V_, bool)
        for comp in np.argsort(-csize)[:3]:                        # three largest components
            members = np.nonzero(lab == comp)[0]
            # root = node with the largest adjacent C in the component
            em = np.nonzero(elab == comp)[0]; root = a[em[np.argmax(ec[em])]]
            stack = [(root, -1, 0)]; so = {}
            while stack:
                x, par, st = stack.pop()
                if st == 0:
                    stack.append((x, par, 1))
                    for y in adj[x]:
                        if y != par: stack.append((y, x, 0))
                else:
                    ch = [so[y] for y in adj[x] if y != par]
                    if not ch: so[x] = 1
                    else:
                        mx = max(ch); so[x] = mx + 1 if ch.count(mx) >= 2 else mx
            smax_ = max(smax_, so[root])
        out['strahler_max_spanning'] = int(smax_)
    except Exception as ex: out['strahler_err'] = str(ex)
    return out


def run(name, over):
    P = dict(DEF); P.update(BASE); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    N = P['N']; dt = P['dt']; kap = P['kappa']; FT = np.float32 if P['dtype'] == 'f4' else np.float64
    jj, ii = np.mgrid[0:N, 0:N].astype(float)
    X = ii; Y = jj; c0 = N / 2 - 0.5
    interior = (ii >= 3) & (ii < N - 3) & (jj >= 3) & (jj < N - 3)
    edge_zone = ~ndi.binary_erosion(interior, iterations=2)
    CDRAW = P['c_draw'] if P['c_draw'] > 0 else max(1.0, 2.0 * P['D0'])
    G = np.array([np.exp(P['edge_sigma'] * rng.normal(size=(N, N))) for _ in DIRS]).astype(FT)         # same RNG order as e10.py
    Cinit = np.array([P['D0'] * (1 + P['D0_noise'] * rng.uniform(-1, 1, (N, N))) for _ in DIRS]).astype(FT)
    eta = rng.normal(size=(N, N)).astype(FT)
    food = np.zeros((N, N), FT)
    if P['food_grad'] > 0: food = (food + P['food_grad'] * (X - c0) / N).astype(FT)
    prng = np.random.default_rng(P['seed'] + 12345)

    dist = np.hypot(X - c0, Y - c0)
    F = SimpleNamespace()
    F.wet = dist < P['R_init']
    F.h = np.where(F.wet, P['h_init'], 0.0).astype(FT)
    F.age = np.zeros((N, N), FT); F.slime = np.zeros((N, N), FT); F.twet = np.full((N, N), -1.0, FT); F.twet[F.wet] = 0.0
    F.C = np.zeros((4, N, N), FT); F.actp = np.zeros((4, N, N), bool); F.p = np.zeros((N, N), FT); F.pm = np.zeros((N, N), FT); F.theta = np.zeros((N, N), FT)
    F.Q = np.zeros((4, N, N), FT); F.Qf = np.zeros((4, N, N), FT)
    F.hmax_w = np.full((N, N), -np.inf, FT); F.hmin_w = np.full((N, N), np.inf, FT); F.hsum_w = np.zeros((N, N)); F.wet_w = np.ones((N, N), bool)
    F.sQ = np.zeros((4, N, N)); F.sA = np.zeros((4, N, N))
    hamp_last = np.zeros((N, N)); hmean_last = np.zeros((N, N)); hamp_t = -1.0
    Qnet_last = np.zeros((4, N, N)); Qgross_last = np.zeros((4, N, N)); qwin_t = -1.0
    V0 = float(F.h.sum(dtype=np.float64))
    steps = int(round(P['T'] / dt))
    snaps = sorted(set(int(steps * (i + 1) / P['nsnap']) for i in range(P['nsnap'])))
    log = []; t0 = time.time(); snapi = 0; hmin_seen = 0.0; stop = ''
    mode = P['phase_mode']; eps = P['eps'] if mode != 'none' else 0.0
    wv = 2 * np.pi / P['period']; nper = max(1, int(round(P['period'] / dt))); nwin = nper * P['stat_periods']
    cnt_w = 0; cnt_q = 0
    lock_sum = 0j; lock_n = 0
    mass_err_max = 0.0; neg_steps = 0; neg_vol_max = 0.0; neg_cells_max = 0
    checks = []; q0_series = []; lim_log = []; t_solve = 0.0; diverged = None; ndry_tot = 0; nwet_tot = 0
    solver = P['solver']; sig = 1.0 / (kap * dt)
    mg = MG(N, P['nmin'], FT, P['mg_scale'], P['mg_mass']) if solver != 'exact' else None
    ckpt = set(int(s) for s in P['ckpt_steps'])

    def node_C(C, shp):
        Cn = np.zeros(shp, FT)
        for k, d in enumerate(DIRS): Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d)))
        return Cn

    def render(path, t):
        s = max(1, 1024 // N)
        base = np.zeros((N, N, 3), np.float32); base[:] = (10, 18, 10)
        sl_ = np.clip(F.slime, 0, 1)[..., None]
        base = base * (1 - sl_) + np.array([52, 40, 30], np.float32) * sl_
        b = np.clip(F.h / (1.3 * P['h0']), 0, 1)[..., None]
        body = np.array([40, 34, 8], np.float32) * (1 - b) + np.array([215, 185, 40], np.float32) * b
        base = np.where(F.wet[..., None], body, base)
        im = Image.fromarray(base.astype(np.uint8)).resize((N * s, N * s), Image.NEAREST)
        dr = ImageDraw.Draw(im); segs = []
        for k, d in enumerate(DIRS):
            ys, xs = np.nonzero(F.C[k] > CDRAW)
            for e, a, b_ in zip(F.C[k][ys, xs], xs, ys): segs.append((float(e), a, b_, a + d[0], b_ + d[1]))
        segs.sort()
        for e, a, b_, c_, d_ in segs:
            wd = 0.45 * e ** 0.25
            br = min(1.0, 0.55 + 0.25 * wd)
            dr.line([((a + .5) * s, (b_ + .5) * s), ((c_ + .5) * s, (d_ + .5) * s)],
                    fill=(int(255 * br), int(120 * br), int(40 * br)), width=max(1, int(round(wd * s * (1 if N <= 256 else 0.7)))))
        dr.text((6, 4), f'{name} t={t:.0f}', fill=(255, 255, 255))
        im.save(path)

    def solve_exact(W, rhs, wet):
        shp = wet.shape
        idx = -np.ones(shp, np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
        rows = []; cols = []; vals = []
        for k, d in enumerate(DIRS):
            m = W[k] > 0
            a = idx[m]; b = nb(idx, d)[m]; w = W[k][m].astype(np.float64)
            rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
        ar = np.arange(n); rows.append(ar); cols.append(ar); vals.append(np.full(n, sig))
        A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
        sol = spl.spsolve(A, rhs[wet].astype(np.float64), permc_spec='MMD_AT_PLUS_A')
        pp = np.zeros(shp); pp[wet] = sol
        return pp

    def centroid():
        m = F.h.sum(dtype=np.float64)
        return (float((F.h * X).sum() / m), float((F.h * Y).sum() / m)) if m > 0 else (c0, c0)

    cen0 = centroid(); path_len = 0.0; cen_prev = cen0; traj = []
    y0 = y1 = x0 = x1 = 0; L = None; Gl = Cil = etal = foodl = intl = ezl = None; shp = None
    mrg = P['crop_every'] + 3

    for step in range(steps + 1):
        t = step * dt
        # ---- window (bounding box of the wet set + margin) ----
        if step % P['crop_every'] == 0:
            if L is not None:
                tmp = L.wet_w.copy(); F.wet_w[:] = False; F.wet_w[y0:y1, x0:x1] = tmp
            ry = np.nonzero(F.wet.any(1))[0]; rx = np.nonzero(F.wet.any(0))[0]
            y0 = max(0, ry[0] - mrg); y1 = min(N, ry[-1] + mrg + 1); x0 = max(0, rx[0] - mrg); x1 = min(N, rx[-1] + mrg + 1)
            L = SimpleNamespace(**{k: (v[:, y0:y1, x0:x1] if v.ndim == 3 else v[y0:y1, x0:x1]) for k, v in F.__dict__.items()})
            Gl = G[:, y0:y1, x0:x1]; Cil = Cinit[:, y0:y1, x0:x1]; etal = eta[y0:y1, x0:x1]; foodl = food[y0:y1, x0:x1]
            intl = interior[y0:y1, x0:x1]; ezl = edge_zone[y0:y1, x0:x1]; shp = L.h.shape
            if mg is not None:
                mg.W[0][...] = 0; mg.M[0][...] = 0; mg.S[0][...] = 0; mg.p[0][...] = 0
        wet = L.wet; h = L.h; age = L.age; theta = L.theta; C = L.C; Q = L.Q
        ny, nx = shp
        # ---- edges ----
        for k, d in enumerate(DIRS):
            a = wet & nb(wet, d); new = a & ~L.actp[k]
            C[k][...] = np.where(new, Cil[k], C[k]) * a
            if P['tauQ'] > 0: L.Qf[k][...] = L.Qf[k] * (a & ~new)
            L.actp[k][...] = a
        act = [L.actp[k].copy() for k in range(4)]
        # ---- phase field ----
        if mode == 'osc':
            om = wv * (1 + P['d_omega'] * (1 - np.exp(-age / P['tau_a'])))
            ns = max(1, int(P['osc_sub'])); dts = dt / ns
            for _ in range(ns):
                coup = np.zeros(shp, FT)
                if P['D_theta'] > 0:
                    for d, wt in zip(ALL, WTH): coup += wt * nb(wet, d) * np.sin(nb(theta, d) - theta)
                theta[...] = np.where(wet, theta + dts * (om + P['D_theta'] * coup), 0.0)
        else:
            theta[...] = np.where(wet, wv * t, 0.0)
        # ---- rest thickness ----
        Cn = node_C(C, shp)
        hstar = P['h_old'] + (P['h0'] - P['h_old']) * np.exp(-age / P['tau_a'])
        if P['tau_f'] > 0: hstar = hstar * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f']))
        tube = np.minimum(P['beta'] * np.sqrt(Cn), P['cap'])
        if eps > 0:
            mod = 1 + eps * np.cos(theta)
            hstar = hstar * mod
            if P['pulse_tube']: tube = tube * mod
        hstar = hstar + tube
        # ---- pressure ----
        W = [act[k] * Gl[k] * (C[k] + P['r']) / LS[k] for k in range(4)]
        rhs = np.where(wet, (h - hstar) / dt, 0.0)
        ts = time.time()
        if step in ckpt:
            np.savez_compressed(os.path.join(out, f'ckpt_{step}.npz'), W=np.array(W, np.float64), wet=wet, rhs=rhs.astype(np.float64), C=np.array(C, np.float64),
                                p_prev=np.where(wet, L.p, 0.0).astype(np.float64), h=h.astype(np.float64), hstar=np.asarray(hstar, np.float64), step=step, age=age.astype(np.float64), theta=theta.astype(np.float64), tube0=np.minimum(P['beta'] * np.sqrt(Cn), P['cap']).astype(np.float64),
                                win=np.array([y0, y1, x0, x1]), N=N, sig=sig)
        if solver == 'exact':
            pnew = solve_exact(W, rhs, wet)
            if P['perturb'] > 0: pnew = pnew * (1 + P['perturb'] * prng.normal(size=shp))
        else:
            sy_, sx_ = slice(1 + y0, 1 + y1), slice(1 + x0, 1 + x1)
            for k in range(4): mg.W[0][k, sy_, sx_] = W[k]
            mg.M[0][sy_, sx_] = np.where(wet, sig, 0.0)
            mg.S[0][sy_, sx_] = rhs
            mg.p[0][sy_, sx_] = np.where(wet, L.p + P['extrap'] * (L.p - L.pm), 0.0)     # warm start (optionally extrapolated in time)
            if solver == 'mg':
                mg.build(True)
                for _ in range(P['ncyc']): mg.vcycle(0, P['nu1'], P['nu2'], P['nc'], P['mg_omega'])
            elif solver == 'jac':
                mg.build(False)
                k_jac_n(mg.p[0], mg.W[0], mg.S[0], mg.D[0], P['omega'], P['k'], mg.T[0])
            else: raise ValueError(solver)
            pnew = mg.p[0][sy_, sx_].copy()
            if not np.isfinite(pnew).all() or np.abs(pnew).max() > 1e12:
                diverged = dict(step=step, what='pressure non-finite / > 1e12'); stop = 'diverged'; break
        t_solve += time.time() - ts
        L.pm[...] = L.p; L.p[...] = pnew; p = L.p
        div = np.zeros(shp, FT)
        for k, d in enumerate(DIRS):
            Q[k][...] = W[k] * (p - nb(p, d)); div += Q[k] - rev(Q[k], d)
        # ---- check against the exact solve from the same state ----
        do_chk = P['check_every'] > 0 and step > 0 and step % P['check_every'] == 0
        chk = None
        if do_chk:
            ncomp = ndi.label(wet, structure=np.ones((3, 3)))[1]
            Ce = np.array(C); am = np.array(act); thick = am & (Ce > 100); mid = am & (Ce > CDRAW) & (Ce <= 100); sheet = am & (Ce <= CDRAW)
            chk = dict(step=step, ncomp=ncomp, nwet=int(wet.sum()), Cmax=float(Ce.max()), n_thick=int(thick.sum()), Wmax=float(max(w.max() for w in W)))
            if solver != 'exact':
                pe = solve_exact(W, rhs, wet); Qe = np.array([W[k] * (pe - nb(pe, d)) for k, d in enumerate(DIRS)]); Qa = np.array(Q, np.float64)
                er = lambda m: float(np.sqrt(((Qa - Qe)[m] ** 2).sum() / max((Qe[m] ** 2).sum(), 1e-300))) if m.any() else float('nan')
                res = rhs - sig * np.where(wet, p, 0.0) - div
                chk.update(err_all=er(am), err_thick=er(thick), err_mid=er(mid), err_sheet=er(sheet),
                           res_rel=float(np.sqrt((res[wet].astype(np.float64) ** 2).sum() / max((rhs[wet].astype(np.float64) ** 2).sum(), 1e-300))),
                           gross_ratio_thick=float(np.abs(Qa[thick]).sum() / max(np.abs(Qe[thick]).sum(), 1e-300)) if thick.any() else float('nan'),
                           perr=float(np.sqrt(((p - pe)[wet] ** 2).sum() / max((pe[wet] ** 2).sum(), 1e-300))))
        # ---- positivity-preserving outflow limiter ----
        Fre = [np.abs(Q[k]) for k in range(4)]                     # reinforcement input (pre-limit)
        if P['limit']:
            outf = np.zeros(shp, FT)
            for k, d in enumerate(DIRS): outf += np.maximum(Q[k], 0) + rev(np.maximum(-Q[k], 0), d)
            hp = np.maximum(h, 0.0)
            s_ = np.where(dt * outf > hp, hp / np.maximum(dt * outf, 1e-30), 1.0).astype(FT)
            nlim = int((s_ < 1).sum())
            if nlim:
                div = np.zeros(shp, FT); cut = 0.0; tot = 0.0
                for k, d in enumerate(DIRS):
                    ql = np.where(Q[k] > 0, Q[k] * s_, Q[k] * nb(s_, d))
                    cut += float(np.abs(Q[k] - ql).sum()); tot += float(np.abs(Q[k]).sum())
                    Q[k][...] = ql; div += Q[k] - rev(Q[k], d)
                lim_log.append((step, nlim, cut / max(tot, 1e-300)))
                if P['limit_reinforce'] == 'post': Fre = [np.abs(Q[k]) for k in range(4)]
        h[...] = h - dt * div
        hm_ = float(h[wet].min()) if wet.any() else 0.0
        hmin_seen = min(hmin_seen, hm_)
        if hm_ < 0:
            neg_steps += 1; ng = wet & (h < 0); neg_cells_max = max(neg_cells_max, int(ng.sum())); neg_vol_max = max(neg_vol_max, float(-h[ng].sum()))
        if chk is not None:
            dlt = (h - hstar) - p / kap                             # p = kappa (h_new - h*) holds exactly for the exact solve without limiter
            vc = wet & (Cn > CDRAW); ad = np.abs(dlt)
            chk.update(hmin=hm_, ph_vein_gt0p3=float((ad[vc] > 0.3 * P['h0']).mean()) if vc.any() else 0.0, ph_vein_gt0p05=float((ad[vc] > 0.05 * P['h0']).mean()) if vc.any() else 0.0,
                       ph_vein_gt0p01=float((ad[vc] > 0.01 * P['h0']).mean()) if vc.any() else 0.0,
                       ph_wet_gt0p05=float((ad[wet] > 0.05 * P['h0']).mean()), ph_rms=float(np.sqrt((dlt[wet].astype(np.float64) ** 2).mean())))
            checks.append(chk)
        # ---- reinforcement ----
        if P['tauQ'] > 0:
            a_ = min(1.0, dt / P['tauQ'])
            for k in range(4): L.Qf[k][...] = (L.Qf[k] + a_ * (Fre[k] - L.Qf[k])) * act[k]
            Fr = [L.Qf[k] for k in range(4)]
        else:
            Fr = Fre
        Q0 = P['Q0']
        if P['Q0_auto'] > 0:
            nact = sum(int(a.sum()) for a in act)
            if nact > 0:
                Q0 = max(P['Q0_floor'], P['Q0_auto'] * (sum(float((Fr[k][act[k]].astype(np.float64) ** P['gamma']).sum()) for k in range(4)) / nact) ** (1 / P['gamma']))
        if step % 10 == 0: q0_series.append(Q0)
        for k in range(4):
            f = (Fr[k] / Q0) ** P['gamma']
            C[k][...] = np.clip(C[k] + dt * P['rate'] * (f - C[k]), 0.0, P['Cmax']) * act[k]
        age[...] = np.where(wet, age + dt, 0.0)
        # ---- rolling statistics ----
        L.hmax_w[...] = np.maximum(L.hmax_w, h); L.hmin_w[...] = np.minimum(L.hmin_w, h); L.hsum_w[...] += h; L.wet_w[...] &= wet; cnt_w += 1
        for k in range(4): L.sQ[k][...] += Q[k]; L.sA[k][...] += np.abs(Q[k])
        cnt_q += 1
        if cnt_w >= nper:
            tmp = L.wet_w.copy(); F.wet_w[:] = False; F.wet_w[y0:y1, x0:x1] = tmp
            hamp_last = np.where(F.wet_w, 0.5 * (F.hmax_w - F.hmin_w), 0.0); hmean_last = np.where(F.wet_w, F.hsum_w / cnt_w, 0.0); hamp_t = t
            F.hmax_w[:] = -np.inf; F.hmin_w[:] = np.inf; F.hsum_w[:] = 0; F.wet_w[:] = True; cnt_w = 0
        if cnt_q >= nwin:
            Qnet_last = np.abs(F.sQ) / cnt_q; Qgross_last = F.sA / cnt_q; qwin_t = t
            F.sQ[:] = 0; F.sA[:] = 0; cnt_q = 0
        # ---- drying ----
        Dm = wet & (h < P['h_min']) & (age > P['grace'])
        if Dm.any():
            stay = wet & ~Dm; ns_ = np.zeros(shp)
            for d in ALL: ns_ += nb(stay, d)
            Dm &= ns_ > 0
            stay = wet & ~Dm; ns_[:] = 0
            for d in ALL: ns_ += nb(stay, d)
            give = np.where(Dm, h / np.maximum(ns_, 1), 0.0)
            for d in ALL: h[...] += np.where(stay, nb(give, d), 0.0)
            h[Dm] = 0.0; wet[...] = stay; L.slime[Dm] = 1.0; age[Dm] = 0.0; L.p[Dm] = 0.0; L.pm[Dm] = 0.0; ndry_tot += int(Dm.sum())
        # ---- wetting (thickness yield) ----
        pw = np.where(wet, h, -np.inf)
        pmax = np.full(shp, -np.inf); arg = np.zeros(shp, np.int8); nw = np.zeros(shp)
        for q, d in enumerate(ALL):
            v = nb(pw, d); better = v > pmax
            pmax = np.where(better, v, pmax); arg = np.where(better, q, arg); nw += nb(wet, d)
        yld = P['hy0'] * (1 + P['y_sigma'] * etal) + P['lam'] * (3 - nw) + P['y_s'] * L.slime - P['y_c'] * foodl
        cand = ~wet & intl & (pmax > yld)
        if cand.any():
            ys, xs = np.nonzero(cand); a = arg[ys, xs]
            dx = np.array([d[0] for d in ALL])[a]; dy = np.array([d[1] for d in ALL])[a]
            sy = ys + dy; sx = xs + dx; flat = sy * nx + sx
            cnt = np.bincount(flat, minlength=ny * nx)[flat]
            amt = np.minimum(P['h_fill'], 0.5 * np.maximum(h[sy, sx], 0.0) / cnt)
            np.subtract.at(h, (sy, sx), amt)
            h[ys, xs] = amt; wet[ys, xs] = True; age[ys, xs] = 0.0; L.twet[ys, xs] = t
            L.p[ys, xs] = L.p[sy, sx]; L.pm[ys, xs] = L.pm[sy, sx]; theta[ys, xs] = theta[sy, sx]; nwet_tot += int(ys.size)
            if step > steps // 2:
                psi = np.mod(theta[sy, sx], 2 * np.pi); lock_sum += np.exp(1j * psi).sum(); lock_n += psi.size
        Vnow = float(h.sum(dtype=np.float64)) if (step % 5 == 0) else None
        if Vnow is not None: mass_err_max = max(mass_err_max, abs((Vnow - V0) / V0))
        # ---- log / snapshots ----
        if step % P['log_every'] == 0 or step == steps:
            cen = centroid(); path_len += np.hypot(cen[0] - cen_prev[0], cen[1] - cen_prev[1]); cen_prev = cen
            traj.append((round(t, 2), round(cen[0], 2), round(cen[1], 2), int(F.wet.sum())))
            log.append(dict(t=round(t, 2), area=int(F.wet.sum()), V_err=float((F.h.sum(dtype=np.float64) - V0) / V0), cx=cen[0], cy=cen[1], Cmax=float(F.C.max()), Q0=float(Q0),
                            hmin=hmin_seen, elapsed=round(time.time() - t0, 1)))
            if step % (P['log_every'] * 10) == 0 or step == steps:
                e = log[-1]; print(name, json.dumps({k: (round(v, 5) if isinstance(v, float) else v) for k, v in e.items()}),
                                   ('chk ' + json.dumps({k: round(v, 3) for k, v in checks[-1].items() if k in ('err_all', 'err_thick', 'res_rel')})) if checks else '', flush=True)
        if step in snaps:
            snapi += 1; render(os.path.join(out, f'snapshot_{snapi}_t{int(t):04d}.png'), t)
        if not wet.any(): stop = 'all dry'; break
        if (wet & ezl).any(): stop = f'reached boundary at t={t:.1f}'; break
        if diverged is None and float(C.max()) >= P['Cmax'] * 0.999: diverged = dict(step=step, what='C reached Cmax')
    if stop:
        snapi += 1; render(os.path.join(out, f'snapshot_{snapi}_t{int(t):04d}_stop.png'), t); print(name, 'STOP', stop)
    nstep = step + 1
    wet = F.wet; h = F.h; age = F.age; C = F.C

    # ------------------------------ outputs ------------------------------
    sv = lambda n_, a_: np.save(os.path.join(out, n_), a_)
    sv('h.npy', h.astype(np.float32)); sv('wet.npy', wet); sv('age.npy', np.where(wet, age, -1).astype(np.float32)); sv('theta.npy', np.where(wet, F.theta, np.nan).astype(np.float32))
    sv('slime.npy', F.slime.astype(np.float32)); sv('twet.npy', F.twet.astype(np.float32)); sv('C_edges.npy', C.astype(np.float32))
    sv('Qnet.npy', Qnet_last.astype(np.float32)); sv('Qgross.npy', Qgross_last.astype(np.float32)); sv('hamp.npy', hamp_last.astype(np.float32)); sv('hmean.npy', hmean_last.astype(np.float32))
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    met = dict(name=name, stop=stop, t_end=round(t, 2), nstep=nstep, runtime=round(time.time() - t0, 1), t_solve=round(t_solve, 1), V0=V0,
               mass_err_max=float(max(mass_err_max, max(abs(e['V_err']) for e in log))), h_min_seen=hmin_seen, neg_steps=neg_steps, neg_cells_max=neg_cells_max, neg_vol_max=neg_vol_max,
               diverged=diverged, dry_events=ndry_tot, wet_events=nwet_tot, Cmax_end=float(C.max()), Cmax_run=float(max(e['Cmax'] for e in log)), Q0_med=float(np.median(q0_series)), Q0_series_every10=[float(f'{q:.5g}') for q in q0_series[::10]])
    cen = centroid(); met['disp'] = round(float(np.hypot(cen[0] - cen0[0], cen[1] - cen0[1])), 2); met['path_len'] = round(float(path_len), 2); met['area_end'] = int(wet.sum())
    i0 = int(len(traj) * 0.6); ddx = traj[-1][1] - traj[i0][1]; ddy = traj[-1][2] - traj[i0][2]
    met['late_speed'] = round(float(np.hypot(ddx, ddy) / max(traj[-1][0] - traj[i0][0], 1e-9)), 4)
    if np.hypot(ddx, ddy) < 1.0: ddx, ddy = cen[0] - cen0[0], cen[1] - cen0[1]
    nrm = max(np.hypot(ddx, ddy), 1e-9); dr = [ddx / nrm, ddy / nrm]; met['dir'] = [round(dr[0], 3), round(dr[1], 3)]
    met['disp_dir_deg'] = round(float(np.degrees(np.arctan2(cen[1] - cen0[1], cen[0] - cen0[0]))), 1)
    wm = hmean_last > 0
    if wm.any():
        ha = hamp_last[wm]; hm = hmean_last[wm]; shm = hm > 0.5 * P['h0']
        met['hamp_sheet_mean'] = round(float(ha[shm].mean()), 4) if shm.any() else None; met['hamp_t'] = round(hamp_t, 2)
    if lock_n > 0: met['lock_R'] = round(float(abs(lock_sum) / lock_n), 3)
    if wet.sum() > 30:
        lab, nl = ndi.label(wet, structure=np.ones((3, 3))); sizes = np.bincount(lab.ravel())[1:]
        met['body_components'] = int(nl); big = lab == (np.argmax(sizes) + 1); met['vol_frac_largest'] = round(float(h[big].sum(dtype=np.float64) / h.sum(dtype=np.float64)), 3)
        sm = wet & (h > 0.5 * P['h0']); met['sheet_area_frac'] = round(float(sm.sum() / wet.sum()), 3)
        s = (X[big] - cen[0]) * dr[0] + (Y[big] - cen[1]) * dr[1]; met['len_along'] = round(float(s.max() - s.min() + 1), 1)
        if mode != 'none':
            aw = age[wet]; th = F.theta[wet]; o = np.argsort(aw); n10 = max(3, aw.size // 10)
            met['phase_lead_old_minus_young_turns'] = round(float((th[o[-n10:]].mean() - th[o[:n10]].mean()) / (2 * np.pi)), 3)
        try: met['graph'] = graph_metrics(C.astype(np.float64), h.astype(np.float64), wet, age.astype(np.float64), dr, Qnet_last if qwin_t > 0 else None, Qgross_last if qwin_t > 0 else None, CDRAW)
        except Exception as ex: met['graph_err'] = repr(ex)
    if checks:
        keys = sorted(set().union(*[c.keys() for c in checks]))
        arr = np.array([[c.get(k, np.nan) for k in keys] for c in checks], float); np.save(os.path.join(out, 'checks.npy'), arr); met['check_keys'] = keys
        def st(k):
            v = arr[:, keys.index(k)]; v = v[np.isfinite(v)]
            return None if v.size == 0 else dict(n=int(v.size), med=round(float(np.median(v)), 4), p90=round(float(np.percentile(v, 90)), 4), max=round(float(v.max()), 4), mean=round(float(v.mean()), 4))
        met['checks'] = {k: st(k) for k in keys if k not in ('step',)}
        if 'err_all' in keys:
            v = arr[:, keys.index('err_all')]; i = int(np.nanargmax(v)); met['err_all_argmax'] = {k: float(arr[i, keys.index(k)]) for k in keys}
            hlf = arr[:, keys.index('step')] > nstep // 2
            met['err_all_med_late'] = round(float(np.nanmedian(v[hlf])), 4) if hlf.any() else None
            vt = arr[:, keys.index('err_thick')]; met['err_thick_med_late'] = round(float(np.nanmedian(vt[hlf])), 4) if hlf.any() and np.isfinite(vt[hlf]).any() else None
    if lim_log:
        la = np.array(lim_log, float); met['limiter'] = dict(steps_active=int(la.shape[0]), frac_steps=round(float(la.shape[0] / nstep), 4), cells_max=int(la[:, 1].max()), cells_mean=round(float(la[:, 1].mean()), 2),
                                                             cut_frac_mean=float(la[:, 2].mean()), cut_frac_max=float(la[:, 2].max()))
    if solver != 'exact': met['gpu_cost'] = gpu_cost(N, P['nmin'], P['nu1'], P['nu2'], P['nc'], P['ncyc'])
    met['traj'] = traj; met['log'] = log
    json.dump(met, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    g = met.get('graph', {})
    print(name, 'MET', json.dumps({k: met.get(k) for k in ('stop', 't_end', 'disp', 'disp_dir_deg', 'area_end', 'mass_err_max', 'h_min_seen', 'neg_steps', 'Cmax_end', 'Cmax_run', 'hamp_sheet_mean', 'lock_R', 'body_components', 'dry_events', 'wet_events', 'runtime', 't_solve')}))
    print(name, 'GRAPH', json.dumps({k: g.get(k) for k in ('vein_edges', 'vein_components', 'vein_largest_frac', 'cycles', 'endpoints', 'junctions', 'spearman_logC_pos', 'vein_gross_over_net', 'strahler_max_spanning', 'chord_lattice_frac_7p5', 'orient_len_frac_x_y_d+_d-')}))
    if 'checks' in met and 'err_all' in met['checks']: print(name, 'CHK', json.dumps({k: met['checks'][k] for k in ('err_all', 'err_thick', 'res_rel', 'ph_vein_gt0p3', 'ph_vein_gt0p05') if k in met['checks']}))
    return met


if __name__ == '__main__':
    name = sys.argv[1]; over = dict(REP); over.update(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
    run(name, over)
