import json, glob, os, sys, numpy as np
from scipy.stats import binomtest, wilcoxon
def wrap(a): return (a+180)%360-180
R='../model/runs/'
rows={}
for f in sorted(glob.glob(R+'b_mig_s*/metrics.json')):
    d=os.path.dirname(f); nm=os.path.basename(d); seed=int(nm.split('_')[2][1:]); tag=nm.split('_',3)[3]
    m=json.load(open(f)); P=json.load(open(d+'/params.json')); tr=np.array(m['traj'],float); c0=P['N']/2-0.5; dd=np.hypot(tr[:,1]-c0,tr[:,2]-c0)
    i=int(np.argmax(dd>=25)) if (dd>=25).any() else len(dd)-1; e=wrap(np.degrees(np.arctan2(tr[i,2]-c0,tr[i,1]-c0))-float(P['foods'][0][0]))
    rows.setdefault(seed,{})[tag]=(e, m['t_touch'][0] if m['t_touch'][0] is not None else 400.0, float(np.hypot(tr[-1,1]-c0,tr[-1,2]-c0)))
for tg in ('s25d','y7','y18','y19','y20'):
    E=np.array([v[tg][0] for v in rows.values() if tg in v]); T=np.array([v[tg][1] for v in rows.values() if tg in v]); D=np.array([v[tg][2] for v in rows.values() if tg in v])
    print(tg,'n',len(E),'+%d/-%d'%((E>0).sum(),(E<0).sum()),'mean %.1f med|e| %.1f'%(E.mean(),np.median(np.abs(E))),'touch med %.1f max %.1f'%(np.median(T),T.max()),'disp med %.1f'%np.median(D))
pr=[(v['s25d'],v['y7']) for v in rows.values() if 's25d' in v and 'y7' in v]
if len(pr)>5:
    a=np.array([p[0][1] for p in pr]); b=np.array([p[1][1] for p in pr]); print('paired touch ratio med %.3f'%np.median(b/a), 'disp ratio med %.3f'%np.median(np.array([p[1][2]/p[0][2] for p in pr])))
