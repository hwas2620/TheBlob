#!/usr/bin/env python3
# usage: phasemap.py OUT.png run1 run2 ...  -> phase field at the end of the run (hue = theta mod 2pi relative to the oldest cells; brightness by thickness) + per-front-patch phase table
import sys, os, json, colorsys, numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); tiles = []
for nm in sys.argv[2:]:
    d = os.path.join(HERE, 'runs', nm); th = np.load(os.path.join(d, 'theta.npy')); h = np.load(os.path.join(d, 'body_native.npy')); age = np.load(os.path.join(d, 'age.npy'))
    C = np.load(os.path.join(d, 'vein_native.npy')); wet = h > 0; N = h.shape[0]
    o = np.argsort(age[wet]); ref = np.angle(np.exp(1j * th[wet][o[-max(3, o.size // 20):]]).mean())      # phase of the oldest 5%
    rel = np.where(wet, th - ref, 0.0)                                                                      # negative = lags the oldest cells
    lag = np.mod(-rel, 2 * np.pi) / (2 * np.pi)                                                             # lag in turns (mod 1)
    img = np.zeros((N, N, 3), np.uint8); img[:] = (8, 8, 8)
    ys, xs = np.nonzero(wet)
    for y, x in zip(ys, xs):
        v = 0.45 + 0.55 * min(1.0, max(h[y, x], 0.6 if C[y, x] > 4 else 0.0))
        r, g, b = colorsys.hsv_to_rgb(float(lag[y, x]), 0.9, v); img[y, x] = (int(255 * r), int(255 * g), int(255 * b))
    im = Image.fromarray(img).resize((N * 3, N * 3), Image.NEAREST); dr = ImageDraw.Draw(im)
    dr.text((6, 4), f'{nm}: phase lag behind the oldest 5% of cells (hue: red=0, green=1/3, blue=2/3 turn)', fill=(255, 255, 255)); tiles.append(im)
    # unwrapped lag statistics by age class and per active front patch
    young = wet & (age < 10); lab, nl = ndi.label(ndi.binary_dilation(young, iterations=2)); rows = []
    for i in range(1, nl + 1):
        m = young & (lab == i)
        if m.sum() < 8: continue
        z = np.exp(1j * th[m]).mean(); rows.append((int(m.sum()), round(float(np.mod(ref - np.angle(z), 2 * np.pi) / (2 * np.pi)), 2), round(float(abs(z)), 2), int(np.nonzero(m)[1].mean()), int(np.nonzero(m)[0].mean())))
    thu = th[wet]; au = age[wet]
    cls = [(a0, a1, round(float((thu[(au >= a0) & (au < a1)].mean() - thu[au >= 200].mean()) / (2 * np.pi)), 2) if ((au >= a0) & (au < a1)).any() and (au >= 200).any() else None) for a0, a1 in ((0, 10), (10, 50), (50, 100), (100, 200))]
    print(nm, '| mean unwrapped phase minus phase of age>=200 cells, in turns, by age class:', cls)
    print('    front patches (cells, lag mod 1 turn behind oldest, coherence, x, y):', sorted(rows, reverse=True)[:8])
W = sum(t.size[0] for t in tiles); im = Image.new('RGB', (W, tiles[0].size[1])); x = 0
for t in tiles: im.paste(t, (x, 0)); x += t.size[0]
im.save(sys.argv[1]); print(sys.argv[1], im.size)
