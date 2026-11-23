#!/usr/bin/env python3
"""verify2: 실행마다 metrics.json 과 끝 상태에서 판정에 쓰는 값을 뽑아 data/runs_summary.json 에 쓴다.

usage: collect.py            (scripts/jobs.txt 의 실행 전부, 끝난 것만)
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from measure import torus_label

RUNS = os.path.normpath(os.path.join(HERE, '..', '..', 'model', 'runs'))
TAG = dict(ctrl='w16c', cand='w16gm', dense='w16gm_dense')


def one(scn, seed, arm):
    name = f'b_{scn}_s{seed}_{TAG[arm]}'; rd = os.path.join(RUNS, name); mp = os.path.join(rd, 'metrics.json')
    if not os.path.exists(mp): return None
    m = json.load(open(mp)); P = json.load(open(os.path.join(rd, 'params.json')))
    wet = np.load(os.path.join(rd, 'wet.npy')); h = np.load(os.path.join(rd, 'h.npy'))
    lab, n8 = torus_label(wet, 8); _, n4 = torus_label(wet, 4)
    d = dict(name=name, scn=scn, seed=seed, arm=arm, T=P['T'], stop=m['stop'], t_end=m['t_end'], steps_done=m['steps_done'], runtime=m['runtime'],
             neg_end_cellsteps=m['neg_end_cellsteps'], neg_end_steps=m['neg_end_steps'], neg_cellsteps=m['neg_cellsteps'], mass_err_max=m['mass_err_max'],
             V_crumb=m['V_crumb'], crumb_cells=m['crumb_cells'], V0=m['V0'], V_end=m['V_end'], Vinj=m['Vinj'], disp=m['disp'], path_len=m['path_len'], area_end=m['area_end'],
             t_touch=m['t_touch'], t_exh=m['t_exh'], foods=m['foods'], comps8_end=int(n8), comps4_end=int(n4),
             conn_kept_cellsteps=m.get('conn_kept_cellsteps'), conn_released_cells=m.get('conn_released_cells'), ret_cellsteps=m.get('ret_cellsteps'),
             sup_updates=m.get('sup_updates'), sup_fed_skips=m.get('sup_fed_skips'), hang_cellsteps=m.get('hang_cellsteps'),
             mg_err=m.get('mg_err'), traj_end=m['traj'][-1] if m['traj'] else None)
    tr = np.array([[a[0], a[1], a[2]] for a in m['traj']], float)
    if len(tr):
        c0 = P['N'] / 2 - 0.5; dx = tr[-1, 1] - c0; dy = tr[-1, 2] - c0
        d['disp_angle_deg'] = float(np.degrees(np.arctan2(dy, dx)))
    if arm == 'dense':
        comps = [g['body']['comps'] for g in m['gseries']]; ts = [g['t'] for g in m['gseries']]
        bad = [(t, c) for t, c in zip(ts, comps) if c != 1]
        d.update(dense_n=len(comps), dense_bad=bad[:50], dense_nbad=len(bad), dense_tmin=min(ts) if ts else None, dense_tmax=max(ts) if ts else None)
        ref = os.path.join(RUNS, f'b_{scn}_s{seed}_w16gm', 'h.npy')
        if os.path.exists(ref):
            hr = np.load(ref); d['dense_h_identical'] = bool(np.array_equal(hr, h)); d['dense_wet_identical'] = bool(np.array_equal(np.load(ref.replace('h.npy', 'wet.npy')), wet))
    return d


if __name__ == '__main__':
    jobs = [l.split() for l in open(os.path.join(HERE, 'jobs.txt')) if l.strip()]
    out = []
    for scn, seed, arm in jobs:
        d = one(scn, int(seed), arm)
        if d is not None: out.append(d)
    json.dump(out, open(os.path.join(HERE, '..', 'data', 'runs_summary.json'), 'w'), indent=1)
    print('collected', len(out), 'of', len(jobs))
