#!/usr/bin/env python3
# usage: montage.py OUT.png [--snap=K] [--cols=C] [--tile=T] run1 run2 ...   (tiles one snapshot of each run, default the last, with labels)
import sys, os, glob, json
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]; names = sys.argv[2:]
which = -1; cols = None; T = None
while names and names[0].startswith('--'):
    k, v = names[0][2:].split('='); names = names[1:]
    if k == 'snap': which = int(v) - 1
    if k == 'cols': cols = int(v)
    if k == 'tile': T = int(v)
n = len(names)
if cols is None: cols = min(n, 4 if n > 6 else (3 if n > 4 else (2 if n > 1 else 1)))
rows = (n + cols - 1) // cols
if T is None: T = min(1600 // cols, 520)
W = Image.new('RGB', (cols * T, rows * T), (0, 0, 0)); d = ImageDraw.Draw(W)
for i, nm in enumerate(names):
    snap = which
    if ':' in nm: nm, s = nm.split(':'); snap = int(s) - 1
    fs = sorted(glob.glob(os.path.join(HERE, 'runs', nm, 'snapshot_*.png')))
    if not fs: continue
    im = Image.open(fs[snap]).convert('RGB').resize((T, T), Image.LANCZOS)
    x0, y0 = (i % cols) * T, (i // cols) * T
    W.paste(im, (x0, y0)); lab = nm + ('' if snap == -1 else f' [snap {snap + 1}]')
    try:
        m = json.load(open(os.path.join(HERE, 'runs', nm, 'metrics.json'))); e = m.get('eval_primary', {}); o = m['log'][snap]['own']
        lab2 = f"bp{e.get('branch_points')} wr{e.get('width_ratio_p90_p10')} sr{e.get('strength_ratio_p90_p10')} L.2={o['r0.2'].get('loops_big')} L.35={o['r0.35'].get('loops_big')}"
    except Exception: lab2 = ''
    d.rectangle([x0, y0, x0 + T, y0 + 26], fill=(0, 0, 0)); d.text((x0 + 4, y0 + 2), lab, fill=(255, 255, 255)); d.text((x0 + 4, y0 + 14), lab2, fill=(160, 255, 160))
W.save(out); print(out, W.size)
