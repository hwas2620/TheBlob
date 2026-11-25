#!/usr/bin/env python3
"""judge.py 를 손으로 만든 가짜 측정값으로만 시험한다. usage: python3 test_judge.py"""
import numpy as np, json, os, sys, tempfile, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge as J

fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)


def snap(t, **kw):
    s = dict(t=t, area=500, vol=1000.0, h_min=0.0, n_comp=1, crumbs=0, crumbs05=0, crumb_cells=0, n_bodies10=1, n_bodies3=1, nbig_sq3=1, nbig_d2=1, nbig_thick=1,
             thread_cells=0, qmed=0.1, tips_robust=0, tips_claim=0, film_cells=50, tail_cells=0, tail_n3=0, tail_max=0, tail_free=0, th_tail_old_n=0, th_tail_old_cells=0, th_tail_old_max=0)
    for q in ('0.01', '0.05', '0.2'): s['nf_thread_' + q] = 0; s['nf_tipr_' + q] = 0; s['nf_tipc_' + q] = 0
    for k in ('tail', 'loop', 'head', 'tube', 'free', 'fringe'): s[f'th_{k}_n'] = 0; s[f'th_{k}_cells'] = 0; s[f'th_{k}_max'] = 0
    s.update(kw); return s


def run(scn, seed, arm, T=400.0, snapf=None, t_touch=None, heading=None, mg=None, scl=None, **met):
    m = dict(stop='', t_end=T, steps_done=int(T / 0.1) + 1, mass_err_max=1e-13, h_min_seen=0.0, h_min_end_of_step=0.0, neg_end_cellsteps=0, t_touch=t_touch or [], t_scl=None, scl_steps=0, V_crumb=0.0)
    m.update(met)
    ss = [snapf(t) if snapf else snap(t) for t in np.arange(20.0, T + 1, 20.0)]
    r = dict(run=f'b_{scn}_s{seed}_{arm}', scn=scn, seed=seed, arm=arm, N=192, T=T, metrics=m, steps_expected=int(T / 0.1) + 1, mg_err_list=mg or [0.01, 0.02, 0.05],
             snaps=ss, disp400=60.0, disp200=40.0, heading=heading or {'35': dict(t=100.0, err=5.0)})
    if scl: r['scl'] = scl
    return r


def write(d, runs):
    for f in os.listdir(d):
        if f.endswith('.json'): os.remove(os.path.join(d, f))
    for r in runs: json.dump(r, open(os.path.join(d, r['run'] + '.json'), 'w'))


td = tempfile.mkdtemp(); dd = os.path.join(td, 'data'); od = os.path.join(td, 'out'); os.makedirs(dd)
errs = [6.0, -4.0, 9.0, -12.0, 3.0, -7.0, 11.0, -2.0]
base = []
for i, sd in enumerate(range(901, 909)):
    base.append(run('mig', sd, 'v8c', snapf=lambda t: snap(t, nbig_sq3=2 if t % 40 == 0 else 1, **{'nf_thread_0.05': 12, 'nf_tipr_0.05': 3}), t_touch=[150.0], heading={'35': dict(t=90.0, err=errs[i] * 2)}))
    base.append(run('mig', sd, 'v8v', snapf=lambda t: snap(t, **{'nf_thread_0.05': 2, 'nf_tipr_0.05': 0}), t_touch=[155.0], heading={'35': dict(t=95.0, err=errs[i])}))
for sd in range(911, 915):
    base.append(run('food3', sd, 'v8c', T=480.0, snapf=lambda t: snap(t, tail_cells=30, tail_max=12, th_tail_old_cells=25, **{'nf_thread_0.05': 8, 'nf_tipr_0.05': 2}), t_touch=[50.0, 80.0, 100.0]))
    base.append(run('food3', sd, 'v8v', T=480.0, snapf=lambda t: snap(t, tail_cells=4, tail_max=3, th_tail_old_cells=3, **{'nf_thread_0.05': 1, 'nf_tipr_0.05': 0}), t_touch=[52.0, 85.0, 120.0]))
