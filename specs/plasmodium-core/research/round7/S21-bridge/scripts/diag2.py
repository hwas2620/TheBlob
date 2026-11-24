"""[7차 S21] 진단 2 풀이 (진단 1 풀이에서 꼬리표만 바꿈). 기준선 s20z·s20c는 ../../S20-look/model/runs 에서 읽는다.
python3 diag1.py"""
import os, sys, glob, re, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..', 'model', 'runs'); R20 = os.path.join(HERE, '..', '..', 'S20-look', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label, nb, RING

def rd(scn, s, tag): return os.path.join(R20 if tag.startswith('s20') else R, f'b_{scn}_s{s}_{tag}')
def met(scn, s, tag): return json.load(open(os.path.join(rd(scn, s, tag), 'metrics.json')))
def frames(d): return sorted(glob.glob(os.path.join(d, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
def strands(w, h):
    nw = np.zeros(w.shape, int)
    for dd in RING: nw += nb(w, dd)
    lab = _torus_label(w & (nw <= 2) & (h < 0.6)); sz = np.bincount(lab.ravel())[1:]
    return (int(sz.max()) if sz.size else 0), int((w & (nw <= 1)).sum())
def shape_ar(m):
    ys, xs = np.nonzero(m); N_ = m.shape[0]
    cy = np.angle(np.exp(2j * np.pi * ys / N_).mean()) * N_ / (2 * np.pi); cx = np.angle(np.exp(2j * np.pi * xs / N_).mean()) * N_ / (2 * np.pi)
    dy = ((ys - cy + N_ / 2) % N_) - N_ / 2; dx = ((xs - cx + N_ / 2) % N_) - N_ / 2
    ev = np.linalg.eigvalsh(np.cov(np.vstack([dx, dy])) + 1e-9 * np.eye(2)); return float(np.sqrt(ev[0] / ev[1]))
def long_look(s, tag):
    d = rd('long', s, tag); sl = []; tp = []
    for t in (1000, 1200, 1400):
        Z = np.load(os.path.join(d, f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); a, b = strands(w, h); sl.append(a); tp.append(b)
    sl2 = []      # 600~1600 매 200
    for t in range(600, 1601, 200):
        f = os.path.join(d, f'vs_t{t:04d}.npz')
        if os.path.exists(f): Z = np.load(f); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); sl2.append(strands(w, h)[0])
    m = met('long', s, tag); ts = m.get('t_scl'); t90 = None; ar = None
    if ts is not None:
        for f in frames(d):
            t = int(re.findall(r'vs_t(\d+)', f)[0])
            if t < ts: continue
            Z = np.load(f); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0)
            if h[w & (h >= 1.5)].sum() >= 0.9 * h.sum(): t90 = round(t - ts, 1); break
        if float(m['t_end']) - ts >= 150:
            w = np.load(os.path.join(d, 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(d, 'h.npy')), 0.0)
            lab = _torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]; ar = round(shape_ar(lab == int(np.argmax(vol)) + 1), 2)
    return sl, tp, sl2, (round(ts, 1) if ts else None), t90, ar, m.get('fission_runs') or 0
def health(scn, s, tag):
    b = met(scn, s, tag); return b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and abs(b['V_crumb']) / b['V0'] < 0.001 and b.get('stop', '') in ('', None)
def direction_err(tag, s):
    fs = frames(rd('mig', s, tag)); c0 = np.load(fs[0])['cen']; c1 = None
    for f in fs:
        Z = np.load(f)
        if float(Z['t']) <= 200: c1 = Z['cen']
    N = np.load(fs[0])['wet'].shape[0]; dd = ((c1 - c0 + N / 2) % N) - N / 2; a = np.arctan2(dd[1], dd[0])
    return float(np.degrees((a - np.radians(27) + np.pi) % (2 * np.pi) - np.pi))

out = []
LONG = range(491, 501)
for tag in ('s20z', 's21a', 's21g', 's21h'):
    rows = [long_look(s, tag) for s in LONG]
    sl = [x for r in rows for x in r[0]]; tp = [x for r in rows for x in r[1]]; sl2 = [x for r in rows for x in r[2]]
    out.append(f'long {tag}: L1 가장 긴 실(1000·1200·1400) 평균 {np.mean(sl):.1f} 최대 {max(sl)}  {sl}')
    out.append(f'   자유 끝 평균 {np.mean(tp):.1f}; 600~1600 매 200 가장 긴 실 평균 {np.mean(sl2):.1f}, 100칸 넘는 것 {sum(x >= 100 for x in sl2)}/{len(sl2)}')
    out.append(f'   균핵 시각 {[r[3] for r in rows]}')
    out.append(f'   맺힘 t90 {[r[4] for r in rows]} 중앙 {np.median([r[4] for r in rows if r[4] is not None]):.1f}; 축비 {[r[5] for r in rows]}; 갈라짐 {[r[6] for r in rows]}')
    if tag != 's20z': out.append(f'   건강 {sum(health("long", s, tag) for s in LONG)}/10, 실 끝을 몸으로 돌린 칸 {[met("long", s, tag).get("tiphome_cells") for s in LONG]}')
for tag in ('s20c', 's20z', 's21a', 's21h'):
    e = [direction_err(tag, s) for s in range(491, 499)]; tt = [met('mig', s, tag)['t_touch'][0] for s in range(491, 499)]
    hh = '' if tag.startswith('s20') else f', 건강 {sum(health("mig", s, tag) for s in range(491, 499))}/8'
    out.append(f'mig {tag}: 방향 오차 {[round(x, 1) for x in e]} 부호 평균 {np.mean(e):+.1f} 절댓값 평균 {np.mean(np.abs(e)):.1f}; 닿은 시각 평균 {np.mean([x if x is not None else 400 for x in tt]):.1f} {tt}{hh}')
for tag, ss in (('s20z', range(491, 497)), ('s21h', range(491, 497))):
    tt = [met('food4', s, tag)['t_touch'] for s in ss]
    allr = sum(all(x is not None for x in r) for r in tt); last = [max(x if x is not None else 700 for x in r) for r in tt]
    hh = '' if tag.startswith('s20') else f', 건강 {sum(health("food4", s, tag) for s in ss)}/{len(ss)}'
    out.append(f'food4 {tag} ({ss.start}~{ss.stop - 1}): 모두 닿음 {allr}/{len(ss)}, 마지막 먹이 {[round(x, 1) for x in last]}{hh}')
    out.append(f'   {[[None if x is None else round(x) for x in r] for r in tt]}')
print('\n'.join(out))
