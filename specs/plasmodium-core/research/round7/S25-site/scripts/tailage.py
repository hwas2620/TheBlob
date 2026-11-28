import sys, glob, json, numpy as np
sys.path.insert(0, '/home/user/TheBlob/specs/plasmodium-core/research/round7/S24-shrink/verify9/scripts')
import meas as M
R=sys.argv.pop(1)
for name in sys.argv[1:]:
    met=json.load(open(R+name+'/metrics.json')); tt=[x for x in met['t_touch'] if x is not None]; t0=min(tt) if tt else 1e9
    rows=[]
    for f in sorted(glob.glob(R+name+'/vs_t*.npz')):
        Z=np.load(f); t=float(Z['t'])
        if t < t0 or int(round(t))%20: continue
        wet=Z['wet'].astype(bool); h=Z['h'].astype(float); age=Z['age'].astype(float)
        lab,n,vol,area,V=M.components(wet,h); big=int(np.argmax(vol)); ids=[k for k in range(1,n+1) if vol[k]>=0.05*V] or [big]; main=np.isin(lab,ids)
        rm,rest=M.prune_strict(main); l,nl=M.label8(rm)
        for k in range(1,nl+1):
            m=l==k; s=int(m.sum())
            if s<3 or age[m].min()<10: continue
            nc=M.nbcount(main); tip=m&(nc==1)
            rows.append((t,s,float(age[tip].min()) if tip.any() else -1,float(age[m].max()),float(h[tip].mean()) if tip.any() else -1))
    a=np.array(rows) if rows else np.zeros((0,5))
    print(name,'n',len(rows),'meanlen %.1f'%(a[:,1].mean() if len(a) else 0),'tipage q25/50/75 %s'%(np.percentile(a[:,2],[25,50,75]).round(1) if len(a) else ''),'tip>60: %d'%((a[:,2]>60).sum() if len(a) else 0),'tip h med %.2f'%(np.median(a[:,4]) if len(a) else 0))
    for r in rows[:12]: print('   t%.0f len%d tipage%.1f maxage%.1f tiph%.2f'%r)
