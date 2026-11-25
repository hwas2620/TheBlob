#!/usr/bin/env python3
"""measure.py 를 손으로 만든 가짜 상태로만 시험한다 (모델 실행 없이). usage: python3 test_measure.py"""
import numpy as np, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure as M

N = 96
jj, ii = np.mgrid[0:N, 0:N]
fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)


def disc(cx, cy, r):
    return np.hypot(M.mimg(ii - cx, N), M.mimg(jj - cy, N)) <= r


def S_of(wet, h=None, age=50.0, q=0.1, t=100.0):
    h = np.where(wet, 1.0 if h is None else h, 0.0)
    Q = np.zeros((4, N, N))
    for k, d in enumerate(M.DIRS): Q[k] = np.where(wet & M.nb(wet, d), q, 0.0)
    return dict(wet=wet, h=h, age=np.where(wet, age, 0.0), Qgross=Q, t=t)


# 1. 토러스 라벨: 모서리를 넘어 감긴 원판 하나, 대각선으로만 닿는 두 칸
w = disc(0, 0, 6); lab, n = M.label8(w); check(n == 1, f'모서리에 감긴 원판은 성분 하나 (n={n})')
w = np.zeros((N, N), bool); w[N - 1, N - 1] = True; w[0, 0] = True; check(M.label8(w)[1] == 1, '대각선으로 감겨 닿는 두 칸은 하나')
w = np.zeros((N, N), bool); w[10, 10] = True; w[10, 12] = True; check(M.label8(w)[1] == 2, '한 칸 떨어진 두 칸은 둘')

# 2. 원판 하나: 부스러기 0, 덩이 1, 실 0, 꼬리 0
body = disc(48, 48, 15); o, _ = M.snap_measure(S_of(body), N, scl_lump=True)
check(o['crumbs'] == 0 and o['nbig_sq3'] == 1 and o['nbig_d2'] == 1, f"원판: 부스러기 {o['crumbs']}, 덩이 {o['nbig_sq3']}/{o['nbig_d2']}")
check(o['thread_cells'] == 0 and o['tail_cells'] == 0 and o['th_tail_n'] == 0, f"원판: 실 {o['thread_cells']}, 꼬리 {o['tail_cells']}, 굳센 꼬리 {o['th_tail_n']}")
L = o['lump']; check(L['holes'] == 0 and L['solidity'] > 0.94 and L['disc_iou'] > 0.93, f"원판 모양: 구멍 {L['holes']}, 볼록비 {L['solidity']}, 원판 IoU {L['disc_iou']}")
check(L['sp_h_d'] is None and L['h_cv'] == 0.0, f"고른 두께: spearman {L['sp_h_d']}, cv {L['h_cv']}")

# 3. 부스러기: 원판 + 작은 조각 셋 (하나는 모서리를 넘어 감김)
w = body.copy(); w[5:7, 5:7] = True; w[80:82, 20:22] = True; w[0, 60:62] = True; w[N - 1, 60:62] = True
o, _ = M.snap_measure(S_of(w), N); check(o['crumbs'] == 3 and o['n_comp'] == 4, f"부스러기 셋 (감긴 것 포함): {o['crumbs']}, 성분 {o['n_comp']}")
big = disc(15, 15, 8); w2 = body | big       # 원판 부피의 약 28%: 부스러기 아님, 몸 둘
o, _ = M.snap_measure(S_of(w2), N); check(o['crumbs'] == 0 and o['n_bodies10'] == 2, f"큰 조각은 부스러기 아님: {o['crumbs']}, 몸 {o['n_bodies10']}")

