"""구멍(가장 큰 마른 덩어리가 아닌 마른 덩어리 = 젖은 몸에 둘러싸인 마른 곳) 수와 칸 수, t = 1200·1600·2000. 레이스(격자 무늬)를 잰다."""
import os, sys, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '../model'))
from ref_model import _torus_label
R = {'s8': os.path.join(H, '../../../../stage0/ref/runs'), 's12': os.path.join(H, '../../S12-conn/model/runs'), 's13': os.path.join(H, '../model/runs')}
for tag in sys.argv[1:]:
    out = []
    for s in (181, 182, 183):
        row = []
        for t in (1200, 1600, 2000):
            Z = np.load(os.path.join(R[tag[:3] if tag[:3] in R else tag[:2]], f'b_long_s{s}_{tag}', f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool)
            ld = _torus_label(~w); n = np.bincount(ld.ravel()); n[0] = 0; big = n.argmax(); holes = (n > 0); holes[big] = False
            row += [int(holes.sum()), int(n[holes].sum())]
        out.append(row)
    a = np.array(out)
    print(f'{tag:6s} holes (count / cells) t1200 {a[:,0].mean():.0f}/{a[:,1].mean():.0f}  t1600 {a[:,2].mean():.0f}/{a[:,3].mean():.0f}  t2000 {a[:,4].mean():.0f}/{a[:,5].mean():.0f}   per seed t2000 {a[:,4].tolist()}')
