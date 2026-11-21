#!/usr/bin/env python3
"""diag_crumbs.py — 탐색: long 실행마다 가장 큰 젖은 덩어리 밖의 '작은 조각'(하나가 몸 부피의 2% 미만) 부피 합의 몫과 조각 수.
t >= 1600 저장 상태 평균과 전체 최대. 그리고 이음 길이가 N(=192) 을 넘는 이음 상태의 수 (x_*.json 의 link_len)."""
import sys, os, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vextract as X
REF = '/home/user/TheBlob/specs/plasmodium-core/stage0/ref'
res = {}
for tag in ('vc', 'vnk'):
    for s in range(101, 111):
        run = f'b_long_s{s}_{tag}'; cr = []; npc = []; mid = []
        for f in sorted(glob.glob(os.path.join(REF, 'runs', run, 'vs_t*.npz'))):
            Z = np.load(f); t = float(Z['t'])
            if t < 1000: continue
            h = Z['h'].astype(float); wet = Z['wet'].astype(bool); lab = X._torus_label(wet); V = h[wet].sum(); n = int(lab.max())
            vol = np.bincount(lab.ravel(), weights=np.where(wet, h, 0).ravel(), minlength=n + 1); vol[0] = 0; big = int(np.argmax(vol))
            small = [k for k in range(1, n + 1) if k != big and vol[k] / V < 0.02]
            cr.append((t, float(vol[small].sum() / V), len(small)))
        late = [c for c in cr if c[0] >= 1600]
        x = json.load(open(os.path.join(X.V, 'data', f'x_{run}.json')))
        longlinks = sum(1 for r in x['rows'] if (r.get('link_len') or 0) > x['N'])
        res[run] = dict(crumb_late=round(float(np.mean([c[1] for c in late])), 4), crumb_max=round(max(c[1] for c in cr), 4), pieces_late=round(float(np.mean([c[2] for c in late])), 1), states_link_gt_N=longlinks)
        print(run, res[run], flush=True)
for tag in ('vc', 'vnk'):
    v = [res[f'b_long_s{s}_{tag}'] for s in range(101, 111)]
    print(tag, 'crumb_late 평균', round(np.mean([r['crumb_late'] for r in v]), 4), '중앙', round(np.median([r['crumb_late'] for r in v]), 4), 'pieces_late 중앙', np.median([r['pieces_late'] for r in v]), 'link>N 상태 합', sum(r['states_link_gt_N'] for r in v))
json.dump(res, open(os.path.join(X.V, 'data', 'diag_crumbs.json'), 'w'), indent=1)
