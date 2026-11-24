#!/usr/bin/env python3
"""verify5: 실행 하나를 잰다. usage: measure.py RUN_DIR OUT_JSON

읽는 것: params.json, metrics.json, vs_t*.npz (20 시간 단위마다의 상태), 끝 상태 wet.npy·h.npy, slime.npy
쓰는 것: OUT_JSON (스냅샷마다의 측정, 끝 상태 측정, 갇힘 시각, 건강 수치)
"""
import sys, os, json, glob, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v5lib as L

TRAP_ON = 0.05      # 갇힘: 둘레의 '새 땅' 몫 r(t) < 0.05 인 첫 스냅샷이고
TRAP_STAY = 0.10    #       그 뒤 모든 스냅샷에서 r < 0.10


def debris_of(pieces):
    return [p for p in pieces if p['share'] < L.DEBRIS_FRAC]


def main(rd, outp):
    P = json.load(open(os.path.join(rd, 'params.json')))
    M = json.load(open(os.path.join(rd, 'metrics.json')))
    N = int(P['N']); c0 = N / 2 - 0.5
    jj, ii = np.mgrid[0:N, 0:N]
    wet0 = np.hypot(ii - c0, jj - c0) < P['R_init']
    U = wet0.copy()                                # 지금까지 스냅샷에서 한 번이라도 젖었던 셀 (점액의 아래 어림)
    files = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    snaps = []; labs = []; debm_prev = np.zeros((N, N), bool)
    for f in files:
        Z = np.load(f)
        t = float(Z['t']); wet = Z['wet'].astype(bool); h = Z['h'].astype(np.float64); age = Z['age'].astype(np.float64); Qg = Z['Qgross']
        lab, pieces, bodies = L.bodies_and_lumps(wet, h, N)
        deb = debris_of(pieces)
        debm = np.isin(lab, [p['id'] for p in deb]) if deb else np.zeros((N, N), bool)
        ovl = np.bincount(lab[debm_prev], minlength=int(lab.max()) + 1)      # 앞 스냅샷의 부스러기와 겹친 셀 수 (조각마다)
        n_new = sum(1 for p in deb if ovl[p['id']] == 0)                     # 새로 생긴 부스러기 = 앞 스냅샷의 부스러기와 한 셀도 겹치지 않는 것
        debm_prev = debm
        sens = {}
        for tr in (0.4, 0.6):
            _, _, bs = L.bodies_and_lumps(wet, h, N, thick_rel=tr, with_geom=False)
            sens[f'multi_{tr}'] = any(b['n_lumps'] >= 2 for b in bs); sens[f'dumb_{tr}'] = any(b['dumbbell'] for b in bs)
        U |= wet
        rim = L.dilate8(wet) & ~wet
        r = float((rim & ~U).sum()) / max(int(rim.sum()), 1)
        ds = L.dead_structures(wet, h, age, Qg)
        snaps.append(dict(t=round(t, 2), area=int(wet.sum()), vol=float(np.maximum(h[wet], 0).sum()), n_pieces=len(pieces),
                          n_debris=len(deb), n_debris_new=n_new, debris_shares=[round(p['share'], 5) for p in deb], debris_area=int(sum(p['area'] for p in deb)),
                          bodies=bodies, any_multi=any(b['n_lumps'] >= 2 for b in bodies), any_dumb=any(b['dumbbell'] for b in bodies),
                          all_scl=bool(bodies) and all(b['scl'] for b in bodies), sens=sens,
                          rimfresh=round(r, 5), board_fresh=round(1.0 - float(U.sum()) / (N * N), 5), dead=ds, cen=[float(v) for v in Z['cen']]))
        labs.append(lab.astype(np.int32))
    # 갇힘 시각
    rs = [s['rimfresh'] for s in snaps]; T_trap = None
    for k in range(len(snaps)):
        if rs[k] < TRAP_ON and all(x < TRAP_STAY for x in rs[k:]):
            T_trap = snaps[k]['t']; break
    # 끝 상태
    wetE = np.load(os.path.join(rd, 'wet.npy')).astype(bool); hE = np.load(os.path.join(rd, 'h.npy')).astype(np.float64)
    labE, piecesE, bodiesE = L.bodies_and_lumps(wetE, hE, N)
    final = dict(area=int(wetE.sum()), n_pieces=len(piecesE), n_debris=len(debris_of(piecesE)), debris_shares=[round(p['share'], 5) for p in debris_of(piecesE)], bodies=bodiesE,
                 same_as_last_snapshot=bool(snaps and np.array_equal(wetE, np.load(files[-1])['wet'].astype(bool))))
    # 갇힐 때 10% 넘게 나뉜 몸들이 끝에 각자 균핵인지 (4d)
    split = None
    if T_trap is not None:
        k = [s['t'] for s in snaps].index(T_trap); labT = labs[k]
        bigT = [b for b in snaps[k]['bodies'] if b['share'] > 0.10]
        rec = []
        for b in bigT:
            ov = np.bincount(labE[labT == b['id']], minlength=int(labE.max()) + 1); ov[0] = 0
            e = int(np.argmax(ov)) if ov.sum() > 0 else 0
            eb = next((x for x in bodiesE if x['id'] == e), None)
            rec.append(dict(share_trap=b['share'], end_id=e, end_share=None if eb is None else eb['share'], end_scl=None if eb is None else eb['scl']))
        ends = [x['end_id'] for x in rec]
        for x in rec: x['merged'] = ends.count(x['end_id']) > 1
        split = dict(n_big=len(bigT), bodies=rec)
    # 점액 어림 확인: 끝의 점액 중 스냅샷 합집합에 없는 몫
    sl = np.load(os.path.join(rd, 'slime.npy')) > 0.5
    slime_missed = float((sl & ~U).sum()) / max(int(sl.sum()), 1)
    keys = ('name', 'stop', 't_end', 'steps_done', 'runtime', 'V0', 'Vinj', 'V_end', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step', 'neg_end_cellsteps', 'neg_end_steps',
            'V_crumb', 'crumb_cells', 't_touch', 't_cover', 't_exh', 'foods', 't_scl', 'scl_steps', 'fission_runs', 'conn_kept_cellsteps', 'disp', 'path_len', 'area_end')
    met = {k: M.get(k) for k in keys}
    met['traj'] = M.get('traj')
    out = dict(run=os.path.basename(rd.rstrip('/')), N=N, T=float(P['T']), dt=float(P['dt']), steps_expected=int(round(P['T'] / P['dt'])) + 1, seed=int(P['seed']),
               foods_param=P['foods'], T_trap=T_trap, slime_missed=round(slime_missed, 5), board_slime_end=round(float(sl.mean()), 5),
               snaps=snaps, final=final, split=split, metrics=met)
    os.makedirs(os.path.dirname(os.path.abspath(outp)), exist_ok=True)
    json.dump(out, open(outp, 'w'), default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print(os.path.basename(rd), 'snaps', len(snaps), 'T_trap', T_trap, 'final debris', final['n_debris'], 'slime_missed', round(slime_missed, 4))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
