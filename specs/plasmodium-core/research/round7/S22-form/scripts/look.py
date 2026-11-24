"""실행 장면 그림: python3 look.py out.png 실행폴더 t1 t2 ... (마지막 칸은 끝 상태). 두께 h, 0~vmax"""
import sys, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
out = sys.argv[1]; rds = [a for a in sys.argv[2:] if os.path.isdir(a)]; ts = [int(a) for a in sys.argv[2:] if a.isdigit()]
vmax = float(os.environ.get('VMAX', '3.5'))
fig, ax = plt.subplots(len(rds), len(ts) + 1, figsize=(2.6 * (len(ts) + 1), 2.7 * len(rds)), squeeze=False)
for i, rd in enumerate(rds):
    for j, t in enumerate(ts + [None]):
        if t is None: w = np.load(os.path.join(rd, 'wet.npy')).astype(bool); h = np.load(os.path.join(rd, 'h.npy')); tt = 'end'
        else:
            f = os.path.join(rd, f'vs_t{t:04d}.npz')
            if not os.path.exists(f): ax[i, j].axis('off'); continue
            Z = np.load(f); w = Z['wet']; h = Z['h']; tt = t
        a = ax[i, j]; a.imshow(np.where(w, h, np.nan), cmap='viridis', vmin=0, vmax=vmax, origin='lower', interpolation='nearest')
        a.set_title(f"{os.path.basename(rd).replace('b_', '')} {tt}", fontsize=7); a.set_xticks([]); a.set_yticks([])
plt.tight_layout(); plt.savefig(out, dpi=80)
