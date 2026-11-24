#!/usr/bin/env python3
"""판정 아님: 멀티그리드 풀이 정확도의 같은 입력 맞비교 (mg_deep 없음 = 지금 모델 vs mg_deep=1 = 후보).

저장된 장면(vs_t*.npz)에서 연립방정식을 다시 세운다:
  W_k = act_k * G_k * (C_k + r) / L_k * clip(min(h_i, h_j) / thin_h, 0, 1)^2,  M = 1/(kappa dt) (젖은 칸),  우변 = (h - hmean) / dt
(hmean = 한 주기 평균 두께. 실제 우변의 h* 대신 쓰는 대용품이라 절대값보다 두 풀이의 비가 뜻이 있다.)
찬 출발(p0 = 0)에서 V 주기 1·2·3 번 돌린 뒤 정확한 희소 풀이와의 간선 흐름 상대 오차를 잰다.
usage: mg_ab.py OUT.json VS_FILE [VS_FILE ...]
"""
import json, os, sys
import numpy as np
import scipy.sparse as sp, scipy.sparse.linalg as spl
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.normpath(os.path.join(HERE, '..', '..', 'model'))
sys.path.insert(0, MODEL)
import mgt
from ref_model import hash_normal

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]; LS = [1.0, 1.0, np.sqrt(2), np.sqrt(2)]
nb = lambda a, d: np.roll(a, (-d[1], -d[0]), (0, 1))


def build(f, seed):
    Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); C = Z['C'].astype(float); N = wet.shape[0]
    G = [np.exp(0.5 * hash_normal(seed, k, N * N).reshape(N, N)) for k in range(4)]
    hp = np.maximum(h, 0.0)
    W = [(wet & nb(wet, d)) * G[k] * (C[k] + 0.05) / LS[k] * np.clip(np.minimum(hp, nb(hp, d)) / 0.15, 0, 1) ** 2 for k, d in enumerate(DIRS)]
    M = np.where(wet, 1.0 / (20.0 * 0.1), 0.0); S = np.where(wet, (h - Z['hmean'].astype(float)) / 0.1, 0.0)
    S = np.where(wet & (Z['hmean'] > 0), S, 0.0)
    return W, M, S, wet, N


def exact(W, M, S, wet, N):
    idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n); r = []; c = []; v = []
    for k, d in enumerate(DIRS):
        m = W[k] > 0; a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]; r += [a, b, a, b]; c += [b, a, a, b]; v += [-w, -w, w, w]
    ar = np.arange(n); r.append(ar); c.append(ar); v.append(M[wet])
    A = sp.coo_matrix((np.concatenate(v), (np.concatenate(r), np.concatenate(c))), shape=(n, n)).tocsc()
    p = np.zeros((N, N)); p[wet] = spl.spsolve(A, S[wet]); return p


def ferr(W, pa, pe):
    num = den = 0.0
    for k, d in enumerate(DIRS):
        qa = W[k] * (pa - nb(pa, d)); qe = W[k] * (pe - nb(pe, d)); num += float(((qa - qe) ** 2).sum()); den += float((qe ** 2).sum())
    return (num / max(den, 1e-300)) ** 0.5


if __name__ == '__main__':
    out = []
    for f in sys.argv[2:]:
        nm = os.path.basename(os.path.dirname(f)); seed = int(nm.split('_')[2][1:])
        W, M, S, wet, N = build(f, seed); pe = exact(W, M, S, wet, N); row = dict(file=nm + '/' + os.path.basename(f), wet=int(wet.sum()))
        for lab, deep in (('old', None), ('deep1', 1.0)):
            g = mgt.MGT(N, deep=deep)
            row[lab] = [ferr(W, g.solve(W, M, S, np.zeros((N, N)), ncyc=c), pe) for c in (1, 2, 3)]
        out.append(row); print(row, flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
