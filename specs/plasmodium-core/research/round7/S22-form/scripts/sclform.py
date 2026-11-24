"""S22 균핵 맺힘 재기: python3 sclform.py <실행 폴더>...  (한 줄씩 결과, --json 이면 json)
- t_on: 균핵 모드에 든 때 (metrics t_scl)
- 끝 덩이: 마지막 장면에서 부피가 가장 큰 조각 (8-이웃, 토러스)
- area, disc_iou(같은 넓이·같은 중심 원판과의 IoU), aspect(공분산 축비 √), solidity, h_cv, h_in10(중앙값 ±10% 안 몫)
- iou_mass: 갇힐 때 장면의 두께를 σ 3칸으로 흐려 위에서부터 area 칸을 고른 자리와 끝 덩이의 IoU
- gain: 갇히기 20 전 장면부터 끝까지, 끝 덩이 자리(+1칸) 안 부피 몫. max_share = 한 장면(20) 사이 오른 최대 / 전체 오름
- t50, t90: 그 몫이 처음 값에서 전체 오름의 50%, 90%를 채운 때 (t_on 기준)
"""
import sys, os, json, glob
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import convex_hull_image

S8 = np.ones((3, 3), int)

def tlabel(m):
    lab, n = ndi.label(m, S8)
    if n == 0: return lab, 0
    par = np.arange(n + 1)
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    def u(a, b):
        if a and b:
            a, b = f(a), f(b)
            if a != b: par[max(a, b)] = min(a, b)
    N0, N1 = m.shape
    for i in range(N1):
        for di in (-1, 0, 1): u(lab[0, i], lab[-1, (i + di) % N1])
    for j in range(N0):
        for dj in (-1, 0, 1): u(lab[j, 0], lab[(j + dj) % N0, -1])
    roots = np.array([f(a) for a in range(n + 1)]); uniq = {r: k for k, r in enumerate(sorted(set(roots[1:])), 1)}
    mp = np.zeros(n + 1, int); mp[1:] = [uniq[r] for r in roots[1:]]
    return mp[lab], len(uniq)

def center(mask, w=None):
    N = mask.shape[0]; ys, xs = np.nonzero(mask); w = np.ones(ys.size) if w is None else w[mask]; a = 2 * np.pi / N
    return (np.arctan2((w * np.sin(xs * a)).sum(), (w * np.cos(xs * a)).sum()) / a) % N, (np.arctan2((w * np.sin(ys * a)).sum(), (w * np.cos(ys * a)).sum()) / a) % N

def shape(m, h):
    N = m.shape[0]; cx, cy = center(m); sx, sy = int(round(N / 2 - cx)), int(round(N / 2 - cy))
    mm = np.roll(m, (sy, sx), (0, 1)); hh = np.roll(h, (sy, sx), (0, 1)); ys, xs = np.nonzero(mm); A = int(mm.sum())
    out = dict(area=A)
    if A < 5: return out
    out['solidity'] = float(A / max(convex_hull_image(mm).sum(), 1))
    ev = np.sort(np.linalg.eigvalsh(np.cov(np.vstack([xs - xs.mean(), ys - ys.mean()])))); out['aspect'] = float(np.sqrt(ev[1] / max(ev[0], 1e-9)))
    jj, ii = np.mgrid[0:N, 0:N]; D = np.hypot(ii - xs.mean(), jj - ys.mean()) <= np.sqrt(A / np.pi)
    out['disc_iou'] = float((mm & D).sum() / max((mm | D).sum(), 1))
    hc = hh[mm]; med = float(np.median(hc)); out['h_cv'] = float(hc.std() / max(hc.mean(), 1e-12)); out['h_in10'] = float((np.abs(hc - med) <= 0.1 * med).mean())
    out['h_med'] = med; out['h_p90'] = float(np.percentile(hc, 90)); out['h_p10'] = float(np.percentile(hc, 10))
    return out

