#!/usr/bin/env python3
# usage: montage.py OUT.png run1 run2 ...   (tiles the last snapshot of each run, with labels)
import sys, os, glob
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]; names = sys.argv[2:]
which = -1
if names and names[0].startswith('--snap='): which = int(names[0].split('=')[1]) - 1; names = names[1:]
n = len(names); cols = min(n, 3 if n > 4 else (2 if n > 1 else 1)); rows = (n + cols - 1) // cols
T = 1536 // cols if cols > 1 else 1024
T = min(T, 640)
W = Image.new('RGB', (cols * T, rows * T), (0, 0, 0)); d = ImageDraw.Draw(W)
for i, nm in enumerate(names):
    fs = sorted(glob.glob(os.path.join(HERE, 'runs', nm, 'snapshot_*.png')))
    if not fs: continue
    im = Image.open(fs[which]).convert('RGB').resize((T, T), Image.LANCZOS)
    W.paste(im, ((i % cols) * T, (i // cols) * T)); d.text(((i % cols) * T + 6, (i // cols) * T + 4), nm, fill=(255, 255, 255))
W.save(out); print(out, W.size)
