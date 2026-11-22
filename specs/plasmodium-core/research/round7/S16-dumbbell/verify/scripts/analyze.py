#!/usr/bin/env python3
"""실행 폴더를 읽어 요약을 data/ 에 쓴다.

usage: analyze.py [-j 4]
  data/summary.json          실행마다 요약 (metrics.json 의 건강 값, 먹이 시각, long 의 창 평균)
  data/long_rows/<run>.json  long 실행의 저장 상태마다 값 (성분 수, 아령, 늦은 때의 칸 수)
"""
import json, os, sys, glob
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlib as V

VER = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DATA = os.path.join(VER, 'data')
JOBS = [l.split() for l in open(os.path.join(VER, 'scripts', 'jobs.txt')) if l.strip()]
HEALTH = ('stop', 't_end', 'neg_end_cellsteps', 'neg_end_steps', 'neg_cellsteps', 'mass_err_max', 'V_crumb', 'crumb_cells', 'V0', 'V_end', 'Vinj', 'area_end', 'disp', 'path_len',
          't_touch', 't_cover', 't_exh', 'fM_end', 'conn_kept_cellsteps', 'conn_released_cells', 'ret_cellsteps', 'hang_cellsteps', 'sup_updates', 'sup_fed_skips', 'h_min_end_of_step', 'runtime', 'steps_done')
VARIANTS = {'main': (0.5, 0.05), 'f02': (0.5, 0.02), 'f10': (0.5, 0.10), 'h07': (0.7, 0.05)}


def base(scn, seed, tag):
    d = V.run_dir(scn, seed, tag)
    m = json.load(open(os.path.join(d, 'metrics.json')))
    P = json.load(open(os.path.join(d, 'params.json')))
    out = dict(run=os.path.basename(d), scn=scn, seed=int(seed), tag=tag, T=P['T'], food_M=P.get('food_M'), nfood=len(P.get('foods', [])))
    out.update({k: m.get(k) for k in HEALTH})
    w = np.load(os.path.join(d, 'wet.npy')); out['comps_end'] = V.torus_label(w)[1]
    return out, m, d


