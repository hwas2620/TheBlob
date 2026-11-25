"""S23 풀이 진단: 저장한 풀이 입력(mgdump)마다 켤레기울기 k=1..6의 유량 오차와, 오차를 미리 알려 줄 값(잔차)을 잰다.
python3 pcgk.py out.json dump1.npz ...
- err[k]: 켤레기울기 k 번 뒤 유량 오차 (직접 풀이와 견줌, 모델 mg_err 정의)
- rel[k]: k 번 뒤 상대 잔차 ||S - A p|| / ||S||
- rzr[k]: k 번 뒤 앞풀이 잔차 r·z / (처음 r·z)
- e0: 웜스타트(p0) 그대로의 유량 오차
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'model'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'S22-form', 'scripts'))
import mgt
from mgbench import load, exact, ferr

def pcg_trace(W, M, S, p0, kmax=6, sc=(1.5, 1.5, 1.5), om=0.8, nu=2):
    N = p0.shape[0]; mg = mgt.MGT(N, scales=list(sc), om=om, nu=nu)
    for kk in range(4): mg.W[0][kk][...] = W[kk]
    mg.M[0][...] = M; mg.build(); D = mg.D[0]; Wl = mg.W[0]
    Z0 = np.zeros((N, N)); R = np.zeros((N, N))
    def A(x): mgt.k_resid(x, Wl, Z0, D, R); return -R.copy()
    def B(r):
        mg.S[0][...] = r; mg.p[0][...] = 0.0; mg.vcycle(0, nu, nu, 4, om); return mg.p[0].copy()
    act = D > 0; Sa = np.where(act, S, 0.0); ns = float(np.sqrt((Sa ** 2).sum())) or 1.0
    p = np.where(act, p0, 0.0); r = Sa - A(p); z = B(r); d = z.copy(); rz = float((r * z).sum()); rz0 = rz
    ps, rel, rzr = [], [], []
    for i in range(kmax):
        q = A(d); dq = float((d * q).sum())
        if not dq > 0: ps.append(p.copy()); rel.append(float(np.sqrt((r ** 2).sum())) / ns); rzr.append(rz / rz0 if rz0 else 0.0); continue
        a = rz / dq; p = p + a * d; r = r - a * q
        z = B(r); rz2 = float((r * z).sum()); d = z + (rz2 / rz) * d; rz = rz2
        ps.append(p.copy()); rel.append(float(np.sqrt((r ** 2).sum())) / ns); rzr.append(rz / rz0 if rz0 else 0.0)
    return ps, rel, rzr, float(np.sqrt((np.where(act, Sa - A(np.where(act, p0, 0.0)), 0) ** 2).sum())) / ns

if __name__ == '__main__':
    out = sys.argv[1]; res = []
    for f in sys.argv[2:]:
        W, wet, M, S, p0, t = load(f); pe = exact(W, M, S, wet)
        ps, rel, rzr, rel0 = pcg_trace(W, M, S, p0)
        res.append(dict(f=f, t=t, wet=int(wet.sum()), e0=ferr(W, p0, pe), rel0=rel0, err=[ferr(W, p_, pe) for p_ in ps], rel=rel, rzr=rzr,
                        wmin=float(W[W > 0].min()), wmax=float(W.max())))
        print(os.path.basename(os.path.dirname(os.path.dirname(f))), os.path.basename(f), ' '.join(f"{e:.3f}" for e in res[-1]['err']), f"rel2 {rel[1]:.2e} rzr2 {rzr[1]:.2e} e0 {res[-1]['e0']:.2f}", flush=True)
    json.dump(res, open(out, 'w'))
