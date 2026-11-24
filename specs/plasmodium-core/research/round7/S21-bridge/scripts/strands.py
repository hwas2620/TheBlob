"""[7차 S21] 긴 외가닥 실의 정체를 잰다.
python3 strands.py RUNS_DIR TAG SEEDS(쉼표) [최소 길이=40] [시각들=600,800,...,1600]
외가닥 실 = 젖은 칸 가운데 젖은 8-이웃 ≤ 2이고 h < 0.6인 칸의 8-이웃 덩이 (S20 L1과 같은 정의).
실마다:
  끝: 실 안의 자유 끝(젖은 이웃 ≤ 1) 수
  종류: 실을 빼면 실에 닿은 몸 칸이 몇 덩이로 갈리나. 1이면 '고리'(끊어도 몸은 하나), 2 이상이면 '다리'(끊으면 몸이 갈림), 0/끝 있음이면 '꼬리'
  작은 쪽: 다리일 때 갈린 덩이 가운데 작은 쪽 부피 몫
  h, C(칸 둘레 간선 Cmean 최대), |Qmean|, Qgross 중앙값
"""
import os, sys, glob, re, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label, nb, RING, DIRS, rev
runs, tag, seeds = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')]
Lmin = int(sys.argv[4]) if len(sys.argv) > 4 else 40
TS = [int(x) for x in sys.argv[5].split(',')] if len(sys.argv) > 5 else list(range(600, 1601, 200))

def edge_max(A):
    M = np.zeros(A[0].shape)
    for k, d in enumerate(DIRS): M = np.maximum(M, np.maximum(np.abs(A[k]), np.abs(rev(A[k], d))))
    return M

rows = []
for s in seeds:
    d = os.path.join(runs, f'b_long_s{s}_{tag}')
    for t in TS:
        f = os.path.join(d, f'vs_t{t:04d}.npz')
        if not os.path.exists(f): continue
        Z = np.load(f); w = Z['wet'].astype(bool); h = np.where(w, Z['h'].astype(float), 0.0)
        nw = np.zeros(w.shape, int)
        for dd in RING: nw += nb(w, dd)
        sm = w & (nw <= 2) & (h < 0.6); lab = _torus_label(sm); sz = np.bincount(lab.ravel())
        Cm = edge_max(Z['Cmean']); Qm = edge_max(Z['Qmean']); Qg = edge_max(Z['Qgross'])
        V = h.sum()
        for k in np.nonzero(sz >= Lmin)[0]:
            if k == 0: continue
            m = lab == k; tips = int((m & (nw <= 1)).sum())
            labm = _torus_label(w & ~m); volm = np.bincount(labm.ravel(), weights=h.ravel())
            touch = set()
            for dd in RING: touch |= set(np.unique(nb(labm, dd)[m]).tolist())
            touch.discard(0); small = None
            if len(touch) >= 2: kind = '다리'; small = round(float(min(volm[j] for j in touch)) / V, 3)
            elif tips > 0: kind = '꼬리'
            else: kind = '고리'
            rows.append((s, t, int(sz[k]), kind, tips, len(touch), small, round(float(np.median(h[m])), 2), round(float(np.median(Cm[m])), 1), round(float(np.median(Qm[m])), 3), round(float(np.median(Qg[m])), 3)))
print('시드 시각 길이 종류 끝 닿은덩이 작은쪽몫 h C |Qmean| Qgross')
for r in rows: print(*r)
from collections import Counter
print('종류별 수:', Counter(r[3] for r in rows), ' 길이 ≥ 100:', Counter(r[3] for r in rows if r[2] >= 100))
