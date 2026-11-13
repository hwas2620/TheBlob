#!/usr/bin/env python3
# usage: cmp_edges.py runA/edges_k.npz runB/edges_k.npz  -> similarity of two conductance fields on the same edge layout
import sys, os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
a = np.load(os.path.join(HERE, 'runs', sys.argv[1]))['C'].astype(float); b = np.load(os.path.join(HERE, 'runs', sys.argv[2]))['C'].astype(float)
la = np.log10(a + 1e-6); lb = np.log10(b + 1e-6)
ta = a >= np.quantile(a, 0.9); tb = b >= np.quantile(b, 0.9)
ta2 = a >= np.quantile(a, 0.97); tb2 = b >= np.quantile(b, 0.97)
print(f'corr(log10 C) = {np.corrcoef(la, lb)[0, 1]:.3f}   top10% edge overlap (Jaccard) = {(ta & tb).sum() / (ta | tb).sum():.3f}   top3% overlap = {(ta2 & tb2).sum() / (ta2 | tb2).sum():.3f}'
      f'   Cmax {a.max():.1f} vs {b.max():.1f}   sum C {a.sum():.0f} vs {b.sum():.0f}')
