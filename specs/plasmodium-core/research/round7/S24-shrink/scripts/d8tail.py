"""[S24 진단 7] 먹은 몸의 실 꼬리(L6과 같은 측정: t 200부터 50마다, 자유 끝을 깎아 들어간 칸)를 꼬리표끼리 견줌 (판정 아님).
python3 d8tail.py food4 762,766,767,769 s23c,s23v,y12"""
import sys, os, glob, re, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label, nb, RING
R23 = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model/runs'; R24 = os.path.join(HERE, '..', 'model', 'runs')
def free_tails(w):
    w = w.copy(); pr = np.zeros_like(w)
    for _ in range(400):
        nw = np.zeros(w.shape, int)
        for dd in RING: nw += nb(w, dd)
        e = w & (nw <= 1)
        if not e.any(): break
        pr |= e; w &= ~e
    lab = _torus_label(pr); sz = np.bincount(lab.ravel()); sz[0] = 0
    return int(pr.sum()), (int(sz.max()) if sz.size > 1 else 0)
scn = sys.argv[1]; seeds = [int(x) for x in sys.argv[2].split(',')]; tags = sys.argv[3].split(',')
for tg in tags:
    tot = []; mx = 0
    for s in seeds:
        d = os.path.join(R23 if tg.startswith('s23') else R24, f'b_{scn}_s{s}_{tg}')
        for f in sorted(glob.glob(os.path.join(d, 'vs_t*.npz'))):
            t = int(re.findall(r'vs_t(\d+)', f)[0])
            if t < 200 or t % 50: continue
            a, b = free_tails(np.load(f)['wet'].astype(bool)); tot.append(a); mx = max(mx, b)
    print(f"{tg:5s} 장면 {len(tot)}  꼬리 칸 평균 {np.mean(tot) if tot else float('nan'):.1f}  가장 큰 나무 {mx}")
