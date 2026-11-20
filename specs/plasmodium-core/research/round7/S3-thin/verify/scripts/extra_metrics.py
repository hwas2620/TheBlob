#!/usr/bin/env python3
"""[S3 검증] 채점기(bmet.py)에 없는 것을 실행 폴더에서 직접 잰다. 판정에는 W4(먹은 뒤 몸 밖 부피)만 쓴다.

usage: extra_metrics.py RUN_DIR [RUN_DIR ...] --out DIR      → DIR/extra_<실행>.json

저장 시각(vs_t*.npz, 20 시간 간격)마다
  out      가장 큰 몸 성분(젖은 셀의 8연결, 부피 기준) 밖의 부피 비율 — bmet.body_out 과 같은 정의 (vmet.body_stats)
  thin     젖었고 h < h_min(0.15) 인 셀 수 (마름 차례를 기다리는 셀, grace 안의 새 셀도 섞인다)
  thin_g   그 가운데 age > grace 인 셀 수
  area     젖은 셀 수
  out_flow (탐색) 흐름이 거의 막힌 간선(thin_h 의 곱 (min(h_i,h_j)/0.15)^2 < 0.01, 곧 min h < 0.015)을 끊고 다시 잰 몸 밖 부피
실행 전체
  t_touch, t_exh, V0, V_crumb, crumb_cells, mass_err, h_min_seen, neg_end_steps, fM_end
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'stage0'))
sys.path.insert(0, os.path.join(STAGE0, 'metrics')); sys.path.insert(0, os.path.join(STAGE0, 'ref'))
import vmet


def body_out(wet, h, C, flow_cut=None):
    if not wet.any(): return 1.0
    src, dst, cc, kk = vmet.edge_list(C, wet)
    if flow_cut is not None:
        hf = h.ravel(); keep = np.minimum(np.maximum(hf[src], 0), np.maximum(hf[dst], 0)) >= flow_cut
        src, dst = src[keep], dst[keep]
    return 1.0 - vmet.body_stats(src, dst, wet, h)['body_largest_vol']


def one(rd):
    P = json.load(open(os.path.join(rd, 'params.json'))); m = json.load(open(os.path.join(rd, 'metrics.json')))
    rows = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); C = Z['C'].astype(float); age = Z['age'].astype(float)
        thin = wet & (h < P['h_min'])
        rows.append(dict(t=float(Z['t']), area=int(wet.sum()), out=round(body_out(wet, h, C), 5), out_flow=round(body_out(wet, h, C, flow_cut=0.015), 5),
                         thin=int(thin.sum()), thin_g=int((thin & (age > P['grace'])).sum()), hmin=round(float(h[wet].min()), 5) if wet.any() else None))
    return dict(run=os.path.basename(rd.rstrip('/')), rows=rows, t_touch=m.get('t_touch'), t_exh=m.get('t_exh'), V0=m.get('V0'), V_end=m.get('V_end'), Vinj=m.get('Vinj'),
                V_crumb=m.get('V_crumb'), crumb_cells=m.get('crumb_cells'), mass_err=m.get('mass_err_max'), h_min_seen=m.get('h_min_seen'), neg_end_steps=m.get('neg_end_steps'),
                neg_end_cellsteps=m.get('neg_end_cellsteps'), neg_cellsteps=m.get('neg_cellsteps'), fM_end=m.get('fM_end'), runtime=m.get('runtime'), thin_h=P.get('thin_h', 0.0))


if __name__ == '__main__':
    a = sys.argv[1:]; i = a.index('--out'); out = a[i + 1]; runs = a[:i] + a[i + 2:]; os.makedirs(out, exist_ok=True)
    for rd in runs:
        o = one(rd); json.dump(o, open(os.path.join(out, 'extra_' + o['run'] + '.json'), 'w'))
        print(o['run'], 'max out', max(r['out'] for r in o['rows']), 'max out_flow', max(r['out_flow'] for r in o['rows']))
