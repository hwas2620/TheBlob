import sys, glob, json, numpy as np
sys.path.insert(0, '/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/verify9/scripts')
import meas as M
R='/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/model/runs/'
name=sys.argv[1]; T=float(sys.argv[2])
P=json.load(open(R+name+'/params.json')); print({k:P.get(k) for k in ('tip_fed','tip_fage','ret_tipfree','ret_fed','ret_h','grace','gm_every','tip_home','keep_conn')})
fs=sorted(glob.glob(R+name+'/vs_t*.npz')); ts=[float(np.load(f)['t']) for f in fs]
i=int(np.argmin(np.abs(np.array(ts)-T))); Z=np.load(fs[i])
wet=Z['wet'].astype(bool); h=Z['h'].astype(float); age=Z['age'].astype(float)
lab,n,vol,area,V=M.components(wet,h); main=lab==int(np.argmax(vol))
rm,rest=M.prune_strict(main); l,nl=M.label8(rm); nc=M.nbcount(main)
for k in range(1,nl+1):
    m=l==k
    if m.sum()<3 or age[m].min()<10: continue
    ys,xs=np.nonzero(m&(nc==1)); y,x=ys[0],xs[0]
    for j in (i-1,i,i+1):
        if j<0 or j>=len(fs): continue
        Zj=np.load(fs[j]); w=Zj['wet'].astype(bool); a=Zj['age']; hh=Zj['h']
        print('t',ts[j],'tip',y,x)
        for dy in range(-4,5):
            print(' '.join(('%4.0f'%a[(y+dy)%192,(x+dx)%192] if w[(y+dy)%192,(x+dx)%192] else '   .') for dx in range(-4,5)),'   ',' '.join(('%4.2f'%hh[(y+dy)%192,(x+dx)%192] if w[(y+dy)%192,(x+dx)%192] else '   .') for dx in range(-4,5)))
    break
