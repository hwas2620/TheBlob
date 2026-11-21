"""젖은 몸만 그린다(저장 상태 vs_t*.npz). 마른 곳 검정, 얇은 몸(h<0.3) 어두운 파랑, 두꺼운 몸은 두께에 따라 노랑→주황, 굵은 관(C>50)은 흰색.
python3 montage.py OUT.png RUN T1 T2 ... [-- RUN2 ...]  (줄마다 실행 하나)"""
import os, sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref'))
from ref_model import _torus_label
RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref/runs'))
out = sys.argv[1]; rest = sys.argv[2:]; groups = []; cur = []
for a in rest:
    if a == '--': groups.append(cur); cur = []
    else: cur.append(a)
groups.append(cur); S = 2; lab = 14; rows = []
for g in groups:
    run, ts = g[0], [int(float(x)) for x in g[1:]]; ims = []
    for t in ts:
        Z = np.load(os.path.join(RUNS, run, f'vs_t{t:04d}.npz')); wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); C = Z['C'].astype(float).max(0)
        img = np.zeros(h.shape + (3,), np.uint8)
        thin = wet & (h < 0.3); thick = wet & (h >= 0.3); x = np.clip((h - 0.3) / 0.9, 0, 1)
        img[thin] = (30, 50, 110); img[thick] = np.stack([235 + 0 * x, 200 - 110 * x, 60 - 40 * x], -1)[thick].astype(np.uint8)
        img[wet & (C > 50)] = (255, 255, 255)
        lw = _torus_label(wet); v = np.bincount(lw.ravel(), weights=h.ravel()); v[0] = 0; outf = 1 - v.max() / h.sum()
        lt = _torus_label(thick); vt = np.bincount(lt.ravel(), weights=h.ravel()); vt[0] = 0; nb = int((vt >= 0.1 * h.sum()).sum())
        im = Image.fromarray(img).resize((h.shape[1] * S, h.shape[0] * S), Image.NEAREST); d = ImageDraw.Draw(im)
        d.text((3, 2), f't={t} out={outf:.2f} big={nb}', fill=(255, 255, 255)); ims.append(im)
    rows.append((run, ims))
W_ = max(len(x) for _, x in rows) * (192 * S + 4); H_ = len(rows) * (192 * S + lab)
M = Image.new('RGB', (W_, H_), (60, 60, 60)); d = ImageDraw.Draw(M)
for i, (run, ims) in enumerate(rows):
    d.text((4, i * (192 * S + lab) + 1), run, fill=(255, 255, 255))
    for j, im in enumerate(ims): M.paste(im, (j * (192 * S + 4), i * (192 * S + lab) + lab))
M.save(out); print(out, M.size)
