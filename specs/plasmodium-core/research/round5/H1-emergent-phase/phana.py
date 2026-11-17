#!/usr/bin/env python3
"""[H1] 위상 무늬 진단. ph_ser.npy (t, R, <dθ/dx>, <dθ/dy>, rms dx, rms dy, cx, cy, cv_h) 에서 창 [t0, t1] 의 요약을 낸다.
usage: phana.py t0 t1 RUN ...   진행 축은 창 안의 무게중심 이동 방향(이동이 5셀 미만이면 x축)으로 잡는다.
수축파 실행(wave_lambda>0)은 손으로 넣은 기울기 (2π/λ)(cos α, sin α) 를 더한 값도 낸다(θ_eff 의 기울기).
주의(검증자 지적): 손으로 넣은 항을 더하는 것은 수축파뿐이다. 삼각 격자(tri_k)와 위상 잡음(ph_noise) 실행은 θ 의 기울기만 나오므로
이 진단으로 변형끼리 견주면 안 된다. θ_eff 의 기울기는 verify/m2v.py 가 잰다."""
import json, os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); t0 = float(sys.argv[1]); t1 = float(sys.argv[2])
print('run                 R     |<g>|x100  par   perp  | rms par  perp x100 | time-mean |perp|x100 | dir sweep(deg) | axis(deg) disp | local rms |grad| x100')
for r in sys.argv[3:]:
    f = os.path.join(HERE, 'runs', r, 'ph_ser.npy')
    if not os.path.exists(f): print(r, '(없음)'); continue
    A = np.load(f); P = json.load(open(os.path.join(HERE, 'runs', r, 'params.json')))
    m = (A[:, 0] >= t0) & (A[:, 0] <= t1); B = A[m]
    if len(B) < 3: print(r, '(창이 비었음)'); continue
    d = B[-1, 6:8] - B[0, 6:8]; disp = float(np.hypot(*d)); ax = np.arctan2(d[1], d[0]) if disp >= 5 else 0.0
    gx = B[:, 2].astype(float).copy(); gy = B[:, 3].astype(float).copy()
    if P.get('wave_lambda', 0) > 0:
        al = np.radians(P.get('wave_a0', 0.0)) + (2 * np.pi * B[:, 0] / P['wave_Trot'] if P['wave_Trot'] > 0 else 0.0)
        k = 2 * np.pi / P['wave_lambda']; gx += k * np.cos(al); gy += k * np.sin(al)
    par = gx * np.cos(ax) + gy * np.sin(ax); perp = -gx * np.sin(ax) + gy * np.cos(ax)
    ang = np.unwrap(np.arctan2(gy, gx)); sweep = float(np.degrees(ang.max() - ang.min()))
    print(f"{r:18s} {B[:,1].mean():.3f}  {100*np.hypot(gx.mean(), gy.mean()):6.2f}  {100*par.mean():6.2f} {100*perp.mean():6.2f} | {100*np.sqrt((par**2).mean()):6.2f} {100*np.sqrt((perp**2).mean()):6.2f} |"
          f" {100*np.abs(perp).mean():6.2f} | {sweep:7.0f} | {np.degrees(ax):6.1f} {disp:5.1f} | {100*np.sqrt(B[:,4]**2 + B[:,5]**2).mean():6.2f}")
