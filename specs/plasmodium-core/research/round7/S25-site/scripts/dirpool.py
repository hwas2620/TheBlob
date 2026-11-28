import json, glob, os, numpy as np
from scipy.stats import binomtest
B='/home/user/TheBlob/specs/plasmodium-core/research/round7/'
def wrap(a): return (a+180)%360-180
res={}
for f in glob.glob(B+'S2[0-9]-*/model/runs/b_mig_s*_*/metrics.json')+glob.glob(B+'S2[0-9]-*/model/runs/b_long_s*_*/metrics.json'):
    d=os.path.dirname(f); name=os.path.basename(d); tag=name.split('_',3)[3]; seed=int(name.split('_')[2][1:]); scn=name.split('_')[1]
    try: m=json.load(open(f)); P=json.load(open(d+'/params.json'))
    except Exception: continue
    if 'traj' not in m or not m['traj']: continue
    tr=np.array(m['traj'],float); c0=P['N']/2-0.5; dd=np.hypot(tr[:,1]-c0,tr[:,2]-c0)
    if not (dd>=25).any(): continue
    i=int(np.argmax(dd>=25)); e=wrap(np.degrees(np.arctan2(tr[i,2]-c0,tr[i,1]-c0))-27.0)
    res.setdefault((d.split('/')[-4],tag),[]).append((scn,seed,round(float(e),1),P.get('tri_rnd',0)))
for k in []:
    v=res[k]; e=np.array([x[2] for x in v]); pos=int((e>0).sum()); neg=int((e<0).sum())
    print(k, 'n',len(v),'+%d/-%d'%(pos,neg),'med|e| %.1f'%np.median(np.abs(e)),'mean %.1f'%e.mean(),'tri_rnd',sorted(set(x[3] for x in v)))
cand=[x for k,v in res.items() if k[1] in ('s23v','v8v','s24a','s24b','s24d','v9b') for x in v]
seen={}
for x in cand: seen[(x[0],x[1])]=x
e=np.array([x[2] for x in seen.values()]); pos=int((e>0).sum()); neg=int((e<0).sum())
print('POOLED cand (unique scn,seed):',len(e),'+%d/-%d'%(pos,neg),'p=%.3f'%binomtest(pos,pos+neg).pvalue,'mean %.1f med|e| %.1f'%(e.mean(),np.median(np.abs(e))))
ctrl=[x for k,v in res.items() if k[1] in ('s23c','v8c','s24c','v9c') for x in v]; seen={}
for x in ctrl: seen[(x[0],x[1])]=x
e=np.array([x[2] for x in seen.values()]); pos=int((e>0).sum()); neg=int((e<0).sum())
print('POOLED ctrl:',len(e),'+%d/-%d'%(pos,neg),'p=%.3f'%binomtest(pos,pos+neg).pvalue,'mean %.1f'%e.mean())
from scipy.stats import wilcoxon, ttest_1samp
for lab,tags in (('cand',('s23v','v8v','s24a','s24b','s24d','v9b')),('ctrl',('s23c','v8c','s24c','v9c'))):
    seen={}
    for k,v in res.items():
        if k[1] in tags:
            for x in v: seen[(x[0],x[1])]=x
    e=np.array([x[2] for x in seen.values()]); mig=np.array([x[2] for x in seen.values() if x[0]=='mig']); lg=np.array([x[2] for x in seen.values() if x[0]=='long'])
    print(lab,'n',len(e),'mean %.2f sd %.1f t-p %.3f wil-p %.3f'%(e.mean(),e.std(),ttest_1samp(e,0).pvalue,wilcoxon(e).pvalue),'| mig n%d mean %.1f +%d/-%d | long n%d mean %.1f +%d/-%d'%(len(mig),mig.mean(),(mig>0).sum(),(mig<0).sum(),len(lg),lg.mean(),(lg>0).sum(),(lg<0).sum()))