def run(rd):
    met = json.load(open(os.path.join(rd, 'metrics.json'))); ts = met.get('t_scl')
    fr = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
    H = []; Wt = []; T = []
    for f in fr:
        Z = np.load(f); w = Z['wet'].astype(bool); H.append(np.where(w, Z['h'], 0.0).astype(float)); Wt.append(w); T.append(float(Z['t']))
    hf = np.where(np.load(os.path.join(rd, 'wet.npy')).astype(bool), np.load(os.path.join(rd, 'h.npy')), 0.0); wf = hf > 0
    lab, n = tlabel(wf); R = dict(run=os.path.basename(rd), t_on=ts, n_pieces=n, stop=met.get('stop', ''))
    if n == 0 or ts is None: return R
    vol = np.bincount(lab.ravel(), weights=hf.ravel(), minlength=n + 1); vol[0] = -1; Mf = lab == int(np.argmax(vol))
    R['vfrac_main'] = float(vol.max() / hf.sum()); R.update(shape(Mf, hf))
    R['thin_frac'] = float((hf[Mf] < 0.5).mean())
    T = np.array(T); k0 = int(max([i for i in range(len(T)) if T[i] <= ts] or [0]))
    G = ndi.gaussian_filter(H[k0], 3.0, mode='wrap'); top = np.zeros(G.size, bool); top[np.argsort(-G.ravel(), kind='stable')[:int(Mf.sum())]] = True
    R['iou_mass'] = float((Mf & top.reshape(G.shape)).sum() / max((Mf | top.reshape(G.shape)).sum(), 1))
    Md = ndi.binary_dilation(Mf, S8, mode='wrap') if False else Mf.copy()
    for d in [(0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, -1), (-1, 1)]: Md |= np.roll(Mf, d, (0, 1))
    ks = [i for i in range(len(T)) if T[i] >= ts - 20]
    fr_ = np.array([H[i][Md].sum() / max(H[i].sum(), 1e-12) for i in ks]); tt = T[ks]
    fend = float(Md[wf].sum() and hf[Md].sum() / hf.sum())
    fr_ = np.append(fr_, fend) if tt[-1] < float(met.get('T', tt[-1])) - 1e-6 else fr_
    gain = float(fr_[-1] - fr_[0]); inc = np.diff(fr_)
    R['mass_on'] = float(fr_[0]); R['mass_gain'] = gain; R['max_share'] = float(inc.max() / gain) if gain > 0.05 else None
    def tq(q):
        if gain <= 0.05: return None
        i = int(np.argmax(fr_ >= fr_[0] + q * gain)); return float(tt[min(i, len(tt) - 1)] - ts)
    R['t50'] = tq(0.5); R['t90'] = tq(0.9)
    R['fis'] = met.get('fission_runs'); R['neg'] = met.get('neg_end_cellsteps', met.get('neg_cellsteps')); R['mass_err'] = met.get('mass_err_max', met.get('mass_err'))
    return R

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    rows = [run(a) for a in args]
    if '--json' in sys.argv: print(json.dumps(rows, indent=1)); sys.exit()
    for r in rows:
        f = lambda k, fmt='%.2f': (fmt % r[k]) if isinstance(r.get(k), (int, float)) and r.get(k) is not None else '-'
        print(r['run'], 't_on', f('t_on', '%.0f'), 'pcs', r.get('n_pieces'), 'A', r.get('area'), 'disc', f('disc_iou'), 'iouM', f('iou_mass'), 'asp', f('aspect'), 'sol', f('solidity'),
              'hcv', f('h_cv'), 'in10', f('h_in10'), 'hmed', f('h_med'), 'p10-90', f('h_p10') + '-' + f('h_p90'), 'thin', f('thin_frac'), 'm_on', f('mass_on'), 'maxsh', f('max_share'), 't50', f('t50', '%.0f'), 't90', f('t90', '%.0f'))
