#!/usr/bin/env python3
"""[CRITERIA_CHANGES 1] 외가닥 조각 측정 시험: 손으로 만든 가짜 상태만."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
N = 192
jj, ii = np.mgrid[0:N, 0:N].astype(float)
OK = []


def chk(name, cond, val=None):
    OK.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name + ('' if val is None else f'  [{val}]'))


def disc(cx, cy, r): return np.hypot((ii - cx + N / 2) % N - N / 2, (jj - cy + N / 2) % N - N / 2) <= r


def state(wet, h=None, Q=1.0):
    wet = wet.astype(bool); h = np.where(wet, 1.0 if h is None else h, 0.0); Qg = np.zeros((4, N, N)); C = np.zeros((4, N, N))
    for k, d in enumerate(M.DIRS):
        a = wet & M.nb(wet, d); Qg[k] = np.where(a, Q if np.isscalar(Q) else Q[k], 0.0); C[k] = np.where(a, 10.0, 0.0)
    return dict(wet=wet, h=h, age=np.where(wet, 50.0, 0.0), Qgross=Qg, C=C, t=100.0)


def hline(x0, x1, y, w=1):
    m = np.zeros((N, N), bool)
    for x in range(x0, x1 + 1):
        for dy in range(w): m[(y + dy) % N, x % N] = True
    return m


def vline(x, y0, y1, w=1):
    m = np.zeros((N, N), bool)
    for y in range(y0, y1 + 1):
        for dx in range(w): m[y % N, (x + dx) % N] = True
    return m


def seg(x0, y0, x1, y1):
    m = np.zeros((N, N), bool); n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for s in np.linspace(0, 1, n): m[int(round(y0 + s * (y1 - y0))) % N, int(round(x0 + s * (x1 - x0))) % N] = True
    return m


D = disc(60, 96, 12)
# Y 그물: 원판에서 15칸 → 갈림 → 15칸 가지 둘
Y = hline(72, 86, 96) | seg(86, 96, 97, 107) | seg(86, 96, 97, 85)
fm = M.frame_measures(state(D | Y)); chk('Y 그물: 25칸 이상 외가닥 없음, 끝 2', fm['n_strand25'] == 0 and fm['n_tips2'] == 2 and fm['strand_maxlen'] < 18, (fm['n_strand25'], fm['n_tips2'], round(fm['strand_maxlen'], 1)))
chk('Y 그물: 예전 정의로는 한 덩어리 길이 ~26', fm['thread_maxlen'] > 24, round(fm['thread_maxlen'], 1))
# 그물 끝에 달린 40칸 꼬리
T2 = hline(72, 81, 96) | seg(81, 96, 90, 105) | hline(81, 121, 95)
fm = M.frame_measures(state(D | T2)); chk('갈림 뒤 40칸 꼬리 = 외가닥 꼬리 1', fm['n_strand25_tail'] == 1 and fm['strand_maxlen'] >= 35, (fm['n_strand25_tail'], round(fm['strand_maxlen'], 1)))
# 가운데 2칸 잔가지가 붙은 40칸 꼬리
T3 = hline(72, 111, 96) | vline(92, 97, 98)
fm = M.frame_measures(state(D | T3)); chk('2칸 잔가지는 끊지 않음: 40칸 꼬리 1', fm['n_strand25'] == 1 and fm['strand_maxlen'] >= 36, (fm['n_strand25'], round(fm['strand_maxlen'], 1)))
# 두 원판 사이 50칸 다리
B = disc(60, 96, 10) | disc(130, 96, 10) | hline(69, 121, 96)
fm = M.frame_measures(state(B)); chk('50칸 다리 = 외가닥 다리 1', fm['n_strand25_bridge'] == 1 and fm['n_strand25_tail'] == 0, (fm['n_strand25_bridge'], fm['n_strand25_tail'], round(fm['strand_maxlen'], 1)))
# 격자 그물 (간격 10)
G = np.zeros((N, N), bool)
for k in range(0, 61, 10): G |= hline(72, 132, 66 + k) | vline(72 + k, 66, 126)
fm = M.frame_measures(state(disc(60, 96, 12) | G)); chk('격자 그물: 외가닥 최대 < 20 (바깥 모서리는 갈림점이 아니라 L자 10+10)', fm['strand_maxlen'] < 20 and fm['n_strand25'] == 0, round(fm['strand_maxlen'], 1))
# 흐름 없는 끝: Y 그물에서 한 가지만 죽음
Q = [np.where(M.dilate8(seg(86, 96, 97, 107) & (ii > 90)), 0.001, 1.0) for d in M.DIRS]
fm = M.frame_measures(state(D | Y, Q=Q)); chk('Y 그물 한 가지 끝만 흐름 없음 = 죽은 끝 1', fm['n_dead_tips2'] == 1, fm['n_dead_tips2'])
# 경계를 넘는 꼬리
fm = M.frame_measures(state(disc(150, 60, 12) | hline(162, 202, 60))); chk('경계를 넘는 41칸 꼬리', fm['n_strand25_tail'] == 1 and fm['strand_maxlen'] >= 38, round(fm['strand_maxlen'], 1))
# 폭 2 꼬리
fm = M.frame_measures(state(D | hline(72, 111, 96, w=2))); chk('폭 2 꼬리 40칸 = 외가닥 1', fm['n_strand25'] == 1, round(fm['strand_maxlen'], 1))
print(f'{sum(OK)}/{len(OK)} 통과'); sys.exit(0 if all(OK) else 1)
