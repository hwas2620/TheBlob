"""shape.py RUNDIR [RUNDIR ...] — 저장 상태(20 시간마다, t >= 100)로 잰 모양 지표.
big2_06: h >= 0.6 굵은 칸의 토러스 8연결 조각 가운데 몸 부피 10% 이상이 둘 이상인 몫 (S15 검증자의 정의)
big2_03: 같은 것을 h >= 0.3으로
ncomp_end: 끝 젖은 조각 수, t_touch: 먹이 닿은 시각 (metrics.json)
"""
import sys, glob, json, os
import numpy as np
from scipy import ndimage
S8 = np.ones((3, 3), int)

def tlab(m):
    lab, n = ndimage.label(m, S8)
    if n == 0: return lab, 0
    p = np.arange(n + 1)
    def f(a):
        while p[a] != a: p[a] = p[p[a]]; a = p[a]
        return a
    H, W = m.shape
    def join(a, b):
        if a and b:
            ra, rb = f(a), f(b)
            if ra != rb: p[ra] = rb
    for x in range(W):
        for dx in (-1, 0, 1): join(lab[0, x], lab[H - 1, (x + dx) % W])
    for y in range(H):
        for dy in (-1, 0, 1): join(lab[y, 0], lab[(y + dy) % H, W - 1])
    roots = {}
    mp = np.zeros(n + 1, int)
    for i in range(1, n + 1): mp[i] = roots.setdefault(f(i), len(roots) + 1)
    return mp[lab], len(roots)

def nbig(h, wet, thr, frac=0.1):
    lab, n = tlab(wet & (h >= thr))
    if n == 0: return 0
    s = ndimage.sum(h, lab, range(1, n + 1))
    return int((np.asarray(s) >= frac * h[wet].sum()).sum())

def run_stats(rd):
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))) or sorted(glob.glob(os.path.join(rd, 'lv_t*.npz')))
    b6 = []; b3 = []
    for f in fs:
        d = np.load(f)
        if float(d['t']) < 100: continue
        w = d['wet'].astype(bool); h = d['h']
        b6.append(nbig(h, w, 0.6) >= 2); b3.append(nbig(h, w, 0.3) >= 2)
    out = dict(n=len(b6), big2_06=float(np.mean(b6)) if b6 else None, big2_03=float(np.mean(b3)) if b3 else None)
    if os.path.exists(os.path.join(rd, 'wet.npy')):
        out['ncomp_end'] = tlab(np.load(os.path.join(rd, 'wet.npy')).astype(bool))[1]
    m = json.load(open(os.path.join(rd, 'metrics.json')))
    out['t_touch'] = m.get('t_touch'); out['sup_updates'] = m.get('sup_updates')
    return out

if __name__ == '__main__':
    for rd in sys.argv[1:]:
        print(os.path.basename(rd.rstrip('/')), json.dumps(run_stats(rd)))
