#!/usr/bin/env python3
"""vfig.py — 독립 검증의 그림 (PIL 만 쓴다).
  python3 vfig.py series                 long 의 바깥 몫 out(t): 대조 10 / 후보 10           -> fig/out_series_long.png
  python3 vfig.py montage RUN t1 t2 ...  저장 상태를 그려 이음(다시 찾은 neck)을 자홍색으로 표시 -> fig/montage_<RUN>.png
  python3 vfig.py w3                     후보 long 실행마다 이음의 pin, R_same (judge_v.json)   -> fig/w3_link_flow.png
  python3 vfig.py far                    food4 가장 먼 먹이에 닿은 시각: 대조 vs 후보             -> fig/food4_far.png
"""
import sys, os, json, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont
try: ImageDraw.ImageDraw.font = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 12)    # 한글 글꼴
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vextract

V = vextract.V; REF = '/home/user/TheBlob/specs/plasmodium-core/stage0/ref'; FIG = os.path.join(V, 'fig'); os.makedirs(FIG, exist_ok=True)
TH = vextract.TH


def render(S, s=2, neck=None, label=''):
    N = S['wet'].shape[0]; wet = S['wet'].astype(bool); h = S['h'].astype(float); C = S['C'].astype(float)
    base = np.zeros((N, N, 3), np.float32); base[:] = (10, 18, 10)
    b = np.clip(h / 1.3, 0, 1)[..., None]
    body = np.array([40, 34, 8], np.float32) * (1 - b) + np.array([215, 185, 40], np.float32) * b
    base = np.where(wet[..., None], body, base)
    thin = wet & (h < 0.3); base[thin] = (90, 90, 140)                         # 얇은 젖은 셀(h<0.3): 회청색
    if neck is not None: base[neck] = (255, 0, 255)                             # 다시 찾은 이음(얇은 셀): 자홍색
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((N * s, N * s), Image.NEAREST)
    dr = ImageDraw.Draw(im); segs = []
    for k, d in enumerate(vextract.DIRS):
        ys, xs = np.nonzero((C[k] > 4.0) & wet & vextract.nb(wet, d))
        for e, a, b_ in zip(C[k][ys, xs], xs, ys):
            if 0 <= a + d[0] < N and 0 <= b_ + d[1] < N: segs.append((e, a, b_, a + d[0], b_ + d[1]))
    segs.sort()
    for e, a, b_, c_, d_ in segs:
        wd = 0.45 * e ** 0.25; br = min(1.0, 0.55 + 0.25 * wd)
        dr.line([((a + .5) * s, (b_ + .5) * s), ((c_ + .5) * s, (d_ + .5) * s)], fill=(int(255 * br), int(120 * br), int(40 * br)), width=max(1, int(round(wd * s * 0.5))))
    dr.text((4, 3), label, fill=(255, 255, 255))
    return im


def load_vs(run, t):
    Z = np.load(os.path.join(REF, 'runs', run, f'vs_t{int(t):04d}.npz')); return {k: Z[k] for k in Z.files}


