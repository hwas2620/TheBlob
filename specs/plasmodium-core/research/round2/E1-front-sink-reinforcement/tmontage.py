#!/usr/bin/env python3
# usage: tmontage.py OUT.png snapA,snapB,snapC run1 run2 ...  (rows = runs, columns = snapshot indices (1-based)); crops the vertical middle band
import sys, os, glob
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1]; snaps = [int(x) for x in sys.argv[2].split(',')]; names = sys.argv[3:]
T = 1536 // len(snaps); band = 0.5
Hh = int(T * band)
W = Image.new('RGB', (T * len(snaps), Hh * len(names)), (0, 0, 0)); d = ImageDraw.Draw(W)
for i, nm in enumerate(names):
    fs = sorted(glob.glob(os.path.join(HERE, 'runs', nm, 'snapshot_*.png')), key=lambda f: int(os.path.basename(f).split('_')[1]))
    for j, s in enumerate(snaps):
        if s - 1 >= len(fs): continue
        im = Image.open(fs[s - 1]).convert('RGB'); w, h = im.size
        im = im.crop((0, int(h * (0.5 - band / 2)), w, int(h * (0.5 + band / 2)))).resize((T, Hh), Image.LANCZOS)
        W.paste(im, (j * T, i * Hh)); d.text((j * T + 6, i * Hh + 4), f'{nm}  snap {s}', fill=(255, 255, 255))
W.save(out); print(out, W.size)