# 4. 아령: 원판 둘을 1칸 실(길이 20)로 잇는다. 실에 흐름 0 이면 흐름 없는 실
a = disc(25, 48, 10); b = disc(71, 48, 10); line = np.zeros((N, N), bool); line[48, 25:72] = True
w = a | b | line; S = S_of(w); thr = line & ~a & ~b
for k in range(4): S['Qgross'][k][thr | M.nb(thr, M.DIRS[k])] = 0.0
o, _ = M.snap_measure(S, N)
check(o['nbig_sq3'] == 2 and o['nbig_d2'] == 2, f"아령: 덩이 {o['nbig_sq3']}/{o['nbig_d2']}")
check(o['th_tube_n'] == 1 and 20 <= o['th_tube_cells'] <= 30, f"아령의 실은 tube: {o['th_tube_n']}, {o['th_tube_cells']}칸")
check(o['nf_thread_0.05'] >= 20, f"흐름 없는 실 칸: {o['nf_thread_0.05']}")
check(o['tail_cells'] == 0, f"양 끝이 이어진 실은 꼬리가 아님: {o['tail_cells']}")
o2, _ = M.snap_measure(S_of(w), N); check(o2['nf_thread_0.05'] == 0, f"흐름이 고르면 흐름 없는 실 0: {o2['nf_thread_0.05']}")
# 두꺼운 덩이 둘 + 얇은 판(넓음): 열림 덩이는 하나, 두께 기준은 둘
sheet = disc(48, 48, 22); hh = np.where(disc(38, 48, 6) | disc(58, 48, 6), 2.0, 0.2)
o, _ = M.snap_measure(S_of(sheet, h=hh), N); check(o['nbig_sq3'] == 1 and o['nbig_thick'] == 2, f"넓은 얇은 판: 열림 덩이 {o['nbig_sq3']}, 두께 덩이 {o['nbig_thick']}")
check(o['film_cells'] > 500, f"넓은 판 안쪽의 얇은 막 칸: {o['film_cells']}")

# 5. 곧은 꼬리 (1칸 폭, 길이 15): 주장 정의로 깎인다
w = body.copy(); w[48, 64:79] = True
o, _ = M.snap_measure(S_of(w), N)
check(o['tail_cells'] == 15 and o['tail_max'] == 15 and o['tail_n3'] == 1, f"곧은 꼬리: {o['tail_cells']}칸, 최대 {o['tail_max']}")
check(o['th_tail_n'] == 1 and o['tips_claim'] == 1 and o['tips_robust'] == 1, f"곧은 꼬리: 굳센 {o['th_tail_n']}, 끝(주장) {o['tips_claim']}, 끝(굳센) {o['tips_robust']}")
S = S_of(w)
for k in range(4): S['Qgross'][k][:, 70:80] = 0.0
o, _ = M.snap_measure(S, N); check(o['nf_tipr_0.05'] == 1 and o['nf_tipc_0.05'] == 1, f"흐름 없는 가지 끝: {o['nf_tipr_0.05']}, {o['nf_tipc_0.05']}")

# 6. 계단 꼬리 (4-연결): 주장 정의는 첫 꺾임에서 멈추고, 굳센 정의는 잡는다
w = body.copy(); y, x = 48, 63
for s in range(8): w[y, x] = True; x += 1; w[y, x] = True; y += 1
o, _ = M.snap_measure(S_of(w), N)
check(o['tail_cells'] <= 2, f"계단 꼬리: 주장 정의로는 거의 안 깎임 ({o['tail_cells']}칸)")
check(o['th_tail_n'] == 1 and o['th_tail_cells'] >= 14, f"계단 꼬리: 굳센 정의 {o['th_tail_n']}개, {o['th_tail_cells']}칸")

# 7. 앞머리(5x5)가 달린 가지, 몸에 두 끝이 붙은 고리
w = body.copy(); w[48, 64:76] = True; w[46:51, 76:81] = True
o, _ = M.snap_measure(S_of(w), N); check(o['th_head_n'] == 1 and o['tail_cells'] == 0, f"앞머리 달린 가지: head {o['th_head_n']}, 꼬리 {o['tail_cells']}")
w = body.copy(); w[40, 58:76] = True; w[40:57, 75] = True; w[56, 58:76] = True      # 몸 오른쪽에 두 곳으로 붙은 U자 실
o, _ = M.snap_measure(S_of(w), N); check(o['th_loop_n'] >= 1 and o['th_tail_n'] == 0, f"몸에 두 끝이 붙은 고리: loop {o['th_loop_n']}, tail {o['th_tail_n']}")