def montage(run, times, s=2):
    W = TH['W3']; ims = []
    for t in times:
        S = load_vs(run, t); neck, neckp, info = vextract.find_neck(S['h'].astype(float), S['wet'].astype(bool), W['neck_h'], W['neck_min'])
        x = json.load(open(os.path.join(V, 'data', f'x_{run}.json'))); r = next(r for r in x['rows'] if abs(r['t'] - t) < 1e-6)
        lab = f"{run} t={t:.0f} out={r['out']:.2f}" + (f" link={info['link_len']:.0f} pin={r.get('pin', float('nan')):.2f} Rs={r.get('R_same') or float('nan'):.2f}" if neck.any() else '')
        ims.append(render(S, s, neck if neck.any() else None, lab))
    n = len(ims); cols = min(n, 4); rows = (n + cols - 1) // cols; w, h = ims[0].size
    out = Image.new('RGB', (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (255, 255, 255))
    for i, im in enumerate(ims): out.paste(im, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    p = os.path.join(FIG, f'montage_{run}.png'); out.save(p); print(p)


def axes(dr, x0, y0, w, h, xmax, ymax, title, xlab, ylab, yticks):
    dr.rectangle([x0, y0, x0 + w, y0 + h], outline=(0, 0, 0)); dr.text((x0, y0 - 14), title, fill=(0, 0, 0))
    dr.text((x0 + w // 2 - 20, y0 + h + 16), xlab, fill=(0, 0, 0)); dr.text((x0 - 40, y0 - 14), ylab, fill=(0, 0, 0))
    for v in yticks:
        y = y0 + h - v / ymax * h; dr.line([x0 - 4, y, x0, y], fill=(0, 0, 0)); dr.text((x0 - 34, y - 6), f'{v:g}', fill=(0, 0, 0))
    for v in (np.linspace(0, xmax, 5) if xlab else []):
        x = x0 + v / xmax * w; dr.line([x, y0 + h, x, y0 + h + 4], fill=(0, 0, 0)); dr.text((x - 10, y0 + h + 4), f'{v:.0f}', fill=(0, 0, 0))


PAL = [(31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40), (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127), (188, 189, 34), (23, 190, 207)]


def series():
    img = Image.new('RGB', (1100, 420), (255, 255, 255)); dr = ImageDraw.Draw(img); ymax = 0.6
    for j, tag in enumerate(('vc', 'vnk')):
        x0 = 60 + j * 540; y0 = 40; w = 480; h = 320
        axes(dr, x0, y0, w, h, 2000, ymax, ('대조 (vc)' if tag == 'vc' else '후보 (vnk, 이음 지키기)') + ' — long, 바깥 몫 out(t), 선 = 0.10', 't', 'out', [0, 0.1, 0.2, 0.4, 0.6])
        y = y0 + h - 0.1 / ymax * h; dr.line([x0, y, x0 + w, y], fill=(200, 0, 0))
        for i, s in enumerate(range(101, 111)):
            f = os.path.join(V, 'data', f'x_b_long_s{s}_{tag}.json')
            if not os.path.exists(f): continue
            rows = json.load(open(f))['rows']
            pts = [(x0 + r['t'] / 2000 * w, y0 + h - min(r['out'], ymax) / ymax * h) for r in rows]
            if len(pts) > 1: dr.line(pts, fill=PAL[i], width=2)
            dr.text((x0 + w - 40, y0 + 4 + 12 * i), f's{s}', fill=PAL[i])
    p = os.path.join(FIG, 'out_series_long.png'); img.save(p); print(p)


def w3fig():
    J = json.load(open(os.path.join(V, 'judge_v.json'))); runs = J['W3']['res']['vnk']['runs']; runs0 = J['W3']['res']['vc']['runs']
    img = Image.new('RGB', (900, 380), (255, 255, 255)); dr = ImageDraw.Draw(img)
    x0, y0, w, h = 60, 40, 800, 280; ymax = 2.0
    axes(dr, x0, y0, w, h, 1, ymax, 'long 실행마다 이음 간선: 파랑 = pin (C<=20 비율), 주황 = R_same (같은 굵기 관 대비 흐름). 옅은 색 = 대조의 "될 뻔한 이음"', '', '', [0, 0.5, 1, 1.5, 2])
    for v, col in ((0.5, (150, 150, 150)), (0.6, (230, 200, 160))):
        y = y0 + h - v / ymax * h; dr.line([x0, y, x0 + w, y], fill=col)
    n = len(runs); bw = w / max(n, 1)
    for i, (r, r0) in enumerate(zip(runs, runs0)):
        xc = x0 + (i + 0.5) * bw
        for j, (val, col) in enumerate(((r['pin'], (31, 119, 180)), (r['R_same'], (255, 127, 14)), (r0['pin'], (160, 190, 220)), (r0['R_same'], (250, 200, 150)))):
            if val is None: continue
            xa = xc - 2 * 14 + j * 14; dr.rectangle([xa, y0 + h - min(val, ymax) / ymax * h, xa + 12, y0 + h], fill=col)
        dr.text((xc - 22, y0 + h + 22), f"s{r['seed']} n={r['n_neck_states']}", fill=(0, 0, 0))
    p = os.path.join(FIG, 'w3_link_flow.png'); img.save(p); print(p)


def far():
    J = json.load(open(os.path.join(V, 'judge_v.json'))); rows = J['C5']['rows']; i = TH['W1']['far_food_index']
    img = Image.new('RGB', (520, 520), (255, 255, 255)); dr = ImageDraw.Draw(img); x0, y0, w, h = 70, 40, 400, 400; tmax = 760
    axes(dr, x0, y0, w, h, tmax, tmax, 'food4 가장 먼 먹이에 닿은 시각 (못 닿음 = 740 자리)', '대조', '후보', [0, 200, 400, 600, 740])
    dr.line([x0, y0 + h, x0 + w, y0], fill=(180, 180, 180))
    for r in rows:
        a = r['t_touch_c'][i]; b = r['t_touch_k'][i]; a = 740 if a is None else a; b = 740 if b is None else b
        x = x0 + a / tmax * w; y = y0 + h - b / tmax * h; dr.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(31, 119, 180), width=2); dr.text((x + 5, y - 5), str(r['seed']), fill=(100, 100, 100))
    p = os.path.join(FIG, 'food4_far.png'); img.save(p); print(p)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'series': series()
    elif cmd == 'montage': montage(sys.argv[2], [float(t) for t in sys.argv[3:]])
    elif cmd == 'w3': w3fig()
    elif cmd == 'far': far()


def geocap(run, t_before, t_after, s=3):
    """탐색 그림: 끊어지기 전 상태에 모델이 지키는 이음(자홍)과 거리 제한 때문에 지키지 못하는 얇은 길(하늘색), 끊어진 뒤 상태"""
    import diag_geocap as D
    S = load_vs(run, t_before); h = S['h'].astype(float); wet = S['wet'].astype(bool); N = h.shape[0]
    pc, _, _ = D.masks(h, wet, N); pn, _, _ = D.masks(h, wet, 10 * N)
    im1 = render(S, s, None, f'{run} t={t_before:.0f}: 자홍 = 모델이 지키는 이음, 하늘 = 거리 제한(N={N})으로 못 지키는 얇은 길')
    a = np.array(im1); m1 = np.kron(pc, np.ones((s, s), bool)); m2 = np.kron(pn & ~pc, np.ones((s, s), bool))
    a[m1] = (255, 0, 255); a[m2] = (0, 230, 255); im1 = Image.fromarray(a)
    S2 = load_vs(run, t_after); x = json.load(open(os.path.join(V, 'data', f'x_{run}.json'))); r = next(r for r in x['rows'] if abs(r['t'] - t_after) < 1e-6)
    im2 = render(S2, s, None, f'{run} t={t_after:.0f}: 끊어짐, out={r["out"]:.2f}')
    a2 = np.array(im2); gone = np.kron(pn & ~S2['wet'].astype(bool), np.ones((s, s), bool)); a2[gone] = (255, 60, 60); im2 = Image.fromarray(a2)
    ImageDraw.Draw(im2).text((4, 18), '빨강 = t=%.0f 의 이음 길에서 마른 셀' % t_before, fill=(255, 255, 255))
    w, h_ = im1.size; out = Image.new('RGB', (2 * w + 6, h_), (255, 255, 255)); out.paste(im1, (0, 0)); out.paste(im2, (w + 6, 0))
    p = os.path.join(FIG, f'geocap_{run}.png'); out.save(p); print(p)


if __name__ == '__main__' and sys.argv[1] == 'geocap':
    geocap(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
