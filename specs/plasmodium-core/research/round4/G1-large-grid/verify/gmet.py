#!/usr/bin/env python3
"""[verify] G1 저장 배열(wet.npy, h.npy, C_edges.npy, twet.npy)에서 윤곽의 대각/축 비와 띠 폭을 독립적으로 잰다. anaG.py 를 import 하지 않는다.
usage: gmet.py RUN_DIR [RUN_DIR ...]

윤곽: 중심 = 구멍을 메운 젖은 영역의 무게중심. 방향 φ(1도 간격)마다 젖은 셀의 최대 반지름 R(φ).
   비(최대) = 대각 4방향 ±7.5도 안의 최대 R 의 평균 / 축 4방향의 같은 값   (실험자 정의와 같은 꼴, 중심만 다름)
   비(평균) = 대각 ±7.5도 안 R(φ) 평균 / 축 ±7.5도 안 R(φ) 평균            (돌출 하나에 덜 민감)
   a4 = R(φ) 의 4차 푸리에 성분(복소). 격자에 정렬된 비등방이면 위상이 0도(축이 김) 또는 180도(대각이 김). 비 ≈ (1 - Re a4)/(1 + Re a4)... (a4 는 R0 로 나눈 값의 2배)
띠: 중심에서 0.5도 간격 광선을 쏘아 0.5셀 간격으로 젖음을 읽는다.
   w_tot(φ)  = 광선 위 젖은 길이의 합
   w_out(φ)  = 가장 바깥 젖은 점에서 안쪽으로, 3셀 넘는 마른 틈이 나올 때까지의 길이(바깥 띠의 폭)
   식: w_식 = V/(2π·R·0.45),  고리 넓이로 정확히 풀면 w_고리 = R - sqrt(R² - V/(0.45π))
"""
import numpy as np, json, sys, os
from scipy import ndimage as ndi

DX = [1, 0, 1, 1]; DY = [0, 1, 1, -1]


def contour(mask, cx, cy):
    ys, xs = np.nonzero(mask); ang = (np.degrees(np.arctan2(ys - cy, xs - cx)) % 360); rr = np.hypot(ys - cy, xs - cx)
    b = np.floor(ang).astype(int) % 360; R = np.zeros(360)
    np.maximum.at(R, b, rr)
    R[R == 0] = np.nan
    if np.isnan(R).any():
        idx = np.arange(360); ok = ~np.isnan(R); R = np.interp(idx, idx[ok], R[ok], period=360)
    return R


def sector(R, a, half=7.5):
    d = np.abs(((np.arange(360) + 0.5 - a + 180) % 360) - 180)
    return R[d <= half]


