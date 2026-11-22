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
import mgt

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
    thin_h=0.0, thin_pow=2.0,    # [S3] thickness-limited edge conductance (0 = off)
    fan_comp=0,                  # [R4] 1: front competition (Kuroda 2015: after a branching one of the two fronts stops extending and disappears). Off by default
    fan_young=10.0, fan_new=2.0, # [R4] a front = 8-connected cluster of cells younger than fan_young; its vigour = cells younger than fan_new in it
    fan_frac=0.5, fan_tau=40.0,  # [R4] a front whose vigour stays below fan_frac x the strongest front's for fan_tau stops: it wets no more cells
    fan_age=4.0, fan_min=10, fan_every=1.0,   # [R4] stopped cells age (1 + fan_age) times faster; clusters smaller than fan_min cells are not fronts; update every fan_every
    fan_gain=0.0,                # [R4b] >0: no threshold. Every front but the strongest stalls at rate min(1, fan_gain*(1 - vigour/strongest)); 0 = the R4 threshold rule (fan_frac)
    fan_slow=0.0,                # [R4b] >0: a partly stalled front wets less readily: its donor thickness counts fan_slow*h0*min(1, stall/fan_tau) less (the loser slows before it stops)
    fan_up=0.0,                  # [S5] >0: a front climbing the scent (mean food field of its newest cells exceeds that of its older cells by more than fan_up*food_amp) is exempt: it never stalls
    neck_keep=0, neck_h=0.3, neck_min=0.1, neck_C=20.0, neck_every=1.0,   # [S5] 1: when the thick body (h >= neck_h) falls into two or more big parts (volume >= neck_min of the body) that are still joined by thin wet cells,
                                 #      the shortest wet path between them is kept as a tube: its thin cells do not dry, their rest thickness is at least neck_h, and the conductance of its edges is at least neck_C
    sup_age=0.0, sup_h=0.3, sup_min=0.1, sup_tau=8.0, sup_every=1.0,   # [S7] >0: when the thick body (h >= sup_h) is in two or more big parts (volume >= sup_min of the body), every wet cell goes to its nearest
                                 #      big part (distance along wet cells, no limit); a part whose net outflow across its borders with the other parts (edge flux EMA over sup_tau) is e per unit volume and time
                                 #      ages faster: sage rate x (1 + sup_age * max(0, e) * tau_a). A part that gives its body away stiffens, pushes more out and drains into the other (fan competition by flow)
    wall_tau=0.0,                # [S5] >0: the tube wall remembers its conductance: tube thickness uses Cwall = max(Cn, Cwall*exp(-dt/wall_tau)) (a vein's wall outlives a drop of its flow); 0 = off
    fan_food=0.0, fan_scent=0.01,   # [R4b] >0: a newly wet cell counts 1 + fan_food*min(1, c/(fan_scent*food_amp)) in its front's vigour (c: food field) - fronts in a food's scent are not out-competed
    crumb_from=0,  # [stage0 C] first step at which crumb_dry acts (parity dumps switch it on in a state that still holds isolated cells)
    crumb_dry=0,   # [split] 1: a drying cell with no wet neighbour left dries too (its volume is dropped and booked in V_crumb) - no stuck isolated cells
    neg_fill=0,   # [split] 1: with neg_dry, a kept bridge cell (bridge_keep) whose thickness went negative is not dried; its deficit is shared among its neighbours in proportion to their thickness
    edge_t=0.0,    # [S9] >0: edge tension - a wet cell's rest thickness is lowered by edge_t * (dry 8-neighbours)/8: the rim is pushed inward (tips more than straight edges), a detached piece draws itself in
                   # [S16] 3: as 2, and each step one kept run (taken in turn) is tested alone - all other kept runs stay - and dries if the body stays whole without it.
                   #      Under 2 a loop never opens: its cells dry together, each looks like the cut between the others, and all are kept
    keep_conn=0,   # [S15] 2: as 1, but a run of drying cells is judged as a whole (two neighbouring drying cells could otherwise each see one side and cut a thread)
                   # [S12] 1: the body never tears - a drying cell whose staying wet 8-neighbours would end up in two or more separate wet pieces (global torus labelling) does not dry;
                   #      if it went negative its deficit is taken from its neighbours (as neg_fill). Loops of the network still open, branches then draw back from their free ends
    ret_h=0.0,     # [S10] >0: tip/rim retraction - an old (rest thickness incl. tube below h_min) wet cell on the rim that is not a bridge (Yokoi <= 1) and thinner than ret_h dries even above h_min,
                   #      handing its volume to its staying neighbours (inward): abandoned branches and films draw back into the body instead of emptying in place
    ret_glob=0,    # [S14] 1: retraction ignores the local bridge test (Yokoi); with keep_conn the global labelling alone keeps the body in one piece, so loops of old lines and threads open and draw back
    ret_tip=0,     # [S13] 1: a thread end (a wet cell with exactly one wet 8-neighbour) that meets the other ret_h conditions retracts whatever its thickness: a blob hanging on a thread rolls back along it
    bridge_h=0.0,  # [S10] >0: with bridge_keep, a bridge cell is also kept while h >= bridge_h whatever its conductance (a thread breaks only once it is nearly empty)
    sup_cap=0.0,   # [S10] >0: the S7 ageing factor is at most 1 + sup_cap
    hang_age=0.0,  # [S16] >0 (with keep_conn): a piece that hangs on the body only through kept (would-tear) drying cells - every piece of the staying body but the biggest - ages (1 + hang_age) times faster,
                   #      so a lobe or blob hanging on a dead thread draws back into the main body. Off while fed (ret_fed window). Recomputed each step that has kept cells
    ret_fed=0.0,   # [S16] >0: retraction (ret_h) acts only on a hungry body - nothing eaten for more than ret_fed time units (a fed plasmodium keeps its sheet and spreads)
    sup_fed=0.0,   # [S16] >0: S7 acts only on a hungry body - one that has eaten nothing for more than sup_fed time units (a starved plasmodium gathers into one front; a fed one keeps its fronts)
    edge_iso=0,    # [S9] 1: edge tension uses the isotropic edge measure 1 - (Gaussian-weighted wet fraction, sigma curv_sigma) instead of (dry 8-neighbours)/8 (the 8-count favours axis-aligned edges: bodies turn square)
    dry_edge=0,    # [S9] 1: only a wet cell with at least one dry 8-neighbour may dry (negative cells still dry at once): a draining film retreats from its rim, no holes open inside it
    bridge_mem=0.0, bridge_mem_tau=1e9,   # [split] >0: a bridge cell is also kept while its remembered peak conductance (max of Cn, forgetting with time constant bridge_mem_tau) is >= bridge_mem: strands that were real veins outlive the flow that made them
    gm_every=20.0, nsnap=5, log_every=50,
    # --- N2 (front isotropy) ---
    wet_rho=0.0, curv='n8', curv_sigma=1.5, curv_ref=0.33, curv_gain=8.0, curv_cap=99.0, stop_touch=0,
    # --- F1 (mass on food) ---
    dry_weight='equal',          # 'h': redistribute a drying cell's volume to staying neighbours in proportion to their thickness
    neg_diag=0, neg_dry=0,       # neg_dry=1: a cell whose thickness went negative dries at once (ignores grace and bridge_keep); its deficit is taken from the staying neighbours
    wave_lambda=0.0, wave_Trot=80.0,   # prescribed rotating body-scale phase ramp (0 = off)
    food_dw=None,                # per-food angular-frequency offset of the contraction phase on live-food cells (rad per unit time): masses drift in and out of phase
    food_phase=None,             # per-food phase offset of the contraction on live-food cells (diagnostic: forces the food masses out of phase)
    mech_beta=0.0,               # mechanical phase feedback: dtheta/dt += mech_beta * (h - mean rest thickness)/h0 * sin(theta); <0 favours anti-phase between volume-exchanging parts
    solver='exact', ncyc=2, nc=4, extrap=0.5, check_every=0,     # solver='mg': torus multigrid (mgt.py), warm start with time extrapolation
    res_gate=0.0,                # >0: in ramp mode the factor H grows only where h >= res_gate * (current mean rest thickness)
    res_acc=0, res_tau=30.0,     # 1: rest thickness on food grows by what the cell has eaten (cap h_res); 2: ramps toward h_res with time constant res_tau; 0: jumps to h_res on contact
    limit_net=0,                 # positivity limiter on NET outflow: only cells that would go negative scale down their outgoing edge fluxes
    stiff_h=0.0, stiff_pow=2.0,  # thin cells are stiffer: kappa_i = kappa*max(1,(stiff_h/h_i)^stiff_pow); 0 = off
    sat_scent=0.0,               # [split] see the yield threshold: >0 limits the satiety term to scent-free ground
    sat_k=0.0, sat_tau=10.0,     # satiety: yield threshold += sat_k*S, S low-passed indicator of live food being covered
    c_lat=0.0,                   # lateral spreading of conductance to parallel neighbour edges (fraction per unit time)
    mech_rel=0.0, mech_gmax=0.5,     # [H1] accommodation feedback on the phase: dtheta/dt += clip(mech_rel*(h-hbar)/hbar, +-mech_gmax*omega)*sin(theta); <0: an over-filled cell is pulled toward its relaxed (thick) phase
    tri_v=0.0,   # [H1] drift speed of the triangle lattice (cells per unit time; y drifts at 0.618 of it)
    tri_k=0.0, tri_P=128.0, tri_T=80.0,   # [H1] centroid-free rotating gradient: theta_eff = theta + tri_k*(cos(2*pi*t/T)*tri(x) + sin(2*pi*t/T)*tri(y)), tri = zero-mean triangle wave of period tri_P and slope +-1 (torus-periodic when N % tri_P == 0)
    ph_noise=0.0, ph_noise_len=30.0, ph_noise_T=80.0,   # [H1] smooth random phase offset added to the contraction phase: theta_eff = theta + ph_noise*xi(x,t); ph_noise_T>0 rotates between two independent fields
    om_noise_T=0.0, om_noise_seed=None,  # [H1] om_noise_T>0: the frequency field rotates between two independent fields, xi = cos(2*pi*t/T)*xi1 + sin(2*pi*t/T)*xi2; om_noise_seed: seed of the field (default seed+7919)
    om_noise=0.0, om_noise_len=30.0, # [H1] static smooth random frequency field: omega *= 1 + om_noise*xi(x), xi unit-variance Gaussian field of correlation length om_noise_len
    om_food=0.0,                     # [H1] frequency boost on live food discs: omega *= 1 + om_food
    ph_every=10,                     # [H1] record phase-pattern diagnostics every ph_every steps
    noise='np',                  # [stage0] 'hash': static noise fields from the integer-hash generator shared with the browser (hashNoise.ts)
    dump_dir=None, dump_state_steps=(), dump_solver_steps=(),   # [stage0] export full states (at the start of a step) and solver inputs/outputs as float32 .bin.gz
    dump_food=0, dump_tag='state',                              # [stage0 B] dump_food=1: the state dump also carries the stored-mass factor Hres, the previous mean rest thickness and the per-food state
    wave_a0=0.0, vsave=0,        # [verify] wave_a0: initial direction (deg) of the prescribed wave; vsave=1: save a light state every gm_every
    slime0='',                   # [stage0 B] initial slime outside the disc: 'half' = on the half plane x < centre, 'all' = everywhere (slime avoidance test)
    f32=0,                       # [stage0 B] 1: round the stored state to float32 at the end of every step and keep the phase in [0, 2pi) - what the GPU textures do. Control experiment only
                                 #            2: in addition the multigrid solver keeps its iterates in float32 arrays (solver='mg' only)
)
# E7 "sheet front" parameter set = base of every E10 run
BASE = dict(T=400, kappa=20, hy0=1.05, h_fill=0.2, Q0_auto=0.2, tau_a=50, r=0.05, D0=2, rate=0.05, lam=0.06, y_sigma=0.02)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]
WTH = [4 / 6 if (d[0] == 0 or d[1] == 0) else 1 / 6 for d in ALL]
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]     # cyclic order around a cell


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # a at the neighbour in direction d
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))      # edge array of the neighbour at -d (edge arriving here)


