"""[S24 진단 6] 균핵 맺힘 중 바깥 칸: 끝 덩이로부터 몸을 따라 잰 거리 몫(dn)별로 젖은 칸 수, 평균 h, 평균 쉼 두께 exp(-sage/50), h - 쉼 두께 (판정 아님)
python3 d6look.py 실행폴더 [t_scl]"""
import sys, os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label, nb, RING
rd = sys.argv[1]; m = json.load(open(os.path.join(rd, 'metrics.json'))); ts = m['t_scl']
we = np.load(os.path.join(rd, 'wet.npy')).astype(bool); he = np.load(os.path.join(rd, 'h.npy'))
lab = _torus_label(we); vol = np.bincount(lab.ravel(), weights=np.where(we, he, 0).ravel()); vol[0] = 0; core = lab == int(np.argmax(vol))
t0 = int(np.ceil(ts / 20) * 20); Z = np.load(os.path.join(rd, f'vs_t{t0:04d}.npz')); w0 = Z['wet'].astype(bool)
N = w0.shape[0]; M = w0 | core; D = np.full((N, N), -1); D[core] = 0; fr = core.copy(); k = 0
while fr.any():
    k += 1; nf = np.zeros((N, N), bool)
    for dd in RING: nf |= nb(fr, dd)
    nf &= M & (D < 0); D[nf] = k; fr = nf
ob = w0 & ~core; dmx = D[ob].max(); dn = np.where(ob, D / max(dmx, 1), -1)
bins = [(0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.01)]
print(f"{os.path.basename(rd)} t_scl {ts} 끝 덩이 {int(core.sum())}칸, 바깥(t {t0}) {int(ob.sum())}칸, 최대 거리 {dmx}")
for t in range(t0, int(ts) + 200, 20):
    f = os.path.join(rd, f'vs_t{t:04d}.npz')
    if not os.path.exists(f): continue
    Z = np.load(f); w = Z['wet'].astype(bool); h = Z['h']; hs = np.exp(-Z['sage'] / 50.0)
    row = [f"t {t:4d} (+{t - ts:5.1f}) 덩이 h {h[core & w].mean():.2f}"]
    for a, b in bins:
        sel = ob & (dn >= a) & (dn < b); ww = sel & w
        row.append(f"dn {a:.2f}-{b:.2f}: 젖음 {int(ww.sum()):4d}/{int(sel.sum()):4d} h {h[ww].mean() if ww.any() else 0:.2f} h* {hs[ww].mean() if ww.any() else 0:.2f}")
    print(' | '.join(row))
