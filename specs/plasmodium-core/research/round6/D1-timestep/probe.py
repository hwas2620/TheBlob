#!/usr/bin/env python3
"""[S1] 저장해 둔 풀이 상태(public/stage0/ref/solver_*.bin.gz)에서 풀이 구성별 유량 오차를 잰다.
물음: 멀티그리드 V 사이클을 켤레기울기(PCG)의 앞처리로 쓰면 같은 사이클 수에서 유량 오차가 얼마나 줄어드는가.
usage: probe.py [REF_DIR]"""
import gzip, json, os, sys, numpy as np
import mgt_pcg as mgt
HERE = os.path.dirname(os.path.abspath(__file__))
REF = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'public', 'stage0', 'ref'))
DIRS = [(0, 1), (1, 0), (1, 1), (-1, 1)]   # E, N, NE, SE  (dy, dx)
nb = lambda a, d: np.roll(a, (-d[0], -d[1]), (0, 1))


def load(f):
    raw = np.frombuffer(gzip.open(os.path.join(REF, f['file'])).read(), '<f4').astype(np.float64); N = f['N']; out = {}
    for fl in f['fields']:
        a = raw[fl['offset']:fl['offset'] + fl['ch'] * N * N].reshape(fl['ch'], N, N); out[fl['name']] = a if fl['ch'] > 1 else a[0]
    return out


def ferr(W, pa, pe):
    num = 0.0; den = 0.0
    for k, d in enumerate(DIRS):
        qa = W[k] * (pa - nb(pa, d)); qe = W[k] * (pe - nb(pe, d)); num += float(((qa - qe) ** 2).sum()); den += float((qe ** 2).sum())
    return (num / max(den, 1e-300)) ** 0.5


class Solver:
    def __init__(self, N, W, M, scale=1.5, nu=2, nc=4):
        self.mg = mgt.MGT(N, scale=scale); self.nu = nu; self.nc = nc
        for k in range(4): self.mg.W[0][k][...] = W[k]
        self.mg.M[0][...] = M; self.mg.build(); self.zero = np.zeros((N, N)); self.tmp = np.zeros((N, N))

    def A(self, p):
        mgt.k_resid(p, self.mg.W[0], self.zero, self.mg.D[0], self.tmp); return -self.tmp

    def V(self, r, ncyc=1):
        """앞처리: 영에서 출발한 V 사이클 ncyc 번"""
        self.mg.S[0][...] = r; self.mg.p[0][...] = 0
        for _ in range(ncyc): self.mg.vcycle(0, self.nu, self.nu, self.nc, 0.8)
        return self.mg.p[0].copy()

    def plain(self, b, x0, n):
        self.mg.S[0][...] = b; self.mg.p[0][...] = x0; out = []
        for _ in range(n): self.mg.vcycle(0, self.nu, self.nu, self.nc, 0.8); out.append(self.mg.p[0].copy())
        return out

    def pcg(self, b, x0, n):
        x = x0.copy(); r = b - self.A(x); z = self.V(r); p = z.copy(); rz = float((r * z).sum()); out = []
        for _ in range(n):
            Ap = self.A(p); a = rz / float((p * Ap).sum()); x = x + a * p; r = r - a * Ap; out.append(x.copy())
            z = self.V(r); rz2 = float((r * z).sum()); p = z + (rz2 / rz) * p; rz = rz2
        return out

    def sd(self, b, x0, n):
        """가장 가파른 내림(앞처리된): x += a z, a = (r·z)/(z·Az). 켤레 방향을 쓰지 않는 값싼 꼴"""
        x = x0.copy(); out = []
        for _ in range(n):
            r = b - self.A(x); z = self.V(r); Az = self.A(z); a = float((r * z).sum()) / float((z * Az).sum()); x = x + a * z; out.append(x.copy())
        return out


man = json.load(open(os.path.join(REF, 'manifest.json')))
f3 = lambda a: ' '.join('%.4f' % x for x in a)
for f in man['files']:
    if f['kind'] != 'solver': continue
    d = load(f); N = f['N']; W, M, b, p0, pe = d['W'], d['M'], d['rhs'], d['p0'], d['pe']
    print(f"== {f['tag']}  젖은 셀 {f['wet']}  웜스타트의 유량 오차 {ferr(W, p0, pe):.4f}   (기록된 값: 1~3사이클 {f3(f['flux_err'])})")
    for scale in (1.5, 1.0, 2.0):
        for nu in (2, 1):
            s = Solver(N, W, M, scale=scale, nu=nu)
            pl = [ferr(W, x, pe) for x in s.plain(b, p0, 6)]
            cg = [ferr(W, x, pe) for x in s.pcg(b, p0, 6)]
            sd = [ferr(W, x, pe) for x in s.sd(b, p0, 6)]
            print(f'  조대 가중치 1/{scale}, V({nu},{nu}):  그냥 사이클 1~6회 {f3(pl)}')
            print(f'  {"":24s}  PCG 1~6회        {f3(cg)}')
            print(f'  {"":24s}  가파른 내림 1~6회 {f3(sd)}')
