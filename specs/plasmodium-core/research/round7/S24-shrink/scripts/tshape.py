"""[S24 진단 2] 균핵 쉼 두께 모양 변형을 갇히기 직전 장면에서 따로 만들어, 여덟째 검증자의 7(f) 측정(lump_metrics)으로 잰다 (판정 아님).
python3 tshape.py   (S23 결승 s23v: long 761~770, slimeall 771~776, 그리고 셋째 거르기 long 781~790·slimeall 791~796)
변형 (모두 자리 고르기는 s23v 와 같다: σ5/σ10, 0.8, 틈 메우기, 가장 작은 넓이 V/3.5)
- cur : R ∝ G5^2 · (1 + u/max u)              (s23v)
- c3  : R ∝ G5^2 · (1 + 3 u/max u)
- q1c2: R ∝ G5   · (1 + 2 u/max u)
- drop: R ∝ u + 0.15 max u (방울 모양만)
그리고 'end' = 실행 끝 덩이의 실제 h (cur 의 결과)
"""
import os, sys, json, numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.insert(0, '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/verify8/scripts')
from sitepick import pick
from tprof import cap
from measure import lump_metrics
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label
RUNS = os.path.join(HERE, '..', '..', 'S23-fix', 'model', 'runs')

def clipfit(w, Vb, tmax=5.0):
    R = Vb * w / w.sum()
    for _ in range(6): R = np.clip(R * Vb / R.sum(), 0.3, tmax)
    return R

def variants(G5, T, Vb, U):
    g = np.maximum(G5[T], 1e-9); u = U[T] / U[T].max()
    return dict(cur=clipfit(g ** 2 * (1 + u), Vb), c3=clipfit(g ** 2 * (1 + 3 * u), Vb), q1c2=clipfit(g * (1 + 2 * u), Vb), drop=clipfit(u + 0.15, Vb))

def f_ok(L):
    sp, ra, cv, st = L['sp_h_d'], L['h_ratio'], L['h_cv'], L['max_step_frac']
    return (sp is not None and sp >= 0.5) and (ra is not None and ra >= 1.5) and cv >= 0.15 and (st is None or st <= 0.5)

cases = [('long', s) for s in range(761, 771)] + [('slimeall', s) for s in range(771, 777)] + [('long', s) for s in range(781, 791)] + [('slimeall', s) for s in range(791, 797)]
acc = {}
for scn, s in cases:
    d = os.path.join(RUNS, f'b_{scn}_s{s}_s23v')
    try:
        m = json.load(open(os.path.join(d, 'metrics.json'))); ts = m['t_scl']
        if ts is None: continue
        Z = np.load(os.path.join(d, f'vs_t{int(ts // 20 * 20):04d}.npz'))
    except Exception as e:
        print(scn, s, 'skip', type(e).__name__); continue
    w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); N = w.shape[0]
    T, Vb = pick(h, w, s1=5, s2=10, hole=4, frac=0.8, tmin=1.2, tmax=3.5)
    hw = np.where(w, np.maximum(h, 0), 0); G5 = gaussian_filter(hw, 5, mode='wrap', truncate=3.0); U = cap(T)
    res = {}
    for k, R in variants(G5, T, Vb, U).items():
        H = np.zeros((N, N)); H[T] = R; res[k] = lump_metrics(T, H, N)[0]; res[k]['top'] = float((R >= 4.999).mean())
    try:
        Te = int(m['t_end']) // 20 * 20; Ze = np.load(os.path.join(d, f'vs_t{Te:04d}.npz')); we = Ze['wet'].astype(bool); he = np.where(we, Ze['h'], 0.0)
        lab = _torus_label(we); vol = np.bincount(lab.ravel(), weights=he.ravel()); vol[0] = 0; big = lab == int(np.argmax(vol))
        res['end'] = lump_metrics(big, he, N)[0]; res['end']['top'] = float((he[big] >= 4.999).mean())
    except Exception: pass
    for k, L in res.items(): acc.setdefault(k, []).append((scn, s, L))
    print(f"{scn:8s} {s} A {int(T.sum()):4d}  " + '  '.join(f"{k} sp {L['sp_h_d']:.2f} c/e {L['h_ratio'] or 0:.2f} cv {L['h_cv']:.2f} st {L['max_step_frac'] or 0:.2f} top {L['top']:.2f}{'' if f_ok(L) else ' ✗'}" for k, L in res.items()))
print('\n변형별: 7(f) 실패 수 / 판, sp 최소, c/e 최소, cv 최소·중앙, 위 한도 칸 몫 최대')
for k, L in acc.items():
    sp = [x[2]['sp_h_d'] or 0 for x in L]; ra = [x[2]['h_ratio'] or 0 for x in L]; cv = [x[2]['h_cv'] for x in L]; tp = [x[2]['top'] for x in L]
    bad = [f"{x[0][0]}{x[1]}" for x in L if not f_ok(x[2])]
    print(f"  {k:5s} 실패 {len(bad)}/{len(L)} {bad}  sp 최소 {min(sp):.2f}  c/e 최소 {min(ra):.2f}  cv 최소 {min(cv):.2f} 중앙 {np.median(cv):.2f}  top 최대 {max(tp):.2f}")
