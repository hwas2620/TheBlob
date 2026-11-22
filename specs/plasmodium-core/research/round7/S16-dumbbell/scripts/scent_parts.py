"""scent_parts.py RUNDIR T1 T2 ... — [S16 진단] 저장 상태에서 S7의 덩이(h >= 0.6, 몸 부피 10% 이상, 젖은 칸을 가까운 덩이로 나눔)마다
새 칸(age < 2)의 냄새 평균 − 나머지 칸의 냄새 평균. 냄새는 params.json의 먹이 자리에서 다시 계산한다."""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model'))
from ref_model import _torus_label, nb, ALL
rd = sys.argv[1]; P = json.load(open(os.path.join(rd, 'params.json')))
N = P['N']; c0 = N / 2; X, Y = np.meshgrid(np.arange(N), np.arange(N))
food = np.zeros((N, N))
for a_, d_ in P['foods']:
    fx, fy = c0 + d_ * np.cos(np.radians(a_)), c0 + d_ * np.sin(np.radians(a_))
    for sx in (-N, 0, N):
        for sy in (-N, 0, N): food += P['food_amp'] * np.exp(-((X - fx - sx) ** 2 + (Y - fy - sy) ** 2) / (2 * P['food_sigma'] ** 2))
for t in sys.argv[2:]:
    fp = os.path.join(rd, f'vs_t{int(t):04d}.npz'); Z = np.load(fp if os.path.exists(fp) else os.path.join(rd, f'lv_t{int(t):04d}.npz'))
    wet = Z['wet'].astype(bool); h = Z['h']; age = Z['age']
    thk = wet & (h >= 0.6); ls = _torus_label(thk); ns = int(ls.max())
    vs = np.bincount(ls.ravel(), weights=np.where(thk, h, 0).ravel(), minlength=ns + 1); vs[0] = 0
    bg = [k for k in np.argsort(vs)[::-1] if vs[k] >= 0.1 * h[wet].sum()]
    rg = np.zeros((N, N), np.int32)
    for j, k in enumerate(bg): rg[ls == k] = j + 1
    fr = rg > 0
    while fr.any():
        new = np.zeros((N, N), np.int32)
        for d in ALL:
            cand = nb(rg, d) * nb(fr, d); new = np.where((new == 0) & (cand > 0), cand, new)
        new = np.where(wet & (rg == 0), new, 0); fr = new > 0; rg += new
    out = []
    for j in range(1, len(bg) + 1):
        m = rg == j; yn = m & (age < 2.0); yo = m & (age >= 2.0)
        d = (food[yn].mean() - food[yo].mean()) if yn.any() and yo.any() else float('nan')
        out.append(f'part{j} vol={h[m].sum() / h[wet].sum():.2f} young={int(yn.sum())} dscent={d:+.4f} scent={food[m].mean():.3f}')
    print(f't={t}', ' | '.join(out))
