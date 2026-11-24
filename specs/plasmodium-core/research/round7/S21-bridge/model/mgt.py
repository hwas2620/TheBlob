"""토러스(주기 경계) 격자용 멀티그리드 — N1(n1.py)의 풀이 구성을 주기 경계로 옮긴 것.

연산자:  M_i p_i + sum_e W_e (p_i - p_j) = S_i      (M_i = 차폐 항, 마른 셀은 M=0 으로 비활성)
간선 채널 k: 0=E (y,x+1), 1=N (y+1,x), 2=NE (y+1,x+1), 3=SE (y-1,x+1).  W[k,y,x] 는 셀 (y,x) 에서 그 이웃으로 가는 간선.
구성(N1 에서 통과한 것): 감쇠 Jacobi omega=0.8, V(2,2), 2x2 합 제한, 조각 상수 보간,
조대 연산자는 간선 가중치만 /1.5 (과보정), 차폐 항은 자식 합 그대로. 조대 연산자는 매 스텝 다시 만든다.
모든 커널은 9점 스텐실 또는 2x2 축소·확대다(GPU 로 옮길 수 있는 연산만 쓴다).
"""
import numpy as np
from numba import njit, prange


@njit(cache=True, parallel=True)
def k_diag(W, M, D):
    n0, n1 = D.shape
    for j in prange(n0):
        jm = (j - 1) % n0; jp = (j + 1) % n0
        for i in range(n1):
            im = (i - 1) % n1
            if M[j, i] > 0:
                D[j, i] = M[j, i] + (W[0, j, i] + W[0, j, im] + W[1, j, i] + W[1, jm, i]
                                     + W[2, j, i] + W[2, jm, im] + W[3, j, i] + W[3, jp, im])
            else:
                D[j, i] = 0.0


@njit(cache=True, parallel=True)
def k_resid(p, W, S, D, R):
    n0, n1 = D.shape
    for j in prange(n0):
        jm = (j - 1) % n0; jp = (j + 1) % n0
        for i in range(n1):
            if D[j, i] > 0:
                im = (i - 1) % n1; ip = (i + 1) % n1
                nbr = (W[0, j, i] * p[j, ip] + W[0, j, im] * p[j, im] + W[1, j, i] * p[jp, i] + W[1, jm, i] * p[jm, i]
                       + W[2, j, i] * p[jp, ip] + W[2, jm, im] * p[jm, im]
                       + W[3, j, i] * p[jm, ip] + W[3, jp, im] * p[jp, im])
                R[j, i] = S[j, i] - (D[j, i] * p[j, i] - nbr)
            else:
                R[j, i] = 0.0


@njit(cache=True, parallel=True)
def _jac1(p, W, S, D, om, out):
    n0, n1 = D.shape
    for j in prange(n0):
        jm = (j - 1) % n0; jp = (j + 1) % n0
        for i in range(n1):
            if D[j, i] > 0:
                im = (i - 1) % n1; ip = (i + 1) % n1
                nbr = (W[0, j, i] * p[j, ip] + W[0, j, im] * p[j, im] + W[1, j, i] * p[jp, i] + W[1, jm, i] * p[jm, i]
                       + W[2, j, i] * p[jp, ip] + W[2, jm, im] * p[jm, im]
                       + W[3, j, i] * p[jm, ip] + W[3, jp, im] * p[jp, im])
                out[j, i] = (1 - om) * p[j, i] + om * (S[j, i] + nbr) / D[j, i]
            else:
                out[j, i] = 0.0


