#!/usr/bin/env python3
"""주 세션의 독립 비교: 같은 시드의 직접 풀이 실행과 멀티그리드 실행이 같은 시각에 얼마나 같은 상태인가.
usage: mycmp.py EXACT_RUN MG_RUN step [step ...]   (ckpt_<step>.npz 를 전체 격자에 되돌려 비교)"""
import numpy as np, sys, os
DXY = [(1, 0), (0, 1), (1, 1), (1, -1)]

def full(run, step):
    z = np.load(os.path.join(run, f'ckpt_{step}.npz')); N = int(z['N']); y0, y1, x0, x1 = [int(v) for v in z['win']]
    wet = np.zeros((N, N), bool); C = np.zeros((4, N, N)); h = np.zeros((N, N))
    wet[y0:y1, x0:x1] = z['wet']; C[:, y0:y1, x0:x1] = z['C']; h[y0:y1, x0:x1] = z['h']
    return wet, C, h

def vein_cells(C, thr):
    N = C.shape[1]; m = np.zeros((N, N), bool)
    for k, (dx, dy) in enumerate(DXY):
        e = C[k] > thr; m |= e; ys, xs = np.nonzero(e); m[ys + dy, xs + dx] = True
    return m

def jac(a, b):
    u = (a | b).sum(); return float((a & b).sum() / u) if u else float('nan')

def dil(m, r=1):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1): out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out

ex, mg = sys.argv[1], sys.argv[2]
for s in sys.argv[3:]:
    we, Ce, he = full(ex, s); wm, Cm, hm = full(mg, s)
    row = dict(step=int(s), wet_jaccard=round(jac(we, wm), 3), wet_cells=(int(we.sum()), int(wm.sum())),
               h_corr_on_common=round(float(np.corrcoef(he[we & wm], hm[we & wm])[0, 1]), 3))
    for thr in (4, 30, 100):
        ve, vm = vein_cells(Ce, thr), vein_cells(Cm, thr)
        # 정확 일치와, 1셀 이내 어긋남을 허용한 일치(각 실행의 정맥 셀이 상대 실행의 정맥에서 1셀 안에 있는 비율)
        row[f'vein{thr}_jaccard'] = round(jac(ve, vm), 3)
        row[f'vein{thr}_within1'] = (round(float((ve & dil(vm)).sum() / max(ve.sum(), 1)), 3), round(float((vm & dil(ve)).sum() / max(vm.sum(), 1)), 3))
        row[f'vein{thr}_n'] = (int(ve.sum()), int(vm.sum()))
    both = (Ce > 0) & (Cm > 0)
    row['logC_corr_common_edges'] = round(float(np.corrcoef(np.log(Ce[both]), np.log(Cm[both]))[0, 1]), 3)
    print(row)