def do_long(job):
    scn, seed, tag = job
    out, m, d = base(scn, seed, tag)
    if tag == 'v16ghd':      # 촘촘 검사: gseries 의 body.comps 가 스텝마다
        gs = m.get('gseries', [])
        comps = [g['body']['comps'] for g in gs]; ts = [g['t'] for g in gs]
        bad = [[t, c] for t, c in zip(ts, comps) if c != 1]
        out.update(dense_n=len(comps), dense_bad=len(bad), dense_bad_first=bad[:10], dense_tmin=min(ts) if ts else None, dense_tmax=max(ts) if ts else None)
        ref = V.run_dir(scn, seed, 'v16gh')
        if os.path.exists(os.path.join(ref, 'h.npy')):
            a = np.load(os.path.join(d, 'h.npy')); b = np.load(os.path.join(ref, 'h.npy'))
            out['same_as_v16gh'] = bool(np.array_equal(a, b)); out['maxdiff_vs_v16gh'] = float(np.abs(a.astype(float) - b).max())
        return out
    rows = []
    for S in V.load_vs(d):
        wet = S['wet'].astype(bool); h = S['h'].astype(float); t = float(S['t'])
        lab, nc = V.torus_label(wet)
        r = dict(t=t, comps=nc, area=int(wet.sum()), Vb=float(h[wet].sum()))
        if nc > 1:
            vol = np.bincount(lab.ravel(), weights=np.where(wet, h, 0).ravel()); vol[0] = 0
            r['detached_frac'] = float(1 - vol.max() / vol.sum())
        else: r['detached_frac'] = 0.0
        for nm, (hth, fr) in VARIANTS.items():
            db = V.dumbbell(wet, h, hth, fr, do_d2=True, lab_w=lab)
            r[f'D1_{nm}'] = db['D1']; r[f'D2_{nm}'] = db['D2']; r[f'nbig_{nm}'] = db['nbig']
            if nm == 'main': r['pairs'] = db['pairs']
        r['thick_frac'] = float(h[wet & (h > 0.5)].sum() / max(r['Vb'], 1e-12))
        if t >= 1000 - 1e-6: r.update(V.late_cells(S))
        # 정맥 (보조): Cmean > 4 인 활성 간선 수
        act = V.active(wet); Cm = S['Cmean']
        r['vein_edges'] = int(sum(int((act[k] & (Cm[k] > 4)).sum()) for k in range(4)))
        rows.append(r)
    os.makedirs(os.path.join(DATA, 'long_rows'), exist_ok=True)
    json.dump(rows, open(os.path.join(DATA, 'long_rows', out['run'] + '.json'), 'w'))
    def wmean(key, t0, t1):
        v = [float(r[key]) for r in rows if t0 - 1e-6 <= r['t'] <= t1 + 1e-6 and key in r]
        return (float(np.mean(v)) if v else None), len(v)
    for nm in VARIANTS:
        for D in ('D1', 'D2'):
            out[f'f_{D}_{nm}'], n = wmean(f'{D}_{nm}', 200, 2000)
            out[f'f_{D}_{nm}_late'], _ = wmean(f'{D}_{nm}', 1000, 2000)
    out['n_win2'] = n
    for k in ('film', 'dead', 'deadC', 'endline', 'onewide', 'area'):
        out[f'late_{k}'], out['n_win3'] = wmean(k, 1500, 2000)
    for k in ('film', 'dead', 'deadC', 'endline'):
        v = [r[k] / max(r['area'], 1) for r in rows if 1500 - 1e-6 <= r['t'] <= 2000 + 1e-6 and k in r]
        out[f'late_{k}_per_area'] = float(np.mean(v)) if v else None
    out['n_snap'] = len(rows); out['snap_comps_gt1'] = [[r['t'], r['comps'], round(r['detached_frac'], 4)] for r in rows if r['comps'] != 1]
    out['max_detached_frac'] = max(r['detached_frac'] for r in rows) if rows else None
    out['late_vein_edges'], _ = wmean('vein_edges', 1500, 2000)
    out['late_thick_frac'], _ = wmean('thick_frac', 1500, 2000)
    return out


def do_other(job):
    scn, seed, tag = job
    out, m, d = base(scn, seed, tag)
    tt = out['t_touch'] or []
    T = float(out['T'])
    if scn == 'mig':
        out['t_mig'] = tt[0] if tt and tt[0] is not None else T
        out['missed'] = int(not tt or tt[0] is None)
    else:
        out['missed'] = int(sum(v is None for v in tt))
        out['t_all'] = T if out['missed'] else max(tt)
        got = [v for v in tt if v is not None]
        out['t_first'] = min(got) if got else T
        M = float(out['food_M']); fe = out['fM_end']
        out['eaten'] = float(sum(M - (v if v is not None else M) for v in fe) / (len(fe) * M))
    # 저장 상태마다 성분 수 (보조)
    cs = [V.torus_label(S['wet'].astype(bool))[1] for S in V.load_vs(d)]
    out['snap_comps_max'] = max(cs) if cs else None; out['snap_comps_gt1'] = int(sum(c > 1 for c in cs))
    return out


def work(job):
    try:
        return do_long(job) if job[0] == 'long' else do_other(job)
    except Exception as e:
        return dict(run=f'b_{job[0]}_s{job[1]}_{job[2]}', scn=job[0], seed=int(job[1]), tag=job[2], error=repr(e))


if __name__ == '__main__':
    nj = int(sys.argv[sys.argv.index('-j') + 1]) if '-j' in sys.argv else 4
    jobs = [tuple(j) for j in JOBS]
    jobs.sort(key=lambda j: (j[2] == 'v16ghd', j[0] != 'long'))     # 촘촘 검사는 v16gh 뒤에
    with Pool(nj) as p: res = p.map(work, jobs, chunksize=1)
    os.makedirs(DATA, exist_ok=True)
    json.dump(res, open(os.path.join(DATA, 'summary.json'), 'w'), indent=1)
    err = [r for r in res if 'error' in r]
    print(len(res), 'runs,', len(err), 'errors'); [print(r['run'], r['error']) for r in err]
