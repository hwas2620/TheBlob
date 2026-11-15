#!/usr/bin/env python3
"""[verify] 도달 시각 배열 twet.npy 에서 시각별 발자국(그때까지 한 번이라도 젖은 자리)의 윤곽 비를 낸다. usage: gfoot.py RUN_DIR ..."""
import numpy as np, sys, os, json
from scipy import ndimage as ndi
def contour(mask, cx, cy):
    ys, xs = np.nonzero(mask); ang = np.degrees(np.arctan2(ys - cy, xs - cx)) % 360; rr = np.hypot(ys - cy, xs - cx)
    R = np.zeros(360); np.maximum.at(R, np.floor(ang).astype(int) % 360, rr); return R
def sec(R, a, half=7.5):
    d = np.abs(((np.arange(360) + 0.5 - a + 180) % 360) - 180); return R[d <= half]
for rd in sys.argv[1:]:
    tw = np.load(os.path.join(rd, 'twet.npy')); P = json.load(open(os.path.join(rd, 'params.json'))); T = P['T']; out = []
    for f in (0.2, 0.4, 0.6, 0.8, 1.0):
        F = (tw >= 0) & (tw <= f * T); F = ndi.binary_fill_holes(F); ys, xs = np.nonzero(F); cy, cx = ys.mean(), xs.mean(); R = contour(F, cx, cy)
        rmax = np.mean([sec(R, a).max() for a in (45, 135, 225, 315)]) / np.mean([sec(R, a).max() for a in (0, 90, 180, 270)])
        rmean = np.mean([sec(R, a).mean() for a in (45, 135, 225, 315)]) / np.mean([sec(R, a).mean() for a in (0, 90, 180, 270)])
        ph = np.radians(np.arange(360) + 0.5); a4 = 2 * (R * np.exp(-4j * ph)).mean() / R.mean()
        out.append(f"t={f*T:.0f}: 비 {rmax:.3f}/{rmean:.3f} a4 {abs(a4):.3f}@{np.degrees(np.angle(a4)):+.0f}° R {R.mean():.0f}")
    print(f"{os.path.basename(rd.rstrip('/')):20s} " + ' | '.join(out))
