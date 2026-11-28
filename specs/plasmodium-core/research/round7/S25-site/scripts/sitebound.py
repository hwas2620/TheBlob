"""갇힐 때 장면에서: (1) 둥근 덩이(넓이 A)가 받을 수 있는 가장 높은 D6 순위, (2) D6 로 흘러 채운 A 칸의 순위·촘촘함"""
import sys, glob, json, numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, '.')
import meas9 as M
R = '../../S24-shrink/model/runs/'
for s in [1001,1002,1003,1004,1005,1006,1007,1008,1201]:
    rd = R + f'b_slimeall_s{s}_v9b'; Z = np.load(rd + '/vs_t0130.npz'); w = Z['wet'].astype(bool); h = Z['h'].astype(float)
    lab, n, vol, area, V = M.components(w, h); B = lab == int(np.argmax(vol)); Vb = float(np.maximum(h[B], 0).sum())
    D6 = M.disk_sum(np.where(w, np.maximum(h, 0), 0), 6); bv = D6[B]; rk = np.empty(bv.size); rk[np.argsort(bv, kind='stable')] = np.arange(bv.size) / max(bv.size - 1, 1); Rk = np.zeros(w.shape); Rk[B] = rk
    A = int(Vb / 3.5) + 1
    out = [f's{s} body {int(B.sum())} A {A}']
    for f in (1.0, 1.2):
        r = np.sqrt(f * A / np.pi); yy, xx = np.mgrid[-int(r)-1:int(r)+2, -int(r)-1:int(r)+2]; k = (np.hypot(xx, yy) <= r).astype(float)
        S = ndi.convolve(Rk * B, k, mode='wrap'); C = ndi.convolve(B.astype(float), k, mode='wrap'); mr = np.where(C > 0.6 * k.sum(), S / np.maximum(C, 1), 0)
        out.append(f'disk{f}: best {mr.max():.2f}')
    # flood on D6 from its peak, A cells, 8-connected, inside B
    import heapq
    fi = np.flatnonzero(B); s0 = int(fi[np.argmax(D6.ravel()[fi])]); hp = [(-D6.ravel()[s0], s0)]; seen = {s0}; T = np.zeros(w.shape, bool); nn = 0; N = w.shape[0]
    while hp and nn < A:
        g, c = heapq.heappop(hp); y, x = divmod(c, N); T[y, x] = True; nn += 1
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                yy_, xx_ = (y+dy) % N, (x+dx) % N; cc = yy_*N+xx_
                if cc not in seen and B[yy_, xx_]: seen.add(cc); heapq.heappush(hp, (-D6[yy_, xx_], cc))
    out.append(f'D6flood: rank {Rk[T].mean():.2f} sol {M.solidity(T):.2f} iou {M.disc_iou(T):.2f}')
    print('  '.join(out), flush=True)
