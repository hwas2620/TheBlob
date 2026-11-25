#!/usr/bin/env python3
"""v7extra (보충 외가닥 사슬) 시험: 가짜 상태만"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v7extra as X
N = 192; yy, xx = np.mgrid[0:N, 0:N]
def disc(cx, cy, r): return np.hypot((xx - cx + N / 2) % N - N / 2, (yy - cy + N / 2) % N - N / 2) <= r
def line(m, x0, y0, x1, y1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n): m[int(round(y0 + (y1 - y0) * i / (n - 1))) % N, int(round(x0 + (x1 - x0) * i / (n - 1))) % N] = True
    return m
fails = 0
def check(nm, c, info):
    global fails; print(('ok   ' if c else 'FAIL ') + nm, info); fails += (not c)
w = line(disc(40, 96, 15), 55, 96, 105, 96); f = X.frame_chains(w, np.where(w, 1.0, 0))
check('tail 50', 45 <= f['chain_tail_max'] <= 55 and f['n_tail30c'] == 1, f)
w = line(disc(40, 96, 15) | disc(140, 96, 15), 55, 96, 125, 96); f = X.frame_chains(w, np.where(w, 1.0, 0))
check('trunk 70 between two cores', 60 <= f['chain_trunk_max'] <= 75 and f['chain_max'] < 10, f)
# 몸 뒤 그물 (간격 10 격자, 60x60) 은 긴 사슬이 없다
w = disc(40, 96, 15)
for k in range(0, 61, 10): line(w, 55 + k, 66, 55 + k, 126); line(w, 55, 66 + k, 115, 66 + k)
line(w, 50, 66, 55, 66); line(w, 50, 126, 55, 126)
f = X.frame_chains(w, np.where(w, 1.0, 0)); check('mesh: no chain > 30', f['chain_max'] <= 30 and f['n_chain100'] == 0, f)
# 그물 끝에서 120 칸 실 + 작은 덩이
line(w, 115, 96, 175, 96); line(w, 175, 96, 175, 156); w |= disc(175, 160, 3)
f = X.frame_chains(w, np.where(w, 1.0, 0)); check('long thread with blob off a mesh: chain > 100', f['n_chain100'] >= 1 and f['chain_max'] > 100, f)
# 고리 > 100
w = disc(60, 96, 12)
line(w, 72, 92, 150, 92); line(w, 150, 92, 150, 100); line(w, 150, 100, 72, 100)
f = X.frame_chains(w, np.where(w, 1.0, 0)); check('loop: chain > 100, link', f['n_chain100'] == 1 and f['chain100_kinds'] == ['link'], f)
# 나무꼴 외가닥
w = line(disc(40, 96, 15), 55, 96, 105, 96); f = X.frame_trees(w, np.where(w, 1.0, 0)); check('tree: tail 50', 45 <= f['tree_max'] <= 56 and f['n_tree30'] == 1, f)
w = disc(40, 96, 15)
for k in range(0, 61, 10): line(w, 55 + k, 66, 55 + k, 126); line(w, 55, 66 + k, 115, 66 + k)
line(w, 50, 66, 55, 66); line(w, 50, 126, 55, 126)
f = X.frame_trees(w, np.where(w, 1.0, 0)); check('tree: mesh has no long strand', f['tree_max'] < 30, f)
line(w, 115, 96, 175, 96); line(w, 175, 96, 175, 156); w |= disc(175, 160, 3); line(w, 150, 96, 150, 76)
f = X.frame_trees(w, np.where(w, 1.0, 0)); check('tree: 120 thread off a mesh with a side branch -> > 100', f['n_tree100'] == 1, f)
w = disc(60, 96, 12); line(w, 72, 92, 150, 92); line(w, 150, 92, 150, 100); line(w, 150, 100, 72, 100)
f = X.frame_trees(w, np.where(w, 1.0, 0)); check('tree: loop > 100', f['n_tree100'] == 1, f)
w = line(disc(40, 96, 15) | disc(140, 96, 15), 55, 96, 125, 96); f = X.frame_trees(w, np.where(w, 1.0, 0)); check('tree: trunk excluded', f['tree_max'] < 10 and f['tree_trunk_max'] > 60, f)
w = line(disc(40, 96, 15), 55, 96, 125, 96); f = X.frame_trees(w, np.where(w, 1.0, 0)); check('reach of a 70 tail from a disc ~ 70 (torus 192)', 68 <= f['reach'] <= 72, f['reach'])
print('FAILURES', fails); sys.exit(1 if fails else 0)
