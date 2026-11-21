#!/usr/bin/env python3
"""diag_diverge.py — 확인용: long 쌍마다 대조와 후보의 저장 상태(h, C)가 처음 달라지는 시각과, 후보에서 이음이 처음 보인 저장 시각(다시 찾은 neck).
규칙이 작동하기 전에는 두 실행이 비트 단위로 같아야 한다."""
import os, json, glob
import numpy as np
V = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S6-neck-mg3/verify'; REF = '/home/user/TheBlob/specs/plasmodium-core/stage0/ref/runs'
for s in range(101, 111):
    a = f'{REF}/b_long_s{s}_vc'; b = f'{REF}/b_long_s{s}_vnk'; first = None
    for f in sorted(glob.glob(a + '/vs_t*.npz')):
        g = f.replace(a, b); Za = np.load(f); Zb = np.load(g)
        if not (np.array_equal(Za['h'], Zb['h']) and np.array_equal(Za['C'], Zb['C'])): first = float(Za['t']); break
    x = json.load(open(f'{V}/data/x_b_long_s{s}_vnk.json'))
    fn = next((r['t'] for r in x['rows'] if r.get('n_neck', 0) > 0), None)
    print(f's{s}: 처음 달라진 저장 시각 {first}, 후보에서 이음이 처음 보인 저장 시각 {fn}')