# ---------------------------------------------------------------- [stage0] shared hash noise and export
def _lowbias32(x):
    x = np.asarray(x, dtype=np.uint64) & np.uint64(0xFFFFFFFF)
    x ^= x >> np.uint64(16); x = (x * np.uint64(0x7feb352d)) & np.uint64(0xFFFFFFFF)
    x ^= x >> np.uint64(15); x = (x * np.uint64(0x846ca68b)) & np.uint64(0xFFFFFFFF)
    x ^= x >> np.uint64(16)
    return x


def hash_u01(seed, stream, n):
    """n uniforms in (0,1): u_i = (lowbias32(lowbias32(i ^ key1) + key2) + 0.5) / 2^32, key1 from the seed, key2 from the stream."""
    k1 = _lowbias32(np.uint64((int(seed) + 0x9E3779B9) & 0xFFFFFFFF)); k2 = _lowbias32(np.uint64((int(stream) * 0x85EBCA6B + 0xC2B2AE35) & 0xFFFFFFFF))
    i = np.arange(n, dtype=np.uint64)
    x = _lowbias32((_lowbias32(i ^ k1) + k2) & np.uint64(0xFFFFFFFF))
    return (x.astype(np.float64) + 0.5) / 4294967296.0


def hash_normal(seed, stream, n):
    """Box-Muller from sub-streams 2*stream and 2*stream+1."""
    return np.sqrt(-2.0 * np.log(hash_u01(seed, 2 * stream, n))) * np.cos(2.0 * np.pi * hash_u01(seed, 2 * stream + 1, n))


def _dump(P, tag, step, t, fields, extra=None):
    """fields: list of (name, array or list of arrays). Writes <dump_dir>/<tag>.bin.gz (float32 LE, concatenated) and appends to <dump_dir>/manifest.json."""
    import gzip
    d = P['dump_dir']; os.makedirs(d, exist_ok=True); N = P['N']; buf = []; desc = []; off = 0
    for nm, a in fields:
        a = np.asarray(a, dtype=np.float32); ch = 1 if a.ndim == 2 else a.shape[0]
        buf.append(a.reshape(-1).astype('<f4').tobytes()); desc.append(dict(name=nm, ch=ch, offset=off)); off += ch * N * N
    fn = tag + '.bin.gz'
    with gzip.open(os.path.join(d, fn), 'wb', compresslevel=9) as f: f.write(b''.join(buf))
    mp = os.path.join(d, 'manifest.json'); man = json.load(open(mp)) if os.path.exists(mp) else dict(files=[])
    man['files'] = [e for e in man['files'] if e['file'] != fn] + [dict(file=fn, tag=tag, N=N, step=int(step), t=float(t), seed=int(P['seed']), fields=desc, floats=off, **(extra or {}))]
    json.dump(man, open(mp, 'w'), indent=1)


