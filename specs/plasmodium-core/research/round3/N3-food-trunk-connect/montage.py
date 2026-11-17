#!/usr/bin/env python3
"""usage: montage.py OUT.png [--time RUN | RUN1 RUN2 ...] [--cols K] [--cell PX]   (final snapshots of several runs, or all snapshots of one run)"""
import sys, os, glob
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]; outp = a.pop(0); cols = 4; cell = 480
if '--cols' in a: i = a.index('--cols'); cols = int(a[i + 1]); del a[i:i + 2]
if '--cell' in a: i = a.index('--cell'); cell = int(a[i + 1]); del a[i:i + 2]
snap = lambda r: sorted(glob.glob(os.path.join(HERE, 'runs', r, 'snapshot_*.png')), key=lambda f: int(os.path.basename(f).split('_')[1]))
if a[0] == '--time': fs = snap(a[1])
else: fs = [snap(r.split('@')[0])[int(r.split('@')[1]) if '@' in r else -1] for r in a]
rows = (len(fs) + cols - 1) // cols
im = Image.new('RGB', (cell * min(cols, len(fs)), cell * rows))
for i, f in enumerate(fs): im.paste(Image.open(f).resize((cell, cell), Image.LANCZOS), ((i % cols) * cell, (i // cols) * cell))
im.save(outp); print(outp, im.size, len(fs))
