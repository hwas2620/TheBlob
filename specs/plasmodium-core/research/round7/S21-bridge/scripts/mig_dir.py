#!/usr/bin/env python3
"""이주 방향 오차: 처음 → t 200 무게중심 이동 방향이 유인원 방향에서 벗어난 각도 (+ = 반시계).
usage: mig_dir.py TAG TARGET_DEG SEED... (시나리오는 환경 변수 SCN, 기본 mig)"""
import sys, os, glob, re, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SCN = os.environ.get('SCN', 'mig'); tag = sys.argv[1]; tgt = float(sys.argv[2]); seeds = [int(x) for x in sys.argv[3:]]
errs = []; touch = []
for s in seeds:
    rd = os.path.join(HERE, '..', 'model', 'runs', f'b_{SCN}_s{s}_{tag}')
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    c0 = np.load(fs[0])['cen']; c1 = None
    for f in fs:
        Z = np.load(f)
        if float(Z['t']) <= 200: c1 = Z['cen']
    N = np.load(fs[0])['wet'].shape[0]; d = ((c1 - c0 + N / 2) % N) - N / 2; a = np.arctan2(d[1], d[0])
    errs.append(round(float(np.degrees((a - np.radians(tgt) + np.pi) % (2 * np.pi) - np.pi)), 1))
    touch.append(json.load(open(os.path.join(rd, 'metrics.json')))['t_touch'][0])
print(SCN, tag, '목표', tgt, '방향 오차', errs, '평균', round(float(np.mean(errs)), 1), '|평균|', round(float(np.mean(np.abs(errs))), 1), '닿은 시각', touch)
