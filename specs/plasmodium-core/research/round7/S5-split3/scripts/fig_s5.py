"""S5 그림: 실행이 저장한 사진(snapshot_*.png)을 줄마다 이어 붙인다. python3 fig_s5.py OUT.png RUN [RUN ...]"""
import os, sys, glob
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.abspath(os.path.join(HERE, '../../../../stage0/ref/runs')); T = 260
out = sys.argv[1]; runs = sys.argv[2:]; rows = []
for r in runs:
    rows.append((r, [Image.open(f).convert('RGB').resize((T, T), Image.LANCZOS) for f in sorted(glob.glob(os.path.join(RUNS, r, 'snapshot_*.png')))]))
cols = max(len(x) for _, x in rows); lab = 14
W = Image.new('RGB', (cols * T, len(rows) * (T + lab)), (0, 0, 0)); d = ImageDraw.Draw(W)
for i, (r, ims) in enumerate(rows):
    d.text((4, i * (T + lab) + 1), r, fill=(255, 255, 255))
    for j, im in enumerate(ims): W.paste(im, (j * T, i * (T + lab) + lab))
W.save(out); print(out, W.size)
