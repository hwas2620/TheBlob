#!/usr/bin/env python3
"""여러 실행의 montage.png(시간 순 스냅샷 가로 배열)를 세로로 쌓아 한 장으로 만든다. 사용: stack.py OUT.png WIDTH RUN1 RUN2 ..."""
import sys, os
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
out, W = sys.argv[1], int(sys.argv[2])
ims = []
for nm in sys.argv[3:]:
    im = Image.open(os.path.join(HERE, 'runs', nm, 'montage.png'))
    h = int(im.size[1] * W / im.size[0])
    ims.append(im.resize((W, h), Image.LANCZOS))
M = Image.new('RGB', (W, sum(i.size[1] for i in ims)))
y = 0
for im in ims:
    M.paste(im, (0, y)); y += im.size[1]
M.save(out); print(out, M.size)