def analyse(rd):
    P = json.load(open(os.path.join(rd, 'params.json')))
    wet = np.load(os.path.join(rd, 'wet.npy')).astype(bool); h = np.load(os.path.join(rd, 'h.npy')).astype(float); C = np.load(os.path.join(rd, 'C_edges.npy')).astype(float)
    N = wet.shape[0]; V = float(h.sum()); A = int(wet.sum()); out = dict(run=os.path.basename(rd.rstrip('/')), N=N, tau_a=P.get('tau_a'), wave=P.get('wave_lambda') or 0, wet_rho=P.get('wet_rho'), seed=P.get('seed'),
                                                                 V=round(V, 1), area=A, hbar=round(V / A, 4), hmin=float(h[wet].min()))
    out['hbar_median'] = round(float(np.median(h[wet])), 3)
    filled = ndi.binary_fill_holes(ndi.binary_closing(wet, structure=np.ones((3, 3)), iterations=2))
    ys, xs = np.nonzero(filled); cy, cx = ys.mean(), xs.mean(); out['centre'] = [round(cx, 1), round(cy, 1)]
    R = contour(wet, cx, cy)
    ax_max = np.mean([sector(R, a).max() for a in (0, 90, 180, 270)]); dg_max = np.mean([sector(R, a).max() for a in (45, 135, 225, 315)])
    ax_mean = np.mean([sector(R, a).mean() for a in (0, 90, 180, 270)]); dg_mean = np.mean([sector(R, a).mean() for a in (45, 135, 225, 315)])
    ph = np.radians(np.arange(360) + 0.5); R0 = R.mean(); a4 = 2 * (R * np.exp(-4j * ph)).mean() / R0; a2 = 2 * (R * np.exp(-2j * ph)).mean() / R0; a8 = 2 * (R * np.exp(-8j * ph)).mean() / R0
    out.update(ratio_max=round(float(dg_max / ax_max), 3), ratio_mean=round(float(dg_mean / ax_mean), 3), R_axis=round(float(ax_max), 1), R_diag=round(float(dg_max), 1), R_mean=round(float(R0), 1),
               a4_amp=round(float(abs(a4)), 4), a4_phase_deg=round(float(np.degrees(np.angle(a4))), 0), a4_real=round(float(a4.real), 4), a2_amp=round(float(abs(a2)), 3), a8_real=round(float(a8.real), 4))
    # 실험자 정의(젖은 셀 좌표의 평균을 중심으로) 재계산
    ysw, xsw = np.nonzero(wet); Rw = contour(wet, xsw.mean(), ysw.mean())
    out['ratio_max_wetcentre'] = round(float(np.mean([sector(Rw, a).max() for a in (45, 135, 225, 315)]) / np.mean([sector(Rw, a).max() for a in (0, 90, 180, 270)])), 3)
    # 한 번이라도 젖었던 자리(발자국)의 윤곽
    tw = os.path.join(rd, 'twet.npy')
    if os.path.exists(tw):
        foot = np.load(tw) >= 0; Rf = contour(foot, cx, cy)
        out['ratio_max_footprint'] = round(float(np.mean([sector(Rf, a).max() for a in (45, 135, 225, 315)]) / np.mean([sector(Rf, a).max() for a in (0, 90, 180, 270)])), 3)
        out['ratio_mean_footprint'] = round(float(np.mean([sector(Rf, a).mean() for a in (45, 135, 225, 315)]) / np.mean([sector(Rf, a).mean() for a in (0, 90, 180, 270)])), 3)
    # ---- 띠 ----
    out['wet_frac_of_filled'] = round(float(A / filled.sum()), 3)
    phis = np.radians(np.arange(0, 360, 0.5)); wt = []; wo = []; rout = []
    rs = np.arange(0, R.max() + 3, 0.5)
    for p_ in phis:
        yy = np.clip(np.rint(cy + rs * np.sin(p_)).astype(int), 0, N - 1); xx = np.clip(np.rint(cx + rs * np.cos(p_)).astype(int), 0, N - 1)
        w = wet[yy, xx]
        if not w.any(): continue
        io = np.nonzero(w)[0][-1]; rout.append(rs[io]); wt.append(0.5 * w.sum())
        gap = 0; i = io
        while i >= 0:
            if w[i]: gap = 0
            else:
                gap += 1
                if gap > 6: break            # 3셀 넘는 마른 틈
            i -= 1
        wo.append(rs[io] - rs[min(i + gap, io)] + 0.5 if i >= 0 else rs[io])
    wt = np.array(wt); wo = np.array(wo); rout = np.array(rout)
    out.update(w_tot_med=round(float(np.median(wt)), 1), w_tot_q25=round(float(np.percentile(wt, 25)), 1), w_tot_q75=round(float(np.percentile(wt, 75)), 1),
               w_out_med=round(float(np.median(wo)), 1), w_out_q25=round(float(np.percentile(wo, 25)), 1), w_out_q75=round(float(np.percentile(wo, 75)), 1), R_ray_mean=round(float(rout.mean()), 1))
    # 반지름 정규화 분포: 젖은 셀의 rho = r/R(phi)
    ang = (np.degrees(np.arctan2(ysw - cy, xsw - cx)) % 360); rho = np.hypot(ysw - cy, xsw - cx) / R[np.floor(ang).astype(int) % 360]
    out['wet_rho_q10_q50_q90'] = [round(float(v), 3) for v in np.percentile(rho, [10, 50, 90])]
    out['wet_frac_inner_half'] = round(float((rho < 0.5).mean()), 3)          # 고리라면 작다(균일 원반이면 0.25)
    # 실험자 방식(메운 모양의 가장자리까지 거리)도 내 코드로 다시
    dist = ndi.distance_transform_edt(filled); dw = dist[wet]; out['edt_wet_med_p90'] = [round(float(np.median(dw)), 1), round(float(np.percentile(dw, 90)), 1)]
    Rr = out['R_axis']
    out['w_formula_Raxis'] = round(V / (2 * np.pi * Rr * 0.45), 1); out['w_formula_Rmean'] = round(V / (2 * np.pi * R0 * 0.45), 1)
    disc = R0 ** 2 - V / (0.45 * np.pi); out['w_annulus_Rmean'] = round(float(R0 - np.sqrt(disc)), 1) if disc > 0 else None
    out['w_area_over_perim'] = round(float(A / (2 * np.pi * R0)), 1)       # 넓이/둘레: 식에서 0.45 를 실제 평균 두께로 바꾼 것과 같다
    # ---- 정맥(C>4) 최대 성분 (경계 있는 격자: 감김 없음) ----
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    S = []; D = []
    for k in range(4):
        ys_, xs_ = np.nonzero(C[k] > 4.0); y2 = ys_ + DY[k]; x2 = xs_ + DX[k]; ok = (y2 >= 0) & (y2 < N) & (x2 >= 0) & (x2 < N)
        S.append((ys_ * N + xs_)[ok]); D.append((y2 * N + x2)[ok])
    S = np.concatenate(S); D = np.concatenate(D)
    if S.size:
        nc, lab = connected_components(coo_matrix((np.ones(S.size, np.int8), (S, D)), shape=(N * N, N * N)), directed=False)
        out['vein_E'] = int(S.size); out['vein_largest'] = round(float(np.bincount(lab[S]).max() / S.size), 3)
        vc = np.zeros(N * N, bool); vc[S] = True; vc[D] = True; dv = dist.ravel()[vc & wet.ravel()]
        out['edt_vein_med_p90'] = [round(float(np.median(dv)), 1), round(float(np.percentile(dv, 90)), 1)]
    return out


if __name__ == '__main__':
    for rd in sys.argv[1:]:
        o = analyse(rd); print(json.dumps(o, ensure_ascii=False))
