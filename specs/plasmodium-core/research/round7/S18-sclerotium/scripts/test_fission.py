"""[S17] keep_conn=4 (갈라짐 허용) 작은 시험: 큰 덩이 둘을 잇는 실은 끊기고, 큰 덩이와 작은 덩이를 잇는 실은 지켜진다(작은 쪽만 매달린 조각)."""
import os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
import ref_model as R
src = open(os.path.join(HERE, '..', 'model', 'ref_model.py')).read()
blk = src[src.index("        if P['keep_conn'] and Dm.any():"):src.index("        if Dm.any():\n            stay = wet & ~Dm")]
blk = '\n'.join(l[8:] for l in blk.split('\n'))
def run(kc, wet, h, Dm):
    g = dict(np=np, _torus_label=R._torus_label, nb=R.nb, ALL=R.ALL, N=wet.shape[0], P=dict(R.DEF, keep_conn=kc, hang_age=4.0), wet=wet, Dm=Dm.copy(), negm=None, fill=None,
             nconn=0, nrel=0, nfis=0, step=0, h=h, t=0.0, t_eat=-1e18, hangm=np.zeros(wet.shape, bool), nhang=0, scl=False, t_kept=np.full(wet.shape, -1e18))
    exec(blk, g); return g['Dm'], g['hangm'], g['nfis']
N = 48
for name, (a, b, xb) in (('큰 덩이 둘', ((5, 15), (30, 40), (5, 15))), ('큰 덩이 + 작은 덩이', ((5, 15), (22, 24), (8, 12)))):
    wet = np.zeros((N, N), bool); wet[a[0]:a[1], 5:15] = True; wet[b[0]:b[1], xb[0]:xb[1]] = True
    top = a[1]; bot = b[0]
    for y in range(top, bot): wet[y, 9] = True       # 한 칸 폭 실
    h = np.where(wet, 1.0, 0.0); Dm = np.zeros((N, N), bool); Dm[top + 2:top + 5, 9] = True
    V = float(wet.sum()); print(f'  ({name}: 몸 {V:.0f}칸)')
    for kc in (3, 4):
        out, hang, nf = run(kc, wet, h, Dm)
        print(f'{name:12s} keep_conn={kc}: 마른 칸 {int(out.sum())}/{int(Dm.sum())}, 조각 {R._torus_label(wet & ~out).max()}, 갈라짐 {nf}, 매달린 조각 칸 {int(hang.sum())}')
