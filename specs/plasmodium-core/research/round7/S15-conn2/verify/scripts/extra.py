#!/usr/bin/env python3
"""주장 밖의 것 (판정 뒤에 만든 것, 판정에는 쓰지 않는다). long 의 저장 상태(lv_t*.npz, 20 시간마다)와 스텝별 숫자로.

  holes     젖지 않은 성분 수 − 1 (몸에 둘러싸인 구멍·고리의 수, 어림)
  rim_frac  가장자리 셀(마른 8이웃이 있는 젖은 셀) / 넓이
  vol_thin  h < 0.3 인 셀에 든 부피의 비율
  top1      가장 큰 굵은 조각(h ≥ 0.6)의 부피 / 몸 부피
  turnover  이웃한 저장 시각 사이에 젖음이 바뀐 셀 / 넓이
  gap       큰 굵은 조각이 둘 이상일 때, 가장 큰 두 조각 사이의 젖은 셀을 따라 잰 가장 짧은 거리(셀)
  comps     (대조) 끝의 조각 수와 크기
usage: extra.py → data/extra.json
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.normpath(os.path.join(HERE, '..', '..', 'model'))
sys.path.insert(0, HERE)
import monitor
from monitor import nbr, RING


def geo_gap(wet, A, B):
    """A 에서 B 까지 젖은 셀만 밟는 8이웃 걸음 수 (A, B 는 젖은 셀 마스크). 이어지지 않으면 None"""
    seen = A.copy(); fr = A.copy(); d = 0
    while fr.any():
        if (fr & B).any(): return d
        nx = np.zeros_like(fr)
        for q in RING: nx |= nbr(fr, q)
        fr = nx & wet & ~seen; seen |= fr; d += 1
    return None


def state_stats(wet, h):
    o = {}
    lab, n = monitor.tlabel(~wet); o['holes'] = max(0, n - 1)
    nd = np.zeros(wet.shape, np.int8)
    for q in RING: nd += ~nbr(wet, q)
    a = int(wet.sum()); o['area'] = a; o['rim_frac'] = float((wet & (nd > 0)).sum() / max(a, 1))
    V = float(h[wet].sum()); o['vol_thin'] = float(h[wet & (h < 0.3)].sum() / V)
    th = wet & (h >= 0.6); lt, nt = monitor.tlabel(th)
    if nt:
        vt = np.bincount(lt[th], weights=h[th], minlength=nt + 1); o['top1'] = float(vt.max() / V)
        big = [k for k in np.argsort(vt)[::-1] if k > 0 and vt[k] >= 0.1 * V]
        o['gap'] = geo_gap(wet, lt == big[0], lt == big[1]) if len(big) >= 2 else None
    else:
        o['top1'] = 0.0; o['gap'] = None
    return o


def main():
    out = {}
    for rd in sorted(glob.glob(os.path.join(MODEL, 'runs', 'b_long_s2[01]*_v15[ck]'))):
        name = os.path.basename(rd)
        if '_s220_' in name or not os.path.exists(os.path.join(rd, 'metrics.json')): continue
        fs = sorted(glob.glob(os.path.join(rd, 'lv_t*.npz'))); rows = []; prev = None
        for f in fs:
            Z = np.load(f); w = Z['wet'].astype(bool); h = Z['h'].astype(float); t = float(Z['t'])
            r = state_stats(w, h); r['t'] = t
            r['turnover'] = float((w ^ prev).sum() / max(int(w.sum()), 1)) if prev is not None else None; prev = w
            rows.append(r)
        L = [r for r in rows if r['t'] >= 1500]
        o = dict(late={k: float(np.mean([r[k] for r in L if r[k] is not None])) if any(r[k] is not None for r in L) else None
                       for k in ('holes', 'rim_frac', 'vol_thin', 'top1', 'turnover', 'area', 'gap')},
                 late_gap_n=sum(r['gap'] is not None for r in L), rows=rows)
        w = np.load(os.path.join(rd, 'wet.npy')); h = np.load(os.path.join(rd, 'h.npy')).astype(float); lab, n = monitor.tlabel(w)
        sz = np.bincount(lab[w], minlength=n + 1)[1:]; vol = np.bincount(lab[w], weights=h[w], minlength=n + 1)[1:]
        o['end_comps'] = dict(n=n, sizes=sorted(sz.tolist(), reverse=True)[:10], vol_frac=sorted((vol / vol.sum()).round(4).tolist(), reverse=True)[:10])
        out[name] = o; print(name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in o['late'].items()}, o['end_comps']['n'], flush=True)
    json.dump(out, open(os.path.join(HERE, '..', 'data', 'extra.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
