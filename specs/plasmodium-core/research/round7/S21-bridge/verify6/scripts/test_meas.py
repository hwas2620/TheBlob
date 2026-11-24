#!/usr/bin/env python3
"""측정 코드 시험: 손으로 만든 가짜 상태만 쓴다 (모델 실행 결과는 쓰지 않는다)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
import judge as J

N = 192
jj, ii = np.mgrid[0:N, 0:N].astype(float)
OK = []


def chk(name, cond, val=None):
    OK.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name + ('' if val is None else f'  [{val}]'))


def tor(cx, cy):
    return np.hypot((ii - cx + N / 2) % N - N / 2, (jj - cy + N / 2) % N - N / 2)


def disc(cx, cy, r): return tor(cx, cy) <= r


def state(wet, h=None, age=None, Q=1.0):
    wet = wet.astype(bool)
    h = np.where(wet, 1.0 if h is None else h, 0.0)
    age = np.where(wet, 50.0 if age is None else age, 0.0)
    Qg = np.zeros((4, N, N)); C = np.zeros((4, N, N))
    for k, d in enumerate(M.DIRS):
        a = wet & M.nb(wet, d); Qg[k] = np.where(a, Q if np.isscalar(Q) else Q[k], 0.0); C[k] = np.where(a, 10.0, 0.0)
    return dict(wet=wet, h=h, age=age, Qgross=Qg, C=C, t=100.0)


def hline(x0, x1, y, w=1):
    m = np.zeros((N, N), bool)
    for x in range(x0, x1 + 1):
        for dy in range(w): m[(y + dy) % N, x % N] = True
    return m


# 1. 토러스 라벨
m = disc(0.0, 0.0, 6)
lab, n = M.tlabel(m); chk('tlabel: 네 귀퉁이에 걸린 원판 하나 = 조각 1', n == 1, n)
lab, n = M.tlabel(disc(50, 50, 5) | disc(120, 120, 5)); chk('tlabel: 떨어진 원판 둘 = 조각 2', n == 2, n)
m = np.zeros((N, N), bool); m[10, 0] = True; m[11, N - 1] = True
lab, n = M.tlabel(m); chk('tlabel: 경계 너머 대각 이웃 = 조각 1', n == 1, n)

# 2. 칸 흐름의 방향 색인
wet = disc(80, 80, 6); S = state(wet, Q=0.0); S['Qgross'][0, 80, 80] = 5.0
fl = M.cell_flow(S['Qgross'], wet); chk('cell_flow: 동쪽 간선 하나가 양 끝 칸에 잡힌다', fl[80, 80] == 5 and fl[80, 81] == 5 and fl[80, 79] == 0, (fl[80, 80], fl[80, 81], fl[80, 79]))
S['Qgross'][:] = 0; S['Qgross'][3, 80, 80] = 7.0      # SE = (x+1, y-1)
fl = M.cell_flow(S['Qgross'], wet); chk('cell_flow: SE 간선 (x+1, y-1)', fl[80, 80] == 7 and fl[79, 81] == 7, (fl[80, 80], fl[79, 81]))

# 3. 부스러기
wet = disc(60, 60, 15) | disc(150, 150, 1.5); h = np.where(disc(150, 150, 1.5), 0.3, 1.0)
fm = M.frame_measures(state(wet, h)); chk('부스러기: 큰 몸 + 작은 조각 = 1', fm['n_debris'] == 1 and fm['n_comp'] == 2, fm['n_debris'])
wet = disc(60, 60, 15) | disc(0.0, 100, 1.5)
fm = M.frame_measures(state(wet, np.where(disc(0.0, 100, 1.5), 0.3, 1.0))); chk('부스러기: 경계에 걸친 작은 조각도 1', fm['n_debris'] == 1 and fm['n_comp'] == 2, (fm['n_debris'], fm['n_comp']))
wet = disc(60, 60, 15) | disc(140, 60, 10)
fm = M.frame_measures(state(wet)); chk('분열: 큰 조각 둘 = split, 부스러기 0', fm['split'] and fm['n_debris'] == 0, (fm['split'], fm['n_debris']))

# 4. 아령
A = disc(60, 96, 10); B = disc(130, 96, 10); T = hline(69, 121, 96)
wet = A | B | T; h = np.where(A | B, 1.2, 0.3)
fm = M.frame_measures(state(wet, h)); chk('아령: 두 원판 + 가는 실 = dumbbell', fm['dumbbell'] and fm['dumbbell_any'], (fm['dumbbell'], fm['n_big_lumps_max']))
wet = (((ii - 96) / 25) ** 2 + ((jj - 96) / 10) ** 2) <= 1
fm = M.frame_measures(state(wet, 1.0)); chk('아령: 타원 하나 = 아령 아님', not fm['dumbbell_any'], fm['n_big_lumps_max'])
band = (np.abs(jj - 96) <= 4) & (ii >= 60) & (ii <= 130)
wet = A | B | band; h = np.where(A | B, 1.2, 0.4)
fm = M.frame_measures(state(wet, h)); chk('아령: 넓은 얇은 띠로 이어진 두 덩이 = 덩이 둘이지만 가는 목 아님', fm['dumbbell_any'] and not fm['dumbbell'], (fm['dumbbell_any'], fm['dumbbell']))
wet = A | B | hline(69, 121, 94, w=5); h = np.where(A | B, 1.2, 0.3)
fm = M.frame_measures(state(wet, h)); chk('아령: 폭 5 의 띠 = 가는 목 아님', not fm['dumbbell'], fm['dumbbell'])
wet = A | B | hline(69, 121, 95, w=3); h = np.where(A | B, 1.2, 0.3)
fm = M.frame_measures(state(wet, h)); chk('아령: 폭 3 의 목 = 가는 목', fm['dumbbell'], fm['dumbbell'])

# 5. 실 길이, 꼬리/다리
D = disc(60, 60, 12); T = hline(72, 111, 60)          # 40 칸 꼬리
wet = D | T; fm = M.frame_measures(state(wet))
chk('실: 40 칸 꼬리 길이 >= 38', 38 <= fm['thread_maxlen'] <= 42 and fm['n_long25'] == 1 and fm['n_long25_tail'] == 1, (fm['thread_maxlen'], fm['n_long25_tail']))
wet = disc(150, 60, 12) | hline(162, 202, 60)        # x 162..191, 0..10 로 경계를 넘는 41 칸 꼬리
fm = M.frame_measures(state(wet)); chk('실: 경계를 넘는 꼬리 길이 >= 40', fm['thread_maxlen'] >= 40 and fm['n_long25_tail'] == 1, fm['thread_maxlen'])
wet = disc(60, 60, 10) | disc(130, 60, 10) | hline(69, 121, 60)
fm = M.frame_measures(state(wet, np.where(disc(60, 60, 10) | disc(130, 60, 10), 1.0, 0.5)))
chk('실: 두 몸을 잇는 다리 = bridge', fm['n_long25_bridge'] == 1 and fm['n_long25_tail'] == 0, (fm['n_long25_bridge'], fm['n_long25_tail']))
wet = disc(60, 60, 12) | hline(72, 111, 60, w=2); fm = M.frame_measures(state(wet))
chk('실: 폭 2 꼬리도 실', fm['n_long25'] == 1, fm['thread_maxlen'])
wet = disc(60, 60, 12) | hline(72, 111, 59, w=3); fm = M.frame_measures(state(wet))
chk('실: 폭 3 꼬리는 3x3 실 아님, 폭 4 이하 기준에서는 긴 실', fm['n_long25'] == 0 and fm['n_long25_w4'] == 1, (fm['n_long25'], fm['n_long25_w4']))

# 6. 흐름 없는 실 / 가지 끝
D = disc(60, 60, 12); T = hline(72, 91, 60); wet = D | T
Q = [np.where(M.nb(T, d) | T, 0.001, 1.0) for d in M.DIRS]
fm = M.frame_measures(state(wet, Q=Q)); chk('흐름 없는 꼬리: 죽은 실 칸 >= 18, 죽은 가지 끝 1', fm['dead_thread_cells'] >= 18 and fm['n_dead_tips'] == 1 and fm['n_dead_threads'] == 1, (fm['dead_thread_cells'], fm['n_dead_tips']))
fm = M.frame_measures(state(wet, Q=1.0)); chk('흐르는 꼬리: 죽은 실 0, 죽은 끝 0, 끝 1', fm['dead_thread_cells'] == 0 and fm['n_dead_tips'] == 0 and fm['n_tips'] == 1, (fm['dead_thread_cells'], fm['n_tips']))
Q = [np.where((T & (ii >= 85)) | M.nb(T & (ii >= 85), d), 0.001, 1.0) for d in M.DIRS]
fm = M.frame_measures(state(wet, Q=Q)); chk('끝 쪽만 죽은 꼬리: 죽은 끝 1, 실 전체는 살아 있음', fm['n_dead_tips'] == 1 and fm['n_dead_threads'] == 0, (fm['n_dead_tips'], fm['n_dead_threads']))

# 7. 얇은 막
D = disc(96, 96, 20); ring = (tor(96, 96) >= 5) & (tor(96, 96) <= 12)
fm = M.frame_measures(state(D, np.where(ring, 0.2, 1.0))); a = int(ring.sum())
chk('얇은 막: 고리 넓이만큼', abs(fm['film_cells'] - a) <= 0.1 * a, (fm['film_cells'], a))
fm = M.frame_measures(state(D, np.where(ring, 0.2, 1.0), age=np.where(ring, 5.0, 50.0))); chk('얇은 막: 어린 칸(앞머리)은 막 아님', fm['film_cells'] == 0, fm['film_cells'])

# 8. 모양
fm = M.frame_measures(state(disc(96, 96, 15), 3.0)); p = fm['pieces'][0]
chk('모양: 원판 solidity>0.95, iso<1.1, disc_iou>0.93, aspect<1.05', p['solidity'] > 0.95 and p['iso'] < 1.1 and p['disc_iou'] > 0.93 and p['aspect'] < 1.05, {k: round(p[k], 3) for k in ('solidity', 'iso', 'disc_iou', 'aspect', 'radial_cv')})
chk('균핵 상태: 원판 = S', fm['scl_state'] if 'scl_state' in fm else M.scl_state(fm))
fm = M.frame_measures(state(disc(0.0, 0.0, 15), 3.0)); q = fm['pieces'][0]
chk('모양: 귀퉁이에 걸친 원판도 같은 값', abs(q['solidity'] - p['solidity']) < 0.01 and abs(q['disc_iou'] - p['disc_iou']) < 0.01 and not q['wraps'], (round(q['solidity'], 3), round(q['disc_iou'], 3)))
E = (((ii - 96) / 24) ** 2 + ((jj - 96) / 12) ** 2) <= 1
fm = M.frame_measures(state(E, 3.0)); p = fm['pieces'][0]
chk('모양: 타원 aspect ~2, disc_iou < 0.8', 1.8 < p['aspect'] < 2.2 and p['disc_iou'] < 0.8, (round(p['aspect'], 2), round(p['disc_iou'], 3)))
fm = M.frame_measures(state(disc(96, 96, 15) | hline(111, 140, 96), 3.0)); chk('균핵 상태: 꼬리 달린 원판 = S 아님', not M.scl_state(fm), fm['pieces'][0]['thread_comps'])
fm = M.frame_measures(state(disc(60, 96, 10) | disc(130, 96, 10) | hline(69, 121, 96), np.where(disc(60, 96, 10) | disc(130, 96, 10), 1.2, 0.3)))
chk('균핵 상태: 아령 = S 아님', not M.scl_state(fm))
fm = M.frame_measures(state(disc(60, 96, 14) | disc(130, 96, 14), 2.0)); chk('균핵 상태: 떨어진 두 원판(각자 덩이) = S', M.scl_state(fm))
cres = ((tor(96, 96) <= 18) & ~(tor(104, 96) <= 14))
fm = M.frame_measures(state(cres, 2.0)); p = fm['pieces'][0]; chk('모양: 초승달 solidity < 0.7', p['solidity'] < 0.7, round(p['solidity'], 3))
hh = np.where(disc(96, 96, 15), 1.0 + 0.5 * (ii > 96), 0.0); fm = M.frame_measures(state(disc(96, 96, 15), hh)); p = fm['pieces'][0]
chk('두께 CV: 1 과 1.5 반반이면 ~0.2', 0.15 < p['h_cv'] < 0.25, round(p['h_cv'], 3))

# 9. 새 땅 몫
wet = disc(96, 96, 10); sl = (ii < 96) & ~wet
r = M.fresh_rim_share(wet, sl); chk('새 땅 몫: 왼쪽 절반 점액 = ~0.5', 0.4 < r < 0.6, round(r, 3))

# 10. 방향 오차 (judge.py)
c0 = N / 2 - 0.5
for ang in (27.0, 40.0, 10.0, -20.0):
    tr = [[t, c0 + 0.3 * t * np.cos(np.radians(ang)), c0 + 0.3 * t * np.sin(np.radians(ang)), 400] for t in np.arange(0, 400, 5.0)]
    d = J.heading(tr, c0, 27.0, 25.0)
    chk(f'방향 오차: 직선 {ang}도 -> {ang - 27:+.0f}도', abs(d - (ang - 27.0)) < 0.5, round(d, 2))
tr = [[t, c0 + 0.05 * t, c0, 400] for t in np.arange(0, 400, 5.0)]
chk('방향 오차: 25칸을 못 가면 None', J.heading(tr, c0, 27.0, 25.0) is None)
chk('부호 검정: 16 중 13 같은 부호 p<0.05', J.sign_p(13, 16) < 0.05 and J.sign_p(11, 16) > 0.05, (round(J.sign_p(13, 16), 4), round(J.sign_p(11, 16), 4)))
# 11. 형성 시각·갑작스러움 (judge.py)
fr = [dict(t=float(t), scl_state=(t >= 300)) for t in range(20, 801, 20)]
chk('형성 시각: 처음 S 가 된 장면', J.t_form(fr, 130.0) == 300.0, J.t_form(fr, 130.0))
chk('풀림: 다시 S 가 아니게 된 몫', J.unravel_frac(fr, 300.0) == 0.0)
fr2 = [dict(t=float(t), scl_state=(t >= 300 and t not in (500, 520, 540))) for t in range(20, 801, 20)]
chk('풀림: 뒤 25 장면 중 셋 빠지면 3/25', abs(J.unravel_frac(fr2, 300.0) - 3 / 25) < 1e-9, J.unravel_frac(fr2, 300.0))

print(f'{sum(OK)}/{len(OK)} 통과')
sys.exit(0 if all(OK) else 1)
