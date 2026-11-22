"""[S16] keep_conn 2와 3의 차이: 한 칸 폭 고리의 여러 칸이 한꺼번에 마를 때 (2는 하나도 못 마르고, 3은 한 덩어리를 풀어 준다).
진짜 다리(두 덩어리를 잇는 실 하나)는 3도 지킨다."""
import os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
import ref_model as R
src = open(os.path.join(HERE, '..', 'model', 'ref_model.py')).read()
blk = src[src.index("        if P['keep_conn'] and Dm.any():"):src.index("        if Dm.any():\n            stay = wet & ~Dm")]
blk = '\n'.join(l[8:] for l in blk.split('\n'))
def run(kc, wet, Dm, step=0):
    g = dict(np=np, _torus_label=R._torus_label, nb=R.nb, ALL=R.ALL, N=wet.shape[0], P=dict(keep_conn=kc), wet=wet, Dm=Dm.copy(), negm=None, fill=None, nconn=0, nrel=0, step=step)
    exec(blk, g); return g['Dm']
N = 40
# 1) a blob with a thread loop: the loop leaves the blob at (12,8) and comes back at (12,20); every 3rd loop cell dries this step
wet = np.zeros((N, N), bool); wet[5:12, 5:24] = True
loop = [(y, 8) for y in range(12, 30)] + [(29, x) for x in range(9, 21)] + [(y, 20) for y in range(12, 29)]
for y, x in loop: wet[y, x] = True
Dm = np.zeros((N, N), bool)
for i, (y, x) in enumerate(loop):
    if i % 3 == 1: Dm[y, x] = True
n0 = R._torus_label(wet).max()
for kc in (2, 3):
    for step in range(3):
        out = run(kc, wet, Dm, step); print(f'loop   keep_conn={kc} step={step}: dried {int(out.sum())}/{int(Dm.sum())}, pieces {n0} -> {R._torus_label(wet & ~out).max()}')
# 2) a true bridge: two blobs joined by one thread; a run of 5 thread cells dries
wet = np.zeros((N, N), bool); wet[5:12, 5:12] = True; wet[25:32, 5:12] = True
for y in range(12, 25): wet[y, 8] = True
Dm = np.zeros((N, N), bool); Dm[15:20, 8] = True
for kc in (2, 3):
    for step in range(3):
        out = run(kc, wet, Dm, step); print(f'bridge keep_conn={kc} step={step}: dried {int(out.sum())}/5, pieces after {R._torus_label(wet & ~out).max()}')
