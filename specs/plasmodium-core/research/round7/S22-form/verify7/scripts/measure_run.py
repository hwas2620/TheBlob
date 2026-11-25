#!/usr/bin/env python3
"""verify7: 실행 폴더 하나를 재서 verify7/data/<실행 이름>.json 에 쓴다.

usage: measure_run.py RUN_DIR [RUN_DIR ...]

- 저장 상태(vs_t*.npz, 20 시간마다)마다 v7lib.frame_measures
- metrics.json 의 기록(멈춤, 부피 오차, 음수, 닿은 시각, 균핵 시작 t_scl, 궤적), mg_err_series.json 의 유량 오차
- 균핵 분석(CRITERIA.md 2.7): 갇힌 시각 = t_scl(후보). 갇힘 장면 = t_scl 이하 마지막 저장 상태
"""
import json, os, sys, glob, re
import numpy as np
from scipy.ndimage import gaussian_filter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7lib as L

OUT = os.environ.get('V7_DATA') or os.path.normpath(os.path.join(HERE, '..', 'data'))


def load_frames(rd):
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    return fs


def scl_analysis(frames_raw, t_trap, sig=(2.0, 4.0, 8.0)):
    """frames_raw: [(t, wet, h)] 시각 순. 갇힘 장면부터 끝까지"""
    ts = np.array([f[0] for f in frames_raw])
    i0 = int(np.nonzero(ts <= t_trap + 1e-9)[0].max()) if (ts <= t_trap + 1e-9).any() else 0
    t0, wet0, h0 = frames_raw[i0]
    tE, wetE, hE = frames_raw[-1]
    hp0 = np.where(wet0, np.maximum(h0, 0), 0)
    labE, nE = L.torus_label(wetE)
    hpE = np.where(wetE, np.maximum(hE, 0), 0); VE = hpE.sum()
    volE = np.bincount(labE.ravel(), weights=hpE.ravel(), minlength=nE + 1)
    Mend = np.isin(labE, [k for k in range(1, nE + 1) if volE[k] >= L.BODY7 * VE])
    Md = Mend.copy()
    for d in L.ALL8:
        Md |= L.nb(Mend, d)
    out = dict(t_trap=float(t_trap), t_trap_frame=float(t0), t_end_frame=float(tE))
    # 갇힐 때 짙던 곳: 흐린 두께(sigma)의 끝 덩이 위 평균 / 갇힘 장면 몸 위 평균
    for s in sig:
        G = gaussian_filter(hp0, s, mode='wrap', truncate=3.0)
        Dr = []
        for k in range(1, nE + 1):
            if volE[k] >= L.BODY7 * VE:
                bm = labE == k
                Dr.append(float(G[bm].mean() / max(G[wet0].mean(), 1e-300)))
        out[f'D_ratio_s{int(s)}'] = Dr
    # 모임 곡선 f(t) = 끝 덩이(1칸 넓힘) 안 부피 / 전체 부피
    f = []
    for (t, w, h) in frames_raw[i0:]:
        hp = np.where(w, np.maximum(h, 0), 0)
        f.append([float(t), float(hp[Md].sum() / max(hp.sum(), 1e-300))])
    out['f_curve'] = f
    fa = np.array(f)
    if len(fa) >= 2:
        fs, fe = fa[0, 1], fa[-1, 1]
        out['f_start'] = float(fs); out['f_end'] = float(fe)
        if fe - fs > 0.05:
            def cross(q):
                lvl = fs + q * (fe - fs)
                for j in range(1, len(fa)):
                    if fa[j, 1] >= lvl:
                        a, b = fa[j - 1], fa[j]
                        return float(a[0] + (lvl - a[1]) / max(b[1] - a[1], 1e-12) * (b[0] - a[0]))
                return None
            out['t10'] = cross(0.1); out['t90'] = cross(0.9)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for rd in sys.argv[1:]:
        rd = rd.rstrip('/'); name = os.path.basename(rd)
        m = json.load(open(os.path.join(rd, 'metrics.json')))
        P = json.load(open(os.path.join(rd, 'params.json')))
        errs = json.load(open(os.path.join(rd, 'mg_err_series.json'))) if os.path.exists(os.path.join(rd, 'mg_err_series.json')) else []
        mt = re.match(r'b_(\w+?)_s(\d+)_(\w+)$', name)
        rec = dict(name=name, scn=mt.group(1), seed=int(mt.group(2)), tag=mt.group(3), N=P['N'], T=P['T'], dt=P['dt'],
                   foods=m.get('foods'), food_r=P.get('food_r'), c0=P['N'] / 2 - 0.5)
        for k in ('stop', 't_end', 'steps_done', 'runtime', 'V0', 'Vinj', 'V_end', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step', 'neg_end_cellsteps', 'neg_end_steps',
                  'V_crumb', 'crumb_cells', 't_scl', 'scl_steps', 'fission_runs', 't_touch', 't_cover', 't_exh', 'mg_err', 'mg_err_n', 'disp', 'lim_steps', 'neg_cellsteps',
                  'conn_kept_cellsteps', 'ret_cellsteps', 'tiphome_cells', 'sup_updates'):
            rec[k] = m.get(k)
        rec['traj'] = m['traj']
        rec['vlog'] = [[e['t'], e['V'], e['Vinj']] for e in m['log']]
        rec['mg_err_series'] = errs
        frames = []; raw = []
        for f in load_frames(rd):
            Z = np.load(f)
            t = float(Z['t']); wet = Z['wet'].astype(bool); h = Z['h'].astype(float)
            fm, _ = L.frame_measures(wet, h, Qg=Z['Qgross'].astype(float), hmean=Z['hmean'].astype(float))
            fm['t'] = t
            frames.append(fm); raw.append((t, wet, h))
        rec['frames'] = frames
        if rec['t_scl'] is not None and raw:
            rec['scl'] = scl_analysis(raw, rec['t_scl'])
        json.dump(rec, open(os.path.join(OUT, name + '.json'), 'w'))
        print(name, 'frames', len(frames), 'stop', rec['stop'], 't_scl', rec['t_scl'], flush=True)


if __name__ == '__main__':
    main()
