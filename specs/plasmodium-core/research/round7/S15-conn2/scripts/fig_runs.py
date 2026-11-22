"""[S15] 실행 여럿을 나란히 그린다. 줄마다 꼬리표 하나, 칸마다 시각 하나. 먹이 자리는 빨간 원.
python3 fig_runs.py OUT.png SCN SEED TAG1,TAG2,... T1 T2 ...
색: 얇은 칸(h < 0.3) 파랑, 두꺼운 칸 노랑~빨강(두꺼울수록 붉다), 먹이 농도가 높은 칸 흰색."""
import os, sys, json, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label
out, scn, seed, tags = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4].split(','); ts = [int(x) for x in sys.argv[5:]]
rows = []
for tag in tags:
    rd = os.path.join(RUNS, f'b_{scn}_s{seed}_{tag}'); m = json.load(open(os.path.join(rd, 'metrics.json'))); F = m.get('foods') or []; ims = []
    print(tag, 'touch', m.get('t_touch'))
    for t in ts:
        Z = np.load(os.path.join(rd, f'vs_t{t:04d}.npz')); wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); N = h.shape[0]
        S = 2 if N >= 256 else 3
        img = np.zeros((N, N, 3), np.uint8); thin = wet & (h < 0.3); thick = wet & (h >= 0.3); x = np.clip((h - 0.3) / 0.9, 0, 1)
        img[thin] = (30, 50, 110); img[thick] = np.stack([235 + 0 * x, 200 - 110 * x, 60 - 40 * x], -1)[thick].astype(np.uint8)
        if 'C' in Z.files: img[wet & (Z['C'].astype(float).max(0) > 50)] = (255, 255, 255)
        lw = _torus_label(wet); print(f'  t={t} area={int(wet.sum())} V={h.sum():.0f} pieces={lw.max()} thin={int(thin.sum())}')
        im = Image.fromarray(img).resize((N * S, N * S), Image.NEAREST); d = ImageDraw.Draw(im)
        for k, (fx, fy) in enumerate(F): d.ellipse((fx * S - 12, fy * S - 12, fx * S + 12, fy * S + 12), outline=(255, 60, 60)); d.text((fx * S + 14, fy * S - 6), str(k + 1), fill=(255, 60, 60))
        d.text((3, 2), f'{tag} t={t}', fill=(255, 255, 255)); ims.append(im)
    rows.append(ims)
W = rows[0][0].size[0]; M = Image.new('RGB', (len(ts) * (W + 4), len(rows) * (W + 4)), (60, 60, 60))
for i, ims in enumerate(rows):
    for j, im in enumerate(ims): M.paste(im, (j * (W + 4), i * (W + 4)))
M.save(out); print('saved', out)
