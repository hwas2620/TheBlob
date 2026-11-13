#!/usr/bin/env python3
"""usage: montage.py out.png cols run1 run2 ...  (last snapshot of each run; cell width 480)"""
import sys, os, glob
from PIL import Image
out = sys.argv[1]; cols = int(sys.argv[2]); runs = sys.argv[3:]; W = int(os.environ.get('CELL', 480)); ims = []
which = os.environ.get('SNAP', 'last')
for r in runs:
    fs = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runs', r, 'snapshot_*.png')))
    if not fs: ims.append(Image.new('RGB', (W, W))); continue
    f = fs[-1] if which == 'last' else fs[min(int(which), len(fs) - 1)]
    ims.append(Image.open(f).convert('RGB').resize((W, W), Image.LANCZOS))
rows = (len(ims) + cols - 1) // cols; M = Image.new('RGB', (cols * W, rows * W))
for i, im in enumerate(ims): M.paste(im, ((i % cols) * W, (i // cols) * W))
M.save(out); print(out, M.size)