# 8. 2칸 폭 실의 끝은 굳센 끝으로 잡힌다
w = body.copy(); w[48:50, 64:80] = True
o, _ = M.snap_measure(S_of(w), N); check(o['tips_robust'] == 1 and o['tips_claim'] == 0, f"2칸 폭 실: 굳센 끝 {o['tips_robust']}, 주장 끝 {o['tips_claim']}")
check(o['th_tail_n'] == 1, f"2칸 폭 매달린 실: 굳센 꼬리 {o['th_tail_n']}")

# 9. 덩이 모양: 고리(구멍), 십자(볼록비 낮음), 두께가 안쪽으로 커짐
ring = disc(48, 48, 14) & ~disc(48, 48, 5); L, _ = M.lump_metrics(ring, np.ones((N, N)), N); check(L['holes'] > 50, f"고리 모양의 구멍: {L['holes']}")
cross = ((np.abs(ii - 48) <= 2) & (np.abs(jj - 48) <= 20)) | ((np.abs(jj - 48) <= 2) & (np.abs(ii - 48) <= 20))
L, _ = M.lump_metrics(cross, np.ones((N, N)), N); check(L['solidity'] < 0.4 and L['disc_iou'] < 0.5, f"십자: 볼록비 {L['solidity']}, 원판 IoU {L['disc_iou']}")
m = disc(48, 48, 14); from scipy import ndimage as ndi
d = ndi.distance_transform_edt(m); L, _ = M.lump_metrics(m, 0.3 + 0.2 * d, N)
check(L['sp_h_d'] > 0.95 and L['h_ratio'] > 2 and L['max_step_frac'] < 0.3, f"가운데 두꺼움: spearman {L['sp_h_d']}, 비 {L['h_ratio']}, 최대 계단 {L['max_step_frac']}")
L, _ = M.lump_metrics(m, np.where(d >= 2, 3.0, 0.3), N); check(L['max_step_frac'] > 0.9, f"절벽 두께(가장자리만 얇음): 최대 계단 {L['max_step_frac']}")
L, _ = M.lump_metrics(disc(1, 1, 12), np.ones((N, N)), N); check(L['disc_iou'] > 0.93 and not L['wraps'], f"모서리에 감긴 원판도 바르게: IoU {L['disc_iou']}")
ell = ((ii - 48) / 16.0) ** 2 + ((jj - 48) / 8.0) ** 2 <= 1; L, _ = M.lump_metrics(ell, np.ones((N, N)), N); check(L['disc_iou'] < 0.8, f"긴 타원은 원판 아님: IoU {L['disc_iou']}")

for rr in (8, 11, 18):
    L, _ = M.lump_metrics(disc(48, 48, rr), np.ones((N, N)), N); check(L['solidity'] > 0.92, f'디지털 원판 r={rr}: 볼록비 {L["solidity"]}')

# 10. 방향 오차, 넓이 시계열
traj = [[0, 47.5, 47.5, 1], [10, 47.5 + 10 * np.cos(np.radians(37)), 47.5 + 10 * np.sin(np.radians(37)), 1], [20, 47.5 + 40 * np.cos(np.radians(37)), 47.5 + 40 * np.sin(np.radians(37)), 1]]
hd = M.heading(traj, (47.5 + 70 * np.cos(np.radians(27)), 47.5 + 70 * np.sin(np.radians(27))), 47.5)
check(abs(hd['35']['err'] - 10.0) < 1e-6 and hd['35']['t'] == 20, f"방향 오차 +10도: {hd['35']}")
traj2 = [[0, 47.5, 47.5, 1], [20, 47.5 + 40 * np.cos(np.radians(10)), 47.5 + 40 * np.sin(np.radians(10)), 1]]
check(abs(M.heading(traj2, (47.5 + 70 * np.cos(np.radians(27)), 47.5 + 70 * np.sin(np.radians(27))), 47.5)['35']['err'] + 17.0) < 1e-6, '방향 오차 -17도')
area = np.concatenate([np.full(100, 900), np.linspace(900, 500, 1001), np.full(500, 500)]).astype(int)
tm = M.area_timing(area, 0.1, 10.0)
check(abs(tm['t50'] - 50.0) < 0.5 and abs(tm['t90'] - 90.0) < 0.5 and abs(tm['max10'] - 0.1) < 0.01, f"넓이 시계열: t50 {tm['t50']}, t90 {tm['t90']}, 10시간 창 몫 {tm['max10']}")
area = np.concatenate([np.full(105, 900), np.full(500, 500)]).astype(int); tm = M.area_timing(area, 0.1, 10.0)
check(tm['t90'] <= 0.6 and tm['max10'] >= 0.99, f"갑자기 맺힘: t90 {tm['t90']}, 몫 {tm['max10']}")

