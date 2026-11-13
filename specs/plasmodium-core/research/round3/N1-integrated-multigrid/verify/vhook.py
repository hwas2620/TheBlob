"""verification hooks (independent of n1.py's own check): own sparse assembly + splu, per-step flux error, true h minimum, p-h residual."""
import numpy as np, os, json
import scipy.sparse as sp, scipy.sparse.linalg as spl

DXY = [(1, 0), (0, 1), (1, 1), (1, -1)]      # (dx, dy) per edge channel, as documented in n1.py


def shift(a, dx, dy, fill=0):
    """value of a at (y+dy, x+dx), no wrap."""
    out = np.full(a.shape, fill, a.dtype); ny, nx = a.shape
    ys = slice(max(0, -dy), ny - max(0, dy)); xs = slice(max(0, -dx), nx - max(0, dx))
    yt = slice(max(0, dy), ny - max(0, -dy)); xt = slice(max(0, dx), nx - max(0, -dx))
    out[ys, xs] = a[yt, xt]
    return out


def solve_own(W, rhs, wet, sig):
    ny, nx = wet.shape; idx = np.full((ny, nx), -1, np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
    diag = np.full(n, sig, float); I = []; J = []; V = []
    for k, (dx, dy) in enumerate(DXY):
        w = np.asarray(W[k], float); m = w > 0
        if not m.any(): continue
        ys, xs = np.nonzero(m); y2 = ys + dy; x2 = xs + dx
        assert y2.min() >= 0 and y2.max() < ny and x2.min() >= 0 and x2.max() < nx, 'active edge leaves the window'
        a = idx[ys, xs]; b = idx[y2, x2]; assert (a >= 0).all() and (b >= 0).all(), 'edge touches dry cell'
        ww = w[ys, xs]; np.add.at(diag, a, ww); np.add.at(diag, b, ww)
        I += [a, b]; J += [b, a]; V += [-ww, -ww]
    I.append(np.arange(n)); J.append(np.arange(n)); V.append(diag)
    A = sp.csc_matrix((np.concatenate(V), (np.concatenate(I), np.concatenate(J))), shape=(n, n))
    x = spl.splu(A).solve(np.asarray(rhs, float)[wet])
    pe = np.zeros((ny, nx)); pe[wet] = x
    return pe, A


def flux_own(W, p):
    return np.array([np.asarray(W[k], float) * (p - shift(p, dx, dy)) for k, (dx, dy) in enumerate(DXY)])


def div_own(Q):
    d = np.zeros(Q.shape[1:])
    for k, (dx, dy) in enumerate(DXY): d += Q[k] - shift(Q[k], -dx, -dy)
    return d


class Hook:
    def __init__(self, P, out):
        self.P = P; self.out = out; self.rows = []; self.hrows = []; self.sig = 1.0 / (P['kappa'] * P['dt'])

    def after_solve(self, step, W, rhs, wet, p, Q, C, act, h, hstar, Cn, p_warm, win):
        P = self.P; dt = P['dt']; kap = P['kappa']
        Wa = np.array(W, float); pe, A = solve_own(Wa, rhs, wet, self.sig); Qe = flux_own(Wa, pe)
        pa = np.where(wet, np.asarray(p, float), 0.0); Qa = flux_own(Wa, pa)      # flux recomputed by my own stencil from the solver's p
        Qm = np.array(Q, float)                                                    # flux the model actually used
        am = Wa > 0; Ca = np.array(C, float); thick = am & (Ca > 100); thin = am & (Ca <= 4)
        nrm = lambda X, m: float(np.sqrt((X[m] ** 2).sum()))
        e = lambda X, m: nrm(X - Qe, m) / max(nrm(Qe, m), 1e-300) if m.any() else np.nan
        de = div_own(Qe); dm = div_own(Qm)
        res = np.asarray(rhs, float) - self.sig * pa - dm                           # residual of the solver's p
        r = dict(step=step, nwet=int(wet.sum()), err_all=e(Qm, am), err_thick=e(Qm, thick), err_thin=e(Qm, thin), err_myflux=e(Qa, am),
                 err_div=float(np.sqrt(((dm - de)[wet] ** 2).sum() / max((de[wet] ** 2).sum(), 1e-300))),
                 res_rel=float(np.sqrt((res[wet] ** 2).sum() / max((np.asarray(rhs, float)[wet] ** 2).sum(), 1e-300))),
                 gross_ratio_thick=float(np.abs(Qm[thick]).sum() / max(np.abs(Qe[thick]).sum(), 1e-300)) if thick.any() else np.nan,
                 n_thick=int(thick.sum()), Cmax=float(Ca.max()), rhs_rms=float(np.sqrt((np.asarray(rhs, float)[wet] ** 2).mean())))
        # sign agreement of flux on thick edges (silently reversed flow?)
        if thick.any(): r['sign_disagree_thick'] = float((np.sign(Qm[thick]) != np.sign(Qe[thick])).mean())
        if p_warm is not None:
            pw = np.where(wet, np.asarray(p_warm, float), 0.0); r['err_warm'] = e(flux_own(Wa, pw), am)
        # p-h relation: h_new - h* - p/kappa = dt * residual  (exact solve: 0)
        dlt = dt * res; vc = wet & (np.asarray(Cn) > 4); ad = np.abs(dlt)
        r.update(ph_max=float(ad[wet].max()), ph_rms=float(np.sqrt((dlt[wet] ** 2).mean())),
                 ph_vein_gt0p05=float((ad[vc] > 0.05).mean()) if vc.any() else 0.0, ph_vein_gt0p3=float((ad[vc] > 0.3).mean()) if vc.any() else 0.0,
                 ph_wet_gt0p05=float((ad[wet] > 0.05).mean()),
                 hexact_min=float((np.asarray(h, float) - dt * de)[wet].min()))            # h minimum the exact solve would have produced from this state
        self.rows.append(r)

    def after_h(self, step, h, wet, hstar, p, age):
        if not wet.any(): return
        hw = np.asarray(h, float)[wet]; i = int(np.argmin(hw))
        self.hrows.append((step, float(hw[i]), float(np.asarray(age, float)[wet][i]), int((hw < 0).sum()), int((hw < 0.02).sum())))

    def save(self):
        if self.rows:
            keys = sorted(set().union(*[r.keys() for r in self.rows]))
            np.save(os.path.join(self.out, 'vh_checks.npy'), np.array([[r.get(k, np.nan) for k in keys] for r in self.rows], float))
            json.dump(keys, open(os.path.join(self.out, 'vh_keys.json'), 'w'))
        np.save(os.path.join(self.out, 'vh_hmin.npy'), np.array(self.hrows, float))
