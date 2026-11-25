#!/usr/bin/env python3
"""verify7 측정→판정 흐름 시험: 손으로 만든 가짜 실행 폴더(가짜 vs_t*.npz, metrics.json, params.json)로 measure_run.py 와 judge.py 를 끝까지 돌린다.
usage: test_pipeline.py WORKDIR"""
import os, sys, json, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
W = sys.argv[1]; RUNS = os.path.join(W, 'runs'); DATA = os.path.join(W, 'data'); os.makedirs(RUNS, exist_ok=True); os.makedirs(DATA, exist_ok=True)
N = 96; yy, xx = np.mgrid[0:N, 0:N]; c0 = N / 2 - 0.5
mimg = lambda v: (v + N / 2) % N - N / 2


def fake_run(scn, seed, tag, T, foods, tail=False, crumb=False, scl_t=None, dumb=False, ang=27.0):
    name = f'b_{scn}_s{seed}_{tag}'; rd = os.path.join(RUNS, name); os.makedirs(rd, exist_ok=True)
    traj = []; log = []
    for t in np.arange(0, T + 1e-9, 5.0):
        cx = c0 + 0.2 * t * np.cos(np.radians(ang)); cy = c0 + 0.2 * t * np.sin(np.radians(ang))
        traj.append([float(t), float(cx), float(cy), 400]); log.append(dict(t=float(t), V=700.0, Vinj=0.0))
    for t in np.arange(20, T + 1e-9, 20.0):
        cx = c0 + 0.2 * t * np.cos(np.radians(ang)); cy = c0 + 0.2 * t * np.sin(np.radians(ang))
        r = 12 if (scl_t is None or t < scl_t + 100) else 9
        wet = np.hypot(mimg(xx - cx), mimg(yy - cy)) <= r
        if dumb: wet |= np.hypot(mimg(xx - cx - 30), mimg(yy - cy)) <= 9; wet[int(cy) % N, [int(cx + k) % N for k in range(12, 22)]] = True
        if tail: wet[int(cy) % N, [int(cx - 12 - k) % N for k in range(40)]] = True
        if crumb: wet[(int(cy) + 30) % N, (int(cx) + 30) % N] = True; wet[(int(cy) + 31) % N, (int(cx) + 30) % N] = True
        h = np.where(wet, 700.0 / wet.sum(), 0.0).astype(np.float32)
        Qg = np.zeros((4, N, N), np.float32)
        np.savez_compressed(os.path.join(rd, f'vs_t{int(t):04d}.npz'), wet=wet, h=h, Qgross=Qg, hmean=h, t=t)
    m = dict(stop='', t_end=T, steps_done=int(T / 0.1) + 1, runtime=1.0, V0=700.0, Vinj=0.0, V_end=700.0, mass_err_max=1e-13, h_min_seen=0.0, h_min_end_of_step=0.0,
             neg_end_cellsteps=0, neg_end_steps=0, V_crumb=0.0, crumb_cells=0, t_scl=scl_t, scl_steps=0, fission_runs=0,
             t_touch=[100.0 + 10 * i for i in range(len(foods))], t_cover=None, t_exh=None, mg_err=None, mg_err_n=0, disp=0, traj=traj, log=log,
             foods=[[c0 + d * np.cos(np.radians(a)), c0 + d * np.sin(np.radians(a))] for a, d in foods])
    json.dump(m, open(os.path.join(rd, 'metrics.json'), 'w'))
    json.dump(dict(N=N, T=T, dt=0.1, food_r=4.0, ncyc=2, nc=4), open(os.path.join(rd, 'params.json'), 'w'))
    json.dump([[20 * i, 0.01 * (1 + (i % 3)), 0.02] for i in range(1, 30)], open(os.path.join(rd, 'mg_err_series.json'), 'w'))
    return rd


rds = []
for seed in (661, 662):
    rds += [fake_run('long', seed, 'v7c', 400, [[27, 70]], tail=True, dumb=True, ang=27 + (seed - 661.5) * 10),
            fake_run('long', seed, 'v7y', 400, [[27, 70]], ang=27 + (seed - 661.5) * 10)]
for seed in (667, 668):
    rds += [fake_run('mig', seed, 'v7c', 400, [[27, 70]], crumb=True, dumb=True), fake_run('mig', seed, 'v7y', 400, [[27, 70]], ang=27 + (seed - 667.5) * 20)]
rds += [fake_run('food3', 691, 'v7c', 200, [[20, 40], [140, 40], [260, 40]]), fake_run('food3', 691, 'v7y', 200, [[20, 40], [140, 40], [260, 40]])]
rds += [fake_run('slimeall', 681, 'v7c', 800, [], tail=True), fake_run('slimeall', 681, 'v7y', 800, [], scl_t=130.0)]
env = dict(os.environ, V7_DATA=DATA, V7_OUTDIR=W)
jb = os.path.join(W, 'jobs.txt'); open(jb, 'w').write('\n'.join(os.path.basename(r).replace('b_', '').replace('_s', ' ').replace('_v7', ' v7') for r in rds) + '\n')
env['V7_JOBS'] = jb
subprocess.run([sys.executable, os.path.join(HERE, 'measure_run.py')] + rds, check=True, env=env)
subprocess.run([sys.executable, os.path.join(HERE, 'judge.py')], check=True, env=env)
J = json.load(open(os.path.join(W, 'judge_out.json')))
print('claim1 crumbs ctrl/cand', J['claim1']['v7c']['frac_frames_with_crumb'], J['claim1']['v7y']['frac_frames_with_crumb'])
print('claim2 dumbbell ctrl/cand', J['claim2']['v7c']['frac_dumbbell'], J['claim2']['v7y']['frac_dumbbell'])
print('claim5 cand errors', J['claim5']['v7y']['errors'])
print('claim6 tail frac ctrl/cand', J['claim6']['v7c']['frac_tail30'], J['claim6']['v7y']['frac_tail30'])
print('claim7 runs', [(x['name'], x['a'], x['b'], x['d'], x['t_form']) for x in J['claim7']['runs']])
assert abs(J['claim1']['v7c']['frac_frames_with_crumb'] - 36 / 118) < 1e-9 and J['claim1']['v7y']['frac_frames_with_crumb'] == 0
assert J['claim2']['v7c']['frac_dumbbell'] > 0.9 and J['claim2']['v7y']['frac_dumbbell'] == 0
assert J['claim6']['v7c']['frac_tail30'] > 0.4 and J['claim6']['v7y']['frac_tail30'] == 0
assert sorted(J['claim5']['v7y']['errors']) == [-10.0, -5.0, 5.0, 10.0], J['claim5']['v7y']['errors']
x = J['claim7']['runs'][0]; assert x['a'] and x['t_form'] is not None and x['t_form'] >= x['t90'] - 20 and x['d'] is True, x
print('PIPELINE OK')
