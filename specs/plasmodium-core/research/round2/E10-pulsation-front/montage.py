#!/usr/bin/env python3
# usage: montage.py OUT.png [--time] run1 run2 ...   (default: last snapshot of each run; --time: all snapshots of each run as a row)
import sys, os, glob
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[2:]; timemode = '--time' in args; args = [a for a in args if a != '--time']
rows = []
for nm in args:
    fs = sorted(glob.glob(os.path.join(HERE, 'runs', nm, 'snapshot_*.png')))
    if not fs: continue
    rows.append(fs if timemode else [fs[-1]])
if timemode:
    ncol = max(len(r) for r in rows); cells = rows
else:
    flat = [r[0] for r in rows]; ncol = min(4, len(flat)); cells = [flat[i:i + ncol] for i in range(0, len(flat), ncol)]
tile = min(480, 1900 // ncol)
W = ncol * tile; Hh = len(cells) * tile
im = Image.new('RGB', (W, Hh), (0, 0, 0))
for r, row in enumerate(cells):
    for c, f in enumerate(row):
        im.paste(Image.open(f).convert('RGB').resize((tile, tile), Image.LANCZOS), (c * tile, r * tile))
im.save(sys.argv[1]); print(sys.argv[1], im.size)
