#!/usr/bin/env python3
"""기준선(N3 의 B_res_a27_s*)과 고친 젖음 규칙들(L27_<variant>_s*)의 형태 지표 비교. 먹이 27도 거리 45, T=320, 시드 1~3. 값은 시드 3개의 [최소, 중앙, 최대]."""
import json, numpy as np, os, sys
sys.path.insert(0, '.')
PATS={'base':'../N3-food-trunk-connect/runs/B_res_a27_s%d','c0':'runs/L27_r100_c0_s%d','g15':'runs/L27_r092_g15_s%d','g20':'runs/L27_r092_g20_s%d'}
def load(d):
    m=json.load(open(d+'/metrics.json')); gs=m['gseries']; tt=m['t_touch'][0]
    post=[g for g in gs if g['t']>tt]
    med=lambda k: float(np.median([g['vein'][k] for g in post]))
    full=m['full']; last=full[sorted(full)[-1]]
    out=dict(t_touch=tt, mass_err=m['mass_err_max'], h_min=m['h_min_seen'], hamp_sheet_rel=m['hamp'].get('sheet_rel'),
             vein_largest=med('largest'), vein_or_sheet_largest=med('largest_ws'), edges=med('edges'), endpoints=med('endpoints'), junctions=med('junctions'), cycles=med('cycles'),
             C_med=med('C_med'), C_p90=med('C_p90'), body_comps_end=post[-1]['body']['comps'], body_largest_vol=post[-1]['body']['largest_vol'],
             strahler_max=last.get('strahler',{}).get('strahler_max'), chord_lattice_frac=last.get('orient',{}).get('L>=5',{}).get('frac_within7p5'))
    # 위치-logC Spearman (C>4 간선, 먹이 방향 축으로 투영) 을 최종 상태에서 직접 계산
    C=np.load(d+'/C_edges.npy'); N=C.shape[1]; ang=np.radians(27.0); ux,uy=np.cos(ang),np.sin(ang)
    from scipy.stats import spearmanr
    xs=[];cs=[]
    for k,(dx,dy) in enumerate([(1,0),(0,1),(1,1),(1,-1)]):
        ys,xx=np.nonzero(C[k]>4); xs.append((xx+dx/2)*ux+(ys+dy/2)*uy); cs.append(np.log(C[k][ys,xx]))
    xs=np.concatenate(xs); cs=np.concatenate(cs)
    out['spearman_pos_logC']=float(spearmanr(xs,cs)[0])
    return out
res={}
for tag,pat in PATS.items():
    rows=[load(pat%s) for s in (1,2,3) if os.path.exists(pat%s+'/metrics.json')]
    if rows: res[tag]=rows
keys=list(next(iter(res.values()))[0].keys())
print('지표'.ljust(24), ' | '.join(f'{t} (n={len(r)})'.ljust(26) for t,r in res.items()))
for k in keys:
    cells=[]
    for t,r in res.items():
        v=[x[k] for x in r if x[k] is not None]
        if not v: cells.append('-'.ljust(26)); continue
        v=sorted(v); fmt=(lambda x: f'{x:.2e}') if k=='mass_err' else (lambda x: f'{x:.3g}')
        cells.append(('['+', '.join(fmt(x) for x in v)+']').ljust(26))
    print(k.ljust(24), ' | '.join(cells))
json.dump(res, open('cmp_morph2.json','w'), indent=1)
