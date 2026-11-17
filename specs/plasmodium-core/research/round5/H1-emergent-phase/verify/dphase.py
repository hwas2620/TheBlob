#!/usr/bin/env python3
"""[verify5] 먹이 덩어리 사이의 실제 수축 위상차. hfood.npy 의 원반별 원형 평균 theta(스텝마다) + 손으로 넣은 항(wave/tri, 원반 중심에서 해석적으로)을 더한 theta_eff 의 쌍별 차.
먹는 동안 창에서 rms(감긴 위상차), |평균 벡터|(잠김). ph_noise 는 더하지 않는다(장 재생성이 필요). usage: import 해서 pair_dphase(run_dir) 사용."""
import numpy as np, json, os
def tri(u, P): return np.abs(((u + P / 2) % P) - P / 2) - P / 4
def pair_dphase(rd):
    P = json.load(open(os.path.join(rd, 'params.json'))); m = json.load(open(os.path.join(rd, 'metrics.json')))
    a = np.load(os.path.join(rd, 'hfood.npy')).astype(float); nf = len(P['foods']); dt = P['dt']; t = np.arange(a.shape[0]) * dt
    tt = m['t_touch']; ex = [v for v in m['t_exh'] if v is not None]
    if any(v is None for v in tt) or not ex: return None
    t0 = max(tt) + 20; t1 = min(ex); w = (t >= t0) & (t <= t1)
    N = P['N']; c0 = N / 2 - 0.5; fp = [(c0 + d * np.cos(np.radians(an)), c0 + d * np.sin(np.radians(an))) for an, d in P['foods']]
    th = [a[:, nf + k].copy() for k in range(nf)]
    for k, (fx, fy) in enumerate(fp):
        if P.get('wave_lambda', 0) > 0:
            al = np.radians(P.get('wave_a0', 0.0)) + (2 * np.pi * t / P['wave_Trot'] if P['wave_Trot'] > 0 else 0.0)
            th[k] = th[k] + (2 * np.pi / P['wave_lambda']) * (fx * np.cos(al) + fy * np.sin(al))      # 무게중심 항은 쌍의 차에서 지워진다
        if P.get('tri_k', 0) > 0:
            vy = 0.618 * P.get('tri_v', 0.0) if P.get('tri_vy') is None else P['tri_vy']
            th[k] = th[k] + P['tri_k'] * (np.cos(2 * np.pi * t / P['tri_T']) * tri(fx - P.get('tri_x0', 0.0) - P.get('tri_v', 0.0) * t, P['tri_P']) + np.sin(2 * np.pi * t / P['tri_T']) * tri(fy - P.get('tri_y0', 0.0) - vy * t, P['tri_P']))
    out = {}
    for i in range(nf):
        for j in range(i + 1, nf):
            d = np.angle(np.exp(1j * (th[i] - th[j])))[w]; d = d[np.isfinite(d)]
            d0 = np.angle(np.exp(1j * (a[:, nf + i] - a[:, nf + j])))[w]; d0 = d0[np.isfinite(d0)]
            out[f'{i}-{j}'] = dict(rms=float(np.sqrt((d ** 2).mean())), absmean=float(np.abs(d).mean()), rms_theta_only=float(np.sqrt((d0 ** 2).mean())))
    return out
if __name__ == '__main__':
    import sys
    for rd in sys.argv[1:]: print(rd, json.dumps(pair_dphase(rd)))
