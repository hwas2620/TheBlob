"""[S14 결승 진단] food4에서 먹이를 놓친 실행을 그린다. 줄마다 실행 하나, 칸마다 시각 하나. 먹이 자리는 빨간 원.
python3 diag_food4.py OUT.png SEED T1 T2 ... (대조 s14c, 후보 s14gd 두 줄). 몸에서 각 먹이까지 가장 가까운 거리도 찍는다."""
import os, sys, json, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label
out, seed, ts = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3:]]; S = 2; rows = []
for tag in ('s14c', 's14gd'):
    rd = os.path.join(RUNS, f'b_food4_s{seed}_{tag}'); m = json.load(open(os.path.join(rd, 'metrics.json'))); F = m['foods']; ims = []
    print(tag, 'touch', m['t_touch'])
    for t in ts:
        Z = np.load(os.path.join(rd, f'vs_t{t:04d}.npz')); wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); N = h.shape[0]
        img = np.zeros((N, N, 3), np.uint8); thin = wet & (h < 0.3); thick = wet & (h >= 0.3); x = np.clip((h - 0.3) / 0.9, 0, 1)
        img[thin] = (30, 50, 110); img[thick] = np.stack([235 + 0 * x, 200 - 110 * x, 60 - 40 * x], -1)[thick].astype(np.uint8)
        img[wet & (Z['C'].astype(float).max(0) > 50)] = (255, 255, 255)
        ys, xs = np.nonzero(wet); dist = []
        for fx, fy in F:
            dx = np.abs(xs - fx); dx = np.minimum(dx, N - dx); dy = np.abs(ys - fy); dy = np.minimum(dy, N - dy); dist.append(float(np.sqrt(dx * dx + dy * dy).min()) if xs.size else np.nan)
        lw = _torus_label(wet); print(f'  t={t} area={int(wet.sum())} V={h.sum():.0f} pieces={lw.max()} dist_to_food={[round(d_, 1) for d_ in dist]}')
        im = Image.fromarray(img).resize((N * S, N * S), Image.NEAREST); d = ImageDraw.Draw(im)
        for k, (fx, fy) in enumerate(F): d.ellipse((fx * S - 12, fy * S - 12, fx * S + 12, fy * S + 12), outline=(255, 60, 60)); d.text((fx * S + 14, fy * S - 6), str(k + 1), fill=(255, 60, 60))
        d.text((3, 2), f'{tag} t={t}', fill=(255, 255, 255)); ims.append(im)
    rows.append(ims)
N2 = rows[0][0].size[0]; M = Image.new('RGB', (len(ts) * (N2 + 4), 2 * (N2 + 4)), (60, 60, 60))
for i, ims in enumerate(rows):
    for j, im in enumerate(ims): M.paste(im, (j * (N2 + 4), i * (N2 + 4)))
M.save(out)
