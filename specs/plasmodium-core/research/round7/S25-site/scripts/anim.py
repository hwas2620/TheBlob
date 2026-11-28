"""저장된 장면(vs_t*.npz)으로 모델과 같은 그림을 그려 움직이는 그림(GIF)을 만든다.
usage: anim.py OUT.gif "제목1|RUN_DIR1" ["제목2|RUN_DIR2" ...] [--every 20] [--t0 0] [--t1 9999] [--scale 3] [--fine 100:300:5]"""
import sys, os, glob, json, re, numpy as np
from PIL import Image, ImageDraw, ImageFont
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
args = sys.argv[1:]; out = args.pop(0); panels = []; opt = dict(every=20, t0=0, t1=1e9, scale=3, fine=None, ms=120, veins='1', hmax='1.3', crop='0', follow='0')
while args:
    a = args.pop(0)
    if a.startswith('--'): opt[a[2:]] = args.pop(0)
    else: panels.append(a.split('|'))
every = float(opt['every']); t0 = float(opt['t0']); t1 = float(opt['t1']); s = int(opt['scale'])
try: FONT = ImageFont.truetype('/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf', 20)
except Exception:
    fs_ = glob.glob('/usr/share/fonts/**/*CJK*', recursive=True) + glob.glob('/usr/share/fonts/**/*Nanum*', recursive=True)
    FONT = ImageFont.truetype(fs_[0], 15 * s // 2) if fs_ else ImageFont.load_default()
def frames_of(rd):
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    return {int(re.findall(r'vs_t(\d+)', f)[0]): f for f in fs}
def want(t):
    if not (t0 <= t <= t1): return False
    if opt['fine']:
        a, b, st = (float(x) for x in opt['fine'].split(':'))
        if a <= t <= b: return abs(t / st - round(t / st)) < 1e-6
    return abs(t / every - round(t / every)) < 1e-6
P = [json.load(open(os.path.join(rd, 'params.json'))) for _, rd in panels]; F = [frames_of(rd) for _, rd in panels]
times = sorted(set.intersection(*[set(f) for f in F])); times = [t for t in times if want(t)]
slime = [None] * len(panels); ims = []
box = None
if int(opt['crop']) > 0:      # 모든 장면에서 젖었던 칸을 감싸는 상자(+여유) 로 자른다 (토러스 감김은 무시)
    U = None
    for t in times:
        for Fi in F:
            w_ = np.load(Fi[t])['wet'].astype(bool); U = w_ if U is None else (U | w_)
    ys_, xs_ = np.nonzero(U); mg_ = int(opt['crop']); N_ = U.shape[0]
    box = (max(0, xs_.min() - mg_), max(0, ys_.min() - mg_), min(N_, xs_.max() + 1 + mg_), min(N_, ys_.max() + 1 + mg_))
for t in times:
    row = []
    for i, ((title, rd), Pi, Fi) in enumerate(zip(panels, P, F)):
        Z = np.load(Fi[t]); N = Z['wet'].shape[0]; wet = Z['wet'].astype(bool); h = Z['h'].astype(float); C = Z['C']
        if slime[i] is None: slime[i] = np.ones((N, N), bool) if Pi.get('slime0') == 'all' else np.zeros((N, N), bool)
        slime[i] |= wet
        c0 = N / 2 - 0.5; fpos = [(c0 + d_ * np.cos(np.radians(a_)), c0 + d_ * np.sin(np.radians(a_))) for a_, d_ in Pi['foods']]
        sl_i = slime[i]
        if opt['follow'] == '1':      # 몸(부피 가중 원형 평균)을 가운데로 옮겨 그린다
            ys_, xs_ = np.nonzero(wet); wv_ = h[wet]
            cy_ = np.angle((wv_ * np.exp(2j * np.pi * ys_ / N)).sum()) * N / (2 * np.pi); cx_ = np.angle((wv_ * np.exp(2j * np.pi * xs_ / N)).sum()) * N / (2 * np.pi)
            oy_ = int(round(N / 2 - cy_)) % N; ox_ = int(round(N / 2 - cx_)) % N
            wet = np.roll(wet, (oy_, ox_), (0, 1)); h = np.roll(h, (oy_, ox_), (0, 1)); C = np.roll(C, (oy_, ox_), (1, 2)); sl_i = np.roll(sl_i, (oy_, ox_), (0, 1))
            fpos = [((fx + ox_) % N, (fy + oy_) % N) for fx, fy in fpos]
        fM = Z['fM'] if Z['fM'].size else np.ones(len(fpos))
        jj, ii = np.mgrid[0:N, 0:N]; food = np.zeros((N, N))
        for k_, (fx, fy) in enumerate(fpos):
            if fM[k_] > 0: food += np.exp(-(((ii - fx + N / 2) % N - N / 2) ** 2 + ((jj - fy + N / 2) % N - N / 2) ** 2) / (2 * Pi.get('food_sigma', 60) ** 2))
        base = np.zeros((N, N, 3), np.float32); base[:] = (10, 18, 10); base += np.clip(food, 0, 1)[..., None] * np.array([0, 22, 60], np.float32)
        sl = sl_i[..., None].astype(np.float32); base = base * (1 - sl) + np.array([52, 40, 30], np.float32) * sl
        hm_ = float(opt['hmax']); b = np.clip(h / (hm_ * Pi.get('h0', 1.0)), 0, 1)[..., None]
        if hm_ > 1.3:      # 두께를 넓게: 어두운 노랑 → 밝은 노랑 → 흰빛
            b2 = np.clip((h / Pi.get('h0', 1.0) - 1.3) / (hm_ - 1.3), 0, 1)[..., None]; b1 = np.clip(h / (1.3 * Pi.get('h0', 1.0)), 0, 1)[..., None]
            body = (np.array([40, 34, 8], np.float32) * (1 - b1) + np.array([215, 185, 40], np.float32) * b1) * (1 - b2) + np.array([255, 245, 200], np.float32) * b2
        else: body = np.array([40, 34, 8], np.float32) * (1 - b) + np.array([215, 185, 40], np.float32) * b
        base = np.where(wet[..., None], body, base)
        im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).resize((N * s, N * s), Image.NEAREST); dr = ImageDraw.Draw(im)
        CD = Pi['c_draw'] if Pi.get('c_draw', 0) > 0 else max(1.0, 2.0 * Pi.get('D0', 1.0)); segs = []
        for k, d in (enumerate(DIRS) if opt['veins'] == '1' else []):
            ys, xs = np.nonzero((C[k] > CD) & wet & np.roll(wet, (-d[1], -d[0]), (0, 1)))
            for e, a, b_ in zip(C[k][ys, xs], xs, ys):
                if 0 <= a + d[0] < N and 0 <= b_ + d[1] < N: segs.append((float(e), a, b_, a + d[0], b_ + d[1]))
        segs.sort()
        for e, a, b_, c_, d_ in segs:
            wd = 0.45 * e ** 0.25; br = min(1.0, 0.55 + 0.25 * wd)
            dr.line([((a + .5) * s, (b_ + .5) * s), ((c_ + .5) * s, (d_ + .5) * s)], fill=(int(255 * br), int(120 * br), int(40 * br)), width=max(1, int(round(wd * s))))
        for k_, (fx, fy) in enumerate(fpos):
            rr = Pi.get('food_r', 4.0) * s; col = (60, 220, 255) if fM[k_] > 0 else (120, 120, 120)
            dr.ellipse([(fx + .5) * s - rr, (fy + .5) * s - rr, (fx + .5) * s + rr, (fy + .5) * s + rr], outline=col, width=2)
        if box is not None: im = im.crop(tuple(v * s for v in box)); dr = ImageDraw.Draw(im)
        dr.text((8, 6), f'{title}   t = {t}', fill=(255, 255, 255), font=FONT)
        row.append(im)
    W = sum(r.width for r in row) + 6 * (len(row) - 1); fr = Image.new('RGB', (W, row[0].height), (0, 0, 0)); x = 0
    for r in row: fr.paste(r, (x, 0)); x += r.width + 6
    ims.append(fr.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))
dur = [int(opt['ms'])] * len(ims); dur[-1] = 2500
ims[0].save(out, save_all=True, append_images=ims[1:], duration=dur, loop=0, optimize=True)
ims[-1].convert('RGB').save(out.replace('.gif', '_last.png'))
print(out, len(ims), 'frames', os.path.getsize(out) // 1024, 'KB')
