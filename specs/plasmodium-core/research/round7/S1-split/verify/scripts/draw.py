#!/usr/bin/env python3
"""[검증] 저장된 상태(vs_t*.npz)를 그림으로 그린다 (PIL 만 쓴다).

usage:
  draw.py times OUT.png T1,T2,... RUN [RUN ...] [--px 2]        행 = 실행, 열 = 시각
  draw.py ends  OUT.png T RUN [RUN ...] [--px 2] [--cols 3]     실행마다 시각 T(없으면 마지막 저장 시각) 한 장. 한 줄에 cols 장
  draw.py crop  OUT.png T X0,Y0,W,H RUN [RUN ...] [--px 6]      한 시각의 일부를 크게

색
  노랑(어두움→밝음)   젖은 셀, 두께 0 → 1.3
  하늘색              "얇은 셀": 젖었고 h < h_min(0.15) 이고 젖은 지 grace(2) 넘은 셀 (마름 문턱 아래인데 남아 있는 셀)
  보라                가장 큰 덩어리(8연결, 부피 기준)에 들지 않은 젖은 셀 (두께에 따라 밝기)
  빨강                음수 두께인 젖은 셀
  주황 선             정맥: 전도도 C > 4 인 간선 (굵기 ∝ C^0.25)
  원                  먹이·유인원 (하늘색 = 남아 있음, 회색 = 다 먹음)
  짙은 갈색 바탕      (--slime 을 주면) 지나간 자리. 기본은 그리지 않는다
"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'stage0'))
sys.path.insert(0, os.path.join(STAGE0, 'metrics')); sys.path.insert(0, os.path.join(STAGE0, 'ref'))
import vmet

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


def load(run, t):
    P = json.load(open(os.path.join(run, 'params.json')))
    fs = sorted(glob.glob(os.path.join(run, 'vs_t*.npz')))
    if t is None: f = fs[-1]
    else:
        f = os.path.join(run, 'vs_t%04d.npz' % int(round(t)))
        if not os.path.exists(f): return None, P
    Z = np.load(f); return {k: Z[k] for k in Z.files}, P


def panel(S, P, px=2, label='', box=None):
    N = P['N']
    if S is None:
        im = Image.new('RGB', (N * px, N * px), (30, 0, 0)); ImageDraw.Draw(im).text((6, 4), label + ' (no state)', fill=(255, 255, 255)); return im
    wet = S['wet'].astype(bool); h = S['h'].astype(float); C = S['C'].astype(float); age = S['age'].astype(float)
    img = np.zeros((N, N, 3), np.float32); img[:] = (10, 12, 16)
    b = np.clip(h / 1.3, 0, 1)[..., None]
    body = np.array([52, 46, 14], np.float32) * (1 - b) + np.array([235, 205, 60], np.float32) * b
    img = np.where(wet[..., None], body, img)
    # 가장 큰 덩어리 밖
    out = 0.0; ncomp = 0
    if wet.any():
        src, dst, cc, kk = vmet.edge_list(C, wet); nc, lab = vmet.comps(src, dst, N * N); w = wet.ravel()
        vol = np.bincount(lab[w], weights=h.ravel()[w], minlength=nc); big = int(np.argmax(vol)); outm = wet & (lab.reshape(N, N) != big)
        out = 1.0 - vol[big] / max(vol.sum(), 1e-12); ncomp = int((np.bincount(lab[w], minlength=nc) > 0).sum())
        b2 = np.clip(0.35 + h / 1.3, 0, 1)[..., None]
        img = np.where(outm[..., None], np.array([170, 90, 255], np.float32) * b2, img)
    thin = wet & (h < P['h_min']) & (age > P['grace'])
    img[thin] = (0, 190, 255)
    img[wet & (h < 0)] = (255, 30, 30)
    if box:
        x0, y0, w_, h_ = box; idx_y = np.arange(y0, y0 + h_) % N; idx_x = np.arange(x0, x0 + w_) % N
        img = img[np.ix_(idx_y, idx_x)]
    H, W = img.shape[:2]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W * px, H * px), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    ox, oy = (box[0], box[1]) if box else (0, 0)
    segs = []
    for k, d in enumerate(DIRS):
        ys, xs = np.nonzero(C[k] > 4.0)
        for e, a, b_ in zip(C[k][ys, xs], xs, ys):
            a2 = (a - ox) % N; b2_ = (b_ - oy) % N
            if 0 <= a2 + d[0] < W and 0 <= b2_ + d[1] < H and a2 < W and b2_ < H: segs.append((e, a2, b2_, a2 + d[0], b2_ + d[1]))
    segs.sort()
    for e, a, b_, c_, d_ in segs:
        wd = 0.30 * e ** 0.25
        dr.line([((a + .5) * px, (b_ + .5) * px), ((c_ + .5) * px, (d_ + .5) * px)], fill=(255, 120, 30), width=max(1, int(round(wd * px / 2))))
    for k_, (fx, fy) in enumerate(vmet.food_positions(P) if P.get('foods') else []):
        fM = S.get('fM'); live = True if fM is None else bool(np.asarray(fM)[k_] > 0)
        rr = P['food_r'] * px; cx = ((fx - ox) % N + .5) * px; cy = ((fy - oy) % N + .5) * px
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(60, 230, 255) if live else (150, 150, 150), width=1)
    txt = f"{label} t={float(S['t']):.0f} area={int(wet.sum())} thin={int(thin.sum())} out={out:.3f} n={ncomp}"
    dr.rectangle([0, 0, 6 * len(txt) + 8, 13], fill=(0, 0, 0)); dr.text((3, 1), txt, fill=(255, 255, 255))
    return im


def grid(ims, ncols, pad=4):
    w = max(i.width for i in ims); h = max(i.height for i in ims); nrows = (len(ims) + ncols - 1) // ncols
    out = Image.new('RGB', (ncols * w + (ncols + 1) * pad, nrows * h + (nrows + 1) * pad), (70, 70, 70))
    for i, im in enumerate(ims): out.paste(im, (pad + (i % ncols) * (w + pad), pad + (i // ncols) * (h + pad)))
    return out


def save(im, path, colors=96):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    im.quantize(colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)
    print(path, im.size, '%.0f KB' % (os.path.getsize(path) / 1024))


def short(run):
    return os.path.basename(run.rstrip('/')).replace('b_', '')


def main():
    a = sys.argv[1:]; px = 2; cols = 3
    if '--px' in a: i = a.index('--px'); px = int(a[i + 1]); a = a[:i] + a[i + 2:]
    if '--cols' in a: i = a.index('--cols'); cols = int(a[i + 1]); a = a[:i] + a[i + 2:]
    mode, out = a[0], a[1]
    if mode == 'times':
        ts = [float(v) for v in a[2].split(',')]; runs = a[3:]; ims = []
        for r in runs:
            for t in ts:
                S, P = load(r, t); ims.append(panel(S, P, px, short(r)))
        save(grid(ims, len(ts)), out)
    elif mode == 'ends':
        t = None if a[2] in ('end', '-') else float(a[2]); runs = a[3:]; ims = []
        for r in runs:
            S, P = load(r, t); ims.append(panel(S, P, px, short(r)))
        save(grid(ims, cols), out)
    elif mode == 'crop':
        t = float(a[2]); box = [int(v) for v in a[3].split(',')]; runs = a[4:]; ims = []
        for r in runs:
            S, P = load(r, t); ims.append(panel(S, P, px, short(r), box=box))
        save(grid(ims, cols), out)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
