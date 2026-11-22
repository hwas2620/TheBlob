#!/usr/bin/env python3
"""[7차 S15] 찢어짐 틈 막기 + 먹이 놓침 거르기 판정. 기준은 ../SCREEN.md (실행 전에 커밋).
대조 s15c와 후보는 모두 이 폴더의 모델 복사본(model/runs). long 지표 정의는 S14 screen_s14.py와 같다(film()은 S8에서 옮김)."""
import json, os, sys, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs'); SUM = os.path.join(HERE, '..', 'summaries')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S4-fan2', 'scripts')); from judge_s4 import long_stats
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label, RING, nb
LONG = [221, 222, 223]; FOOD = [221, 222, 223, 224, 225, 226]; C = 's15c'; TAGS = ['s15d', 's15k', 's15dc']
K = ['split_frac', 'nbig2', 'piece_max', 'thin_late', 'out_late', 'line_end', 'thread_end', 'area_end', 'pieces_end']


def film(rd):
    nb2 = []; thin = []; outl = []; piece = 0.0
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); t = float(Z['t'])
        if t < 100: continue
        wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); V = h.sum(); thick = wet & (h >= 0.3)
        lt = _torus_label(thick); vt = np.bincount(lt.ravel(), weights=h.ravel()); vt[0] = 0; nb2.append(int((vt >= 0.1 * V).sum() >= 2))
        lw = _torus_label(wet); vw = np.bincount(lw.ravel(), weights=h.ravel()); vw[0] = 0; srt = np.sort(vw[1:])[::-1]
        if len(srt) > 1: piece = max(piece, float(srt[1] / V))
        if t >= 1600: thin.append(int((wet & (h < 0.3)).sum())); outl.append(float(1 - srt[0] / V))
    return dict(nbig2=float(np.mean(nb2)), piece_max=piece, thin_late=float(np.mean(thin)), out_late=float(np.mean(outl)))


def lstats(tag, s):
    rd = os.path.join(RUNS, f'b_long_s{s}_{tag}'); f = os.path.join(SUM, f'long_s{s}_{tag}.json')
    if not os.path.exists(os.path.join(rd, 'metrics.json')): return None
    if not os.path.exists(f):
        m = json.load(open(os.path.join(rd, 'metrics.json'))); r = long_stats(rd); r.update(film(rd))
        Z = np.load(os.path.join(rd, 'vs_t2000.npz')); w = Z['wet'].astype(bool); hh = np.where(w, Z['h'].astype(float), 0.0)
        xb = [~nb(w, d) for d in RING]; Nc = np.zeros(w.shape, np.int8)
        for q in (0, 2, 4, 6): Nc += xb[q].astype(np.int8) - (xb[q] & xb[q + 1] & xb[(q + 2) % 8]).astype(np.int8)
        r.update(line_end=int((w & (Nc > 1)).sum()), thread_end=int((w & (hh < 0.3) & (Nc > 1)).sum()), pieces_end=int(_torus_label(w).max()) - 1, area_end=m['area_end'])
        json.dump(r, open(f, 'w'))
    return json.load(open(f))


def met(scn, s, tag):
    f = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}', 'metrics.json')
    return json.load(open(f)) if os.path.exists(f) else None


def health(scn, s, tag):
    m = met(scn, s, tag); n = int(_torus_label(np.load(os.path.join(RUNS, f'b_{scn}_s{s}_{tag}', 'wet.npy')).astype(bool)).max())
    return dict(ncomp=n, neg=m['neg_end_cellsteps'], err=m['mass_err_max'], crumb=m['V_crumb'] / m['V0'])


M = {}
for tag in [C] + TAGS:
    rs = [lstats(tag, s) for s in LONG]
    if any(r is None for r in rs): print(tag, 'long 빠짐', [s for s, r in zip(LONG, rs) if r is None]); continue
    M[tag] = {k: float(np.mean([r[k] for r in rs])) for k in K}
    print(f'{tag:6s} ' + ' '.join(f'{k}={M[tag][k]:.3g}' for k in K))
    for s, r in zip(LONG, rs): print(f'   s{s} ' + ' '.join(f'{k}={r[k]:.3g}' for k in K))
print()
for tag in TAGS:
    if tag not in M or C not in M: continue
    x, c = M[tag], M[C]
    c1 = x['split_frac'] <= 0.5 * c['split_frac'] and x['nbig2'] <= 0.5 * c['nbig2']; c2 = x['out_late'] <= 0.5 * c['out_late']
    c3 = x['thin_late'] <= c['thin_late']; c4 = x['line_end'] <= c['line_end']
    fm = [(met('food4', s, C), met('food4', s, tag)) for s in FOOD]
    if any(a is None or b is None for a, b in fm): print(tag, 'food4 빠짐'); continue
    ra = sum(all(t is not None for t in a['t_touch']) for a, _ in fm); rb = sum(all(t is not None for t in b['t_touch']) for _, b in fm)
    late = sum(1 for a, b in fm for ta, tb in zip(a['t_touch'], b['t_touch']) if ta is not None and (tb is None or tb > ta + 50))
    c5 = rb >= ra and late <= 1
    H = [health(scn, s, tag) for scn, ss in (('long', LONG), ('food4', FOOD)) for s in ss]
    c6 = all(h['ncomp'] == 1 and h['neg'] == 0 and h['err'] < 1e-10 and h['crumb'] < 0.01 for h in H)
    print(f'{tag} (기준 {C}): 1 갈라짐 {c1} ({x["split_frac"]:.3f}/{x["nbig2"]:.3f} vs {c["split_frac"]:.3f}/{c["nbig2"]:.3f}) | 2 몸 밖 {c2} ({x["out_late"]:.3f} vs {c["out_late"]:.3f}) '
          f'| 3 얇은 칸 {c3} ({x["thin_late"]:.0f} vs {c["thin_late"]:.0f}) | 4 줄 칸 {c4} ({x["line_end"]:.0f} vs {c["line_end"]:.0f}) '
          f'| 5 food4 모두 닿음 {rb} vs {ra}, 늦음 {late} → {c5} | 6 건강 {c6} (덩어리 {[h["ncomp"] for h in H]}, 음수 {sum(h["neg"] for h in H)}, 부피오차 최대 {max(h["err"] for h in H):.1e}, 버린 최대 {max(h["crumb"] for h in H):.1e}) '
          f'→ {"넘김" if c1 and c2 and c3 and c4 and c5 and c6 else "탈락"}')
    print(f'   [관문 아님: 끝 넓이 {x["area_end"] / c["area_end"]:.2f}배, 끝 실 칸 {x["thread_end"]:.0f} (대조 {c["thread_end"]:.0f})]')
    for s, (a, b) in zip(FOOD, fm): print(f'   food4 s{s}: 대조 {a["t_touch"]} 후보 {b["t_touch"]}')
print('\n진단 (판정 아님, 이미 쓴 시드)')
for s, tags in ((196, ('s15d', 's15dc')), (197, ('s15d', 's15dc')), (199, ('s15d',))):
    for tag in tags:
        m = met('food4', s, tag)
        if m is None: print(f'  food4 s{s} {tag} 빠짐'); continue
        print(f'  food4 s{s} {tag}: 닿음 {m["t_touch"]} 끝 덩어리 {health("food4", s, tag)["ncomp"]}')
