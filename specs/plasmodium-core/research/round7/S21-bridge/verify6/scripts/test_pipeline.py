#!/usr/bin/env python3
"""측정 → 판정 전체 흐름 시험: 손으로 만든 가짜 실행 폴더로 measure_runs.py 와 judge.py 를 끝까지 돌린다.
usage: test_pipeline.py SCRATCH_DIR
"""
import json, os, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
root = sys.argv[1]; runs = os.path.join(root, 'runs'); data = os.path.join(root, 'data'); os.makedirs(runs, exist_ok=True); os.makedirs(data, exist_ok=True)
N = 192; jj, ii = np.mgrid[0:N, 0:N].astype(float); c0 = N / 2 - 0.5
tor = lambda cx, cy: np.hypot((ii - cx + N / 2) % N - N / 2, (jj - cy + N / 2) % N - N / 2)


def mk(scn, seed, tag, T, frame_fn, t_scl=None, touch=(None,), foods=[[27, 70]], slime0=''):
    rd = os.path.join(runs, f'b_{scn}_s{seed}_{tag}'); os.makedirs(rd, exist_ok=True)
    P = dict(N=N, T=T, dt=0.1, foods=foods, R_init=12.0, slime0=slime0, food_M=0, eat=0, ncyc=2, mg_deep=0, tri_rnd=0, scl_f=0, keep_conn=0)
    json.dump(P, open(os.path.join(rd, 'params.json'), 'w'))
    traj = []; areas = []
    for t in np.arange(0, T + 0.01, 5.0):
        wet, h = frame_fn(t); traj.append([float(t), float(c0 + 0.25 * t * np.cos(np.radians(27 + (5 if tag == 'v6c' else -3 + seed % 7)))),
                                           float(c0 + 0.25 * t * np.sin(np.radians(27 + (5 if tag == 'v6c' else -3 + seed % 7)))), int(wet.sum())])
    for t in np.arange(0, T + 0.01, 1.0): areas += [int(frame_fn(t)[0].sum())] * 10      # 1 시간마다 재서 10 스텝씩 채운다
    met = dict(stop='', t_end=T, steps_done=int(round(T / 0.1)) + 1, runtime=1.0, V0=1357.0, V_end=1357.0, Vinj=0.0, V_crumb=0.0, crumb_cells=0, mass_err_max=1e-12,
               h_min_seen=0.0, h_min_end_of_step=0.0, neg_end_cellsteps=0, neg_end_steps=0, neg_cellsteps=0, t_touch=list(touch), t_cover=[None] * len(touch), t_exh=[None] * len(touch),
               t_scl=t_scl, scl_steps=0, fission_runs=0, disp=1.0, path_len=1.0, area_end=areas[-1], foods=foods, traj=traj, mg_err=None, mg_err_n=0)
    json.dump(met, open(os.path.join(rd, 'metrics.json'), 'w'))
    json.dump([[20 * i, 0.01 + 0.001 * i, 0.02] for i in range(10)], open(os.path.join(rd, 'mg_err_series.json'), 'w'))
    np.savez_compressed(os.path.join(rd, 'series.npz'), area=np.array(areas))
    for t in np.arange(20, T + 0.01, 20.0):
        wet, h = frame_fn(t)
        Qg = np.array([np.where(wet, 1.0, 0.0)] * 4, np.float32); C = np.array([np.where(wet, 10.0, 0.0)] * 4, np.float32)
        np.savez_compressed(os.path.join(rd, f'vs_t{int(round(t)):04d}.npz'), C=C, wet=wet, h=h.astype(np.float32), age=np.where(wet, 50.0, 0).astype(np.float32),
                            sage=np.zeros((N, N), np.float32), theta=np.zeros((N, N), np.float32), Qgross=Qg, Qmean=Qg, Cmean=C, t=t, fM=np.zeros(1), cen=np.array([c0, c0]),
                            hamp=np.zeros((N, N), np.float32), hmean=np.where(wet, 1.0, 0).astype(np.float32))
    wet, h = frame_fn(T); np.save(os.path.join(rd, 'wet.npy'), wet); np.save(os.path.join(rd, 'slime.npy'), (~wet).astype(np.float32) if slime0 == 'all' else np.zeros((N, N), np.float32))
    np.save(os.path.join(rd, 'twet.npy'), np.where(wet, 0.0, -1.0).astype(np.float32))
    return rd


def moving(debris, dumb, tail):
    def f(t):
        cx = c0 + 0.25 * t * np.cos(np.radians(27)); cy = c0 + 0.25 * t * np.sin(np.radians(27))
        wet = tor(cx, cy) <= 14; h = np.where(wet, 1.0, 0.0)
        if dumb and int(t) % 40 == 0:
            B = tor(cx - 40, cy) <= 9; T_ = (np.abs(jj - round(cy)) < 0.5) & (((ii - (cx - 32)) % N) < 18); wet = wet | B | T_; h = np.where(B, 1.2, np.where(T_ & ~(tor(cx, cy) <= 14), 0.3, h))
        if debris: D = tor(cx + 40, cy + 40) <= 1.5; wet = wet | D; h = np.where(D, 0.3, h)
        if tail: T2 = (np.abs(jj - round(cy)) < 0.5) & (((ii - (cx + 14)) % N) < 30); wet = wet | T2; h = np.where(T2 & ~(tor(cx, cy) <= 14), 0.4, h)
        return wet, h
    return f


