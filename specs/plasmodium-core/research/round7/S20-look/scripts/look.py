#!/usr/bin/env python3
"""[7차 S20] 겉모습 진단 측정.
  threads TAG SEED...   : long t 600/1000/1400에서 가장 긴 외가닥 실(젖은 이웃 ≤ 2, h < 0.6) 길이, 30칸 넘는 실 수, 자유 끝 수
  jump TAG SEED...      : mig 무게중심의 유인원 방향 옆 어긋남(칸) t 100, 150, 200, 400 (+ = 반시계)
  scl TAG SEED...       : long 균핵: t_scl, 끝 몸 수, 가장 큰 몸의 넓이·축비·볼록도·두께 고르기, 맺힘에 걸린 시간(얇은 칸 몫 ≤ 5%가 된 첫 저장 시각 − t_scl)"""
import sys, os, glob, re, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'model'))
from ref_model import _torus_label, nb, RING
def frames(d): return sorted(glob.glob(os.path.join(d, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
def load(d, t): Z = np.load(os.path.join(d, f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); return Z, w, np.where(w, Z['h'], 0.0)
def threads(w, h):
    nw = np.zeros(w.shape, int)
    for dd in RING: nw += nb(w, dd)
    line = w & (nw <= 2) & (h < 0.6); lab = _torus_label(line)
    if lab.max() == 0: return 0, 0, 0
    sz = np.bincount(lab.ravel())[1:]; tips = int((w & (nw <= 1)).sum())
    return int(sz.max()), int((sz >= 30).sum()), tips
def shape(m, h):      # 축비(작은/큰 고유값의 제곱근), 볼록도(넓이/볼록껍질 넓이), 두께 변동계수
    from scipy.spatial import ConvexHull
    ys, xs = np.nonzero(m); N = m.shape[0]
    cy = np.angle(np.exp(2j * np.pi * ys / N).mean()) * N / (2 * np.pi); cx = np.angle(np.exp(2j * np.pi * xs / N).mean()) * N / (2 * np.pi)
    dy = ((ys - cy + N / 2) % N) - N / 2; dx = ((xs - cx + N / 2) % N) - N / 2
    ev = np.linalg.eigvalsh(np.cov(np.vstack([dx, dy])) + 1e-9 * np.eye(2)); ar = float(np.sqrt(ev[0] / ev[1]))
    try: hull = ConvexHull(np.vstack([dx, dy]).T).volume; cv = float(m.sum() / max(hull, 1.0))
    except Exception: cv = float('nan')
    hv = h[m]; return ar, min(cv, 1.0), float(hv.std() / max(hv.mean(), 1e-9))
mode, tag = sys.argv[1], sys.argv[2]; seeds = [int(x) for x in sys.argv[3:]]
for s in seeds:
    if mode == 'threads':
        d = os.path.join(R, f'b_long_s{s}_{tag}'); out = []
        for t in (600, 1000, 1400):
            try: Z, w, h = load(d, t); out.append(threads(w, h))
            except FileNotFoundError: out.append(None)
        print(tag, s, '(가장 긴 실, 30칸 넘는 실 수, 자유 끝) t600/1000/1400:', out)
    elif mode == 'jump':
        d = os.path.join(R, f'b_mig_s{s}_{tag}'); fs = frames(d); c0 = np.load(fs[0])['cen']; N = np.load(fs[0])['wet'].shape[0]
        a = np.radians(27); res = []
        for t in (100, 150, 200, 400):
            try: c = np.load(os.path.join(d, f'vs_t{t:04d}.npz'))['cen']
            except FileNotFoundError: res.append(None); continue
            dd = ((c - c0 + N / 2) % N) - N / 2; res.append(round(float(-dd[0] * np.sin(a) + dd[1] * np.cos(a)), 1))
        print(tag, s, '옆 어긋남(칸) t100/150/200/400:', res)
    elif mode == 'scl':
        d = os.path.join(R, f'b_long_s{s}_{tag}'); m = json.load(open(os.path.join(d, 'metrics.json'))); ts = m.get('t_scl')
        w = np.load(os.path.join(d, 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(d, 'h.npy')), 0.0)
        lab = _torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]; big = lab == int(np.argmax(vol)) + 1
        ar, cv, hcv = shape(big, h); tf = None; t90 = None
        if ts is not None:
            for f in frames(d):
                t = int(re.findall(r'vs_t(\d+)', f)[0])
                if t < ts: continue
                Z = np.load(f); ww = Z['wet'].astype(bool); hh = np.where(ww, Z['h'], 0.0)
                if (ww & (hh < 0.5)).sum() / max(ww.sum(), 1) <= 0.05 and tf is None: tf = round(t - ts, 1)
                if hh[ww & (hh >= 1.5)].sum() >= 0.9 * hh.sum() and t90 is None: t90 = round(t - ts, 1)
                if tf is not None and t90 is not None: break
        traj = []
        if ts is not None:
            for f in frames(d):
                t = int(re.findall(r'vs_t(\d+)', f)[0])
                if t < ts - 20 or len(traj) >= 8: continue
                Z = np.load(f); ww = Z['wet'].astype(bool); hh = np.where(ww, Z['h'], 0.0); traj.append((t, round(float(hh[ww & (hh >= 1.5)].sum() / max(hh.sum(), 1e-9)), 2)))
        print(tag, s, '두꺼운 칸 부피 몫 (t, 몫):', traj)
        print(tag, s, '균핵', ts, '얇은 칸 사라짐', tf, '부피 90%가 두꺼운 칸', t90, '| 끝 몸', len(vol), '가장 큰 몸 넓이', int(big.sum()), '축비', round(ar, 2), '볼록도', round(cv, 2), '두께 변동', round(hcv, 2), '얇은 칸 몫', round(float((w & (h < 0.5)).sum()) / w.sum(), 3))
