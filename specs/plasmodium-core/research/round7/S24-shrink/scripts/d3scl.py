"""[S24 진단 4] 균핵 실행 요약: 넓이 몰림(검증자 area_timing), 끝 덩이 모양·두께(검증자 lump_metrics), 끝 넓이 (판정 아님).
python3 d3scl.py 꼬리표,꼬리표 [시나리오]"""
import sys, os, json, glob, numpy as np
sys.path.insert(0, '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/verify8/scripts')
from measure import area_timing, lump_metrics
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label
R = {'s23v': '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model/runs', 's23c': '/home/user/TheBlob/specs/plasmodium-core/research/round7/S23-fix/model/runs'}
R24 = os.path.join(HERE, '..', 'model', 'runs')
tags = sys.argv[1].split(','); scn = sys.argv[2] if len(sys.argv) > 2 else '*'
for tg in tags:
    rows = []
    for rd in sorted(glob.glob(os.path.join(R.get(tg, R24), f'b_{scn}_s*_{tg}'))):
        m = json.load(open(os.path.join(rd, 'metrics.json'))); P = json.load(open(os.path.join(rd, 'params.json'))); ts = m.get('t_scl')
        if ts is None: continue
        ser = np.load(os.path.join(rd, 'series.npz')); o = area_timing(ser['area'], P['dt'], ts)
        w = np.load(os.path.join(rd, 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(rd, 'h.npy')), 0.0); N = w.shape[0]
        lab = _torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel()); vol[0] = 0; big = lab == int(np.argmax(vol))
        L = lump_metrics(big, h, N)[0]; ncomp = int(lab.max())
        fok = (L['sp_h_d'] or 0) >= 0.5 and (L['h_ratio'] or 0) >= 1.5 and L['h_cv'] >= 0.15 and (L['max_step_frac'] or 0) <= 0.5
        dok = (o['t90'] or 0) >= 30 and (o['max10'] or 1) <= 0.35
        rows.append((dok, fok))
        print(f"{tg:5s} {os.path.basename(rd):26s} t_scl {ts:7.1f} A {o['A0']:5d}→{L['area']:4d} 조각 {ncomp} t10 {o['t10']} t50 {o['t50']} t90 {o['t90']} max10 {o['max10']} {'d✓' if dok else 'd✗'} | "
              f"sp {L['sp_h_d']} c/e {L['h_ratio']} cv {L['h_cv']} st {L['max_step_frac']} {'f✓' if fok else 'f✗'} | 구멍 {L['holes']} 볼록 {L['solidity']} 원판 {L['disc_iou']}")
    if rows: print(f"  {tg}: (d) 통과 {sum(r[0] for r in rows)}/{len(rows)}, (f) 통과 {sum(r[1] for r in rows)}/{len(rows)}")
