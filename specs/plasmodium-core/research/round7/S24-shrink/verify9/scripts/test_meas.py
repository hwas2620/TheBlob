#!/usr/bin/env python3
"""측정 코드 시험: 손으로 만든 가짜 상태만 쓴다 (모델 실행 없음). 실패하면 AssertionError."""
import os, sys, json, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M

N = 96


def blank(): return np.zeros((N, N), bool)


def put(m, y0, y1, x0, x1): m[y0:y1, x0:x1] = True; return m


def qzero(): return np.zeros((4, N, N))


def t_label_torus():
    m = blank(); m[10:20, 90:96] = True; m[10:20, 0:5] = True          # 좌우 감김
    m[94:96, 40:45] = True; m[0:3, 41:43] = True                        # 위아래 감김
    m[50, 95] = True; m[51, 0] = True                                   # 대각 감김
    m[95, 70] = True; m[0, 69] = True                                   # 대각 감김 (위아래)
    lab, n = M.label8(m); assert n == 4, n
    m2 = blank(); m2[95, 95] = True; m2[0, 0] = True; assert M.label8(m2)[1] == 1   # 모서리 대각


def body_with_features():
    w = blank(); put(w, 20, 50, 20, 50)                                 # 30x30 본체
    for i in range(10): w[35, 50 + i] = True                            # 오른쪽 1칸 폭 꼬리 10칸 (x 50..59)
    put(w, 20, 22, 10, 20)                                              # 왼쪽 위 2칸 폭 꼬리 (x 10..19)
    for i in range(6): w[50 + i, 30] = True; w[50 + i, 40] = True       # 아래로 관: x=30, x=40 기둥 6칸
    for x in range(30, 41): w[56, x] = True                              # 그 밑을 잇는 가로대 → 고리
    put(w, 80, 82, 80, 82)                                              # 부스러기 2x2
    for i in range(5): w[70, 10 + i] = True                             # 떨어진 가는 조각 5칸
    h = np.where(w, 1.0, 0.0); h[35, 50:60] = 0.3
    age = np.where(w, 100.0, 0.0)
    return w, h, age


def t_snapshot():
    w, h, age = body_with_features()
    r = M.snapshot(w, h, age, qzero())
    assert r['nmain'] == 1, r['nmain']
    assert r['ncrumb'] == 2 and r['crumb_cells'] == 9, (r['ncrumb'], r['crumb_cells'])
    assert r['det_thin_cells'] == 5 and r['det_thin_tips'] == 2, (r['det_thin_cells'], r['det_thin_tips'])
    t = r['tail']; assert t['n'] == 1 and t['max'] in (9, 10), t          # 1칸 폭 꼬리만 (끝에서 깎임; 밑동 칸은 본체 셋과 닿아 남는다)
    te = r['tail_ext']; assert te['n'] == 2 and te['max'] >= 18, te       # 2칸 폭 꼬리도
    assert r['tube']['n'] == 1 and r['tube']['cells'] >= 20, r['tube']     # 고리는 깎이지 않는다
    f = r['flow']['0.01']; assert f['B_tips'] == 1, f                       # 유량 0 → 끝 하나 흐름 없음
    assert f['B_cells'] >= 10 + 20 + 20, f                                 # 꼬리, 2칸 꼬리, 관 모두 흐름 없음
    assert f['A_cells'] == f['B_cells'] + 5 and f['A_tips'] == f['B_tips'] + 2
    assert not r['db'] and not r['multi']
    # 흐름을 주면: 꼬리의 모든 간선(밑동 포함)에 0.1 → 흐름 있음
    Q = qzero()
    for x in range(49, 60): Q[0, 35, x] = 0.1                           # 동쪽 간선 (35, x)-(35, x+1)
    r2 = M.snapshot(w, h, age, Q); f2 = r2['flow']['0.01']
    assert f2['B_tips'] == 0, f2
    assert f2['B_cells'] == f['B_cells'] - 10, (f2, f)
    # 어린 꼬리는 탐색 가지로 따로
    age2 = age.copy(); age2[35, 55:60] = 3.0
    r3 = M.snapshot(w, h, age2, qzero()); assert r3['tail']['n'] == 0 and r3['tail']['young_n'] == 1, r3['tail']


