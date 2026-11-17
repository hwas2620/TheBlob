#!/usr/bin/env python3
"""[verify5] 축 방향 치우침 진단(저장된 vs_t*.npz 에서). usage: aniso.py ROOT mig|food RUN ...  -> 실행마다 한 줄(JSON 은 aniso/<ROOT표시>_<RUN>.json)
정맥 방향 지수 O4 = (n_축 - sqrt2*n_대각)/(n_축 + sqrt2*n_대각): 간선 길이로 가중한 4겹 비등방성. 방향이 고르게 퍼진 계단 경로면 0, 모두 축 방향이면 +1, 모두 대각이면 -1.
x 대 y: O2 = (n_x - n_y)/(n_x + n_y).  문턱 C>4, C>30. 유량 가중(Qgross) 판도 낸다.
윤곽: 가장 큰 몸 성분의 젖은 셀에서, 무게중심 기준 방향별(22.5도 통 16개) 최대 반지름 r(a). R4 = sum r(a) cos(4a) / sum r(a) (축 쪽으로 튀어나오면 +), 축/대각 도달 비.
창: mig 는 t>=200, food 는 [max(닿은 시각)+20, 첫 먹이가 떨어진 시각]."""
import numpy as np, json, os, sys, glob
from scipy import ndimage as ndi
DX = np.array([1, 0, 1, 1]); DY = np.array([0, 1, 1, -1])
def wrapd(v, N): return (v + N / 2.0) % N - N / 2.0
def one(run_dir, kind):
    P = json.load(open(os.path.join(run_dir, 'params.json'))); met = json.load(open(os.path.join(run_dir, 'metrics.json'))); N = P['N']
    if kind == 'food':
        tt = met['t_touch']; ex = [v for v in met['t_exh'] if v is not None]
        if any(v is None for v in tt): return None
        t0 = max(tt) + 20; t1 = min(ex) if ex else 1e9
    else: t0, t1 = 200.0, 1e9
    yy, xx = np.indices((N, N)); rows = []
    for f in sorted(glob.glob(os.path.join(run_dir, 'vs_t*.npz'))):
        Z = np.load(f); t = float(Z['t'])
        if not (t0 <= t <= t1 + 1e-6): continue
        C = Z['C'].astype(float); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); Qg = Z['Qgross'].astype(float)
        r = dict(t=t)
        for thr in (4.0, 30.0):
            n = []
            for k in range(4):
                act = wet & np.roll(wet, (-DY[k], -DX[k]), (0, 1)); n.append(int((act & (C[k] > thr)).sum()))
            ax = n[0] + n[1]; dg = 2 ** 0.5 * (n[2] + n[3])
            r[f'O4_{thr:g}'] = (ax - dg) / max(ax + dg, 1e-9); r[f'O2_{thr:g}'] = (n[0] - n[1]) / max(n[0] + n[1], 1); r[f'D2_{thr:g}'] = (n[2] - n[3]) / max(n[2] + n[3], 1); r[f'n_{thr:g}'] = n
        q = [float(Qg[k][wet & np.roll(wet, (-DY[k], -DX[k]), (0, 1))].sum()) for k in range(4)]     # 총 유량(절댓값 시간 평균)의 방향별 합
        ax = q[0] + q[1]; dg = 2 ** 0.5 * (q[2] + q[3]); r['O4_Q'] = (ax - dg) / max(ax + dg, 1e-12); r['O2_Q'] = (q[0] - q[1]) / max(q[0] + q[1], 1e-12)
        lab, nl = ndi.label(np.tile(wet, (3, 3)), structure=np.ones((3, 3)))     # 토러스: 3x3 타일에서 가운데 타일의 가장 큰 성분
        cen = Z['cen']; cx, cy = float(cen[0]) % N, float(cen[1]) % N
        vol = ndi.sum(np.tile(h, (3, 3)), lab, index=np.arange(1, nl + 1)); mid = np.zeros((3 * N, 3 * N), bool); mid[N:2 * N, N:2 * N] = True
        ls = np.unique(lab[mid]); ls = ls[ls > 0]; best = int(ls[np.argmax(vol[ls - 1])])
        m = lab == best; ys, xs = np.nonzero(m); w = np.tile(h, (3, 3))[ys, xs]
        # 가운데 타일에 무게중심이 오는 사본 하나만 쓴다: 성분의 질량 중심을 내고 그 주변 N/2 안
        mx = (w * xs).sum() / w.sum(); my = (w * ys).sum() / w.sum()
        dxs = xs - mx; dys = ys - my; rr = np.hypot(dxs, dys); ang = np.degrees(np.arctan2(dys, dxs)) % 360
        reach = np.array([rr[np.abs(((ang - a + 180) % 360) - 180) <= 11.25].max() if (np.abs(((ang - a + 180) % 360) - 180) <= 11.25).any() else 0.0 for a in np.arange(0, 360, 22.5)])
        a_ = np.radians(np.arange(0, 360, 22.5)); r['R4'] = float((reach * np.cos(4 * a_)).sum() / reach.sum()); r['axdg'] = float(reach[[0, 4, 8, 12]].mean() / max(reach[[2, 6, 10, 14]].mean(), 1e-9)); r['rmean'] = float(reach.mean())
        # 두께 가중 2차 모멘트의 주축 방향과 길쭉함
        Ixx = (w * dxs ** 2).sum() / w.sum(); Iyy = (w * dys ** 2).sum() / w.sum(); Ixy = (w * dxs * dys).sum() / w.sum()
        ev = np.linalg.eigvalsh([[Ixx, Ixy], [Ixy, Iyy]]); r['elong'] = float(np.sqrt(ev[1] / max(ev[0], 1e-9))); r['maj_deg'] = float(np.degrees(0.5 * np.arctan2(2 * Ixy, Ixx - Iyy)) % 180)
        rows.append(r)
    if not rows: return None
    out = dict(run=os.path.basename(run_dir.rstrip('/')), n=len(rows))
    for k in ('O4_4', 'O4_30', 'O2_4', 'O2_30', 'D2_4', 'D2_30', 'O4_Q', 'O2_Q', 'R4', 'axdg', 'rmean', 'elong'): out[k] = float(np.mean([r[k] for r in rows]))
    return out
if __name__ == '__main__':
    ROOT = sys.argv[1]; kind = sys.argv[2]; os.makedirs('aniso', exist_ok=True); tag = 'A' if os.path.abspath(ROOT) != os.path.abspath('.') else 'V'
    for r in sys.argv[3:]:
        cf = f'aniso/{tag}_{r}.json'
        if os.path.exists(cf): o = json.load(open(cf))
        else:
            if not os.path.exists(os.path.join(ROOT, 'runs', r, 'metrics.json')): print(r, '(없음)'); continue
            o = one(os.path.join(ROOT, 'runs', r), kind)
            if o is None: print(r, '(창 없음)'); continue
            json.dump(o, open(cf, 'w'))
        print(f"{o['run']:18s} n={o['n']:2d} O4(C>4) {o['O4_4']:+.3f} O4(C>30) {o['O4_30']:+.3f} O4(Q) {o['O4_Q']:+.3f} | O2(C>4) {o['O2_4']:+.3f} O2(C>30) {o['O2_30']:+.3f} O2(Q) {o['O2_Q']:+.3f} | 윤곽 R4 {o['R4']:+.3f} 축/대각 {o['axdg']:.3f} 평균반지름 {o['rmean']:.1f} 길쭉함 {o['elong']:.2f}")
