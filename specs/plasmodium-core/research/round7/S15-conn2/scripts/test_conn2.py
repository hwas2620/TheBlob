"""[S15] keep_conn 1과 2의 차이를 작은 그림으로 확인: 두 덩어리를 잇는 한 칸 폭 실의 여러 칸이 한꺼번에 마를 때."""
import os, sys, re, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
import ref_model as R
src = open(os.path.join(HERE, '..', 'model', 'ref_model.py')).read()
blk = src[src.index("        if P['keep_conn'] and Dm.any():"):src.index("        if Dm.any():\n            stay = wet & ~Dm")]
blk = '\n'.join(l[8:] for l in blk.split('\n'))
def run(kc, wet, Dm):
    g = dict(np=np, _torus_label=R._torus_label, nb=R.nb, ALL=R.ALL, N=wet.shape[0], P=dict(keep_conn=kc), wet=wet, Dm=Dm.copy(), negm=None, fill=None, nconn=0)
    exec(blk, g); return g['Dm']
N = 40; wet = np.zeros((N, N), bool); wet[5:12, 5:12] = True; wet[25:32, 5:12] = True
for y in range(12, 25): wet[y, 8] = True            # a one-cell thread joining the two blobs
for name, D in (('one cell', [(18, 8)]), ('run of 5', [(y, 8) for y in range(15, 20)]), ('two separate cells', [(14, 8), (22, 8)])):
    Dm = np.zeros((N, N), bool)
    for y, x in D: Dm[y, x] = True
    for kc in (1, 2):
        out = run(kc, wet, Dm); left = wet & ~out
        print(f'{name:18s} keep_conn={kc}: dried {int(out.sum())}/{len(D)}, pieces after {R._torus_label(left).max()}')
# a loose end: thread with a free tip (only one blob); the whole run may dry
wet2 = wet.copy(); wet2[25:32, 5:12] = False; wet2[24, 8] = False
Dm = np.zeros((N, N), bool); Dm[18:24, 8] = True
for kc in (1, 2):
    out = run(kc, wet2, Dm); print(f'free-end run       keep_conn={kc}: dried {int(out.sum())}/6, pieces after {R._torus_label(wet2 & ~out).max()}')
