#!/usr/bin/env python3
"""[S7 독립 검증] long 실행의 저장 상태마다 지표를 잰다 (주장 1, 2a, 5).

usage: vlong.py RUN_DIR [RUN_DIR ...]      -> data/long/<실행>.json

상태마다: t, V(몸 부피), area(젖은 칸 수),
  out    = 1 - 가장 큰 젖은 덩어리 부피 / V
  piece  = 둘째로 큰 젖은 덩어리 부피 / V   (조각 하나)
  debris = 가장 큰 것 밖의 덩어리 가운데 하나하나가 0.05 V 미만인 것들의 부피 합 / V
  nbig   = 큰 두꺼운 덩어리 수 (h >= 0.3, 부피 >= 0.1 V),  conn2 = 그 가운데 둘 이상이 같은 젖은 덩어리 안에 있음
  nlobe  = 5x5 로 연 두꺼운 마스크의 큰 엽 수 (nlobe1, nlobe3: 3x3, 7x7 로 연 것. 민감도)
  nfan   = [2a′] 10 칸 이하로 떨어진 엽을 한 무리로 묶은 큰 부채 수 (CRITERIA_CHANGES.md 2)
  thin   = h < 0.3 인 젖은 칸 수, thin_vol = 그 부피 / V
10 번째 상태마다 ref_model._torus_label 과 내 scipy 그래프 라벨이 같은 나눔인지 맞춰 본다 (lab_check).
"""
import json, os, sys
import numpy as np
from vcommon import states, load, _torus_label, graph_cc, comp_vols, big_parts, lobes, fans, lobes_r, VER


def same_partition(a, b):
    m = (a > 0) | (b > 0)
    if not np.array_equal(a > 0, b > 0): return False
    pa = a[m]; pb = b[m]
    # 같은 나눔 = 라벨 쌍이 일대일
    pairs = np.unique(np.stack([pa, pb]), axis=1)
    return len(np.unique(pairs[0])) == pairs.shape[1] == len(np.unique(pairs[1]))


def measure(rd):
    rows = []; chk = []
    for i, (t, f) in enumerate(states(rd)):
        S = load(f); wet, h = S['wet'], S['h']; V = float(h.sum())
        lw = _torus_label(wet); vw = np.sort(comp_vols(lw, h)[1:])[::-1]
        if i % 10 == 0: chk.append(bool(same_partition(lw, graph_cc(wet))))
        lt, big, vb = big_parts(wet, h, V)
        conn2 = False
        if len(big) >= 2:
            owner = [np.bincount(lw[lt == k]).argmax() for k in big]
            conn2 = len(set(owner)) < len(owner)
        thin = wet & (h < 0.3)
        rows.append(dict(t=t, V=V, area=int(wet.sum()), ncomp=int(vw.size),
                         out=float(1 - vw[0] / V) if vw.size else 1.0, piece=float(vw[1] / V) if vw.size > 1 else 0.0,
                         debris=float(vw[1:][vw[1:] < 0.05 * V].sum() / V) if vw.size > 1 else 0.0,
                         nbig=len(big), big_frac=[round(v / V, 4) for v in vb], conn2=bool(conn2), nlobe=lobes(wet, h, V), nfan=fans(wet, h, V), nlobe1=lobes_r(wet, h, V, 1), nlobe3=lobes_r(wet, h, V, 3),
                         thin=int(thin.sum()), thin_vol=float(h[thin].sum() / V)))
    return dict(run=os.path.basename(rd.rstrip('/')), rows=rows, lab_check=chk)


if __name__ == '__main__':
    od = os.path.join(VER, 'data', 'long'); os.makedirs(od, exist_ok=True)
    for rd in sys.argv[1:]:
        o = measure(rd); json.dump(o, open(os.path.join(od, o['run'] + '.json'), 'w'))
        r = [x for x in o['rows'] if x['t'] >= 100]
        print(o['run'], 'states', len(o['rows']), 'split', round(np.mean([x['out'] >= 0.1 for x in r]), 3), 'piece_max', round(max(x['piece'] for x in r), 3),
              'nbig2', round(np.mean([x['nbig'] >= 2 for x in r]), 3), 'lobe2', round(np.mean([x['nlobe'] >= 2 for x in r]), 3), 'lab_check', all(o['lab_check']), flush=True)