def t_dumbbell():
    w = blank(); put(w, 20, 35, 10, 25); put(w, 20, 35, 45, 60)
    for x in range(25, 45): w[27, x] = True                             # 1칸 폭 실로 이음
    h = np.where(w, 1.0, 0.0); age = np.where(w, 100.0, 0.0)
    r = M.snapshot(w, h, age, qzero()); assert r['db'] and r['multi'], r['db_detail']
    w2 = w.copy(); put(w2, 25, 31, 25, 45)                               # 6칸 폭 다리 → 한 덩이
    r = M.snapshot(w2, np.where(w2, 1.0, 0.0), np.where(w2, 100.0, 0.0), qzero()); assert not r['db'] and not r['multi'], r['db_detail']
    w3 = w.copy(); put(w3, 26, 29, 25, 45)                               # 3칸 폭 다리 → 덩이 둘이지만 가는 실은 아님
    r = M.snapshot(w3, np.where(w3, 1.0, 0.0), np.where(w3, 100.0, 0.0), qzero()); assert (not r['db']) and r['multi'], r['db_detail']
    w4 = blank(); put(w4, 20, 35, 10, 25); put(w4, 20, 24, 45, 49)        # 작은 쪽이 15% 미만 → 아령 아님
    for x in range(25, 45): w4[22, x] = True
    r = M.snapshot(w4, np.where(w4, 1.0, 0.0), np.where(w4, 100.0, 0.0), qzero()); assert not r['db'], r['db_detail']
    # 감김을 가로지르는 아령
    w5 = np.roll(w, 40, axis=1); r = M.snapshot(w5, np.where(w5, 1.0, 0.0), np.where(w5, 100.0, 0.0), qzero()); assert r['db'], r['db_detail']


def t_holes_shape():
    w = blank(); put(w, 30, 50, 30, 50); assert M.holes(w) == 0
    w[40, 40] = False; w[41, 41] = False; assert M.holes(w) == 2
    ring = blank(); put(ring, 10, 20, 10, 20); ring[12:18, 12:18] = False; assert M.holes(ring) == 36
    yy, xx = np.mgrid[0:N, 0:N]; disc = np.hypot(xx - 47.3, yy - 50.1) <= 12
    assert M.disc_iou(disc) > 0.97, M.disc_iou(disc)
    assert M.solidity(disc) > 0.9, M.solidity(disc)
    bar = blank(); put(bar, 40, 46, 10, 80); assert M.disc_iou(bar) < 0.5
    L = blank(); put(L, 10, 40, 10, 16); put(L, 34, 40, 10, 40); assert M.solidity(L) < 0.6, M.solidity(L)
    discw = np.roll(np.roll(disc, 50, 1), 49, 0); assert abs(M.disc_iou(discw) - M.disc_iou(disc)) < 1e-9
    c1 = M.centred_coords(disc); c2 = M.centred_coords(discw); assert M.shape_iou(c1, c2) > 0.99


def t_profile():
    yy, xx = np.mgrid[0:N, 0:N]; r = np.hypot(xx - 48, yy - 48); L = r <= 12
    hm = np.where(L, 1.0 + 3.0 * (1 - r / 12.5), 0.0)                    # 가운데 두껍고 천천히 얇아짐
    p = M.profile(L, hm); assert p['ratio'] > 1.5 and p['rho'] > 0.7 and p['mono'] and p['gradual'], p
    flat = np.where(L, 1.0, 0.0); p = M.profile(L, flat); assert p['ratio'] < 1.01 and not p['gradual'], p
    step = np.where(L, np.where(r < 3, 4.0, 1.0), 0.0); p = M.profile(L, step); assert not p['gradual'], p    # 한 고리에서 뛴다


