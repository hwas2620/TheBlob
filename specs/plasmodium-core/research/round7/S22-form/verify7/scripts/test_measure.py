#!/usr/bin/env python3
"""verify7 측정 코드 시험: 손으로 만든 가짜 상태로만 (모델 실행 결과를 쓰지 않는다)."""
import os, sys
import numpy as np
from collections import deque
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v7lib as L
import measure_run as MR
import judge as JG

N = 96
yy, xx = np.mgrid[0:N, 0:N]


def disc(cx, cy, r):
    return np.hypot(L.mimg(xx - cx, N), L.mimg(yy - cy, N)) <= r


def line(m, x0, y0, x1, y1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n):
        x = int(round(x0 + (x1 - x0) * i / max(n - 1, 1))) % N; y = int(round(y0 + (y1 - y0) * i / max(n - 1, 1))) % N
        m[y, x] = True
    return m


def bfs_count(mask):
    seen = np.zeros_like(mask); n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]: continue
        n += 1; q = deque([(y0, x0)]); seen[y0, x0] = True
        while q:
            y, x = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    a, b = (y + dy) % mask.shape[0], (x + dx) % mask.shape[1]
                    if mask[a, b] and not seen[a, b]: seen[a, b] = True; q.append((a, b))
    return n


def fm(wet, h=None, Qg=None, hmean=None):
    if h is None: h = np.where(wet, 1.0, 0.0)
    return L.frame_measures(wet, h, Qg=Qg, hmean=hmean)[0]


def check(name, cond, info=''):
    print(('ok   ' if cond else 'FAIL ') + name + ('  ' + str(info) if info else ''))
    if not cond: check.fail += 1
check.fail = 0

# 1. 토러스 연결 성분 = 단순 BFS
rng = np.random.default_rng(3)
for i in range(5):
    m = rng.random((40, 40)) < 0.35
    check(f'torus_label vs BFS #{i}', L.torus_label(m)[1] == bfs_count(m), (L.torus_label(m)[1], bfs_count(m)))
# 경계를 넘는 원반은 하나
w = disc(0, 0, 10); check('wrapped disc is one body', L.torus_label(w)[1] == 1)
# 2. 원반 하나
w = disc(48, 48, 15); f = fm(w)
check('disc: no crumb, no dumbbell, no tail', f['n_crumb'] == 0 and f['n_dumbbell_bodies'] == 0 and f['n_tail30'] == 0 and f['n_far100'] == 0, (f['n_crumb'], f['n_dumbbell_bodies'], f['n_tail30']))
b = f['bodies'][0]
check('disc: compact, solidity>0.9, disc_iou>0.9, Pn~1', b['compact'] and b['solidity'] > 0.9 and b['disc_iou'] > 0.9 and 0.9 < b['Pn'] < 1.25, (b['solidity'], b['disc_iou'], b['Pn']))
wb = disc(0, 0, 15); fb = fm(wb)['bodies'][0]
check('wrapped disc: same shape numbers', abs(fb['solidity'] - b['solidity']) < 1e-9 and abs(fb['disc_iou'] - b['disc_iou']) < 1e-9 and fb['area'] == b['area'], (fb['solidity'], fb['area']))
# 3. 부스러기
w2 = w.copy(); w2[10:13, 10:13] = True; h2 = np.where(w2, 1.0, 0.0); h2[10:13, 10:13] = 0.5
f = fm(w2, h2); check('crumb counted', f['n_crumb'] == 1 and f['n_comp'] == 2, (f['n_crumb'], f['crumb_vol']))
w3 = w.copy(); w3[5:25, 5:25] = True; f = fm(w3); check('large separate piece is not a crumb', f['n_crumb'] == 0, (f['n_crumb'], f['n_frag'], f['n_ge10']))
# 4. 아령: 원반 둘을 1 칸 실로
wd = disc(25, 48, 10) | disc(71, 48, 10); wd = line(wd, 35, 48, 61, 48); f = fm(wd)
check('dumbbell detected', f['n_dumbbell_bodies'] == 1 and f['lobes'] == [2], (f['n_dumbbell_bodies'], f['lobes']))
check('dumbbell thread is a trunk, not a tail', f['n_trunk'] >= 1 and f['n_tail30'] == 0 and f['max_trunk_L'] >= 20, (f['n_trunk'], f['max_trunk_L'], f['max_tail_L']))
# 넓은 목(폭 9)은 아령이 아니다
ww = disc(25, 48, 10) | disc(71, 48, 10); ww[44:53, 30:66] = True; f = fm(ww)
check('wide neck: not a dumbbell', f['n_dumbbell_bodies'] == 0, f['lobes'])
# 5. 꼬리 50
wt = disc(30, 48, 12); wt = line(wt, 42, 48, 91, 48); f = fm(wt)
check('tail ~50 found', f['n_tail30'] == 1 and 45 <= f['max_tail_L'] <= 55, f['max_tail_L'])
wt2 = disc(30, 48, 12); wt2 = line(wt2, 42, 48, 62, 48); f = fm(wt2)
check('tail ~20 is not long', f['n_tail30'] == 0 and 15 <= f['max_tail_L'] <= 25, f['max_tail_L'])
# 대각선 꼬리 (2칸 폭 계단)
wtd = disc(30, 30, 10)
for i in range(35):
    wtd[(38 + i) % N, (38 + i) % N] = True; wtd[(38 + i) % N, (39 + i) % N] = True
