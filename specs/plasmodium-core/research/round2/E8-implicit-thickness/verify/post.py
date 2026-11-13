#!/usr/bin/env python3
"""time-resolved scoring of state_snap*.npz (same tube rendering as e8.py) + graph stats; also torus-wrap check"""
import sys, os, json, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import reeval, graphstats
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))
def render(C, act, h, rs_=3, Cmin=0.02, shift=(0, 0)):
    if shift != (0, 0):
        C = [np.roll(c, shift, (0, 1)) for c in C]; act = np.roll(act, shift, (0, 1)); h = np.roll(h, shift, (0, 1))
    N = act.shape[0]; body = np.where(act, h, 0).astype(np.float32)
    imv = Image.new('F', (N * rs_, N * rs_), 0.0); drv = ImageDraw.Draw(imv); segs = []
    for k, d in enumerate(DIRS):
        E = act & nb(act, d) & (C[k] > 1.5 * Cmin); ys, xs = np.nonzero(E)
        ok = (xs + d[0] >= 0) & (xs + d[0] < N) & (ys + d[1] >= 0) & (ys + d[1] < N)
        for e, x_, y_ in zip(C[k][ys[ok], xs[ok]], xs[ok], ys[ok]): segs.append((float(e), int(x_), int(y_), d[0], d[1]))
    segs.sort()
    for e, x_, y_, dx, dy in segs:
        wd = 0.7 * e ** 0.25
        drv.line([((x_ + .5) * rs_, (y_ + .5) * rs_), ((x_ + dx + .5) * rs_, (y_ + dy + .5) * rs_)], fill=float(wd), width=max(1, int(round(wd * rs_))))
    body_r = np.kron(body, np.ones((rs_, rs_), np.float32))
    return body_r, (np.asarray(imv) * (body_r > 0)).astype(np.float32)
if __name__ == '__main__':
    shift = (0, 0)
    args = sys.argv[1:]
    if '--shift' in args: i = args.index('--shift'); shift = (int(args[i + 1]), int(args[i + 2])); del args[i:i + 3]
    for f in args:
        z = np.load(f); C = [c.astype(float) for c in z['C']]; act = z['act']; h = z['h'].astype(float)
        b, v = render(C, act, h, shift=shift); o = reeval.score(b, v)
        g = graphstats.stats(np.array(C), act, h, thr_list=(15, 100))
        print('==', '/'.join(f.split('/')[-2:]), 'shift', shift)
        for r in o: print('  rendered rel', r, {k: o[r][k] for k in ('BP', 'loops', 'va', 'vl', 'ncomp', 'wr', 'sr', 'bcomp', 'blf', 'all3')})
        print('  graph', {k: g[k] for k in ('n_act', 'thr15', 'thr100', 'act_cols_x0_x127', 'act_rows_y0_y127', 'h_max', 'mass_outside_act_frac')})