def t_sclerotium():
    """가짜 균핵: 덩이 L (원판) + 오른쪽으로 뻗은 막·실. 바깥은 거리 순으로 마르거나(좋은 경우) 한꺼번에 마른다(나쁜 경우)"""
    yy, xx = np.mgrid[0:N, 0:N]; r = np.hypot(xx - 40, yy - 48)
    L = r <= 10
    B = L.copy(); put(B, 40, 56, 40, 70)                                  # 넓은 막
    for x in range(70, 85): B[48, x] = True                              # 실
    B[46:50, 38:42] = True
    hole = blank(); hole[47, 37] = True; hole[48, 43] = True               # 갇힐 때 덩이 자리 안의 구멍 둘
    B0 = B & ~hole
    G = M.geo_dist(B | L, L); assert np.isfinite(G[B]).all()
    hm_end = np.where(L, 1.0 + 2.0 * (1 - r / 10.5), 0.0)
    xs_ = np.arange(N)[None, :] + 0 * yy
    def make(order_good):
        snaps = []; out = B & ~L; dmax = G[out].max()
        for t in np.arange(100.0, 400.1, 5.0):
            if t <= 120: w = B0.copy()
            else:
                if order_good: gone = out & (G > dmax * (1 - (t - 120) / 100.0))     # 먼 곳부터 100 시간에 걸쳐
                else: gone = out if t >= 160 else blank()                            # 한꺼번에
                w = (L & B0) | (out & ~gone)
                w = w | (hole & (xs_ < 40) & (t >= 150)) | (hole & (xs_ >= 40) & (t >= 190))   # 구멍 둘을 40 시간 차로 메운다
            h = np.where(w, np.where(L, hm_end, 0.4), 0.0)
            snaps.append((float(t), w, h, h.copy()))
        return snaps
    good = M.sclerotium(make(True), 120.0)
    d = good['d']; assert d['n_out'] > 100 and d['rho'] < -0.8 and d['dur'] >= 40 and d['maxwin10'] <= 0.35 and d['near_med'] >= d['q75'], d
    assert d['n_fill'] == 2
    assert good['a']['n_end'] == 1 and good['a']['tail_max_end'] == 0, good['a']
    assert good['e']['holes'] == 0 and good['e']['solidity'] > 0.9, good['e']
    assert good['f']['ratio'] > 1.5 and good['f']['gradual'], good['f']
    assert good['b']['max_area_ratio'] <= 1.0 + 1e-9 and good['b']['outside_union_frac'] == 0.0, good['b']
    bad = M.sclerotium(make(False), 120.0)
    assert bad['d']['maxwin10'] > 0.9 and bad['d']['dur'] <= 10, bad['d']
    # 짙은 곳: 갇힐 때 L 자리의 두께를 크게, 막은 얇게 → 순위 높음
    s2 = make(True); t0, w0, h0, _ = s2[4]; h0 = np.where(L, 2.0, np.where(w0, 0.4, 0.0)); s2[4] = (t0, w0, h0, h0)
    s3 = M.sclerotium(s2, 120.0); assert s3['c']['rank_mean'] > 0.7 and s3['c']['peak_dist'] == 0.0, s3['c']
    s2b = make(True); t0, w0, _, _ = s2b[4]; h0 = np.where(w0, np.where(xx > 55, 2.0, 0.4), 0.0); s2b[4] = (t0, w0, h0, h0)    # 짙은 곳이 막 끝 → 순위 낮음
    s3b = M.sclerotium(s2b, 120.0); assert s3b['c']['rank_mean'] < 0.5 and s3b['c']['peak_dist'] > 3, s3b['c']
    assert s3['c']['disc_iou'] > 0.95
    # 다시 넓어지면 (b) 가 잡는다
    s4 = make(True); t_, w_, h_, _ = s4[-3]; w_ = w_.copy(); put(w_, 30, 34, 60, 66); s4[-3] = (t_, w_, np.where(w_, 1.0, 0.0), np.where(w_, 1.0, 0.0))
    b4 = M.sclerotium(s4, 120.0)['b']; assert b4['outside_union_frac'] > 0.05, b4
    # 갈라지면 (a) 가 잡는다
    s5 = make(True); t_, w_, h_, _ = s5[-1]; w_ = w_.copy(); put(w_, 10, 22, 80, 92); s5[-1] = (t_, w_, np.where(w_, 1.0, 0.0), np.where(w_, 1.0, 0.0))
    a5 = M.sclerotium(s5, 120.0)['a']; assert a5['n_end'] == 2, a5
    assert M.sclerotium(make(True), None)['trapped'] is False