write(dd, base); R = J.main(dd, od)
check(R['c1']['verdict'] == J.OK, f"1 부스러기 없음 -> 맞음 ({R['c1']['verdict']})")
check(R['c2']['verdict'] == J.OK, f"2 아령 대조 0.5, 후보 0 -> 맞음 ({R['c2']['verdict']}, {R['c2']['agg']['c_db']} -> {R['c2']['agg']['v_db']})")
check(R['c3']['verdict'] == J.OK, f"3 흐름 없는 실 12 -> 2, 끝 3 -> 0 -> 맞음 ({R['c3']['verdict']})")
check(R['c4']['verdict'] == J.OK and R['c4']['b']['median_ratio'] == 1.2, f"4 먹이 같고 마지막 닿음 비 1.2 -> 맞음 ({R['c4']['verdict']}, {R['c4']['b']['median_ratio']})")
check(R['c5']['verdict'] == J.OK, f"5 방향 오차 작고 양쪽 -> 맞음 ({R['c5']['verdict']}, {R['c5']['v8v']['med_abs']}, p {R['c5']['v8v']['p_side']})")
check(R['c6']['verdict'] == J.OK, f"6 꼬리 30 -> 4, 길이 12 -> 3 -> 맞음 ({R['c6']['verdict']})")
check(R['c7']['verdict'] == J.UNK and R['c7']['qualified'] == 0, f"7 균핵 실행 없음 -> 판정 못 함 ({R['c7']['verdict']})")
check(R['c8']['verdict'] == J.OK, f"8 건강 -> 맞음 ({R['c8']['verdict']})")
check(R['c9']['verdict'] == J.OK, f"9 풀이 오차 같음 -> 맞음 ({R['c9']['verdict']})")

# 틀린 경우들
bad = copy.deepcopy(base)
for r in bad:
    if r['arm'] == 'v8v':
        for s in r['snaps']:
            if s['t'] % 60 == 0: s['crumbs'] = 1
            s['nbig_sq3'] = 2 if s['t'] % 40 == 0 else 1
        r['mg_err_list'] = [0.01, 0.02, 0.7]
        if r['scn'] == 'food3': r['metrics']['t_touch'] = [52.0, 85.0, 200.0]
        if r['scn'] == 'mig': r['heading'] = {'35': dict(t=95.0, err=abs(r['heading']['35']['err']) + 1)}
        if r['seed'] == 901: r['metrics']['neg_end_cellsteps'] = 3
write(dd, bad); R = J.main(dd, od)
check(R['c1']['verdict'] == J.NO, f"1 스냅숏 1/3 에 부스러기 -> 틀림 ({R['c1']['verdict']}, {R['c1']['v8v']})")
check(R['c2']['verdict'] == J.NO, f"2 후보도 아령 같음 -> 틀림 ({R['c2']['verdict']})")
check(R['c4']['verdict'] == J.NO and R['c4']['b']['median_ratio'] == 2.0, f"4 마지막 닿음 비 2.0 -> 틀림 ({R['c4']['b']['median_ratio']})")
check(R['c5']['verdict'] == J.NO, f"5 여덟 시드 모두 + 쪽 -> 틀림 ({R['c5']['verdict']}, p {R['c5']['v8v']['p_side']})")
check(R['c8']['verdict'] == J.NO and R['c8']['bad'] == ['b_mig_s901_v8v'], f"8 음수 두께 한 판 -> 틀림 ({R['c8']['bad']})")
check(R['c9']['verdict'] == J.NO, f"9 최대 0.7 -> 틀림 ({R['c9']['verdict']})")

# 먹이 하나 덜 닿음 x3 -> 4(a) 틀림, 대조에 꼬리 없음 -> 6 판정 못 함
b2 = copy.deepcopy(base)
for r in b2:
    if r['scn'] == 'food3' and r['arm'] == 'v8v' and r['seed'] < 914: r['metrics']['t_touch'] = [52.0, 85.0, None]
    if r['scn'] == 'food3' and r['arm'] == 'v8c':
        for s in r['snaps']: s['tail_cells'] = 0; s['tail_max'] = 0
write(dd, b2); R = J.main(dd, od)
check(R['c4']['a']['deficit'] == 3 and R['c4']['a']['verdict'] == J.NO, f"4(a) 세 개 덜 닿음 -> 틀림 ({R['c4']['a']})")
check(R['c6']['verdict'] == J.UNK, f"6 대조에도 꼬리 없음 -> 판정 못 함 ({R['c6']['verdict']})")

# 균핵: 판 여섯 (모두 통과) / 한 판 구멍 / 두 판 구멍 / 원판 모양
import measure as M
N = 96; jj, ii = np.mgrid[0:N, 0:N]


