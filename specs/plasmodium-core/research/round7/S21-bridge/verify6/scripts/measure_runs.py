#!/usr/bin/env python3
"""실행 폴더마다 측정해 verify6/data/<실행이름>.json 에 쓴다.

usage: measure_runs.py RUN_DIR [RUN_DIR ...]   (이미 측정한 것은 건너뛴다. --force 로 다시)
"""
import glob, json, os, sys
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import meas as M

DATA = os.environ.get('VERIFY6_DATA') or os.path.normpath(os.path.join(HERE, '..', 'data'))


def parse_name(rd):
    nm = os.path.basename(rd.rstrip('/'))
    a = nm.split('_')            # b_<scn>_s<seed>_<tag>
    return dict(name=nm, scn=a[1], seed=int(a[2][1:]), tag=a[3])


def one(rd):
    try:
        return _one(rd)
    except Exception as e:      # 돌다 죽은 실행(metrics.json 없음 등): 건너뛰고 알린다. 판정(주장 8)에서 '자료 없음'으로 잡힌다
        return os.path.basename(rd.rstrip('/')), f'ERROR {type(e).__name__}: {e}'


def _one(rd):
    info = parse_name(rd)
    out_path = os.path.join(DATA, info['name'] + '.json')
    if os.path.exists(out_path) and '--force' not in sys.argv:
        return info['name'], 'skip'
    P = json.load(open(os.path.join(rd, 'params.json')))
    met = json.load(open(os.path.join(rd, 'metrics.json')))
    ser = np.load(os.path.join(rd, 'series.npz'))
    N = int(P['N']); dt = float(P['dt']); c0 = N / 2 - 0.5
    keys = ('stop', 't_end', 'steps_done', 'runtime', 'V0', 'V_end', 'Vinj', 'V_crumb', 'crumb_cells', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step',
            'neg_end_cellsteps', 'neg_end_steps', 'neg_cellsteps', 't_touch', 't_cover', 't_exh', 't_scl', 'scl_steps', 'fission_runs', 'disp', 'path_len',
            'area_end', 'foods', 'conn_kept_cellsteps', 'ret_cellsteps', 'tiphome_cells', 'lim_steps', 'lim_cut_max', 'mg_err', 'mg_err_n')
    R = dict(info, N=N, T=float(P['T']), dt=dt, c0=c0, steps_expected=int(round(P['T'] / dt)) + 1, met={k: met.get(k) for k in keys})
    R['traj'] = met['traj']
    R['P'] = {k: P.get(k) for k in ('foods', 'food_M', 'eat', 'slime0', 'R_init', 'ncyc', 'mg_deep', 'tri_rnd', 'scl_f', 'keep_conn')}
    errs = json.load(open(os.path.join(rd, 'mg_err_series.json')))
    R['mg_err_series'] = errs
    area = ser['area']; R['area_1t'] = [int(v) for v in area[::max(1, int(round(1.0 / dt)))]]
    # ---- 장면들 ----
    files = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
    twet = np.load(os.path.join(rd, 'twet.npy')) if os.path.exists(os.path.join(rd, 'twet.npy')) else None
    ever = None; frames = []; wets = []; hs = []
    init_slime = None
    for f in files:
        Z = np.load(f)
        S = {k: Z[k] for k in ('wet', 'h', 'age', 'Qgross', 'C')}; S['t'] = float(Z['t'])
        wet = S['wet'].astype(bool); t = S['t']
        if ever is None:
            jj, ii = np.mgrid[0:N, 0:N]
            wet0 = np.hypot(ii - c0, jj - c0) < float(P['R_init'])
            ever = wet0.copy()
            init_slime = np.zeros((N, N), bool)
            if P.get('slime0') == 'all': init_slime = ~wet0
            elif P.get('slime0') == 'half': init_slime = (ii < c0) & ~wet0
        ever |= wet
        ev = ever | ((twet >= 0) & (twet <= t) if twet is not None else False)
        slime_now = (ev | init_slime) & ~wet
        fm = M.frame_measures(S)
        fm['fresh_rim'] = M.fresh_rim_share(wet, slime_now)
        fm['scl_state'] = M.scl_state(fm)
        fm['cen'] = [float(v) for v in Z['cen']]
        frames.append(fm); wets.append(wet); hs.append(np.where(wet, S['h'], 0.0).astype(np.float32))
    # 마지막 장면의 몸(가장 큰 조각)과 비교: 장면마다 마지막 몸 전체와의 IoU, 균핵이 시작된 때의 덩이 자리와의 IoU
    if frames:
        Wf = wets[-1]
        for fm, w in zip(frames, wets):
            fm['iou_final'] = float((w & Wf).sum() / max((w | Wf).sum(), 1))
        lab, n = M.tlabel(Wf)
        if n:
            vol = np.bincount(lab.ravel(), weights=hs[-1].ravel().astype(float), minlength=n + 1); vol[0] = -1
            Mf = lab == int(np.argmax(vol)); A = int(Mf.sum())
            ts = met.get('t_scl')
            if ts is not None:
                k0 = max([i for i, fm in enumerate(frames) if fm['t'] <= ts] or [0])
                from scipy import ndimage as ndi
                G = ndi.gaussian_filter(hs[k0].astype(float), 3.0, mode='wrap')
                top = np.zeros(G.size, bool); top[np.argsort(-G.ravel(), kind='stable')[:A]] = True; MA = top.reshape(G.shape)
                R['scl_shape'] = dict(t_on=ts, t_on_frame=frames[k0]['t'], area_final=A, iou_mass=float((Mf & MA).sum() / max((Mf | MA).sum(), 1)),
                                      overlap_onset=float((Mf & wets[k0]).sum() / max(A, 1)))
    R['frames'] = frames
    # 마지막 상태의 새 땅 몫 (실행 끝에 저장된 점액으로 정확히)
    if os.path.exists(os.path.join(rd, 'slime.npy')):
        sl = np.load(os.path.join(rd, 'slime.npy')) >= 0.5; wf = np.load(os.path.join(rd, 'wet.npy')).astype(bool)
        R['fresh_rim_end'] = M.fresh_rim_share(wf, sl & ~wf)
    json.dump(R, open(out_path, 'w'))
    return info['name'], len(frames)


if __name__ == '__main__':
    os.makedirs(DATA, exist_ok=True)
    rds = [a for a in sys.argv[1:] if not a.startswith('--')]
    with Pool(int(os.environ.get('NPROC', '4'))) as pool:
        for nm, r in pool.imap_unordered(one, rds):
            print(nm, r, flush=True)