def _torus_label(mask):
    """8-connected labels on the torus (components that touch across the edges are merged)"""
    from scipy import ndimage as _ndi
    N_ = mask.shape[0]
    lab, n = _ndi.label(mask, structure=np.ones((3, 3)))
    if n == 0: return lab
    parent = np.arange(n + 1)
    def f(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for i in range(N_):
        for d in (-1, 0, 1):
            for a, b in ((lab[i, 0], lab[(i + d) % N_, N_ - 1]), (lab[0, i], lab[N_ - 1, (i + d) % N_])):
                if a and b:
                    a, b = f(a), f(b)
                    if a != b: parent[b] = a
    root = np.array([f(k) for k in range(n + 1)])
    _, comp = np.unique(root, return_inverse=True)
    return comp[lab]


def run(name, over):
    P = dict(DEF); P.update(BASE); P.update(over)
    out = os.path.join(HERE, 'runs', name); os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(P['seed'])
    if P['ph_noise'] > 0:
        from scipy.ndimage import gaussian_filter as _gf
        _rp = np.random.default_rng(P['seed'] + 104729 if P['om_noise_seed'] is None else int(P['om_noise_seed']) + 1)
        PX1 = _gf(_rp.normal(size=(P['N'], P['N'])), P['ph_noise_len'], mode='wrap'); PX1 = PX1 / PX1.std()
        PX2 = _gf(_rp.normal(size=(P['N'], P['N'])), P['ph_noise_len'], mode='wrap'); PX2 = PX2 / PX2.std()
    if P['om_noise'] > 0:
        from scipy.ndimage import gaussian_filter as _gf
        _r = np.random.default_rng(P['seed'] + 7919 if P['om_noise_seed'] is None else int(P['om_noise_seed']))
        XI1 = _gf(_r.normal(size=(P['N'], P['N'])), P['om_noise_len'], mode='wrap'); XI1 = XI1 / XI1.std()
        XI2 = _gf(_r.normal(size=(P['N'], P['N'])), P['om_noise_len'], mode='wrap'); XI2 = XI2 / XI2.std(); XI = XI1
    N = P['N']; dt = P['dt']; kap = P['kappa']
    jj, ii = np.mgrid[0:N, 0:N].astype(float)
    X = ii; Y = jj; c0 = N / 2 - 0.5
    mimg = lambda v: (v + N / 2) % N - N / 2
    Ls = [1.0, 1.0, np.sqrt(2), np.sqrt(2)]
    CDRAW = P['c_draw'] if P['c_draw'] > 0 else max(1.0, 2.0 * P['D0'])    # vein = edge reinforced above 2x fresh-sheet conductance
    if P['noise'] == 'hash':     # streams: 0-3 edge noise G (normal), 4-7 fresh-edge conductance (uniform), 8 yield noise eta (normal); index = y*N + x
        G = [np.exp(P['edge_sigma'] * hash_normal(P['seed'], k_, N * N).reshape(N, N)) for k_ in range(4)]
        Cinit = [P['D0'] * (1 + P['D0_noise'] * (2.0 * hash_u01(P['seed'], 100 + k_, N * N).reshape(N, N) - 1.0)) for k_ in range(4)]
        eta = hash_normal(P['seed'], 8, N * N).reshape(N, N)
    else:
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
    Vinj = 0.0; V_crumb = 0.0; ncrumb = 0; nret = 0; nconn = 0; nrel = 0; t_eat = -1e18; sup_fed_skips = 0

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
    Hres = np.ones((N, N))            # F1 res_acc: per-cell stored-mass factor of the rest thickness (grows with what the cell has eaten, capped at h_res)

    dist = np.hypot(X - c0, Y - c0)
    wet = dist < P['R_init']
    h = np.where(wet, P['h_init'], 0.0)
    age = np.zeros((N, N)); sage = np.zeros((N, N)); slime = np.zeros((N, N)); twet = np.full((N, N), -1.0); twet[wet] = 0.0
    Cpk = np.zeros((N, N))
    Cwall = np.zeros((N, N))     # [S5] remembered conductance of the tube wall
    Qema = [np.zeros((N, N)) for _ in DIRS]; supm = np.ones((N, N)); hangm = np.zeros((N, N), bool); nhang = 0; sup_steps = 0; sup_log = []   # [S7] EMA of edge flux, ageing factor
    neck = np.zeros((N, N), bool); neckp = np.zeros((N, N), bool); neck_steps = 0; neck_cells = 0   # [S5] kept link: thin cells (neck) and the whole path incl. its ends (neckp)
    stall = np.zeros((N, N)); fan_log = []      # [R4] per-cell stall clock (inherited by newly wet cells from their donor)
    if P['slime0'] == 'half': slime[(X < c0) & ~wet] = 1.0
    elif P['slime0'] == 'all': slime[~wet] = 1.0
    C = [np.zeros((N, N)) for _ in DIRS]; eage = [np.zeros((N, N)) for _ in DIRS]
    act_prev = [np.zeros((N, N), bool) for _ in DIRS]
    p = np.zeros((N, N)); pm = np.zeros((N, N)); mgs = mgt.MGT(N, FT=np.float32 if P['f32'] >= 2 else np.float64) if P['solver'] == 'mg' else None; mg_err = []
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
    sC = [np.zeros((N, N)) for _ in DIRS]; Cmean_last = [np.zeros((N, N)) for _ in DIRS]      # [stage0 B] conductance averaged over the same window as the fluxes
    hmax_w = np.full((N, N), -np.inf); hmin_w = np.full((N, N), np.inf); hsum_w = np.zeros((N, N)); wet_w = np.ones((N, N), bool); cnt_w = 0
    hamp_last = np.zeros((N, N)); hmean_last = np.zeros((N, N))
    ser_new = np.zeros(steps + 1, np.int32); ser_area = np.zeros(steps + 1, np.int32); ser_dry = np.zeros(steps + 1, np.int32); ser_vol = np.zeros(steps + 1, np.float64)
    ser_newl = np.zeros(steps + 1, np.int32)      # [stage0 B] newly wetted cells on the half plane x < centre
    ser_newm = np.zeros(steps + 1, np.int32); ser_newlm = np.zeros(steps + 1, np.int32); wet_end_prev = wet.copy()      # [stage0 B] the same counted from the end-of-step wet masks (what the GPU harness can see)
    neg_end_steps = 0                             # [stage0 B] steps that end with a wet cell of negative thickness
    mass_err_max = 0.0
    gm_n = max(1, int(round(P['gm_every'] / dt))); gseries = []; newdir = np.zeros(3, np.int64); newdir_series = []
    colour = (X.astype(int) % 2) + 2 * (Y.astype(int) % 2)
    negrec = []
    hmin_end = 0.0; neg_end_cellsteps = 0
    hfood_ser = []; ph_ser = []
    nbridge_kept = 0; ntube_kept = 0; nneg_fill = 0; nlim_steps = 0; nlim_cells = 0; lim_cut_max = 0.0; hpre_min = 0.0; neg_cellsteps = 0; S_sat = 0.0

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
        if P['stiff_h'] > 0:
            kap_i = kap * np.maximum(1.0, (P['stiff_h'] / np.maximum(h[wet], 1e-3)) ** P['stiff_pow'])
            sig_i = 1.0 / (kap_i * dt)
        else:
            sig_i = np.full(n, 1.0 / (kap * dt))
        ar = np.arange(n); rows.append(ar); cols.append(ar); vals.append(sig_i)
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
    hbar_prev = h.copy()
    for step in range(steps + 1):
        t = step * dt
        if P['dump_dir'] and step in P['dump_state_steps']:
            flds = [('h', h), ('wet', wet), ('age', age), ('sage', sage), ('theta', theta), ('slime', slime), ('C', C), ('p', p), ('pm', pm)]; ext = dict(kind='state')
            if P['dump_food']:      # per-food state: remaining amount (-1 = unlimited), attractant amplitude, time of exhaustion (None = alive)
                flds += [('Hres', Hres), ('hbar', hbar_prev)]
                ext = dict(kind=P['dump_tag'], fM=[(-1.0 if np.isinf(v) else float(v)) for v in fM], famp=[float(v) for v in famp], t_exh=[(None if np.isnan(v) else float(v)) for v in t_exh])
            _dump(P, f"{P['dump_tag']}_N{N}_s{P['seed']}_step{step:05d}", step, t, flds, ext)
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
            if P['om_noise'] > 0:
                if P['om_noise_T'] > 0: XI = np.cos(2 * np.pi * t / P['om_noise_T']) * XI1 + np.sin(2 * np.pi * t / P['om_noise_T']) * XI2
                om = om * (1 + P['om_noise'] * XI[wet])
            if P['om_food'] != 0 and nf:
                fl_ = np.zeros((N, N), bool)
                for k_ in range(nf):
                    if fM[k_] > 0: fl_ |= fdisc[k_]
                om = om * (1 + P['om_food'] * fl_[wet])
            ns = max(1, int(P['osc_sub'])); dts = dt / ns
            idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
            rows = []; cols = []; vals = []
            for k, d in enumerate(DIRS):
                a = idx[act[k]]; b = nb(idx, d)[act[k]]; rows += [a, b]; cols += [b, a]; vals += [np.full(2 * a.size, WTH[k])]
            Aw = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
            th = theta[wet]
            s_w = ((h - hbar_prev) / P['h0'])[wet] if P['mech_beta'] != 0 else 0.0
            g_w = np.clip(P['mech_rel'] * ((h - hbar_prev) / np.maximum(hbar_prev, 1e-6))[wet], -P['mech_gmax'] * wv, P['mech_gmax'] * wv) if P['mech_rel'] != 0 else 0.0
            for _ in range(ns):
                if P['D_theta'] > 0:
                    sn = np.sin(th); cs = np.cos(th)
                    coup = cs * (Aw @ sn) - sn * (Aw @ cs)        # = sum_j w_j sin(theta_j - theta_i) over wet 8-neighbours
                else: coup = 0.0
                th = th + dts * (om + P['D_theta'] * coup + (P['mech_beta'] * s_w * np.sin(th) if P['mech_beta'] != 0 else 0.0) + (g_w * np.sin(th) if P['mech_rel'] != 0 else 0.0))
            theta = np.zeros((N, N)); theta[wet] = th
        else:
            theta = np.where(wet, wv * t, 0.0)
        # ---- rest thickness ----
        Cn = node_C()
        if P['bridge_mem'] > 0: Cpk = np.maximum(Cn, Cpk * np.exp(-dt / P['bridge_mem_tau']))
        if P['res_acc'] == 2:      # ramp: on live food the stored-mass factor relaxes toward h_res with time constant res_tau (demand builds gradually, mass is drawn from the body)
            gate_ = (h >= P['res_gate'] * hbar_prev) if P['res_gate'] > 0 else 1.0     # the stored-mass target grows only while the cell is filled to its current rest thickness (demand follows supply)
            Hres = Hres + dt * resmask * wet * gate_ * (P['h_res'] - Hres) / P['res_tau']
        Hfac = Hres if P['res_acc'] else (1.0 + (P['h_res'] - 1.0) * resmask)
        hstar = P['h_old'] + (P['h0'] * Hfac - P['h_old']) * np.exp(-sage / P['tau_a'])   # h_res>1: thick reservoir on live food (N3 variant)
        if P['tau_f'] > 0: hstar = hstar * (1 - (1 - P['h_fill'] / P['h0']) * np.exp(-age / P['tau_f']))   # new cell inflates gradually
        if P['wall_tau'] > 0: Cwall = np.where(wet, np.maximum(Cn, Cwall * np.exp(-dt / P['wall_tau'])), 0.0)
        tube = np.minimum(P['beta'] * np.sqrt(np.maximum(Cn, Cwall) if P['wall_tau'] > 0 else Cn), P['cap'])
        hbar_prev = hstar + tube          # unmodulated mean rest thickness (stretch reference for the mechanical phase feedback)
        if eps > 0:
            th_eff = theta
            if P['wave_lambda'] > 0:           # prescribed body-scale contraction wave: linear phase ramp of wavelength wave_lambda, direction rotating once per wave_Trot
                al_ = np.radians(P['wave_a0']) + (2 * np.pi * t / P['wave_Trot'] if P['wave_Trot'] > 0 else 0.0)
                th_eff = theta + (2 * np.pi / P['wave_lambda']) * (mimg(X - cen_u[0]) * np.cos(al_) + mimg(Y - cen_u[1]) * np.sin(al_))
            if P['tri_k'] > 0:
                _tri = lambda u: np.abs(((u + P['tri_P'] / 2) % P['tri_P']) - P['tri_P'] / 2) - P['tri_P'] / 4
                th_eff = th_eff + P['tri_k'] * (np.cos(2 * np.pi * t / P['tri_T']) * _tri(X - P['tri_v'] * t) + np.sin(2 * np.pi * t / P['tri_T']) * _tri(Y - 0.618 * P['tri_v'] * t))
            if P['ph_noise'] > 0:
                th_eff = th_eff + P['ph_noise'] * (PX1 if P['ph_noise_T'] <= 0 else np.cos(2 * np.pi * t / P['ph_noise_T']) * PX1 + np.sin(2 * np.pi * t / P['ph_noise_T']) * PX2)
            if (P['food_phase'] or P['food_dw']) and nf:
                if not P['food_phase']: P['food_phase'] = [0.0] * nf
                th_eff = th_eff.copy()
                for k_ in range(nf):
                    if fM[k_] > 0: th_eff[fdisc[k_]] += P['food_phase'][k_] + (P['food_dw'][k_] * (t - t_touch[k_]) if (P['food_dw'] and not np.isnan(t_touch[k_])) else 0.0)
            mod = 1 + eps * np.cos(th_eff)
            hstar = hstar * mod
            if P['pulse_tube']: tube = tube * mod
        hstar = hstar + tube
        if P['edge_t'] > 0:      # [S9] edge tension
            if P['edge_iso']:
                en_ = np.clip(1.0 - gaussian_filter(wet.astype(float), P['curv_sigma'], mode='wrap', truncate=3.0), 0.0, 1.0)
            else:
                en_ = np.zeros((N, N))
                for d in ALL: en_ += ~nb(wet, d)
                en_ /= 8.0
            hstar = np.where(wet, hstar - P['edge_t'] * en_, hstar)
        if P['neck_keep'] and neck.any(): hstar = np.where(neck & wet, np.maximum(hstar, P['neck_h']), hstar)   # [S5] the kept link refills to a tube
        # ---- pressure / flux / volume ----
        W = [act[k] * G[k] * (C[k] + P['r']) / Ls[k] for k in range(4)]
        if P['thin_h'] > 0:      # [S3] an edge conducts less when either end is nearly empty: x clip(min(h_i, h_j) / thin_h, 0, 1)^thin_pow (an empty tube is a thin tube)
            hp_ = np.maximum(h, 0.0)
            W = [W[k] * np.clip(np.minimum(hp_, nb(hp_, d)) / P['thin_h'], 0.0, 1.0) ** P['thin_pow'] for k, d in enumerate(DIRS)]
        if P['solver'] == 'mg':
            kap_f = kap * np.maximum(1.0, (P['stiff_h'] / np.maximum(h, 1e-3)) ** P['stiff_pow']) if P['stiff_h'] > 0 else kap
            p0 = np.where(wet, p + P['extrap'] * (p - pm), 0.0); pm = p
            if P['dump_dir'] and step in P['dump_solver_steps']:      # replay data: inputs rounded to float32 first, so numpy and the browser start from identical numbers
                r32 = lambda a_: np.asarray(a_, np.float32).astype(np.float64)
                W32 = [r32(w_) for w_ in W]; M32 = r32(np.where(wet, 1.0 / (kap * dt), 0.0)); S32 = r32(np.where(wet, (h - hstar) / dt, 0.0)); P032 = r32(p0)
                mgx = mgt.MGT(N); pk = [mgx.solve(W32, M32, S32, P032, ncyc=c_, nc=P['nc']) for c_ in (1, 2, 3)]
                idx_ = -np.ones((N, N), np.int64); n_ = int(wet.sum()); idx_[wet] = np.arange(n_); rows_ = []; cols_ = []; vals_ = []
                for k, d in enumerate(DIRS):
                    m_ = W32[k] > 0; a_ = idx_[m_]; b_ = nb(idx_, d)[m_]; w_ = W32[k][m_]
                    rows_ += [a_, b_, a_, b_]; cols_ += [b_, a_, a_, b_]; vals_ += [-w_, -w_, w_, w_]
                ar_ = np.arange(n_); rows_.append(ar_); cols_.append(ar_); vals_.append(M32[wet])
                A_ = sp.coo_matrix((np.concatenate(vals_), (np.concatenate(rows_), np.concatenate(cols_))), shape=(n_, n_)).tocsc()
                pe_ = np.zeros((N, N)); pe_[wet] = spl.splu(A_, permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0.0, options=dict(SymmetricMode=True)).solve(S32[wet])
                def ferr_(pa):
                    num = 0.0; den = 0.0
                    for k, d in enumerate(DIRS):
                        qa = W32[k] * (pa - nb(pa, d)); qe = W32[k] * (pe_ - nb(pe_, d)); num += float(((qa - qe) ** 2).sum()); den += float((qe ** 2).sum())
                    return (num / max(den, 1e-300)) ** 0.5
                _dump(P, f"solver_N{N}_s{P['seed']}_step{step:05d}", step, t, [('W', W32), ('M', M32), ('rhs', S32), ('p0', P032), ('p1', pk[0]), ('p2', pk[1]), ('p3', pk[2]), ('pe', pe_)],
                      dict(kind='solver', wet=int(wet.sum()), flux_err=[ferr_(pk[0]), ferr_(pk[1]), ferr_(pk[2])], flux_err_p0=ferr_(P032), nc=int(P['nc'])))
            p = mgs.solve(W, np.where(wet, 1.0 / (kap_f * dt), 0.0), np.where(wet, (h - hstar) / dt, 0.0), p0, ncyc=P['ncyc'], nc=P['nc'])
            if P['check_every'] > 0 and step > 0 and step % P['check_every'] == 0:
                pe = solve(W, hstar); num = 0.0; den = 0.0; numt = 0.0; dent = 0.0
                for k, d in enumerate(DIRS):
                    qa = W[k] * (p - nb(p, d)); qe = W[k] * (pe - nb(pe, d)); thick = C[k] > 100
                    num += float(((qa - qe) ** 2).sum()); den += float((qe ** 2).sum()); numt += float(((qa - qe)[thick] ** 2).sum()); dent += float((qe[thick] ** 2).sum())
                mg_err.append((step, (num / max(den, 1e-300)) ** 0.5, (numt / max(dent, 1e-300)) ** 0.5))
            if not np.isfinite(p).all() or np.abs(p).max() > 1e12: stop = 'diverged'; break
        else:
            pm = p; p = solve(W, hstar)
        div = np.zeros((N, N))
        for k, d in enumerate(DIRS):
            Q[k] = W[k] * (p - nb(p, d)); div += Q[k] - rev(Q[k], d)
        if P['limit_net']:
            hneg = wet & (h - dt * div < 0)
            if hneg.any():
                hpre_min = min(hpre_min, float((h - dt * div)[wet].min()))
                outf = np.zeros((N, N)); inf_ = np.zeros((N, N))
                for k, d in enumerate(DIRS):
                    qp = np.maximum(Q[k], 0); qm = np.maximum(-Q[k], 0)
                    outf += qp + rev(qm, d); inf_ += qm + rev(qp, d)
                a_l = np.ones((N, N))
                a_l[hneg] = np.clip((np.maximum(h[hneg], 0) / dt + inf_[hneg]) / np.maximum(outf[hneg], 1e-30), 0.0, 1.0)
                cut = 0.0; tot = 0.0; div = np.zeros((N, N))
                for k, d in enumerate(DIRS):
                    ql = np.where(Q[k] > 0, Q[k] * a_l, Q[k] * nb(a_l, d))
                    cut += float(np.abs(Q[k] - ql).sum()); tot += float(np.abs(Q[k]).sum())
                    Q[k] = ql; div += Q[k] - rev(Q[k], d)
                nlim_steps += 1; nlim_cells += int(hneg.sum()); lim_cut_max = max(lim_cut_max, cut / max(tot, 1e-300))
        h = h - dt * div
        if P['sup_age'] > 0:                                                   # [S7] edge flux EMA (edges with a dry end are reset)
            a_s = min(1.0, dt / P['sup_tau'])
            for k, d in enumerate(DIRS): Qema[k] = np.where(wet & nb(wet, d), Qema[k] + a_s * (Q[k] - Qema[k]), 0.0)
        hmin_seen = min(hmin_seen, float(h[wet].min()) if wet.any() else 0.0)
        if wet.any() and float(h[wet].min()) < 0:
            ng = wet & (h < 0); neg_cellsteps += int(ng.sum())
            if P['neg_diag'] and len(negrec) < 200000:
                ys_, xs_ = np.nonzero(ng); o_ = np.argsort(h[ys_, xs_])[:5]
                nw_ = np.zeros((N, N))
                for d in ALL: nw_ += nb(wet, d)
                for q_ in o_:
                    y_, x_ = ys_[q_], xs_[q_]
                    negrec.append((step, h[y_, x_], h[y_, x_] + dt * div[y_, x_], hstar[y_, x_], p[y_, x_], sage[y_, x_], age[y_, x_], Cn[y_, x_], float(resmask[y_, x_]), tube[y_, x_], nw_[y_, x_],
                                   float(min(np.hypot(mimg(x_ - fx), mimg(y_ - fy)) for fx, fy in fpos)) if nf else -1.0, int(ng.sum()), float(neck[y_, x_]), float(neckp[y_, x_]), float(div[y_, x_])))
        # ---- eating / injection (N3 I) ----
        if nf:
            changed = False
            for k_ in range(nf):
                m = fdisc[k_] & wet; n_ = int(m.sum())
                if n_ > 0 and np.isnan(t_touch[k_]): t_touch[k_] = t
                if n_ >= 0.5 * fdisc[k_].sum() and np.isnan(t_cover[k_]): t_cover[k_] = t
                if fM[k_] > 0 and n_ > 0 and P['eat'] > 0:
                    amt = min(P['eat'] * n_ * dt, fM[k_]); fM[k_] -= amt
                    if amt > 0: t_eat = t      # [S16] last time anything was eaten
                    if P['gain'] > 0:
                        h[m] += P['gain'] * amt / n_; Vinj += P['gain'] * amt
                        if P['res_acc'] == 1: Hres[m] = np.minimum(Hres[m] + P['gain'] * amt / n_ / P['h0'], P['h_res'])
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
            if P['neck_keep'] and neckp.any(): C[k] = np.where(act[k] & neckp & nb(neckp, DIRS[k]), np.maximum(C[k], P['neck_C']), C[k])
        age = np.where(wet, age + dt, 0.0)
        sage = np.where(wet, sage + dt * (1.0 - resmask) * (supm if P['sup_age'] > 0 else 1.0) * ((1.0 + P['hang_age'] * hangm) if P['hang_age'] > 0 else 1.0), 0.0)
        if P['fan_comp']:
            fan_k = max(1, int(round(P['fan_every'] / dt)))
            if step % fan_k == 0:
                lab_ = _torus_label(wet & (age < P['fan_young']))
                nl_ = int(lab_.max())
                if nl_ > 0:
                    size_ = np.bincount(lab_.ravel(), minlength=nl_ + 1)
                    w_new_ = (wet & (age < P['fan_new'])).astype(float)
                    if P['fan_food'] > 0: w_new_ = w_new_ * (1.0 + P['fan_food'] * np.clip(food / (P['fan_scent'] * P['food_amp']), 0.0, 1.0))
                    vig_ = np.bincount(lab_.ravel(), weights=w_new_.ravel(), minlength=nl_ + 1)
                    fronts_ = [k_ for k_ in range(1, nl_ + 1) if size_[k_] >= P['fan_min']]
                    up_ = np.zeros(nl_ + 1, bool)
                    if P['fan_up'] > 0:     # [S5] scent climbing: newest cells (age < fan_new) vs the older cells of the same front
                        yn_ = (wet & (age < P['fan_new'])).ravel().astype(float); yo_ = (wet & (age >= P['fan_new'])).ravel().astype(float); fr_ = food.ravel(); lr_ = lab_.ravel()
                        cnew_ = np.bincount(lr_, weights=fr_ * yn_, minlength=nl_ + 1) / np.maximum(np.bincount(lr_, weights=yn_, minlength=nl_ + 1), 1.0)
                        cold_ = np.bincount(lr_, weights=fr_ * yo_, minlength=nl_ + 1) / np.maximum(np.bincount(lr_, weights=yo_, minlength=nl_ + 1), 1.0)
                        up_ = (cnew_ - cold_) > P['fan_up'] * P['food_amp']; up_[0] = False
                    if len(fronts_) >= 2 and P['fan_gain'] > 0:     # [R4b] no threshold: the strongest recovers, the others stall in proportion to how far behind they are
                        vmax_ = max(vig_[k_] for k_ in fronts_)
                        rate_ = np.zeros(nl_ + 1)
                        for k_ in fronts_:
                            rate_[k_] = -1.0 if (vig_[k_] >= vmax_ or up_[k_]) else min(1.0, P['fan_gain'] * (1.0 - vig_[k_] / max(vmax_, 1e-12)))
                        rl_ = rate_[lab_]
                        stall = np.where(rl_ > 0, stall + rl_ * fan_k * dt, np.where(rl_ < 0, np.maximum(stall - fan_k * dt, 0.0), stall))
                    elif len(fronts_) >= 2:
                        vmax_ = max(vig_[k_] for k_ in fronts_)
                        weak_ = np.zeros(nl_ + 1, bool); strong_ = np.zeros(nl_ + 1, bool)
                        for k_ in fronts_:
                            if vig_[k_] < P['fan_frac'] * vmax_ and not up_[k_]: weak_[k_] = True
                            else: strong_[k_] = True
                        stall = np.where(weak_[lab_], stall + fan_k * dt, np.where(strong_[lab_], np.maximum(stall - fan_k * dt, 0.0), stall))
                    if step % (fan_k * 10) == 0:
                        fan_log.append([round(t, 2), len(fronts_), int((wet & (stall > P['fan_tau'])).sum()), int(sum(up_[k_] for k_ in fronts_))] + sorted([int(vig_[k_]) for k_ in fronts_], reverse=True)[:4])
            stopped_ = wet & (stall > P['fan_tau'])
            sage = np.where(stopped_, sage + dt * P['fan_age'], sage)
            stall = np.where(wet, stall, 0.0)
        if P['neck_keep'] and step % max(1, int(round(P['neck_every'] / dt))) == 0:     # [S5] find the link between big thick parts
            neck[:] = False; neckp[:] = False
            thick_ = wet & (h >= P['neck_h']); lt_ = _torus_label(thick_); nt_ = int(lt_.max())
            if nt_ >= 2:
                vt_ = np.bincount(lt_.ravel(), weights=np.where(thick_, h, 0.0).ravel(), minlength=nt_ + 1); vt_[0] = 0.0
                big_ = [k_ for k_ in np.argsort(vt_)[::-1] if vt_[k_] >= P['neck_min'] * float(h[wet].sum())]
                if len(big_) >= 2:
                    def _geo(src_):     # [S6 검증] 결함: N 걸음에서 멈춰, N보다 긴 이음은 양 끝이 지켜지지 않는다(verify/REPORT.md 1번). 규칙을 넣지 않아 그대로 둔다
                        dist_ = np.where(src_, 0.0, np.inf); fr_ = src_.copy(); seen_ = src_.copy(); it_ = 0
                        while fr_.any() and it_ < N:
                            it_ += 1; nbm_ = np.zeros((N, N), bool)
                            for d_ in ALL: nbm_ |= nb(fr_, d_)
                            fr_ = nbm_ & wet & ~seen_; dist_[fr_] = it_; seen_ |= fr_
                        return dist_
                    dA_ = _geo(lt_ == big_[0])
                    for kb_ in big_[1:]:
                        dB_ = _geo(lt_ == kb_); sm_ = dA_ + dB_
                        if not np.isfinite(sm_[wet]).any(): continue          # already apart: nothing to keep
                        path_ = wet & (sm_ <= np.min(sm_[wet]) + 1)
                        neckp |= path_; neck |= path_ & ~thick_
            if neck.any(): neck_steps += 1; neck_cells += int(neck.sum())
        if P['sup_age'] > 0 and step % max(1, int(round(P['sup_every'] / dt))) == 0:     # [S7] which big thick part gives its body away
            supm[:] = 1.0
            thk_ = wet & (h >= P['sup_h']); ls_ = _torus_label(thk_); ns_ = int(ls_.max())
            if P['sup_fed'] > 0 and t - t_eat <= P['sup_fed']: ns_ = 0; sup_fed_skips += 1     # [S16] fed: no competition (supm stays 1)
            if ns_ >= 2:
                vs_ = np.bincount(ls_.ravel(), weights=np.where(thk_, h, 0.0).ravel(), minlength=ns_ + 1); vs_[0] = 0.0
                bg_ = [k_ for k_ in np.argsort(vs_)[::-1] if vs_[k_] >= P['sup_min'] * float(h[wet].sum())]
                if len(bg_) >= 2:
                    rg_ = np.zeros((N, N), np.int32)
                    for j_, k_ in enumerate(bg_): rg_[ls_ == k_] = j_ + 1
                    fr_ = rg_ > 0
                    while fr_.any():                                      # grow all parts at once along wet cells (nearest part wins, no distance limit)
                        new_ = np.zeros((N, N), np.int32)
                        for d_ in ALL:
                            cand_ = nb(rg_, d_) * nb(fr_, d_)
                            new_ = np.where((new_ == 0) & (cand_ > 0), cand_, new_)
                        new_ = np.where(wet & (rg_ == 0), new_, 0); fr_ = new_ > 0; rg_ += new_
                    dx_ = np.zeros((N, N))                                # net outflow across the borders between parts only (inner edges cancel, dried cells leave no bias)
                    for k, d in enumerate(DIRS):
                        qx_ = np.where((rg_ > 0) & (nb(rg_, d) > 0) & (rg_ != nb(rg_, d)), Qema[k], 0.0); dx_ += qx_ - rev(qx_, d)
                    ex_ = []
                    for j_ in range(1, len(bg_) + 1):
                        m_ = rg_ == j_; V_ = float(h[m_].sum()); e_ = float(dx_[m_].sum()) / max(V_, 1e-12)
                        ex_.append(e_)
                        if e_ > 0: supm[m_] = 1.0 + (min(P['sup_age'] * e_ * P['tau_a'], P['sup_cap']) if P['sup_cap'] > 0 else P['sup_age'] * e_ * P['tau_a'])
                    sup_steps += 1
                    if len(sup_log) < 20000: sup_log.append((round(t, 2), [round(float(vs_[k_]) / float(h[wet].sum()), 4) for k_ in bg_], [round(e_, 6) for e_ in ex_]))
        if P['slime_tau'] < 1e8: slime *= np.exp(-dt / P['slime_tau'])
        # ---- rolling statistics ----
        hmax_w = np.maximum(hmax_w, h); hmin_w = np.minimum(hmin_w, h); hsum_w += h; wet_w &= wet; cnt_w += 1
        for k in range(4): sQ[k] += Q[k]; sA[k] += np.abs(Q[k]); sC[k] += C[k]
        cnt_q += 1
        if cnt_w >= nper:
            hamp_last = np.where(wet_w, 0.5 * (hmax_w - hmin_w), 0.0); hmean_last = np.where(wet_w, hsum_w / cnt_w, 0.0)
            hmax_w[:] = -np.inf; hmin_w[:] = np.inf; hsum_w[:] = 0; wet_w[:] = True; cnt_w = 0
        if cnt_q >= nwin:
            Qmean_last = [sQ[k] / cnt_q for k in range(4)]; Qgross_last = [sA[k] / cnt_q for k in range(4)]; Cmean_last = [sC[k] / cnt_q for k in range(4)]; qwin_t = t
            for k in range(4): sQ[k][:] = 0; sA[k][:] = 0; sC[k][:] = 0
            cnt_q = 0
        # ---- drying ----
        Dm = wet & (h < P['h_min']) & (age > P['grace'])
        if P['neck_keep'] and neck.any(): Dm &= ~neck                 # [S5] the kept link does not dry
        if P['dry_edge'] and Dm.any():      # [S9] only rim cells dry
            nd_ = np.zeros((N, N), np.int8)
            for d in ALL: nd_ += ~nb(wet, d)
            Dm &= nd_ > 0
        retm = None
        if P['ret_h'] > 0 and not (P['ret_fed'] > 0 and t - t_eat <= P['ret_fed']):      # [S16] ret_fed: fed bodies do not retract. [S10] tip/rim retraction (never cuts a bridge: Yokoi <= 1; one colour of the 4-colouring per step, like bridge_keep)
            xr_ = [~nb(wet, d) for d in RING]
            Ncr_ = np.zeros((N, N), np.int8); ndr_ = np.zeros((N, N), np.int8)
            for q in (0, 2, 4, 6): Ncr_ += xr_[q].astype(np.int8) - (xr_[q] & xr_[q + 1] & xr_[(q + 2) % 8]).astype(np.int8)
            for q in range(8): ndr_ += xr_[q]
            thin_ok_ = (h < P['ret_h']) | ((ndr_ == 7) if P['ret_tip'] else False)      # [S13] ndr_ == 7: exactly one wet neighbour
            retm = wet & (ndr_ > 0) & ((Ncr_ <= 1) | (P['ret_glob'] > 0)) & thin_ok_ & (hbar_prev < P['h_min']) & (age > P['grace']) & (colour == step % 4)
        negm = (wet & (h < 0)) if P['neg_dry'] else None; prot = None
        if Dm.any() or (P['neg_fill'] and negm is not None and negm.any()):
            if P['tube_keep'] > 0:
                keep = Dm & (Cn > P['tube_keep']); ntube_kept += int(keep.sum()); Dm &= ~keep
            if P['bridge_keep']:
                xb = [~nb(wet, d) for d in RING]
                Nc = np.zeros((N, N), np.int8)
                for q in (0, 2, 4, 6): Nc += xb[q].astype(np.int8) - (xb[q] & xb[q + 1] & xb[(q + 2) % 8]).astype(np.int8)
                strong = (Cn >= P['bridge_break']) | ((Cpk >= P['bridge_mem']) if P['bridge_mem'] > 0 else False) | ((h >= P['bridge_h']) if P['bridge_h'] > 0 else False)
                ok = ((Nc <= 1) | ~strong) & (colour == step % 4)
                nbridge_kept += int((Dm & (Nc > 1) & strong).sum()); Dm &= ok
                prot = (Nc > 1) & strong
        if retm is not None and retm.any(): nret += int((retm & ~Dm).sum()); Dm = Dm | retm
        fill = None
        if P['neg_dry']:
            if P['neg_fill'] and prot is not None:     # a kept strand that went negative is not dried: its deficit is taken from its neighbours (below)
                fill = negm & prot; negm = negm & ~prot
            Dm = Dm | negm
        if P['keep_conn'] and Dm.any():      # [S12] never tear the body
            lab_ = _torus_label(wet & ~Dm)
            mn_ = np.full((N, N), np.iinfo(np.int64).max); mx_ = np.zeros((N, N), np.int64)
            for d in ALL:
                l_ = nb(lab_, d).astype(np.int64); mn_ = np.where(l_ > 0, np.minimum(mn_, l_), mn_); mx_ = np.maximum(mx_, l_)
            if P['keep_conn'] >= 2:      # [S15] judge whole runs of drying cells: a run (8-connected) that touches two or more staying pieces is kept whole
                cl_ = _torus_label(Dm); sel_ = Dm & (mx_ > 0)
                cmn_ = np.full(int(cl_.max()) + 1, np.iinfo(np.int64).max); cmx_ = np.zeros(int(cl_.max()) + 1, np.int64)
                np.minimum.at(cmn_, cl_[sel_], mn_[sel_]); np.maximum.at(cmx_, cl_[sel_], mx_[sel_])
                badc_ = (cmx_ > 0) & (cmx_ != cmn_); badc_[0] = False
                bad_ = Dm & badc_[cl_]
                if P['keep_conn'] >= 3 and bad_.any():      # [S16] release one kept run per step if the body stays whole without it alone
                    ids_ = np.nonzero(badc_)[0]; r_ = int(ids_[step % len(ids_)]); R_ = cl_ == r_
                    labR_ = _torus_label(wet & ~(Dm & ~bad_) & ~R_)
                    nbl_ = np.zeros(0, np.int64)
                    for d in ALL: nbl_ = np.union1d(nbl_, nb(labR_, d)[R_])
                    if int((nbl_ > 0).sum()) <= 1: bad_ &= ~R_; nrel += int(R_.sum())
            else:
                bad_ = Dm & (mx_ > 0) & (mx_ != mn_)
            if P['hang_age'] > 0:      # [S16] hanging pieces: all staying pieces but the biggest, while some drying cells are kept
                hangm[:] = False
                if bad_.any() and not (P['ret_fed'] > 0 and t - t_eat <= P['ret_fed']):
                    pv_ = np.bincount(lab_.ravel(), weights=np.where(wet & ~Dm, h, 0.0).ravel()); pv_[0] = -1.0
                    hangm[:] = (lab_ > 0) & (lab_ != int(np.argmax(pv_))); nhang += int(hangm.sum())
            if bad_.any():
                nconn += int(bad_.sum())
                if negm is not None and (bad_ & negm).any(): fill = (bad_ & negm) if fill is None else (fill | (bad_ & negm))
                Dm &= ~bad_
        if Dm.any():
            stay = wet & ~Dm; ns = np.zeros((N, N))
            for d in ALL: ns += nb(stay, d)
            if P['crumb_dry'] and step >= P['crumb_from']:      # a drying cell with no staying neighbour has nowhere to hand its volume: it dries anyway and the (tiny) volume is dropped and booked
                lone = Dm & (ns <= 0)
                if lone.any(): V_crumb += float(h[lone].sum()); ncrumb += int(lone.sum()); h[lone] = 0.0
            else:
                Dm &= ns > 0
            stay = wet & ~Dm; ns[:] = 0
            for d in ALL: ns += nb(stay, d)
            if P['dry_weight'] == 'h':        # share the drying cell's volume (or deficit, if negative) among staying neighbours in proportion to their thickness
                hpos = np.where(stay, np.maximum(h, 0.0), 0.0); sh = np.zeros((N, N))
                for d in ALL: sh += nb(hpos, d)
                gh = np.where(Dm & (sh > 0), h / np.maximum(sh, 1e-30), 0.0); ge = np.where(Dm & (sh <= 0), h / np.maximum(ns, 1), 0.0)
                add = np.zeros((N, N))
                for d in ALL: add += np.where(stay, nb(gh, d) * hpos + nb(ge, d), 0.0)
                h += add
            else:
                give = np.where(Dm, h / np.maximum(ns, 1), 0.0)
                for d in ALL: h += np.where(stay, nb(give, d), 0.0)
            h[Dm] = 0.0; wet = stay; slime[Dm] = 1.0; age[Dm] = 0.0; sage[Dm] = 0.0; p[Dm] = 0.0; pm[Dm] = 0.0; Hres[Dm] = 1.0; Cpk[Dm] = 0.0; Cwall[Dm] = 0.0; neck[Dm] = False; neckp[Dm] = False
            ser_dry[step] = int(Dm.sum())
        if fill is not None and fill.any():
            fill &= wet
            giver = wet & ~fill; hpos = np.where(giver, np.maximum(h, 0.0), 0.0); sh = np.zeros((N, N))
            for d in ALL: sh += nb(hpos, d)
            fok = fill & (sh > 0); gf = np.where(fok, h / np.maximum(sh, 1e-30), 0.0); addf = np.zeros((N, N))
            for d in ALL: addf += np.where(giver, nb(gf, d) * hpos, 0.0)
            h += addf; h[fok] = 0.0; nneg_fill += int(fok.sum())
        # ---- wetting (thickness yield) ----
        pw = np.where(wet, (h - tube) if P['tube_yield'] else h, -np.inf)
        if P['fan_comp'] and P['fan_slow'] > 0: pw = pw - P['fan_slow'] * P['h0'] * np.clip(stall / P['fan_tau'], 0.0, 1.0)   # [R4b] a partly stalled front slows
        if P['fan_comp']: pw = np.where(wet & (stall > P['fan_tau']), -np.inf, pw)     # [R4] a stopped front wets no more cells
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
        if P['sat_k'] > 0:
            feeding = 1.0 if (nf and any((fM[k_] > 0) and bool((fdisc[k_] & wet).any()) for k_ in range(nf))) else 0.0
            S_sat += (dt / P['sat_tau']) * (feeding - S_sat)
        # [split] sat_scent > 0: satiety holds back only the fronts with no food scent (attractant below sat_scent * food_amp); toward a food the front advances as usual
        sat_w = np.clip(1.0 - food / (P['sat_scent'] * P['food_amp']), 0.0, 1.0) if (P['sat_k'] > 0 and P['sat_scent'] > 0) else 1.0
        yld = P['hy0'] * (1 + P['y_sigma'] * eta) + curv + P['y_s'] * slime - P['y_c'] * food + P['sat_k'] * S_sat * sat_w
        # N2: donor thickness seen by the dry cell
        if P['wet_rho'] > 0:                          # sample the wet-masked thickness at distance wet_rho along the diagonals (bilinear, renormalised over wet cells)
            a_ = min(1.0, P['wet_rho'] / np.sqrt(2.0)); wA = a_ * (1 - a_); wD = a_ * a_
            don_ = wet & np.isfinite(pw); hz = np.where(don_, pw, 0.0); wz = don_.astype(float)
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
            h[ys, xs] = amt; wet[ys, xs] = True; age[ys, xs] = 0.0; sage[ys, xs] = 0.0; twet[ys, xs] = t; Hres[ys, xs] = 1.0
            p[ys, xs] = p[sy, sx]; pm[ys, xs] = pm[sy, sx]; theta[ys, xs] = theta[sy, sx]; stall[ys, xs] = stall[sy, sx]
            ser_new[step] = ys.size; ser_newl[step] = int((xs < c0).sum())
            if nf:                                             # direction of new wetting relative to the food(s), seen from the centroid
                vx = mimg(xs - cen_u[0]); vy = mimg(ys - cen_u[1]); vn = np.maximum(np.hypot(vx, vy), 1e-9); best = np.full(xs.size, -2.0)
                live = [k_ for k_ in range(nf) if np.isnan(t_touch[k_])] or list(range(nf))
                for k_ in live:
                    gx = mimg(fpos[k_][0] - cen_u[0]); gy = mimg(fpos[k_][1] - cen_u[1]); gn = max(np.hypot(gx, gy), 1e-9)
                    best = np.maximum(best, (vx * gx + vy * gy) / (vn * gn))
                newdir += np.array([(best > 0.5).sum(), ((best <= 0.5) & (best >= -0.5)).sum(), (best < -0.5).sum()])
        if P['f32']:      # the state the next step starts from is what a float32 texture would hold
            r32 = lambda a_: np.asarray(a_, np.float32).astype(np.float64)
            h = r32(h); p = r32(p); pm = r32(pm); age = r32(age); sage = r32(sage); slime = r32(slime); Hres = r32(Hres); hbar_prev = r32(hbar_prev)
            theta = r32(np.where(wet, np.mod(theta, 2 * np.pi), 0.0)); C = [r32(c_) for c_ in C]
        nm_ = wet & ~wet_end_prev; ser_newm[step] = int(nm_.sum()); ser_newlm[step] = int((nm_ & (X < c0)).sum()); wet_end_prev = wet.copy()
        if wet.any():
            hm_end = float(h[wet].min()); hmin_end = min(hmin_end, hm_end)
            if hm_end < 0: neg_end_cellsteps += int((wet & (h < 0)).sum()); neg_end_steps += 1
        ser_area[step] = int(wet.sum()); ser_vol[step] = h.sum()
        if nf: hfood_ser.append([float(h[fdisc[k_]].sum() / max(int(fdisc[k_].sum()), 1)) for k_ in range(nf)] + [float(np.angle(np.exp(1j * theta[fdisc[k_] & wet]).sum())) if (fdisc[k_] & wet).any() else np.nan for k_ in range(nf)])
        mass_err_max = max(mass_err_max, abs(float((h.sum() - V0 - Vinj + V_crumb) / V0)))
        if step % P['ph_every'] == 0 and mode == 'osc':
            z_ = np.exp(1j * theta); sh_ = wet & (age > 5.0)
            mx_ = sh_ & nb(sh_, (1, 0)); my_ = sh_ & nb(sh_, (0, 1))
            dx_ = np.angle(nb(z_, (1, 0)) * np.conj(z_))[mx_]; dy_ = np.angle(nb(z_, (0, 1)) * np.conj(z_))[my_]
            ph_ser.append([t, float(abs(z_[wet].mean())) if wet.any() else 0.0, float(dx_.mean()) if dx_.size else 0.0, float(dy_.mean()) if dy_.size else 0.0,
                           float(np.sqrt((dx_ ** 2).mean())) if dx_.size else 0.0, float(np.sqrt((dy_ ** 2).mean())) if dy_.size else 0.0,
                           float(cen_u[0]), float(cen_u[1]), float(h[wet].std() / max(h[wet].mean(), 1e-9)) if wet.any() else 0.0])
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
            if P['vsave']: np.savez_compressed(os.path.join(out, f'vs_t{int(round(t)):04d}.npz'), C=np.array(C, np.float32), wet=wet, h=h.astype(np.float32), age=age.astype(np.float32), sage=sage.astype(np.float32), theta=theta.astype(np.float32), Qgross=np.array(Qgross_last, np.float32), Qmean=np.array(Qmean_last, np.float32), Cmean=np.array(Cmean_last, np.float32), t=t, fM=fM.copy(), cen=np.array(cen_u), hamp=hamp_last.astype(np.float32), hmean=hmean_last.astype(np.float32))
        if step in snaps:
            snapi += 1; render(os.path.join(out, f'snapshot_{snapi}_t{int(round(t)):04d}.png'), t)
            S = state(t); np.savez_compressed(os.path.join(out, f'state_t{int(round(t)):04d}.npz'), **S)
            full_states[f't{int(round(t)):04d}'] = graphm.full(S)
        if not wet.any(): stop = 'all dry'; break
        if P['stop_touch'] and nf and not np.isnan(t_touch).any(): stop = 'touched'; break      # [stage0 B] reach-time runs end when every food has been touched
    nstep = step + 1

    # ------------------------------ outputs ------------------------------
    Cn = node_C()
    sv = lambda n_, a_: np.save(os.path.join(out, n_), a_)
    sv('h.npy', h.astype(np.float32)); sv('wet.npy', wet); sv('age.npy', np.where(wet, age, -1).astype(np.float32)); sv('sage.npy', np.where(wet, sage, -1).astype(np.float32))
    sv('C_edges.npy', np.array(C, np.float32)); sv('eage.npy', np.array(eage, np.float32)); sv('Qmean.npy', np.array(Qmean_last, np.float32)); sv('Qgross.npy', np.array(Qgross_last, np.float32))
    sv('theta.npy', np.where(wet, theta, np.nan).astype(np.float32)); sv('slime.npy', slime.astype(np.float32)); sv('twet.npy', twet.astype(np.float32)); sv('food.npy', food.astype(np.float32))
    sv('vein_native.npy', (Cn * wet).astype(np.float32)); sv('hamp.npy', hamp_last.astype(np.float32)); sv('hmean.npy', hmean_last.astype(np.float32))
    if hfood_ser: np.save(os.path.join(out, 'hfood.npy'), np.array(hfood_ser, np.float32))     # per step: mean h on each food disc, then circular-mean phase of each food disc
    if ph_ser: np.save(os.path.join(out, 'ph_ser.npy'), np.array(ph_ser, np.float32))   # [H1] t, order parameter R, mean dtheta/dx, mean dtheta/dy, rms dx, rms dy, centroid x, y, cv of h
    np.save(os.path.join(out, 'G_edges.npy'), np.array(G, np.float32)); json.dump([[float(e_[0]), float(e_[1]), float(e_[2])] for e_ in mg_err], open(os.path.join(out, 'mg_err_series.json'), 'w'))   # [verify]
    np.savez_compressed(os.path.join(out, 'series.npz'), new=ser_new[:nstep], newl=ser_newl[:nstep], newm=ser_newm[:nstep], newlm=ser_newlm[:nstep], area=ser_area[:nstep], dry=ser_dry[:nstep], vol=ser_vol[:nstep], dt=dt)
    json.dump(P, open(os.path.join(out, 'params.json'), 'w'), indent=1)
    cen = centroid()
    if P['neg_diag'] and negrec: np.save(os.path.join(out, 'negrec.npy'), np.array(negrec, float))
    met = dict(name=name, stop=stop, t_end=round(t, 2), runtime=round(time.time() - t0, 1), V0=float(V0), Vinj=float(Vinj), V_end=float(h.sum()),
               mass_err_max=float(mass_err_max), h_min_seen=hmin_seen, disp=round(float(np.hypot(cen[0] - c0, cen[1] - c0)), 2), path_len=round(float(path_len), 2),
               area_end=int(wet.sum()), foods=[[round(a, 2), round(b, 2)] for a, b in fpos],
               t_touch=[None if np.isnan(v) else round(float(v), 1) for v in t_touch], t_cover=[None if np.isnan(v) else round(float(v), 1) for v in t_cover],
               t_exh=[None if np.isnan(v) else round(float(v), 1) for v in t_exh], fM_end=[None if np.isinf(v) else round(float(v), 2) for v in fM],
               bridge_kept_cellsteps=int(nbridge_kept), tube_kept_cellsteps=int(ntube_kept), neg_fill_cellsteps=int(nneg_fill), fan_log=fan_log, neck_updates=int(neck_steps), neck_cells=int(neck_cells), sup_updates=int(sup_steps), sup_log=sup_log, V_crumb=float(V_crumb), crumb_cells=int(ncrumb), ret_cellsteps=int(nret), conn_kept_cellsteps=int(nconn), conn_released_cells=int(nrel), sup_fed_skips=int(sup_fed_skips), hang_cellsteps=int(nhang), traj=traj,
               mg_err=([float(np.median([e[1] for e in mg_err])), float(np.percentile([e[1] for e in mg_err], 90)), float(max(e[1] for e in mg_err)), float(np.median([e[2] for e in mg_err]))] if mg_err else None), mg_err_n=len(mg_err),
               h_min_end_of_step=float(hmin_end), neg_end_cellsteps=int(neg_end_cellsteps), neg_end_steps=int(neg_end_steps), steps_done=int(nstep), lim_steps=int(nlim_steps), lim_cells=int(nlim_cells), lim_cut_max=float(lim_cut_max), h_prelimit_min=float(hpre_min), neg_cellsteps=int(neg_cellsteps))
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
