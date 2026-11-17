#!/usr/bin/env python3
"""전진면 거칠기: 가장 큰 젖은 성분(구멍 채움)의 둘레 / 같은 넓이 원의 둘레, 그리고 몸 안의 마른 구멍 수. usage: rough.py RUN_DIR_OR_NPZ ..."""
import numpy as np, sys, os
from scipy import ndimage as ndi
def rough(wet):
    lab,n=ndi.label(wet,structure=np.ones((3,3)))
    if n==0: return None
    sz=np.bincount(lab.ravel())[1:]; big=lab==(1+np.argmax(sz))
    # 토러스 감김은 무시(몸이 가운데 있음). 구멍 채움
    fill=ndi.binary_fill_holes(big)
    holes=fill&~big; nh=ndi.label(holes)[1]
    A=fill.sum()
    # 둘레: 4이웃 경계 간선 수에 pi/4 보정(격자 계단 평균 보정)
    P=0
    for ax in (0,1):
        P+=int((fill!=np.roll(fill,1,ax)).sum())
    P*=np.pi/4
    return dict(area=int(A), rough=round(float(P/(2*np.sqrt(np.pi*A))),3), holes=int(nh), hole_cells=int(holes.sum()))
if __name__=='__main__':
    for a in sys.argv[1:]:
        if a.endswith('.npz'): w=np.load(a)['wet']
        else: w=np.load(os.path.join(a,'wet.npy'))
        print(a, rough(w))
