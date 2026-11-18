#!/usr/bin/env python3
"""[검증자] 이주 시험의 앞면·뒷면·무게중심 위치를 저장된 상태(vs_t*.npz, 20 시간 단위 간격)에서 직접 잰다.
유인원 방향(첫 먹이의 각도)으로 젖은 셀을 사영해 앞면 = 99백분위, 뒷면 = 1백분위, 무게중심 = 두께 가중 평균.
속도는 주어진 시간 구간의 직선 맞춤 기울기(셀/시간 단위). 스텝당 전진 = 속도 × dt.
usage: front.py T1,T2 NAME ...   (구간 기본 100,400)   또는 모듈로 import 해서 track(name) 사용"""
import json, os, sys, glob, numpy as np, vmet
HERE = os.path.dirname(os.path.abspath(__file__))


def track(name, root=None):
    rd = os.path.join(root or os.path.join(HERE, 'runs'), name)
    P = json.load(open(os.path.join(rd, 'params.json'))); N = P['N']; c0 = N / 2 - 0.5
    ang = np.radians(P['foods'][0][0]); ux, uy = np.cos(ang), np.sin(ang)
    yy, xx = np.indices((N, N)); out = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); cen = Z['cen']; t = float(Z['t'])
        # 가장 큰 몸 성분(부피 기준, 8연결·토러스)만 쓴다: 뒤에 남은 작은 조각이 주기 경계를 넘어 접혀 앞면으로 잡히는 것을 막는다
        src, dst, cc, kk = vmet.edge_list(Z['C'].astype(float), wet); nc, lab = vmet.comps(src, dst, N * N)
        vol = np.bincount(lab[wet.ravel()], weights=h.ravel()[wet.ravel()], minlength=nc); big = (lab == int(np.argmax(vol))).reshape(N, N) & wet
        # 토러스 펼치기: 큰 몸 성분이 차지하지 않은 가장 긴 빈 구간(열·행)을 자르는 곳으로 삼는다(몸이 N/2 보다 길어도 된다). 무게중심 cen(펼친 좌표)이 몸 안에 오도록 상을 고른다.
        def unwrap(occ, c):
            e = np.r_[~occ, ~occ].astype(int); best = 0; bi = 0; run = 0
            for i_, v in enumerate(e):
                run = run + 1 if v else 0
                if run > best: best = run; bi = i_
            start = (bi + 1) % N                      # 빈 구간 바로 다음 = 몸이 시작하는 좌표
            su = c - ((c - start) % N)                # 그 좌표의 펼친 값(무게중심보다 작거나 같다)
            return start, su
        sx, sux = unwrap(big.any(0), cen[0]); sy, suy = unwrap(big.any(1), cen[1])
        dx = sux + ((xx - sx) % N) - c0; dy = suy + ((yy - sy) % N) - c0
        s = (dx * ux + dy * uy)[big]; w = h[big]
        out.append((t, float(np.percentile(s, 99)), float(np.percentile(s, 1)), float((s * w).sum() / w.sum()), float(s.max()), int(wet.sum())))
    return np.array(out), P


def slope(tr, col, t1, t2):
    m = (tr[:, 0] >= t1 - 1e-6) & (tr[:, 0] <= t2 + 1e-6)
    if m.sum() < 3: return float('nan')
    return float(np.polyfit(tr[m, 0], tr[m, col], 1)[0])


def t_reach(tr, col, d):
    """앞면(또는 무게중심)이 거리 d 에 처음 이르는 시각(저장 시점 사이 선형 보간)"""
    y = tr[:, col]; i = np.nonzero(y >= d)[0]
    if i.size == 0: return float('nan')
    i = i[0]
    if i == 0: return float(tr[0, 0])
    return float(tr[i - 1, 0] + (d - y[i - 1]) / (y[i] - y[i - 1]) * (tr[i, 0] - tr[i - 1, 0]))


if __name__ == '__main__':
    t1, t2 = [float(x) for x in sys.argv[1].split(',')]
    print(f'이름 | dt | 앞면 속도 | 뒷면 속도 | 무게중심 속도 (t={t1:.0f}~{t2:.0f}, 셀/시간) | 스텝당 앞면 전진(셀/스텝) | 앞면 위치 t=100/200/300/400 | 뒷면 위치 t=100/200/300/400')
    for n in sys.argv[2:]:
        if not os.path.exists(os.path.join(HERE, 'runs', n, 'metrics.json')): print(n, '(아직 없음)'); continue
        tr, P = track(n); g = lambda c, t: float(np.interp(t, tr[:, 0], tr[:, c])) if t <= tr[-1, 0] else float('nan')
        vf = slope(tr, 1, t1, t2); vr = slope(tr, 2, t1, t2); vc = slope(tr, 3, t1, t2)
        print(f"{n:16s} | {P['dt']} | {vf:.3f} | {vr:.3f} | {vc:.3f} | {vf * P['dt']:.4f} | {'/'.join('%.1f' % g(1, t) for t in (100, 200, 300, 400))} | {'/'.join('%.1f' % g(2, t) for t in (100, 200, 300, 400))}")
