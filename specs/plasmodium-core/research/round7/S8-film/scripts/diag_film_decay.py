"""t=1600에 얇았던(h<0.3) 칸들이 들고 있던 부피가 시간에 따라 어떻게 줄어드는가. 그리고 그 칸의 두께 분포.
python3 diag_film_decay.py"""
import os, sys, numpy as np
RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref/runs'))
TS = list(range(1600, 2001, 20))
def ld(run, t):
    Z = np.load(os.path.join(RUNS, run, f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); return w, np.where(w, Z['h'].astype(float), 0.0)
for tag in ['s7c', 's7k']:
    dec = []; hist = np.zeros(8)
    for s in range(141, 151):
        run = f'b_long_s{s}_{tag}'; w0, h0 = ld(run, 1600); m = w0 & (h0 < 0.3); V0 = h0[m].sum()
        hist += np.histogram(h0[m], bins=[0, 0.15, 0.17, 0.19, 0.21, 0.23, 0.25, 0.27, 0.3])[0]
        dec.append([ld(run, t)[1][m].sum() / V0 for t in TS])
    dec = np.array(dec); print(tag, 'h hist [0,.15,.17,.19,.21,.23,.25,.27,.3]:', (hist / hist.sum()).round(2))
    print(tag, 'volume left of t1600-thin cells at +0,+20,+40,+100,+200,+400:', dec.mean(0)[[0, 1, 2, 5, 10, 20]].round(2), ' per seed +200:', dec[:, 10].round(2))
