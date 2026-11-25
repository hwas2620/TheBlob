#!/usr/bin/env python3
"""verify7 주장 9: 같은 압력 문제를 두 풀이로 다시 푼다 (짝 비교).

usage: replay.py OUT.json RUN_DIR [RUN_DIR ...]
  RUN_DIR/mgdump/step*.npz (모델의 mgdump 기록: W, wet, M, S, p0) 마다
    정답  : 희소 직접 풀이 (검증자가 새로 만든 행렬)
    MG    : mgt.MGT(N).solve(..., ncyc, nc)       — 대조의 풀이 (pcg 끔)
    PCG   : 같은 MGT 에 pcg=True                   — 후보의 풀이
  유량 상대 오차 e_flux = sqrt(sum (q - q_exact)^2 / sum q_exact^2) (모든 간선), 한 스텝 두께 오차 e_dh = max |dt (div q - div q_exact)|
"""
import json, os, sys, glob
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'): os.environ.setdefault(_k, '1')
import numpy as np
import scipy.sparse as sp, scipy.sparse.linalg as spl
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.normpath(os.path.join(HERE, '..', '..', 'model'))
sys.path.insert(0, MODEL)
import mgt     # 시험 대상인 풀이 그 자체 (모델 코드는 고치지 않고 불러 쓰기만 한다)

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
nb = lambda a, d: np.roll(a, (-d[1], -d[0]), (0, 1))
rev = lambda a, d: np.roll(a, (d[1], d[0]), (0, 1))


def exact(W, M, S, wet):
    N = wet.shape[0]; idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
    r = []; c = []; v = []
    for k, d in enumerate(DIRS):
        m = (W[k] > 0) & wet & nb(wet, d); a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
        r += [a, b, a, b]; c += [b, a, a, b]; v += [-w, -w, w, w]
    ar = np.arange(n); r.append(ar); c.append(ar); v.append(M[wet])
    A = sp.coo_matrix((np.concatenate(v), (np.concatenate(r), np.concatenate(c))), shape=(n, n)).tocsc()
    x = spl.spsolve(A, S[wet])
    p = np.zeros((N, N)); p[wet] = x
    return p


def flux(W, p):
    return [W[k] * (p - nb(p, d)) for k, d in enumerate(DIRS)]


def div(Q):
    dv = np.zeros(Q[0].shape)
    for k, d in enumerate(DIRS): dv += Q[k] - rev(Q[k], d)
    return dv


def errs(W, p, Qe, dve, dt):
    Q = flux(W, p); num = sum(float(((Q[k] - Qe[k]) ** 2).sum()) for k in range(4)); den = sum(float((Qe[k] ** 2).sum()) for k in range(4))
    return dict(e_flux=(num / max(den, 1e-300)) ** 0.5, e_dh=float(np.abs(dt * (div(Q) - dve)).max()))


def main():
    out = []
    for rd in sys.argv[2:]:
        P = json.load(open(os.path.join(rd, 'params.json'))); N = P['N']; dt = P['dt']; ncyc = int(P['ncyc']); nc = int(P['nc'])
        mg = mgt.MGT(N); pc = mgt.MGT(N); pc.pcg = True
        for f in sorted(glob.glob(os.path.join(rd, 'mgdump', 'step*.npz'))):
            Z = np.load(f); W = [Z['W'][k] for k in range(4)]; wet = Z['wet'].astype(bool); M = Z['M']; S = Z['S']; p0 = Z['p0']
            pe = exact(W, M, S, wet); Qe = flux(W, pe); dve = div(Qe)
            pm = mg.solve(W, M, S, p0.copy(), ncyc=ncyc, nc=nc)
            pp = pc.solve(W, M, S, p0.copy(), ncyc=ncyc, nc=nc)
            r = dict(run=os.path.basename(rd.rstrip('/')), file=os.path.basename(f), t=float(Z['t']), scl=bool(Z['scl']), n_wet=int(wet.sum()))
            r['mg'] = errs(W, pm, Qe, dve, dt); r['pcg'] = errs(W, pp, Qe, dve, dt); r['p0'] = errs(W, p0, Qe, dve, dt)
            out.append(r)
            print(r['run'], r['file'], 'mg %.3e pcg %.3e p0 %.3e' % (r['mg']['e_flux'], r['pcg']['e_flux'], r['p0']['e_flux']), flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=0)


if __name__ == '__main__':
    main()
