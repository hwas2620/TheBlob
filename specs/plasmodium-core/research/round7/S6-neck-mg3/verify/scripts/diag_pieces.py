#!/usr/bin/env python3
"""diag_pieces.py RUN t [t ...] — 탐색: 갈라진 저장 상태에서 가장 큰 젖은 덩어리 밖의 조각들이 왜 이음 규칙에 지켜지지 않았는지 본다.
조각마다: 전체 부피 몫, 두꺼운(h>=0.3) 부피 몫. 규칙은 두꺼운 부피가 몸 전체 부피의 0.1 이상인 덩어리만 '큰 덩어리'로 보고 이음을 지킨다."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vextract as X
REF = '/home/user/TheBlob/specs/plasmodium-core/stage0/ref'
run = sys.argv[1]
for t in sys.argv[2:]:
    Z = np.load(os.path.join(REF, 'runs', run, f'vs_t{int(float(t)):04d}.npz')); h = Z['h'].astype(float); wet = Z['wet'].astype(bool)
    lab = X._torus_label(wet); V = h[wet].sum(); n = int(lab.max())
    vol = np.bincount(lab.ravel(), weights=np.where(wet, h, 0).ravel(), minlength=n + 1); vol[0] = 0
    thv = np.bincount(lab.ravel(), weights=np.where(wet & (h >= 0.3), h, 0).ravel(), minlength=n + 1)
    big = int(np.argmax(vol)); others = [k for k in np.argsort(vol)[::-1] if k != big and k > 0]
    out = 1 - vol[big] / V
    top = [(round(vol[k] / V, 3), round(thv[k] / V, 3), int((lab == k).sum())) for k in others[:4]]
    small = sum(vol[k] for k in others if vol[k] / V < 0.02) / V
    print(run, 't', t, 'out', round(out, 3), 'pieces', len(others), '| biggest outside pieces (vol frac, thick vol frac, cells):', top, '| vol in pieces < 2%:', round(small, 3))
