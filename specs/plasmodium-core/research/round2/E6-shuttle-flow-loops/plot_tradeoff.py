#!/usr/bin/env python3
"""plot_tradeoff.py OUT.png - loops vs stem->branch taper for the four routes to loops (static PNG, PIL only).
x = big loops (holes >= 4 cell^2 in the tube raster at width > 0.2*p99), log1p axis
y = -Spearman(tube width, distance from the DC source) over vein edges  (0 = no taper, 1 = perfect stem->branch taper)
Palette: reference categorical slots 1-4 (validated, light surface); identity is also carried by the legend and direct labels."""
import sys, os, json, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post
FAM = [
 ('DC + AC, rotating plane wave (label = AC share f)', '#2a78d6',
  [('b_f000_s1', '0'), ('b_f025_prot_s1', '.25'), ('b_f035_prot_s1', '.35'), ('b_f050_prot_s1', '.5'), ('b_f075_prot_s1', '.75'), ('b_f090_prot_s1', '.9'), ('b_f097_prot_s1', '.97'), ('a_plane_rot12_s1', '1')],
  ['b_f000_s2', 'b_f025_prot_s2', 'b_f050_prot_s2', 'b_f090_prot_s2', 'b_f097_prot_s2', 'a_plane_rot12_s2']),
 ('DC + AC, fixed radial wave (label = f)', '#eb6834',
  [('b_f025_rad_s1', '.25'), ('b_f050_rad_s1', '.5'), ('b_f075_rad_s1', '.75'), ('b_f090_rad_s1', '.9'), ('b_f097_rad_s1', '.97'), ('a_radial_s1', '1')],
  ['b_f090_rad_s2', 'b_f097_rad_s2', 'a_radial_s2']),
 ('DC only, exponent (label = gamma)', '#1baf7a',
  [('c_g100_s1', '1.0'), ('c_g105_s1', '1.05'), ('c_g110_s1', '1.1'), ('c_g120_s1', '1.2')],
  ['c_g100_s2', 'c_g105_s2', 'c_g110_s2']),
 ('DC only, fluctuating sink subset (label = p_on / corr. length)', '#eda100',
  [('c_sub_p50_l0_s1', '.5/0'), ('c_sub_p20_l0_s1', '.2/0'), ('c_sub_p05_l0_s1', '.05/0'), ('c_sub_p01_l0_s1', '.01/0'), ('c_sub_p50_l6_s1', '.5/6'), ('c_sub_p20_l6_s1', '.2/6'), ('c_sub_p05_l6_s1', '.05/6'), ('c_sub_p10_l12_s1', '.1/12')],
  ['c_sub_p20_l6_s2', 'c_sub_p05_l0_s2']),
]
W, H = 1280, 840; L, R, T, B = 90, 40, 150, 80
SURF = '#fcfcfb'; INK = '#0b0b0b'; INK2 = '#52514e'; MUTED = '#898781'; GRID = '#e1e0d9'; AXIS = '#c3c2b7'
fb = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; fbb = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F = lambda s, b=False: ImageFont.truetype(fbb if b else fb, s)
im = Image.new('RGB', (W, H), SURF); d = ImageDraw.Draw(im)
xmax = np.log1p(100); ymin, ymax = -0.05, 0.9
X = lambda v: L + (W - L - R) * np.log1p(v) / xmax
Y = lambda v: H - B - (H - T - B) * (v - ymin) / (ymax - ymin)
for v in (0, 1, 2, 5, 10, 20, 50, 100):
    d.line([X(v), T, X(v), H - B], fill=GRID, width=1); d.text((X(v), H - B + 8), str(v), fill=MUTED, font=F(14), anchor='ma')
for v in (0, 0.2, 0.4, 0.6, 0.8):
    d.line([L, Y(v), W - R, Y(v)], fill=GRID, width=1); d.text((L - 10, Y(v)), f'{v:.1f}', fill=MUTED, font=F(14), anchor='rm')
d.line([L, H - B, W - R, H - B], fill=AXIS, width=1)
d.text((L, 14), 'Loops vs. stem-to-branch taper for four routes to loops: every gain in loops costs taper', fill=INK, font=F(19, True))
d.text((L, 42), 'N=128 fixed disc, rear point source + front sink (DC) and/or shuttle wave (AC). Filled = seed 1 (joined in parameter order), ring = seed 2.', fill=INK2, font=F(13))
d.text(((L + W - R) / 2, H - 34), 'big loops in the vein network (count, log scale)', fill=INK2, font=F(15), anchor='ma')
d.text((L - 70, T - 28), 'taper = -Spearman(tube width, distance from source)', fill=INK2, font=F(13))
rows = {r['run']: r for r in post.collect(sorted({n for _, _, a, b in FAM for n in [x[0] for x in a] + b}))}
lx = L; ly = 66
for i, (lab, col, pts, s2) in enumerate(FAM):
    xx = lx + (i % 2) * 560; yy = ly + (i // 2) * 22
    d.ellipse([xx, yy + 2, xx + 12, yy + 14], fill=col); d.text((xx + 20, yy), lab, fill=INK, font=F(13))
for lab, col, pts, s2 in FAM:
    P_ = [(X(rows[n]['Lbig02']), Y(-rows[n]['taper_rho']), t) for n, t in pts if n in rows]
    if lab.startswith('DC only, fluct'): pass
    else: d.line([(a, b) for a, b, _ in P_], fill=col, width=2)
    for n in s2:
        if n in rows:
            a, b = X(rows[n]['Lbig02']), Y(-rows[n]['taper_rho']); d.ellipse([a - 6, b - 6, a + 6, b + 6], outline=col, width=2)
    for a, b, t in P_:
        d.ellipse([a - 7, b - 7, a + 7, b + 7], fill=SURF); d.ellipse([a - 5, b - 5, a + 5, b + 5], fill=col)
        d.text((a + 9, b - 16), t, fill=INK2, font=F(12))
im.save(sys.argv[1]); print(sys.argv[1], im.size)