def scl_run(sd, holes=0, shape='blob', t90=80.0, max10=0.12, sp=0.8, shape_seed=None):
    rng = np.random.default_rng(sd if shape_seed is None else shape_seed)
    if shape == 'disc': m = np.hypot(ii - 48, jj - 48) <= 12
    else:
        th = np.arctan2(jj - 48, ii - 48); Rr = 12 * (1 + 0.25 * np.cos(2 * th + rng.uniform(0, 6)) + 0.15 * np.cos(3 * th + rng.uniform(0, 6))); m = np.hypot(ii - 48, jj - 48) <= Rr
    np.savez_compressed(os.path.join(dd, f'b_slimeall_s{sd}_v8v_lump.npz'), mask=m, h=m.astype(np.float32))
    L = dict(area=int(m.sum()), holes=holes, solidity=0.95, disc_iou=0.97 if shape == 'disc' else 0.8, rough=0.1, wraps=False, sp_h_d=sp, h_ratio=2.0, h_cv=0.3, max_step_frac=0.3, mono_viol=0, dmax=10, prof=[], n_core10=1)
    sc = dict(t_scl=130.0, timing=dict(A0=900, A_end=450, dA=450, t10=10.0, t50=40.0, t90=t90, max10=max10), t_trap_snap=120.0, t_final=800.0, dens_ratio=1.3, dense_frac=0.9, overlap_trap=0.98,
              area_final=450, vol_final=1357.0, amin=388, area_trap=900, n_bodies3_trap=1, conc=[[120.0, 0.5], [800.0, 1.0]], iou_final=[[t, 0.95] for t in np.arange(120.0, 801, 20.0)], lump_final=L)
    f = lambda t: snap(t, lump=dict(L)) if t >= 120 else snap(t)
    return run('slimeall', sd, 'v8v', T=800.0, snapf=f, scl=sc, t_scl=130.0, scl_steps=6700)


S7 = [scl_run(sd) for sd in range(921, 927)]
write(dd, base + S7); R = J.main(dd, od)
check(R['c7']['verdict'] == J.OK and R['c7']['qualified'] == 6 and R['c7']['pair_iou_median'] < 0.9, f"7 균핵 여섯 모두 통과 -> 맞음 ({R['c7']['verdict']}, 짝 IoU 중앙 {R['c7']['pair_iou_median']})")
S7b = [scl_run(921, holes=3)] + [scl_run(sd) for sd in range(922, 927)]
write(dd, base + S7b); R = J.main(dd, od)
check(R['c7']['sub']['e'] == J.UNK and R['c7']['verdict'] == J.UNK, f"7(e) 한 판 구멍 -> 판정 못 함 ({R['c7']['sub']['e']})")
S7c = [scl_run(921, holes=3), scl_run(922, holes=1)] + [scl_run(sd) for sd in range(923, 927)]
write(dd, base + S7c); R = J.main(dd, od)
check(R['c7']['sub']['e'] == J.NO and R['c7']['verdict'] == J.NO, f"7(e) 두 판 구멍 -> 틀림 ({R['c7']['sub']['e']})")
S7d = [scl_run(sd, shape='disc') for sd in range(921, 927)]
write(dd, base + S7d); R = J.main(dd, od)
check(R['c7']['sub']['c'] == J.NO, f"7(c) 모두 원판 -> 틀림 ({R['c7']['sub']['c']}, 짝 IoU {R['c7']['pair_iou_median']})")
S7g = [scl_run(sd, shape_seed=5) for sd in range(921, 927)]
write(dd, base + S7g); R = J.main(dd, od)
check(R['c7']['sub']['c'] == J.NO and R['c7']['pair_iou_median'] > 0.95, f"7(c) 모든 판의 윤곽이 같음 -> 틀림 ({R['c7']['sub']['c']}, 짝 IoU {R['c7']['pair_iou_median']})")
S7e = [scl_run(sd, t90=5.0, max10=0.9) for sd in range(921, 927)]
write(dd, base + S7e); R = J.main(dd, od)
check(R['c7']['sub']['d'] == J.NO, f"7(d) 갑자기 맺힘 -> 틀림 ({R['c7']['sub']['d']})")
S7f = [scl_run(sd) for sd in range(921, 927)]; S7f[0]['metrics']['t_scl'] = None; del S7f[0]['scl']
write(dd, base + S7f); R = J.main(dd, od)
check(R['c7']['verdict'] == J.NO and R['c7']['slime_without_scl'] == [921], f"7 사방 점액 판이 균핵 상태에 들지 않음 -> 틀림 ({R['c7']['slime_without_scl']})")

print('\n실패', len(fails)); sys.exit(1 if fails else 0)
