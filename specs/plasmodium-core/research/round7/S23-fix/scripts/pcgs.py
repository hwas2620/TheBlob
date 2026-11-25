"""S23 풀이 진단 3: 출발점 고르기. 켤레기울기 2번의 유량 오차를 출발점별로 견준다.
warm: p0 그대로 / zero: 0 / guard: 잔차가 0보다 크면 0 / scale: a·p0, a = p0·S / p0·A·p0 (에너지 노름으로 가장 좋은 배율, 0~1로 자름)
python3 pcgs.py out.json dump...
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from pcgk import pcg_trace, load, exact, ferr
import mgt
def Aop(W, M):
    N = M.shape[0]; mg = mgt.MGT(N)
    for kk in range(4): mg.W[0][kk][...] = W[kk]
    mg.M[0][...] = M; mg.build(); Z0 = np.zeros((N, N)); R = np.zeros((N, N)); D = mg.D[0]; Wl = mg.W[0]
    def A(x): mgt.k_resid(x, Wl, Z0, D, R); return -R.copy()
    return A, D > 0
if __name__ == '__main__':
    out = sys.argv[1]; res = []
    for f in sys.argv[2:]:
        W, wet, M, S, p0, t = load(f); pe = exact(W, M, S, wet); A, act = Aop(W, M)
        p0a = np.where(act, p0, 0.0); Sa = np.where(act, S, 0.0); Ap = A(p0a)
        rel0 = float(np.sqrt(((Sa - Ap) ** 2).sum() / max((Sa ** 2).sum(), 1e-300)))
        den = float((p0a * Ap).sum()); a = float((p0a * Sa).sum()) / den if den > 0 else 0.0; ac = min(1.0, max(0.0, a))
        starts = dict(warm=p0a, zero=np.zeros_like(p0a), guard=(np.zeros_like(p0a) if rel0 > 1 else p0a), scale=ac * p0a, scaleu=a * p0a)
        row = dict(f=f, t=t, rel0=rel0, a=a)
        for k_, st in starts.items():
            ps, _, _, _ = pcg_trace(W, M, S, st, kmax=2); row[k_] = ferr(W, ps[1], pe)
        res.append(row)
        print(os.path.basename(os.path.dirname(os.path.dirname(f))), os.path.basename(f), f"rel0 {rel0:.2f} a {a:.3f}", ' '.join(f"{k_} {row[k_]:.3f}" for k_ in starts), flush=True)
    json.dump(res, open(out, 'w'))
