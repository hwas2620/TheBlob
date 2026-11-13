#!/usr/bin/env python3
"""runs/<pattern>/curve.json 의 분기점·고리 시간 곡선을 표로 출력하고(가능하면) PNG 로 그린다.
사용: python3 curves.py OUT.png RUN1 RUN2 ...   (판정 규칙은 summarize.py 와 같음: t>=T/2 의 d lnBP/d ln t)"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]; names = sys.argv[2:]
data = {}
for nm in names:
    C = json.load(open(os.path.join(HERE, 'runs', nm, 'curve.json')))['curve']
    t = np.array([m['t'] for m in C]); bp = np.array([m.get('branch_points', 0) for m in C]); lp = np.array([m.get('loops', 0) for m in C])
    w = np.array([m.get('width_p50', 0) or 0 for m in C]); mv = np.array([m.get('moved_frac', 0) for m in C])
    data[nm] = (t, bp, lp, w, mv)
    T = t[-1]
    def slope(lo, hi):
        k = (t >= lo) & (t <= hi) & (bp > 0)
        return float(np.polyfit(np.log(t[k]), np.log(bp[k]), 1)[0]) if k.sum() >= 3 else float('nan')
    def at(tt):
        return int(bp[np.argmin(np.abs(t - tt))]), int(lp[np.argmin(np.abs(t - tt))])
    q = [at(x) for x in (500, 2000, 8000, T / 2, T)]
    late = bp[t >= T / 2]
    print(f"{nm:30s} T={T} BP/loops @500={q[0]} @2k={q[1]} @8k={q[2]} @T/2={q[3]} @T={q[4]} | slope[T/8,T/2]={slope(T/8, T/2):+.2f} "
          f"slope[T/2,T]={slope(T/2, T):+.2f} | late BP mean={late.mean():.1f} sd={late.std():.1f} min={late.min()} max={late.max()} | w50_end={w[-1]} moved_end={mv[-1]}")
from PIL import Image, ImageDraw
W, H, L, B = 980, 520, 60, 40
im = Image.new('RGB', (W, H), (255, 255, 255)); d = ImageDraw.Draw(im)
tmin = min(v[0].min() for v in data.values()); tmax = max(v[0].max() for v in data.values())
ymin, ymax = 0.8, max(max(v[1].max() for v in data.values()), 10) * 1.3
def X(t): return L + (np.log(t) - np.log(tmin)) / (np.log(tmax) - np.log(tmin)) * (W - L - 250)
def Y(b): return H - B - (np.log(max(b, ymin)) - np.log(ymin)) / (np.log(ymax) - np.log(ymin)) * (H - B - 20)
for yv in (1, 2, 5, 8, 10, 20, 50, 100, 200, 500):
    if yv <= ymax:
        d.line([(L, Y(yv)), (W - 250, Y(yv))], fill=(225, 225, 225) if yv != 8 else (255, 150, 150)); d.text((8, Y(yv) - 6), str(yv), fill=(0, 0, 0))
for tv in (200, 500, 1000, 2000, 5000, 10000, 20000, 50000):
    if tmin <= tv <= tmax:
        d.line([(X(tv), 20), (X(tv), H - B)], fill=(225, 225, 225)); d.text((X(tv) - 12, H - B + 6), str(tv), fill=(0, 0, 0))
cols = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194), (90, 90, 90), (188, 189, 34), (23, 190, 207)]
for k, (nm, (t, bp, lp, w, mv)) in enumerate(data.items()):
    c = cols[k % len(cols)]
    pts = [(X(a), Y(b)) for a, b in zip(t, bp)]
    d.line(pts, fill=c, width=2)
    for p in pts: d.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], fill=c)
    d.text((W - 240, 24 + 16 * k), nm[:38], fill=c)
d.text((L, 4), 'branch points vs step (log-log); red line = 8', fill=(0, 0, 0))
im.save(out); print('saved', out)
