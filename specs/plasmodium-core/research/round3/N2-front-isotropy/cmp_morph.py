#!/usr/bin/env python3
"""기준선(N3 의 B_res_a27_s*)과 고친 젖음 규칙(L27_r100_c0_s*)의 형태 지표 비교. 같은 설정, 같은 시드, 먹이 27도 거리 45, T=320."""
import json, numpy as np, os, sys
B='../N3-food-trunk-connect/runs/B_res_a27_s%d'; F='runs/L27_r100_c0_s%d'
def load(d):
    m=json.load(open(d+'/metrics.json')); gs=m['gseries']; tt=m['t_touch'][0]
    post=[g for g in gs if g['t']>tt]
    med=lambda k: float(np.median([g['vein'][k] for g in post]))
    full=m['full']; last=full[sorted(full)[-1]]
    out=dict(t_touch=tt, area_end=m['area_end'], mass_err=m['mass_err_max'], h_min=m['h_min_seen'], hamp_sheet_rel=m['hamp'].get('sheet_rel'),
             largest_med=round(med('largest'),3), largest_ws_med=round(med('largest_ws'),3), edges_med=med('edges'), endpoints_med=med('endpoints'), junctions_med=med('junctions'), cycles_med=med('cycles'),
             C_med=round(med('C_med'),1), C_p90=round(med('C_p90'),1), body_comps_end=post[-1]['body']['comps'], body_largest_vol=post[-1]['body']['largest_vol'],
             strahler_max=last.get('strahler',{}).get('strahler_max'), orient_frac7p5=last.get('orient',{}).get('L>=5',{}).get('frac_within7p5'),
             edge_len_frac=last.get('orient',{}).get('edge_len_frac[x,y,d+,d-]'))
    for k,v in last.items():
        if isinstance(v,dict):
            for kk,vv in v.items():
                if 'spearman' in kk and 'pos' in kk: out[kk]=vv
    return out
rows={}
for s in (1,2,3):
    for tag,pat in (('base',B),('fix',F)):
        d=pat%s
        if os.path.exists(d+'/metrics.json'): rows[(tag,s)]=load(d)
keys=list(next(iter(rows.values())).keys())
for k in keys:
    print(f'{k:22s}', ' | '.join(f"{t}{s}: {rows[(t,s)].get(k)}" for (t,s) in sorted(rows)))
