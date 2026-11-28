"""slimeall 한 판: 갇힐 때 몸, D6 순위, σ 5 봉우리, 고른 자리(재현), 끝 덩이를 견준다"""
import sys, glob, json, re, numpy as np
from scipy.ndimage import gaussian_filter
sys.path.insert(0, '.'); import meas9 as M
rd = sys.argv[1]; m = json.load(open(rd + '/metrics.json')); ts = m['t_scl']
fs = sorted(glob.glob(rd + '/vs_t*.npz'), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0])); f0 = [f for f in fs if int(re.findall(r'vs_t(\d+)', f)[0]) <= ts][-1]
Z = np.load(f0); w = Z['wet'].astype(bool); h = Z['h'].astype(float); N = w.shape[0]
lab, n, vol, area, V = M.components(w, h); B = lab == int(np.argmax(vol))
D6 = M.disk_sum(np.where(w, np.maximum(h, 0), 0), 6); bv = D6[B]; rk = np.empty(bv.size); rk[np.argsort(bv, kind='stable')] = np.arange(bv.size) / max(bv.size - 1, 1); R = np.zeros(w.shape); R[B] = rk
G5 = gaussian_filter(np.where(w, np.maximum(h, 0), 0), 5, mode='wrap', truncate=3.0)
pk6 = np.unravel_index(np.argmax(np.where(B, D6, -np.inf)), w.shape); pk5 = np.unravel_index(np.argmax(np.where(B, G5, -np.inf)), w.shape)
wE = np.load(rd + '/wet.npy').astype(bool); hE = np.where(wE, np.load(rd + '/h.npy'), 0)
lE, nE, vE, aE, VE = M.components(wE, hE); L = lE == int(np.argmax(vE))
print(f'snap t {float(Z["t"])} t_scl {ts} body {int(B.sum())} D6 peak {pk6} sigma5 peak {pk5} dist {np.hypot(*(((np.array(pk6)-np.array(pk5)+N/2)%N)-N/2)):.1f}')
print(f'final lump {int(L.sum())} cells, in B {int((L&B).sum())}, rank {R[L&B].mean():.3f}, frac of lump outside trap body {1-(L&B).sum()/L.sum():.2f}')
# coarse map: B (.), D6 rank>0.7 (+), lump (#), peaks
ys, xs = np.nonzero(B | L); cy, cx = int(np.median(ys)), int(np.median(xs))
for yy in range(cy - 36, cy + 37, 2):
    row = ''
    for xx in range(cx - 48, cx + 49, 2):
        y_, x_ = yy % N, xx % N
        c = ' '
        if B[y_, x_]: c = '+' if R[y_, x_] > 0.7 else '.'
        if L[y_, x_]: c = '#' if B[y_, x_] and R[y_, x_] > 0.7 else 'o'
        if abs(y_ - pk6[0]) <= 1 and abs(x_ - pk6[1]) <= 1: c = '6'
        if abs(y_ - pk5[0]) <= 1 and abs(x_ - pk5[1]) <= 1: c = '5'
        row += c
    print(row)
