#!/usr/bin/env python3
# usage: montage.py OUT.png COLS name1 name2 ...   (last snapshot of each run, labelled; tile 384 px)
import sys, os, glob
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1]; cols = int(sys.argv[2]); names = sys.argv[3:]; T = int(os.environ.get("TILE", 384))
rows = (len(names) + cols - 1) // cols; im = Image.new('RGB', (cols * T, rows * T), (0, 0, 0)); dr = ImageDraw.Draw(im)
for i, n in enumerate(names):
    which = -1
    if ':' in n: n, w = n.split(':'); which = int(w)
    fs = sorted(glob.glob(os.path.join(HERE, 'runs', n, 'snapshot_*.png')))
    if not fs: continue
    t = Image.open(fs[which]).convert('RGB').resize((T, T), Image.LANCZOS); im.paste(t, ((i % cols) * T, (i // cols) * T))
    dr.text(((i % cols) * T + 4, (i // cols) * T + 4), n, fill=(255, 255, 255))
os.makedirs(os.path.dirname(out) or '.', exist_ok=True); im.save(out)
