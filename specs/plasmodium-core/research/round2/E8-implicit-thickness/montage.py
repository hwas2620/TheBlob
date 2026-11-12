#!/usr/bin/env python3
"""usage: montage.py out.png file [file ...] [--cols K] [--w 320]  : labelled contact sheet"""
import sys, os
from PIL import Image, ImageDraw
args = sys.argv[1:]; cols = 4; w = 320
if '--cols' in args: i = args.index('--cols'); cols = int(args[i + 1]); del args[i:i + 2]
if '--w' in args: i = args.index('--w'); w = int(args[i + 1]); del args[i:i + 2]
out = args[0]; files = args[1:]
tiles = []
for f in files:
    im = Image.open(f).convert('RGB'); h = int(im.height * w / im.width); im = im.resize((w, h), Image.LANCZOS)
    t = Image.new('RGB', (w, h + 14), (0, 0, 0)); t.paste(im, (0, 14))
    ImageDraw.Draw(t).text((2, 1), os.path.basename(os.path.dirname(f)) + '/' + os.path.basename(f)[:14], fill=(255, 255, 255)); tiles.append(t)
rows = (len(tiles) + cols - 1) // cols; th = max(t.height for t in tiles)
M = Image.new('RGB', (cols * w, rows * th), (30, 30, 30))
for i, t in enumerate(tiles): M.paste(t, ((i % cols) * w, (i // cols) * th))
M.save(out); print(out, M.size)
