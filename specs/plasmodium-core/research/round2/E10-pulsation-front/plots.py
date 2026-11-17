#!/usr/bin/env python3
"""E10 small PIL plots (no matplotlib here).
usage: plots.py OUT.png step  run1 run2 ...   -> per run: new wet cells per step (bars) and wet area (line) over the last 12 periods, period ticks, cos(w t) trace
       plots.py OUT.png lock  run1 run2 ...   -> per run: histogram of wetting events vs local phase of the donor cell (24 bins)
       plots.py OUT.png cut   run1 run2 ...   -> per run: tip position along the travel direction and new-wet rate (1-period mean) after the amputation
       plots.py OUT.png hamp  run1 run2 ...   -> stack of the hamp.png maps
"""
import sys, os, json, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1100, 190


def frame(title):
    im = Image.new('RGB', (W, H), (255, 255, 255)); dr = ImageDraw.Draw(im)
    dr.rectangle([50, 22, W - 12, H - 22], outline=(0, 0, 0)); dr.text((52, 5), title, fill=(0, 0, 0))
    return im, dr


def px(x, x0, x1): return 50 + (W - 62) * (x - x0) / max(x1 - x0, 1e-9)
def py(y, y0, y1): return (H - 22) - (H - 44) * (y - y0) / max(y1 - y0, 1e-9)


def load(nm):
    d = os.path.join(HERE, 'runs', nm)
    return d, json.load(open(os.path.join(d, 'params.json'))), json.load(open(os.path.join(d, 'metrics.json')))


out, kind, runs = sys.argv[1], sys.argv[2], sys.argv[3:]
tiles = []
for nm in runs:
    d, P, m = load(nm)
    if kind == 'hamp':
        tiles.append(Image.open(os.path.join(d, 'hamp.png')).convert('RGB').resize((W, W // 2), Image.LANCZOS)); continue
    if kind == 'lock':
        hst = np.array(m.get('lock', {}).get('hist', [0] * 24), float); lk = m.get('lock', {})
        im, dr = frame(f'{nm}: wetting events vs donor phase theta (0..360 deg; h* max at 0)  n={lk.get("n")} R={lk.get("R")} mean phase={lk.get("phase_deg")}  mod index={m.get("new_mod_index")}')
        mx = max(hst.max(), 1)
        for i, v in enumerate(hst):
            dr.rectangle([px(i, 0, 24) + 1, py(v, 0, mx), px(i + 1, 0, 24) - 1, py(0, 0, mx)], fill=(60, 110, 200))
        for i in range(0, 25, 6): dr.text((px(i, 0, 24) - 8, H - 20), str(i * 15), fill=(0, 0, 0))
        dr.text((4, 22), str(int(mx)), fill=(0, 0, 0)); tiles.append(im); continue
    S = np.load(os.path.join(d, 'series.npz')); dt = float(S['dt']); new = S['new'].astype(float); area = S['area'].astype(float); n = new.size
    nper = int(round(P['period'] / dt))
    if kind == 'step':
        i1 = n; i0 = max(0, n - 12 * nper); tt = np.arange(i0, i1) * dt
        im, dr = frame(f'{nm}: new wet cells per step (bars), wet area (red, {area[i0]:.0f}..{area[i0:i1].max():.0f}), cos(wt) (grey); ticks = periods ({P["period"]})  mode={P["phase_mode"]} eps={P["eps"]}')
        mx = max(new[i0:i1].max(), 1)
        for i in range(i0, i1):
            if new[i] > 0: dr.line([px(i * dt, tt[0], tt[-1]), py(new[i], 0, mx), px(i * dt, tt[0], tt[-1]), py(0, 0, mx)], fill=(60, 110, 200), width=2)
        a0, a1 = area[i0:i1].min(), area[i0:i1].max()
        dr.line([(px(t_, tt[0], tt[-1]), py(a, a0, a1)) for t_, a in zip(tt, area[i0:i1])], fill=(210, 40, 40), width=2)
        w = 2 * np.pi / P['period']
        dr.line([(px(t_, tt[0], tt[-1]), py(np.cos(w * t_), -1.2, 6)) for t_ in tt], fill=(140, 140, 140), width=1)
        for k in range(int(np.ceil(tt[0] / P['period'])), int(tt[-1] / P['period']) + 1):
            x = px(k * P['period'], tt[0], tt[-1]); dr.line([x, H - 22, x, H - 16], fill=(0, 0, 0)); dr.text((x - 10, H - 16), f'{k * P["period"]:.0f}', fill=(0, 0, 0))
        dr.text((4, 22), str(int(mx)), fill=(60, 110, 200)); tiles.append(im)
    if kind == 'cut':
        tip = S['tip']; ct = m.get('cut', {}).get('t', 0); ic = int(round(ct / dt)); i0 = max(0, ic - 10 * nper)
        tt = np.arange(i0, n) * dt
        rate = np.convolve(new, np.ones(nper) / (nper * dt), mode='same')
        im, dr = frame(f'{nm}: cut at t={ct} (line). black = sheet tip position along travel dir after the cut, blue = new wet cells per unit time (1-period mean); ticks every 5 periods')
        mx = max(rate[i0:].max(), 1e-6)
        dr.line([(px(t_, tt[0], tt[-1]), py(r_, 0, mx)) for t_, r_ in zip(tt, rate[i0:])], fill=(60, 110, 200), width=2)
        ok = np.isfinite(tip)
        if ok.any():
            t0_, t1_ = np.nanmin(tip), np.nanmax(tip)
            dr.line([(px(i * dt, tt[0], tt[-1]), py(tip[i], t0_, t1_ + 1e-6)) for i in range(i0, n) if ok[i]], fill=(0, 0, 0), width=2)
            dr.text((W - 260, 24), f'tip {t0_:.1f} .. {t1_:.1f} cells', fill=(0, 0, 0))
        x = px(ct, tt[0], tt[-1]); dr.line([x, 22, x, H - 22], fill=(210, 40, 40), width=2)
        k = 0
        while ct + k * 5 * P['period'] <= tt[-1]:
            x = px(ct + k * 5 * P['period'], tt[0], tt[-1]); dr.line([x, H - 22, x, H - 14], fill=(0, 0, 0)); dr.text((x - 6, H - 14), str(5 * k), fill=(0, 0, 0)); k += 1
        dr.text((4, 22), f'{mx:.1f}', fill=(60, 110, 200)); tiles.append(im)
im = Image.new('RGB', (W, sum(t.size[1] for t in tiles)), (255, 255, 255)); y = 0
for t in tiles: im.paste(t, (0, y)); y += t.size[1]
im.save(out); print(out, im.size)