def trap(cand):
    def f(t):
        if cand:      # 그물(넓은 원판 + 가지) 이 t 130..330 에 걸쳐 길쭉한 덩이로 줄어든다
            s = float(np.clip((t - 130) / 200, 0, 1)); a = 30 - 12 * s; b = 30 - 20 * s      # 꼬리는 20(1-s) 칸 (25 칸 미만이라 주장 6 에 걸리지 않는다)
            wet = (((ii - c0) / a) ** 2 + ((jj - c0) / b) ** 2) <= 1
            if s < 1: wet |= (np.abs(jj - 96) < 0.5) & (ii > c0 + a - 1) & (ii < c0 + a + 20 * (1 - s))
            return wet, np.where(wet, 1.0 + 2 * s, 0.0)
        wet = (tor(c0, c0) <= 20) & ~((tor(c0 + 6, c0) <= 8)) | ((np.abs(jj - 96) < 0.5) & (ii > c0 + 19) & (ii < c0 + 40))
        return wet, np.where(wet, 1.0, 0.0)
    return f


jobs = []
for sd in range(531, 547):
    mk('mig', sd, 'v6g', 400.0, moving(False, False, False), touch=(250.0,)); mk('mig', sd, 'v6c', 400.0, moving(True, True, True), touch=(260.0,)); jobs += [f'mig {sd} v6g', f'mig {sd} v6c']
for sd in (571, 572, 573, 574, 575):
    mk('slimeall', sd, 'v6g', 800.0, trap(True), t_scl=130.0, foods=[], touch=(), slime0='all'); mk('slimeall', sd, 'v6c', 800.0, trap(False), foods=[], touch=(), slime0='all')
    jobs += [f'slimeall {sd} v6g', f'slimeall {sd} v6c']
for sd in (541, 542):
    mk('food3', sd, 'v6g', 480.0, moving(False, False, False), touch=(100.0, 200.0, None), foods=[[20, 40], [140, 40], [260, 40]])
    mk('food3', sd, 'v6c', 480.0, moving(False, False, False), touch=(110.0, 190.0, 300.0), foods=[[20, 40], [140, 40], [260, 40]]); jobs += [f'food3 {sd} v6g', f'food3 {sd} v6c']
open(os.path.join(root, 'jobs.txt'), 'w').write('\n'.join(jobs) + '\n')
env = dict(os.environ, VERIFY6_DATA=data, VERIFY6_OUT=root, VERIFY6_JOBS=os.path.join(root, 'jobs.txt'), NPROC='4')
subprocess.run([sys.executable, os.path.join(HERE, 'measure_runs.py'), '--force'] + [os.path.join(runs, d) for d in sorted(os.listdir(runs))], env=env, check=True, stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, os.path.join(HERE, 'judge.py')], env=env, check=True)
J = json.load(open(os.path.join(root, 'judge.json')))
ok = []
def chk(nm, c, v=None): ok.append(bool(c)); print(('PASS ' if c else 'FAIL ') + nm + ('' if v is None else f'  [{v}]'))
chk('1: 후보 부스러기 없음, 대조 있음 -> 맞음', J['c1']['verdict'] == '맞음', (J['c1']['cand_abs_frac'], J['c1']['rel_ctrl_frac']))
chk('2: 대조만 아령(한 장면 걸러) -> 맞음', J['c2']['verdict'] == '맞음', (J['c2']['dumbbell']['cand'], J['c2']['dumbbell']['ctrl']))
chk('6: 대조만 30칸 꼬리 -> 후보 맞음', J['c6']['verdict'] == '맞음' and J['c6']['rel']['ctrl25'] > 0.8, (J['c6']['cand_abs_f25'], J['c6']['rel']['ctrl25']))
chk('5: 후보 방향 오차 -3..+3 고루 -> 맞음', J['c5']['verdict'] == '맞음', J['c5'][ 'v6g']['d25'].get('median_abs'))
chk('5: 대조 +5 도 한쪽 -> 대조는 치우침', J['c5']['v6c']['d25']['sign_p'] < 0.05)
r7 = J['c7']['rows']
chk('7: 가짜 균핵 (가)(나)(라) 모두 지킴', all(r['a'] and r['b'] and r['d'] for r in r7), [(r['t_form'], round(r.get('form_dur', 0), 1)) for r in r7][:2])
chk('7: 길쭉한 덩이 (다) 지킴', all(r['c'] for r in r7), [(r['final_main']['disc_iou'], r['final_main']['aspect'], r.get('iou_mass')) for r in r7][:1])
chk('7: (마) 후보가 대조보다 촘촘·매끈', J['c7']['frac_e'] == 1.0, J['c7']['erows'][:1])
chk('8: 가짜 실행 모두 건강', J['c8']['verdict'] == '맞음', J['c8']['n_ok'])
chk('4: 먹이 하나 덜 닿음 -> 수는 경계 안', list(J['c4']['food_reached']) == [4, 6] and J['c4']['verdict'] == '판정 못 함', J['c4']['food_reached'])
print(f'{sum(ok)}/{len(ok)} 통과'); sys.exit(0 if all(ok) else 1)