# 11. 가짜 실행 폴더 전체: 시시각각 모이는 덩이 (갇힌 뒤 원판 -> 작은 덩이)
td = tempfile.mkdtemp(); rd = os.path.join(td, 'b_slimeall_s999_v8v'); od = os.path.join(td, 'out'); os.makedirs(rd); os.makedirs(od)
P = dict(N=N, T=200.0, dt=0.1, foods=[], eat=0.0)
json.dump(P, open(os.path.join(rd, 'params.json'), 'w'))
traj = [[t, 47.5, 47.5, 100] for t in np.arange(0, 200.1, 5)]
met = dict(stop='', t_end=200.0, steps_done=2001, mass_err_max=1e-13, h_min_seen=0.0, h_min_end_of_step=0.0, neg_end_cellsteps=0, neg_end_steps=0, t_touch=[], t_cover=[], t_exh=[],
           foods=[], t_scl=60.0, scl_steps=1400, fission_runs=0, V0=1.0, Vinj=0.0, V_end=1.0, V_crumb=0.0, crumb_cells=0, runtime=1.0, mg_err=None, mg_nadapt=0, mg_nguard=0, disp=0.0, area_end=1, traj=traj)
json.dump(met, open(os.path.join(rd, 'metrics.json'), 'w')); json.dump([[20, 0.01, 0.01], [40, 0.02, 0.01]], open(os.path.join(rd, 'mg_err_series.json'), 'w'))
areas = []
for t in range(20, 201, 20):
    r = 16 - 6 * min(1.0, max(0.0, (t - 60) / 100.0)); w = disc(40, 50, r) | (((ii - 40) / (r + 6.0)) ** 2 + ((jj - 50) / (r * 0.6)) ** 2 <= 1)
    d = ndi.distance_transform_edt(w); hh = np.where(w, 0.5 + 0.1 * d, 0.0); hh *= 900.0 / hh.sum()
    S = S_of(w, h=hh, t=float(t)); np.savez_compressed(os.path.join(rd, f'vs_t{t:04d}.npz'), **S); areas.append(int(w.sum()))
ser_area = np.interp(np.arange(2001) * 0.1, np.arange(20, 201, 20), areas).astype(int)
np.savez_compressed(os.path.join(rd, 'series.npz'), area=ser_area, vol=np.full(2001, 900.0), dt=0.1)
M.main(rd, od); R = json.load(open(os.path.join(od, 'b_slimeall_s999_v8v.json')))
sc = R['scl']; check(len(R['snaps']) == 10 and R['arm'] == 'v8v' and R['scn'] == 'slimeall' and R['seed'] == 999, '가짜 실행 폴더 읽기')
check(sc['t_trap_snap'] == 60.0 and sc['overlap_trap'] > 0.99 and sc['dens_ratio'] > 1.0, f"갇힐 때 짙던 곳: 겹침 {sc['overlap_trap']}, 짙음 비 {sc['dens_ratio']}")
check(sc['timing']['t90'] is not None and 70 < sc['timing']['t90'] < 100, f"맺힘 시간 t90 {sc['timing']['t90']}")
check(sc['lump_final']['holes'] == 0 and sc['lump_final']['sp_h_d'] > 0.8, f"마지막 덩이: 구멍 {sc['lump_final']['holes']}, spearman {sc['lump_final']['sp_h_d']}")
check(os.path.exists(os.path.join(od, 'b_slimeall_s999_v8v_lump.npz')), '덩이 마스크 저장')
check(R['vol_rel_dev_max'] == 0.0 and R['mg_err_list'] == [0.01, 0.02], '부피·풀이 오차 기록 읽기')

print('\n실패', len(fails)); sys.exit(1 if fails else 0)
