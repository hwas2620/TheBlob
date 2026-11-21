"""S4 그림: 실행이 저장한 사진(snapshot_*.png)을 줄마다 대조(vs4c) · 후보(vs4k)로 이어 붙인다. PIL 만 쓴다.
python3 fig_s4.py  →  ../fig/long_s61_s69.png, ../fig/food.png"""
import os, glob
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.abspath(os.path.join(HERE, '../../../../stage0/ref/runs')); OUT = os.path.join(HERE, '../fig'); os.makedirs(OUT, exist_ok=True)
T = 300

def row(run):
    return [Image.open(f).convert('RGB').resize((T, T), Image.LANCZOS) for f in sorted(glob.glob(os.path.join(RUNS, run, 'snapshot_*.png')))]

def montage(runs, path):
    rows = [(r, row(r)) for r in runs]; cols = max(len(x) for _, x in rows); lab = 16
    W = Image.new('RGB', (cols * T, len(rows) * (T + lab)), (0, 0, 0)); d = ImageDraw.Draw(W)
    for i, (r, ims) in enumerate(rows):
        d.text((4, i * (T + lab) + 2), r + ('  (control: model as is)' if r.endswith('vs4c') else '  (candidate: fan competition R4b)'), fill=(255, 255, 255))
        for j, im in enumerate(ims): W.paste(im, (j * T, i * (T + lab) + lab))
    W.save(path); print(path, W.size)

montage([f'b_long_s{s}_{t}' for s in (61, 69) for t in ('vs4c', 'vs4k')], os.path.join(OUT, 'long_s61_s69.png'))
montage([f'b_{x}_{t}' for x in ('food3_s61', 'food4_s61', 'mig_s63') for t in ('vs4c', 'vs4k')], os.path.join(OUT, 'food.png'))
