import json, glob, os, numpy as np
B='/home/user/TheBlob/specs/plasmodium-core/research/round7/'
def wrap(a): return (a+180)%360-180
tags=('s23v','v8v','s24a','s24b','s24d','v9b'); seen={}
for f in glob.glob(B+'S2[3-4]-*/model/runs/b_mig_s*_*/metrics.json')+glob.glob(B+'S2[3-4]-*/model/runs/b_long_s*_*/metrics.json'):
    d=os.path.dirname(f); name=os.path.basename(d); tag=name.split('_',3)[3]
    if tag not in tags: continue
    seed=int(name.split('_')[2][1:]); scn=name.split('_')[1]
    if (scn,seed) in seen: continue
    P=json.load(open(d+'/params.json'))
    m=json.load(open(f)); tr=np.array(m['traj'],float); c0=P['N']/2-0.5; dd=np.hypot(tr[:,1]-c0,tr[:,2]-c0)
    if not (dd>=25).any(): continue
    i=int(np.argmax(dd>=25)); e=wrap(np.degrees(np.arctan2(tr[i,2]-c0,tr[i,1]-c0))-27.0)
    rt=np.random.default_rng(P['seed']+15485863); ox,oy=rt.uniform(0,P['tri_P'],2); t0=rt.uniform(0,P['tri_T']); sx,sy=(1 if v<0.5 else -1 for v in rt.random(2))
    seen[(scn,seed)]=(e,sx,sy,ox,oy,t0)
E=np.array([v[0] for v in seen.values()])
for sx in (1,-1):
    for sy in (1,-1):
        g=np.array([v[0] for v in seen.values() if v[1]==sx and v[2]==sy])
        print('sx%+d sy%+d n%d mean %.1f +%d/-%d'%(sx,sy,len(g),g.mean(),(g>0).sum(),(g<0).sum()))
t0s=np.array([v[5] for v in seen.values()]); 
for a,b in ((0,20),(20,40),(40,60),(60,80)):
    g=E[(t0s>=a)&(t0s<b)]; print('t0 %d-%d n%d mean %.1f +%d/-%d'%(a,b,len(g),g.mean(),(g>0).sum(),(g<0).sum()))