@njit(cache=True)
def k_jac_n(p, W, S, D, om, k, tmp):
    for _ in range(k // 2):
        _jac1(p, W, S, D, om, tmp); _jac1(tmp, W, S, D, om, p)
    if k % 2:
        _jac1(p, W, S, D, om, tmp); p[:, :] = tmp


@njit(cache=True, parallel=True)
def k_coarsen(W, M, Wc, Mc, f):
    """Wc = f * (집합체 사이를 건너는 미세 간선의 합), Mc = 자식 M 의 합(과보정하지 않음)."""
    nc0 = Mc.shape[0]; nc1 = Mc.shape[1]; n0 = M.shape[0]; n1 = M.shape[1]
    for J in prange(nc0):
        j = 2 * J; j1 = j + 1; j2 = (j + 2) % n0
        for I in range(nc1):
            i = 2 * I; i1 = i + 1
            Wc[0, J, I] = f * (W[0, j, i1] + W[0, j1, i1] + W[2, j, i1] + W[3, j1, i1])
            Wc[1, J, I] = f * (W[1, j1, i] + W[1, j1, i1] + W[2, j1, i] + W[3, j2, i])
            Wc[2, J, I] = f * W[2, j1, i1]
            Wc[3, J, I] = f * W[3, j, i1]
            Mc[J, I] = M[j, i] + M[j, i1] + M[j1, i] + M[j1, i1]


@njit(cache=True, parallel=True)
def k_restrict(R, Sc):
    nc0, nc1 = Sc.shape
    for J in prange(nc0):
        j = 2 * J
        for I in range(nc1):
            i = 2 * I
            Sc[J, I] = R[j, i] + R[j, i + 1] + R[j + 1, i] + R[j + 1, i + 1]


@njit(cache=True, parallel=True)
def k_prolong_add(p, e, D):
    nc0, nc1 = e.shape
    for J in prange(nc0):
        j = 2 * J
        for I in range(nc1):
            i = 2 * I; c = e[J, I]
            if D[j, i] > 0: p[j, i] += c
            if D[j, i + 1] > 0: p[j, i + 1] += c
            if D[j + 1, i] > 0: p[j + 1, i] += c
            if D[j + 1, i + 1] > 0: p[j + 1, i + 1] += c


class MGT:
    def __init__(self, N, nmin=4, scale=1.5, FT=np.float64, deep=None):
        self.f = 1.0 / scale; self.fd = self.f if deep is None else 1.0 / deep     # [S21] deep: 둘째 조대층부터의 과보정 (None 이면 scale 과 같다 = 예전). 1.0 이면 과보정이 층마다 곱해지지 않는다
        sizes = [N]
        while sizes[-1] > nmin and sizes[-1] % 2 == 0: sizes.append(sizes[-1] // 2)
        self.sizes = sizes; self.L = len(sizes); z = lambda n: np.zeros((n, n), FT)
        self.W = [np.zeros((4, n, n), FT) for n in sizes]
        self.M = [z(n) for n in sizes]; self.D = [z(n) for n in sizes]; self.p = [z(n) for n in sizes]; self.S = [z(n) for n in sizes]
        self.R = [z(n) for n in sizes]; self.T = [z(n) for n in sizes]

    def build(self):
        """레벨 0 의 W, M 은 호출자가 채운다."""
        k_diag(self.W[0], self.M[0], self.D[0])
        for l in range(1, self.L):
            k_coarsen(self.W[l - 1], self.M[l - 1], self.W[l], self.M[l], self.f if l == 1 else self.fd); k_diag(self.W[l], self.M[l], self.D[l])

    def vcycle(self, l=0, nu1=2, nu2=2, nc=4, om=0.8):
        p, S, W, D = self.p[l], self.S[l], self.W[l], self.D[l]
        if l == self.L - 1:
            k_jac_n(p, W, S, D, om, nc, self.T[l]); return
        if nu1 > 0: k_jac_n(p, W, S, D, om, nu1, self.T[l])
        k_resid(p, W, S, D, self.R[l]); k_restrict(self.R[l], self.S[l + 1]); self.p[l + 1][...] = 0
        self.vcycle(l + 1, nu1, nu2, nc, om)
        k_prolong_add(p, self.p[l + 1], D)
        if nu2 > 0: k_jac_n(p, W, S, D, om, nu2, self.T[l])

    def solve(self, W4, Mdiag, rhs, p0, ncyc=2, nc=4):
        """W4: 간선 가중치 4채널 배열 목록, Mdiag: 차폐 항(마른 셀 0), rhs: 우변, p0: 웜스타트. 근사 해를 돌려준다."""
        for k in range(4): self.W[0][k][...] = W4[k]
        self.M[0][...] = Mdiag; self.S[0][...] = rhs; self.p[0][...] = p0
        self.build()
        for _ in range(ncyc): self.vcycle(0, 2, 2, nc, 0.8)
        return self.p[0].copy()


def drawcalls(N, nmin=4, ncyc=2, nc=4):
    sizes = [N]
    while sizes[-1] > nmin and sizes[-1] % 2 == 0: sizes.append(sizes[-1] // 2)
    L = len(sizes)
    return dict(levels=L, sizes=sizes, solver_drawcalls=ncyc * ((L - 1) * 7 + nc) + (L - 1))


if __name__ == '__main__':
    # 자체 점검: 무작위 가중치·젖은 마스크에서 희소 직접 풀이와 비교 (주기 경계 포함)
    import scipy.sparse as sp, scipy.sparse.linalg as spl, time
    rng = np.random.default_rng(0); N = 96
    yy, xx = np.mgrid[0:N, 0:N]
    wet = (np.hypot((xx - 10 + N / 2) % N - N / 2, (yy - 5 + N / 2) % N - N / 2) < 30)      # 경계를 넘어 감기는 원반
    DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
    nb = lambda a, d: np.roll(a, (-d[1], -d[0]), (0, 1))
    W = [(wet & nb(wet, d)) * np.exp(1.5 * rng.normal(size=(N, N))) for d in DIRS]
    M = np.where(wet, 0.5, 0.0); rhs = np.where(wet, rng.normal(size=(N, N)), 0.0)
    idx = -np.ones((N, N), np.int64); n = int(wet.sum()); idx[wet] = np.arange(n)
    rows = []; cols = []; vals = []
    for k, d in enumerate(DIRS):
        m = W[k] > 0; a = idx[m]; b = nb(idx, d)[m]; w = W[k][m]
        rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
    ar = np.arange(n); rows.append(ar); cols.append(ar); vals.append(np.full(n, 0.5))
    A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
    pe = np.zeros((N, N)); pe[wet] = spl.spsolve(A, rhs[wet])
    mg = MGT(N); p = np.zeros((N, N))
    for c in range(1, 31):
        p = mg.solve(W, M, rhs, p, ncyc=1)
        if c in (1, 2, 5, 10, 20, 30): print('cycles', c, 'rel err', float(np.linalg.norm((p - pe)[wet]) / np.linalg.norm(pe[wet])))
    print(drawcalls(512), drawcalls(768))
