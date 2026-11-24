#!/usr/bin/env python3
"""[CRITERIA_CHANGES 2] 균핵이 모이는 빠르기: 장면마다 '마지막 장면의 가장 큰 조각 자리'(+1칸 둘레) 안에 든 부피의 몫.
usage: scl_mass.py RUN_DIR [...]   -> verify6/data/scl_mass.json 에 덧붙인다
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
OUT = os.environ.get('VERIFY6_DATA') or os.path.normpath(os.path.join(HERE, '..', 'data'))


def one(rd):
    files = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
    Zl = np.load(files[-1]); wl = Zl['wet'].astype(bool); hl = np.where(wl, Zl['h'], 0.0)
    lab, n = M.tlabel(wl)
    vol = np.bincount(lab.ravel(), weights=hl.ravel(), minlength=n + 1); vol[0] = -1
    foot = M.dilate8(lab == int(np.argmax(vol)))
    ser = []
    for f in files:
        Z = np.load(f); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); V = float(h.sum())
        ser.append([float(Z['t']), float(h[foot].sum() / max(V, 1e-12))])
    return ser


if __name__ == '__main__':
    p = os.path.join(OUT, 'scl_mass.json'); D = json.load(open(p)) if os.path.exists(p) else {}
    for rd in sys.argv[1:]:
        D[os.path.basename(rd.rstrip('/'))] = one(rd); print(os.path.basename(rd.rstrip('/')), 'ok', flush=True)
    json.dump(D, open(p, 'w'))
