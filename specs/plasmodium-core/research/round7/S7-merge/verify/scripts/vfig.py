#!/usr/bin/env python3
"""[S7 독립 검증] 그림 (PIL 만).

usage:
  vfig.py montage SCN SEED T1,T2,...  [--tags v7c,v7k] [--out NAME]   대조(위)·후보(아래) 몸 그림
  vfig.py episode TAG SEED T0 [DT ...]                                 에피소드: 몫(진 쪽 빨강, 이긴 쪽 초록)과 두께
  vfig.py series TAG SEED                                              진단 실행(4 시간 간격)의 몫별 부피·넓이·얇은 몫 시간 변화
색: 마름 = 검정, 두꺼운 칸(h >= 0.3) = 노랑→주황(두꺼울수록 밝음), 얇은 칸(h < 0.3) = 파랑, 가장 큰 젖은 덩어리 밖 = 분홍 테두리 없이 분홍빛
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from vcommon import states, load, _torus_label, comp_vols, big_parts, partition, rundir, VER, TH

FIG = os.path.join(VER, 'fig')


def centre_shift(h):
    """몸(h 가중)의 토러스 원형 평균이 그림 가운데로 오게 하는 이동량 (dy, dx)"""
    N = h.shape[0]; a = 2 * np.pi * np.arange(N) / N; w = h.sum()
    if w <= 0: return (0, 0)
    my = np.angle((h.sum(1) * np.exp(1j * a)).sum()) % (2 * np.pi) * N / (2 * np.pi); mx = np.angle((h.sum(0) * np.exp(1j * a)).sum()) % (2 * np.pi) * N / (2 * np.pi)
    return (int(round(N / 2 - my)), int(round(N / 2 - mx)))


def body_rgb(wet, h, scale=2, shift=None, extra=None):
    """extra: (마스크, 색, 섞는 비율) 목록. shift: (dy, dx), None 이면 몸 가운데로"""
    N = wet.shape[0]; img = np.zeros((N, N, 3), np.float32)
    b = np.clip(h / 1.2, 0, 1)
    thick = wet & (h >= TH); thin = wet & (h < TH)
    img[thick] = (np.array([120, 90, 10]) * (1 - b[thick, None]) + np.array([255, 220, 60]) * b[thick, None])
    img[thin] = np.array([40, 90, 230]) * (0.5 + 0.5 * np.clip(h[thin] / TH, 0, 1))[:, None]
    lw = _torus_label(wet); v = comp_vols(lw, h)
    if v.size > 1:
        main = int(np.argmax(v)); off = wet & (lw != main)
        img[off] = np.array([255, 80, 200])
    for m, col, a in (extra or []): img[m] = (1 - a) * img[m] + a * np.array(col, np.float32)
    sh = centre_shift(h) if shift is None else shift
    img = np.roll(img, sh, (0, 1))
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((N * scale, N * scale), Image.NEAREST)
    return im


def montage(scn, seed, times, tags=('v7c', 'v7k'), out=None):
    ims = []
    for tag in tags:
        rd = rundir(scn, seed, tag); row = []
        for t in times:
            f = os.path.join(rd, f'vs_t{t:04d}.npz')
            if not os.path.exists(f): row.append(None); continue
            S = load(f); sh = centre_shift(S['h']) if scn == 'long' or scn == 'mig' else (0, 0); im = body_rgb(S['wet'], S['h'], shift=sh); d = ImageDraw.Draw(im)
            P_ = json.load(open(os.path.join(rd, 'params.json')))
            if P_.get('reservoir'):
                N_ = P_['N']; c0_ = N_ / 2 - 0.5; sc_ = im.size[0] / N_
                for k_, (a_, d0_) in enumerate(P_['foods']):
                    fx = (c0_ + d0_ * np.cos(np.radians(a_)) + sh[1]) % N_; fy = (c0_ + d0_ * np.sin(np.radians(a_)) + sh[0]) % N_; r_ = P_['food_r'] * sc_
                    d.ellipse([fx * sc_ - r_, fy * sc_ - r_, fx * sc_ + r_, fy * sc_ + r_], outline=(0, 255, 255), width=2); d.text((fx * sc_ + r_, fy * sc_), str(k_), fill=(0, 255, 255))
            V = S['h'].sum(); lt, big, vb = big_parts(S['wet'], S['h'], V)
            d.text((4, 2), f'{tag} s{seed} t={t} big={len(big)} thin={int((S["wet"] & (S["h"] < TH)).sum())}', fill=(255, 255, 255))
            row.append(im)
        ims.append(row)
    W = max(im.size[0] for row in ims for im in row if im); H = max(im.size[1] for row in ims for im in row if im)
    canvas = Image.new('RGB', (W * len(times) + 4 * (len(times) - 1), H * len(tags) + 4 * (len(tags) - 1)), (90, 90, 90))
    for i, row in enumerate(ims):
        for j, im in enumerate(row):
            if im: canvas.paste(im, (j * (W + 4), i * (H + 4)))
    os.makedirs(FIG, exist_ok=True)
    p = os.path.join(FIG, out or f'montage_{scn}_s{seed}.png'); canvas.save(p); print(p)


def episode_fig(tag, seed, t0, dts=(0, 20, 40, 60, 100)):
    import vfate
    rd = rundir('long', seed, tag); S0 = load(os.path.join(rd, f'vs_t{t0:04d}.npz'), ('wet', 'h', 'age'))
    cp = vfate.conn_parts(S0)
    if cp is None: print('이어진 두 덩어리 상태가 아님'); return
    lw0, seeds0, n = cp; reg0 = partition(S0['wet'], seeds0)
    e = vfate.episode(S0, load(os.path.join(rd, f'vs_t{t0 + 60:04d}.npz'), ('wet', 'h', 'age')), 60, None) if os.path.exists(os.path.join(rd, f'vs_t{t0 + 60:04d}.npz')) else None
    L = e['L'] + 1 if e else 1
    sh0 = centre_shift(S0['h'])
    row = []
    for dT in dts:
        f = os.path.join(rd, f'vs_t{t0 + dT:04d}.npz')
        if not os.path.exists(f): continue
        S = load(f, ('wet', 'h', 'age')); wet, h = S['wet'], S['h']
        if dT == 0: reg = reg0
        else:
            orig = S0['wet'] & wet & (S['age'] >= dT - 0.5); reg = partition(wet, np.where(orig, reg0, 0))
        img = body_rgb(wet, h, 2, shift=sh0, extra=[(reg == L, (255, 40, 40), 0.45), ((reg > 0) & (reg != L), (40, 255, 40), 0.45)])
        d = ImageDraw.Draw(img)
        VL = float(h[reg == L].sum()); AL = int((reg == L).sum()); VW = float(h[(reg > 0) & (reg != L)].sum())
        d.text((4, 2), f'{tag} s{seed} t={t0 + dT}  loser V={VL:.0f} A={AL}  winner V={VW:.0f}', fill=(255, 255, 255))
        row.append(img)
    W, H = row[0].size; canvas = Image.new('RGB', (W * len(row) + 4 * (len(row) - 1), H), (90, 90, 90))
    for j, im in enumerate(row): canvas.paste(im, (j * (W + 4), 0))
    p = os.path.join(FIG, f'episode_{tag}_s{seed}_t{t0}.png'); canvas.save(p); print(p, e['cls'] if e else None)


def lobe_fig(scn, seed, tag, times, out=None, r=2):
    """큰 엽을 색으로 칠한 그림 (엽마다 다른 색). 위 글: 큰 두꺼운 덩어리 수 big, 큰 엽 수 lobes"""
    from vcommon import torus_open, BIG
    cols = [(255, 60, 60), (60, 220, 255), (120, 255, 80), (255, 140, 255), (255, 255, 255)]
    rd = rundir(scn, seed, tag); row = []
    for t in times:
        S = load(os.path.join(rd, f'vs_t{t:04d}.npz')); wet, h = S['wet'], S['h']; V = h.sum()
        o = torus_open(wet & (h >= TH), r); lo = _torus_label(o); vo = comp_vols(lo, np.where(o, h, 0.0))
        bigl = [k for k in np.argsort(vo)[::-1] if k > 0 and vo[k] >= BIG * V]
        ex = [(lo == k, cols[i % len(cols)], 0.55) for i, k in enumerate(bigl)]
        lt, big, vb = big_parts(wet, h, V)
        im = body_rgb(wet, h, 2, extra=ex); d = ImageDraw.Draw(im)
        d.text((4, 2), f'{tag} s{seed} t={t} big={len(big)} lobes={len(bigl)} ' + ' '.join(f'{vo[k] / V:.2f}' for k in bigl), fill=(255, 255, 255))
        row.append(im)
    W, H = row[0].size; canvas = Image.new('RGB', (W * len(row) + 4 * (len(row) - 1), H), (90, 90, 90))
    for j, im in enumerate(row): canvas.paste(im, (j * (W + 4), 0))
    p = os.path.join(FIG, out or f'lobes_{scn}_s{seed}_{tag}.png'); canvas.save(p); print(p)


def lineplot(path, series, xlabel='t', ylabel='', ylim=None, title='', size=(900, 420), vlines=()):
    W, H = size; L, R, T, B = 60, 20, 30, 40
    img = Image.new('RGB', size, (255, 255, 255)); d = ImageDraw.Draw(img)
    xs_all = np.concatenate([np.asarray(s[1], float) for s in series]); ys_all = np.concatenate([np.asarray(s[2], float) for s in series])
    x0, x1 = float(np.nanmin(xs_all)), float(np.nanmax(xs_all)); y0, y1 = ylim if ylim else (float(np.nanmin(ys_all)), float(np.nanmax(ys_all)))
    if y1 <= y0: y1 = y0 + 1
    if x1 <= x0: x1 = x0 + 1
    X = lambda x: L + (x - x0) / (x1 - x0) * (W - L - R); Y = lambda y: H - B - (y - y0) / (y1 - y0) * (H - T - B)
    d.rectangle([L, T, W - R, H - B], outline=(0, 0, 0))
    for i in range(6):
        yv = y0 + (y1 - y0) * i / 5; d.line([L - 4, Y(yv), L, Y(yv)], fill=(0, 0, 0)); d.text((4, Y(yv) - 6), f'{yv:.3g}', fill=(0, 0, 0))
        d.line([L, Y(yv), W - R, Y(yv)], fill=(235, 235, 235))
        xv = x0 + (x1 - x0) * i / 5; d.line([X(xv), H - B, X(xv), H - B + 4], fill=(0, 0, 0)); d.text((X(xv) - 12, H - B + 6), f'{xv:.0f}', fill=(0, 0, 0))
    for v in vlines: d.line([X(v), T, X(v), H - B], fill=(200, 200, 200))
    d.text((L, 8), title, fill=(0, 0, 0)); d.text((W // 2, H - 16), xlabel, fill=(0, 0, 0)); d.text((4, T - 20), ylabel, fill=(0, 0, 0))
    lx = W - R - 230; ly = T + 6
    for name, xs, ys, col in series:
        pts = [(X(x), Y(min(max(y, y0), y1))) for x, y in zip(xs, ys) if np.isfinite(y)]
        if len(pts) > 1: d.line(pts, fill=col, width=2)
        elif pts: d.ellipse([pts[0][0] - 2, pts[0][1] - 2, pts[0][0] + 2, pts[0][1] + 2], fill=col)
        d.line([lx, ly + 6, lx + 20, ly + 6], fill=col, width=3); d.text((lx + 26, ly), name, fill=(0, 0, 0)); ly += 14
    img.save(path); print(path)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'montage':
        tags = ('v7c', 'v7k'); out = None
        if '--tags' in a: i = a.index('--tags'); tags = tuple(a[i + 1].split(',')); a = a[:i] + a[i + 2:]
        if '--out' in a: i = a.index('--out'); out = a[i + 1]; a = a[:i] + a[i + 2:]
        montage(a[1], int(a[2]), [int(x) for x in a[3].split(',')], tags, out)
    elif a[0] == 'lobes':
        out = None
        if '--out' in a: i = a.index('--out'); out = a[i + 1]; a = a[:i] + a[i + 2:]
        lobe_fig(a[1], int(a[2]), a[3], [int(x) for x in a[4].split(',')], out)
    elif a[0] == 'episode':
        episode_fig(a[1], int(a[2]), int(a[3]), tuple(int(x) for x in a[4:]) or (0, 20, 40, 60, 100))