def t_judge_smoke():
    """judge.py 가 가짜 실행 기록 묶음에서 끝까지 도는지 (판정 값 자체는 보지 않는다)"""
    import subprocess
    w, h, age = body_with_features(); s = M.snapshot(w, h, age, qzero())
    tmp = tempfile.mkdtemp()
    def fake(scn, seed, tag, cand, T=400.0, foods=1, scl=None):
        snaps_ = []
        for t in np.arange(20.0, T + 0.1, 20.0): x = dict(s); x['t'] = float(t); snaps_.append(x)
        traj = [[float(t), 95.5 + t * 0.1 * np.cos(np.radians(27 + (seed % 3 - 1) * 10)), 95.5 + t * 0.1 * np.sin(np.radians(27 + (seed % 3 - 1) * 10)), 400] for t in np.arange(0, T + 0.1, 5.0)]
        met = dict(stop='', t_end=T, runtime=1, V0=1000.0, Vinj=0.0, V_end=1000.0, mass_err_max=1e-12, h_min_seen=-0.1, h_min_end_of_step=0.0, neg_end_cellsteps=0, neg_end_steps=0,
                   steps_done=int(T / 0.1) + 1, disp=10.0, path_len=10.0, area_end=400, foods=[], t_touch=[100.0 + seed % 7] * foods, t_cover=[], t_exh=[], V_crumb=0.0, crumb_cells=3,
                   t_scl=(130.0 if scl else None), scl_steps=0, conn_kept_cellsteps=1, conn_released_cells=0, fission_runs=0, tiphome_cells=0, neg_fill_cellsteps=0, hang_cellsteps=0,
                   ret_cellsteps=0, sup_updates=0, sup_fed_skips=0, mg_err=None, mg_err_n=3, mg_nadapt=0, mg_nguard=0, lim_steps=0, lim_cells=0, bridge_kept_cellsteps=0, neg_cellsteps=0, traj=traj)
        r = dict(name=f'b_{scn}_s{seed}_{tag}', scn=scn, seed=seed, tag=tag, T=T, N=N, dt=0.1, cand=cand, R_init=12.0, gm_every=20.0, foods=[], c0=95.5, met=met,
                 steps_expected=int(T / 0.1) + 1, mg_err_series=[0.01, 0.02, 0.05], area_series=[], new_series=[], snaps=snaps_)
        if scl: r['scl'] = scl
        json.dump(r, open(os.path.join(tmp, f"run_{r['name']}.json"), 'w'))
    sc = M.sclerotium([(100.0 + 5 * i, w, h, h) for i in range(70)], 130.0)
    for seed in (1001, 1002, 1003, 1004):
        for scn, fo in (('mig', 1), ('long', 1), ('food3', 3), ('asym3', 3), ('food4', 4), ('slimeall', 0)):
            fake(scn, seed, 'v9c', False, foods=fo); fake(scn, seed, 'v9b', True, foods=fo, scl=(sc if scn == 'slimeall' else None))
    p = subprocess.run([sys.executable, os.path.join(HERE, 'judge.py'), tmp, os.path.join(tmp, 'judge')], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-3000:]
    J = json.load(open(os.path.join(tmp, 'judge.json')))
    assert J['1']['crumbs_per_snap_cand'] == 2.0 and J['8']['verdict'] == '맞음', (J['1'], J['8'])


if __name__ == '__main__':
    for f in (t_label_torus, t_snapshot, t_dumbbell, t_holes_shape, t_profile, t_sclerotium, t_judge_smoke):
        f(); print('ok', f.__name__, flush=True)
    print('모든 시험 통과')
