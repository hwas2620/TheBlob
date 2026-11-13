#!/usr/bin/env python3
"""Which structure hosts the most negative eigenmode of the V(2,2) error propagator (scale 1.5)?  usage: modes.py RUN_DIR step"""
import numpy as np, json, sys, os
import scipy.sparse.linalg as spl
from scipy import ndimage as ndi
from n1 import DIRS, nb, rev, MG
rd = sys.argv[1]; st = int(sys.argv[2]); Zf = np.load(os.path.join(rd, f'ckpt_{st}.npz')); Z = {k: Zf[k] for k in Zf.files}
wet = Z['wet']; W = Z['W']; C = Z['C']; N = int(Z['N']); y0, y1, x0, x1 = Z['win']; n = int(wet.sum())
mg = MG(N, 4, np.float64, 1.5, 'exact'); sl = (slice(1 + y0, 1 + y1), slice(1 + x0, 1 + x1))
for k in range(4): mg.W[0][(k,) + sl] = W[k]
mg.M[0][sl] = np.where(wet, float(Z['sig']), 0.0); mg.build(True); mg.S[0][...] = 0
def mv(v):
    buf = np.zeros(wet.shape); buf[wet] = v; mg.p[0][...] = 0; mg.p[0][sl] = buf; mg.vcycle(0, 2, 2, 20, 0.8); return mg.p[0][sl][wet].copy()
vals, vecs = spl.eigs(spl.LinearOperator((n, n), matvec=mv, dtype=np.float64), k=6, which='SR', maxiter=5000, tol=1e-5)
Cn = np.zeros(wet.shape); deg = np.zeros(wet.shape)
for k, d in enumerate(DIRS):
    Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d))); deg += (C[k] > 4) + rev(C[k] > 4, d)
lab, nl = ndi.label(wet, structure=np.ones((3, 3))); sizes = np.bincount(lab.ravel())
out = []
for i in np.argsort(vals.real)[:4]:
    v = np.zeros(wet.shape); v[wet] = np.abs(vecs[:, i].real) ** 2; v /= v.sum()
    top = v > 0.5 * v.max(); pr = 1.0 / (v ** 2).sum()
    ys, xs = np.nonzero(top)
    # dominant edge direction among the vein edges (C>4) touching the mode's cells, weighted by mode weight
    dirw = [float((v * ((C[k] > 4) + rev(C[k] > 4, d))).sum()) for k, d in enumerate(DIRS)]
    out.append(dict(eig=round(float(vals[i].real), 3), participation_cells=round(float(pr), 1), comp_size_weighted=round(float((v * sizes[lab]).sum()), 1),
                    Cn_weighted=round(float((v * Cn).sum()), 1), vein_deg_weighted=round(float((v * deg).sum()), 2), h_weighted=round(float((v * Z['h']).sum()), 3),
                    age_weighted=round(float((v * Z['age']).sum()), 1), dir_weight_x_y_d1_d2=[round(x / max(sum(dirw), 1e-12), 2) for x in dirw],
                    extent_xy=[int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)], n_top=int(top.sum())))
print(json.dumps(dict(run=rd, step=st, nwet=n, ncomp=int(nl), modes=out)))