f = fm(wtd); check('diagonal 2-wide tail ~ 35*sqrt2', f['n_tail30'] == 1 and 40 <= f['max_tail_L'] <= 60, f['max_tail_L'])
# 6. 고리(같은 몸에서 나가 돌아오는 외가닥, 길이 > 100)
N2 = 192; yy2, xx2 = np.mgrid[0:N2, 0:N2]
wl = np.hypot(xx2 - 60, yy2 - 96) <= 12
pts = [(72, 92), (150, 92), (150, 100), (72, 100)]
for (a0, b0), (a1, b1) in zip(pts[:-1], pts[1:]):
    n_ = max(abs(a1 - a0), abs(b1 - b0)) + 1
    for i in range(n_): wl[round(b0 + (b1 - b0) * i / (n_ - 1)), round(a0 + (a1 - a0) * i / (n_ - 1))] = True
f = L.frame_measures(wl, np.where(wl, 1.0, 0.0))[0]
check('loop > 100 found as loop', f['n_far100'] == 1 and f['far100_kinds'] == ['loop'], (f['max_far_L'], f['far100_kinds']))
# 7. 떨어진 두 몸
w7 = disc(20, 20, 10) | disc(70, 70, 10); f = fm(w7)
check('two separate bodies: n_ge10=2, no dumbbell, no crumb', f['n_ge10'] == 2 and f['n_dumbbell_bodies'] == 0 and f['n_crumb'] == 0, (f['n_ge10'], f['n_dumbbell_bodies']))
# 8. 흐름 없는 실과 끝: 몸 간선 유량 1, 꼬리 간선 유량 0
Qg = np.zeros((4, N, N))
body = disc(30, 48, 12)
for k, d in enumerate(L.DIRS): Qg[k] = np.where(body & L.nb(body, d), 1.0, 0.0)
f = fm(wt, Qg=Qg)
check('flowless thread cells and dead tip', f['dead_thread_frac'] > 0.05 and f['dead_tips'] == 1 and abs(f['Fref'] - 1.0) < 1e-9, (f['dead_thread_frac'], f['dead_tips'], f['Fref']))
Qg2 = np.zeros((4, N, N))
for k, d in enumerate(L.DIRS): Qg2[k] = np.where(wt & L.nb(wt, d), 1.0, 0.0)
f = fm(wt, Qg=Qg2); check('flowing thread: not dead', f['dead_thread_frac'] == 0 and f['dead_tips'] == 0, (f['dead_thread_frac'], f['dead_tips']))
# 9. 얇은 막
hf = np.where(w, 1.0, 0.0); hf[w & (xx > 52)] = 0.2
f = fm(w, hf, hmean=hf); check('thin film fraction', 0.2 < f['film_frac'] < 0.5, f['film_frac'])
# 10. 두께 고르지 않음
hg = np.where(w, 0.5 + 2.0 * (xx - 33) / 30.0, 0.0); f = fm(w, hg, hmean=hg); b = f['bodies'][0]
check('uneven thickness: cv>0.15, p90/p10>1.4', b['h_cv_int'] > 0.15 and b['h_p90_p10_int'] > 1.4, (b['h_cv_int'], b['h_p90_p10_int']))
hu = np.where(w, 1.0, 0.0); b = fm(w, hu, hmean=hu)['bodies'][0]
check('even thickness: cv~0', b['h_cv_int'] < 0.01, b['h_cv_int'])
# 11. 균핵 분석: 넓게 퍼진 몸이 짙던 곳(오른쪽 아래)으로 점점 모인다
frames = []
big = disc(48, 48, 25); core = disc(58, 58, 9); V = 1500.0
for i, t in enumerate(range(100, 420, 20)):
    s = min(1.0, max(0.0, (t - 140) / 200.0))      # 140~340 에 걸쳐 모임
    wet = big if s < 1 else core
    hh = np.zeros((N, N)); hh[big] = (1 - s) * V / big.sum(); hh[core] += s * V / core.sum()
    hh = np.where(wet, hh, 0); hh[big & ~wet] = 0
    if i == 0: hh[core] *= 3.0                       # 갇힐 때 짙던 곳
    frames.append((float(t), wet.copy(), hh))
S = MR.scl_analysis(frames, 105.0)
check('scl: dense-place ratio > 1.2', S['D_ratio_s4'][0] > 1.2, S['D_ratio_s4'])
check('scl: gradual t10..t90 spans > 30', S['t10'] is not None and S['t90'] - S['t10'] > 30, (S.get('t10'), S.get('t90')))
# 12. 이주 방향
c0 = N / 2 - 0.5
tr = [[t, c0 + 0.25 * t * np.cos(np.radians(37)), c0 + 0.25 * t * np.sin(np.radians(37)), 100] for t in range(0, 405, 5)]
mm = JG.mig_measures(dict(traj=tr, c0=c0, foods=[[c0 + 70 * np.cos(np.radians(27)), c0 + 70 * np.sin(np.radians(27))]], t_touch=[300.0]))
check('direction error +10 deg', abs(mm['err35'] - 10) < 1e-6 and abs(mm['d400'] - 100) < 1e-6, mm)
tr = [[t, c0 + 0.25 * t * np.cos(np.radians(17)), c0 + 0.25 * t * np.sin(np.radians(17)), 100] for t in range(0, 405, 5)]
mm = JG.mig_measures(dict(traj=tr, c0=c0, foods=[[c0 + 70 * np.cos(np.radians(27)), c0 + 70 * np.sin(np.radians(27))]], t_touch=[None]))
check('direction error -10 deg, untouched', abs(mm['err35'] + 10) < 1e-6 and mm['t_touch'] is None, mm)
print('FAILURES', check.fail)
sys.exit(1 if check.fail else 0)
