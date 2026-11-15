#!/usr/bin/env python3
"""[verify5] 내 실행(ph_ser 13열)에서 위상 기울기 진단 세 가지와 정맥 최대 성분. usage: m2v.py RUN ...
 (1) 작성자 정의: theta 의 몸 평균 기울기(+wave 는 손 기울기)의 가로 성분 |perp| 시간 평균
 (2) th_eff(수축에 실제 쓰인 위상)의 몸 평균 기울기의 |perp| 시간 평균
 (3) th_eff 의 국소 기울기 rms(셀별 크기)의 시간 평균"""
import json, os, sys, numpy as np
def diag(r, t0=100.0, t1=400.0, root='.'):
    A = np.load(os.path.join(root, 'runs', r, 'ph_ser.npy')).astype(float); P = json.load(open(os.path.join(root, 'runs', r, 'params.json')))
    B = A[(A[:, 0] >= t0) & (A[:, 0] <= t1)]
    d = B[-1, 6:8] - B[0, 6:8]; disp = float(np.hypot(*d)); ax = np.arctan2(d[1], d[0]) if disp >= 5 else 0.0
    gx = B[:, 2].copy(); gy = B[:, 3].copy()
    if P.get('wave_lambda', 0) > 0:
        al = np.radians(P.get('wave_a0', 0.0)) + (2 * np.pi * B[:, 0] / P['wave_Trot'] if P['wave_Trot'] > 0 else 0.0)
        k = 2 * np.pi / P['wave_lambda']; gx += k * np.cos(al); gy += k * np.sin(al)
    perp = -gx * np.sin(ax) + gy * np.cos(ax)
    out = dict(d1=100 * np.abs(perp).mean(), axis=np.degrees(ax))
    if B.shape[1] >= 13:
        ex, ey = B[:, 9], B[:, 10]; eperp = -ex * np.sin(ax) + ey * np.cos(ax)
        out['d2'] = 100 * np.abs(eperp).mean(); out['d3'] = 100 * np.sqrt(B[:, 11] ** 2 + B[:, 12] ** 2).mean()
        out['d3th'] = 100 * np.sqrt(B[:, 4] ** 2 + B[:, 5] ** 2).mean()     # theta 자체의 국소 rms
    return out
if __name__ == '__main__':
    for r in sys.argv[1:]:
        if not os.path.exists(f'runs/{r}/ph_ser.npy'): continue
        D = diag(r); o = json.load(open(f'summ/{r}.json'))
        print(f"{r:16s} 정맥최대 {o['vein4_largest_med']:.3f} | (1) 작성자 정의 |perp|x100 {D['d1']:.2f} | (2) th_eff 몸 평균 |perp|x100 {D.get('d2', float('nan')):.2f} | (3) th_eff 국소 rms x100 {D.get('d3', float('nan')):.2f} (theta 만 {D.get('d3th', float('nan')):.2f}) | 축 {D['axis']:.0f}°")
