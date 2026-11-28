#!/usr/bin/env python3
"""verify9: 실행 폴더 하나(또는 여럿)를 측정해 verify9/out/run_<이름>.json 에 쓴다.

usage: analyze.py [-j 4] RUN_DIR [RUN_DIR ...]
읽는 것: metrics.json, params.json, series.npz, mg_err_series.json, vs_t*.npz (모델 코드는 부르지 않는다)
"""
import json, os, sys, glob, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
OUT = os.path.normpath(os.path.join(HERE, '..', 'out'))

KEEP = ('stop', 't_end', 'runtime', 'V0', 'Vinj', 'V_end', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step', 'neg_end_cellsteps', 'neg_end_steps', 'steps_done',
        'disp', 'path_len', 'area_end', 'foods', 't_touch', 't_cover', 't_exh', 'V_crumb', 'crumb_cells', 't_scl', 'scl_steps', 'conn_kept_cellsteps', 'conn_released_cells',
        'fission_runs', 'tiphome_cells', 'neg_fill_cellsteps', 'hang_cellsteps', 'ret_cellsteps', 'sup_updates', 'sup_fed_skips', 'mg_err', 'mg_err_n', 'mg_nadapt', 'mg_nguard',
        'lim_steps', 'lim_cells', 'bridge_kept_cellsteps', 'neg_cellsteps', 'traj')


def load_vs(f):
    Z = np.load(f)
    return dict(t=float(Z['t']), wet=Z['wet'].astype(bool), h=Z['h'].astype(float), age=Z['age'].astype(float), Qg=Z['Qgross'].astype(float),
                hm=Z['hmean'].astype(float))


def one(rd):
    t0 = time.time(); name = os.path.basename(rd.rstrip('/'))
    met = json.load(open(os.path.join(rd, 'metrics.json'))); P = json.load(open(os.path.join(rd, 'params.json')))
    res = dict(name=name, scn=name.split('_')[1], seed=int(name.split('_')[2][1:]), tag=name.split('_', 3)[3] if name.count('_') >= 3 else '',
               T=float(P['T']), N=int(P['N']), dt=float(P['dt']), cand=bool(P.get('keep_conn', 0)), R_init=float(P['R_init']), gm_every=float(P['gm_every']),
               foods=P['foods'], c0=P['N'] / 2 - 0.5)
    res['met'] = {k: met.get(k) for k in KEEP}
    res['steps_expected'] = int(round(P['T'] / P['dt'])) + 1
    e = json.load(open(os.path.join(rd, 'mg_err_series.json')))
    res['mg_err_series'] = [round(float(x[1]), 6) for x in e]
    S = np.load(os.path.join(rd, 'series.npz')); res['area_series'] = S['area'].tolist(); res['new_series'] = S['new'].tolist()
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
    snaps = []; rows = []
    for f in fs:
        s = load_vs(f); ti = int(round(s['t']))
        snaps.append((s['t'], s['wet'], s['h'], s['hm']))
        if ti % 20 == 0:
            r = M.snapshot(s['wet'], s['h'], s['age'], s['Qg']); r['t'] = s['t']; rows.append(r)
    res['snaps'] = rows
    if P.get('scl_f', 0) > 0:
        res['scl'] = M.sclerotium(snaps, met.get('t_scl'))
    res['analyze_s'] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(OUT, f'run_{name}.json'), 'w'))
    return name, res['analyze_s']


if __name__ == '__main__':
    a = sys.argv[1:]; j = 1
    if a and a[0] == '-j': j = int(a[1]); a = a[2:]
    os.makedirs(OUT, exist_ok=True)
    if j > 1:
        from multiprocessing import Pool
        with Pool(j) as pool:
            for nm, s in pool.imap_unordered(one, a): print(nm, s, flush=True)
    else:
        for rd in a: print(*one(rd), flush=True)
