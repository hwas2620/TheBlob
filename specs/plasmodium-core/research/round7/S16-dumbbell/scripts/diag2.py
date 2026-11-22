"""diag2.py — [S16 진단 2] 시드 231~240 (이미 씀). food4 늦음·모두 닿음, long 모양. 판정 아님."""
import json, os, sys, glob, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shape import nbig, tlab
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model', 'runs')
SEEDS = range(231, 241)
def tt(scn, s, tag):
    f = os.path.join(R, f'b_{scn}_s{s}_{tag}', 'metrics.json')
    return json.load(open(f))['t_touch'] if os.path.exists(f) else None
print('== food4: 늦음 = 대조가 닿은 먹이에 50 넘게 늦거나 못 닿음 (10 시드 x 먹이 4)')
for tag in ('s15c', 's15dc', 's16h', 's16hc'):
    late = []; allr = 0; miss = [0] * 4; dly = [[] for _ in range(4)]
    for s in SEEDS:
        c = tt('food4', s, 's15c'); k = tt('food4', s, tag)
        if k is None: continue
        allr += all(x is not None for x in k)
        for i in range(4):
            if k[i] is None: miss[i] += 1
            if c[i] is not None and (k[i] is None or k[i] > c[i] + 50): late.append((s, i + 1, c[i], k[i]))
            if c[i] is not None and k[i] is not None: dly[i].append(k[i] - c[i])
    print(f'{tag:6s} 모두닿음 {allr}  놓침(먹이별) {miss}  늦음 {len(late)}  평균차(먹이별) {[round(np.mean(d), 1) if d else None for d in dly]}')
    for l in late: print('      ', l)
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]
def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))
def lines(w):
    xr = [~nb(w, d) for d in RING]; Nc = np.zeros(w.shape, int)
    for q in (0, 2, 4, 6): Nc += xr[q].astype(int) - (xr[q] & xr[q + 1] & xr[(q + 2) % 8]).astype(int)
    return int((w & (Nc > 1)).sum())
print('== long: big2_06 (t>=100), 늦은 얇은 칸(t>=1600, h<0.3), 끝 줄 칸, 끝 넓이, 끝 조각, 가장 큰 조각 안 줄 칸(t 1000~1500 평균)')
res = {}
for tag in ('s15c', 's15dc', 's16h'):
    rows = []
    for s in SEEDS:
        rd = os.path.join(R, f'b_long_s{s}_{tag}')
        fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
        if not fs: continue
        b6 = []; thin = []; lin_mid = []
        for f in fs:
            Z = np.load(f); t = float(Z['t']); w = Z['wet'].astype(bool); h = Z['h']
            if t >= 100: b6.append(nbig(h, w, 0.6) >= 2)
            if t >= 1600: thin.append(int((w & (h < 0.3)).sum()))
            if 1000 <= t <= 1500:
                lab, n = tlab(w)
                if n: big = lab == np.argmax(np.bincount(lab.ravel(), weights=np.where(w, h, 0).ravel())[1:]) + 1; lin_mid.append(lines(big))
        wE = np.load(os.path.join(rd, 'wet.npy')).astype(bool)
        rows.append((s, np.mean(b6), np.mean(thin), lines(wE), int(wE.sum()), tlab(wE)[1], np.mean(lin_mid)))
    res[tag] = rows
    a = np.array([r[1:] for r in rows])
    print(f'{tag:6s} n={len(rows)} big2_06 {a[:,0].mean():.3f}  thin_late {a[:,1].mean():.0f}  line_end {a[:,2].mean():.0f}  area_end {a[:,3].mean():.0f}  pieces_end {a[:,4].mean():.1f}  line_main_mid {a[:,5].mean():.0f}')
    print('       big2_06 by seed', [round(r[1], 2) for r in rows])
    print('       line_end by seed', [r[3] for r in rows])
