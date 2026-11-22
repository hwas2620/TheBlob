#!/usr/bin/env python3
"""실행 폴더들을 재서 verify/data/summary.json 에 쓴다. 판정은 judge.py 가 한다.

usage: measure.py [--only SCN]
읽는 것: model/runs/b_<scn>_s<seed>_<v15c|v15k>/ 의 metrics.json, params.json, series.npz, wet.npy, vs_t*.npz (먹이·이주), mon.npz (long, vrun.py 가 남김)
"""
import glob, json, os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.normpath(os.path.join(HERE, '..', '..', 'model'))
METRICS = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'stage0', 'metrics'))
sys.path.insert(0, HERE)
import monitor

TAGS = ('v15c', 'v15k')
LATE = 1500.0          # 주장 2 의 "늦은 때" = t >= 1500 (끝 2000)


def wrapd(v, N): return (v + N / 2.0) % N - N / 2.0


def track(states, N):
    """저장 시각마다의 h 무게중심. 직전 무게중심 기준 최소 상으로 따라간다(풀린 좌표)"""
    yy, xx = np.indices((N, N)); c0 = N / 2 - 0.5; cx = cy = c0; out = []
    for t, h in states:
        m = h.sum()
        if m > 0:
            for _ in range(4):
                cx += float((h * wrapd(xx - cx, N)).sum() / m); cy += float((h * wrapd(yy - cy, N)).sum() / m)
        out.append((t, cx, cy))
    return out


def health(rd, met, P, scn):
    exp = int(round(P['T'] / P['dt'])) + 1
    o = dict(stop=met.get('stop', ''), steps_done=met.get('steps_done'), expected_steps=exp)
    o['complete'] = bool(o['stop'] == '' and o['steps_done'] == exp)
    for k in ('neg_end_cellsteps', 'neg_end_steps', 'h_min_end_of_step', 'mass_err_max', 'V_crumb', 'crumb_cells', 'neg_cellsteps', 'h_min_seen',
              'conn_kept_cellsteps', 'ret_cellsteps', 'sup_updates', 'bridge_kept_cellsteps', 'neg_fill_cellsteps', 'area_end', 'disp', 'runtime', 'V0', 'Vinj', 'V_end'):
        o[k] = met.get(k)
    V0 = met['V0']
    # 내 부피 점검: 먹이가 없으면 스텝마다의 Σh(series.npz), 먹이가 있으면 기록(log, 50 스텝마다)의 V - 먹은 양
    if P.get('eat', 0) > 0:
        o['my_mass_err'] = float(max(abs(e['V'] - V0 - e['Vinj']) / V0 for e in met['log']))
        o['my_mass_err_src'] = 'log'
    else:
        s = np.load(os.path.join(rd, 'series.npz')); o['my_mass_err'] = float(np.abs(s['vol'] - V0).max() / V0); o['my_mass_err_src'] = 'series'
    o['my_mass_err_end'] = float(abs(met['V_end'] - V0 - met['Vinj']) / V0)
    w = np.load(os.path.join(rd, 'wet.npy')); h = np.load(os.path.join(rd, 'h.npy'))
    o['ncomp_end'] = monitor.tlabel(w)[1]; o['area_end_wetnpy'] = int(w.sum())
    o['hmin_end_file'] = float(h[w].min()) if w.any() else None
    return o


def saved_states(rd, pat):
    out = []
    for f in sorted(glob.glob(os.path.join(rd, pat))):
        Z = np.load(f); out.append((float(Z['t']), Z['wet'].astype(bool), Z['h'].astype(np.float64)))
    return out


def m_long(rd, o, P):
    Z = np.load(os.path.join(rd, 'mon.npz')); A = Z['stats']; keys = list(Z['keys']); col = {k: A[:, i] for i, k in enumerate(keys)}
    t = col['t']; o['mon_steps'] = int(t.size); o['mon_t'] = [float(t.min()), float(t.max())]
    sp = col['ncomp'] >= 2
    o['split_frac'] = float(sp.mean()); o['t_first_split'] = float(t[sp][0]) if sp.any() else None
    o['ncomp_max'] = int(col['ncomp'].max())
    o['volout_mean'] = float(col['vol_out'].mean()); o['volout_max'] = float(col['vol_out'].max())
    o['areaout_mean'] = float(col['area_out'].mean())
    o['n_neg_steps_mon'] = int((col['n_neg'] > 0).sum())
    for a in monitor.THICK:
        for b in monitor.BIGF: o[f'big2_{a}_{b}'] = float((col[f'big_{a}_{b}'] >= 2).mean())
    L = t >= LATE
    for k in ('thin', 'line', 'line3', 'area'): o[f'late_{k}'] = float(col[k][L].mean())
    o['late_thin_frac'] = float((col['thin'][L] / np.maximum(col['area'][L], 1)).mean()); o['late_line_frac'] = float((col['line'][L] / np.maximum(col['area'][L], 1)).mean())
    o['late_split_frac'] = float(sp[L].mean()); o['late_big2'] = float((col['big_0.6_0.1'][L] >= 2).mean())
    # 시간 구간별 (그림과 보고용)
    seg = []
    for a, b in ((0, 400), (400, 800), (800, 1200), (1200, 1600), (1600, 2001)):
        m = (t >= a) & (t < b)
        seg.append(dict(t=[a, b], split=float(sp[m].mean()), volout=float(col['vol_out'][m].mean()), big2=float((col['big_0.6_0.1'][m] >= 2).mean()),
                        thin=float(col['thin'][m].mean()), line=float(col['line'][m].mean()), area=float(col['area'][m].mean())))
    o['segments'] = seg
    st = saved_states(rd, 'lv_t*.npz')
    if st:
        tr = track([(t_, h_) for t_, _, h_ in st], P['N']); c0 = P['N'] / 2 - 0.5
        o['disp_end'] = float(np.hypot(tr[-1][1] - c0, tr[-1][2] - c0))
        fa = np.radians(P['foods'][0][0]) if P.get('foods') else 0.0
        o['disp_toward'] = float((tr[-1][1] - c0) * np.cos(fa) + (tr[-1][2] - c0) * np.sin(fa))
        o['path'] = float(sum(np.hypot(tr[i][1] - tr[i - 1][1], tr[i][2] - tr[i - 1][2]) for i in range(1, len(tr))))


def m_food(rd, o, P, met):
    tt = met['t_touch']; T = P['T']
    o['t_touch'] = tt; o['n_foods'] = len(tt); o['n_reached'] = int(sum(v is not None for v in tt))
    o['t_all'] = float(max(v for v in tt)) if all(v is not None for v in tt) else float(T)
    o['eaten'] = float(met['Vinj']); o['t_exh'] = met.get('t_exh'); o['fM_end'] = met.get('fM_end')
    st = saved_states(rd, 'vs_t*.npz')
    nc = [monitor.tlabel(w)[1] for _, w, _ in st]
    vo = []
    for _, w, h in st:
        lab, n = monitor.tlabel(w)
        vol = np.bincount(lab[w], weights=h[w], minlength=n + 1); vo.append(1.0 - vol.max() / vol.sum() if vol.sum() > 0 else 0.0)
    o['saved_split_frac'] = float(np.mean(np.array(nc) >= 2)) if nc else None; o['saved_volout_max'] = float(max(vo)) if vo else None
    try:
        sys.path.insert(0, METRICS); import bmet
        b = bmet.food(rd)
        o['bmet'] = {k: b.get(k) for k in ('pass', 'reached', 'thick', 'same_ok', 'pairs', 'body_min', 'body_min_all', 'ratio')}
    except Exception as e:       # 보조 지표일 뿐이다
        o['bmet'] = dict(error=repr(e))


def m_mig(rd, o, P, met):
    T = P['T']; tt = met['t_touch']
    o['t_touch'] = float(tt[0]) if tt and tt[0] is not None else float(T); o['reached'] = bool(tt and tt[0] is not None)
    st = saved_states(rd, 'vs_t*.npz')
    tr = track([(t_, h_) for t_, _, h_ in st], P['N']); c0 = P['N'] / 2 - 0.5; fa = np.radians(P['foods'][0][0])
    o['t_last'] = tr[-1][0]
    o['disp_toward'] = float((tr[-1][1] - c0) * np.cos(fa) + (tr[-1][2] - c0) * np.sin(fa)); o['disp_end'] = float(np.hypot(tr[-1][1] - c0, tr[-1][2] - c0))
    nc = [monitor.tlabel(w)[1] for _, w, _ in st]; o['saved_split_frac'] = float(np.mean(np.array(nc) >= 2))
    tm = met['traj'][-1]; o['model_disp_toward'] = float((tm[1] - c0) * np.cos(fa) + (tm[2] - c0) * np.sin(fa))


def measure(rd):
    name = os.path.basename(rd.rstrip('/')); m = re.match(r'b_(.+?)_s(\d+)_(v15[ck])$', name)
    scn, seed, tag = m.group(1), int(m.group(2)), m.group(3)
    met = json.load(open(os.path.join(rd, 'metrics.json'))); P = json.load(open(os.path.join(rd, 'params.json')))
    o = dict(run=name, scn=scn, seed=seed, tag=tag, arm='control' if tag == 'v15c' else 'candidate',
             params={k: P.get(k) for k in ('sup_age', 'sup_cap', 'keep_conn', 'ret_h', 'ret_glob', 'T', 'N', 'gm_every', 'vsave')})
    o.update(health(rd, met, P, scn))
    if scn == 'long': m_long(rd, o, P)
    elif scn in ('food3', 'asym3', 'food4'): m_food(rd, o, P, met)
    elif scn == 'mig': m_mig(rd, o, P, met)
    return o


def main():
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    fp = os.path.join(HERE, '..', 'data', 'summary.json')
    res = json.load(open(fp)) if os.path.exists(fp) else {}
    for rd in sorted(glob.glob(os.path.join(MODEL, 'runs', 'b_*_s*_v15[ck]'))):
        name = os.path.basename(rd)
        if only and not name.startswith(f'b_{only}_'): continue
        if not os.path.exists(os.path.join(rd, 'metrics.json')): print('skip (unfinished)', name); continue
        seed = int(re.search(r'_s(\d+)_', name).group(1))
        if not 201 <= seed <= 219: continue          # 220 은 같음 시험에만 쓴다
        res[name] = measure(rd); print(name, 'ok', flush=True)
        json.dump(res, open(fp, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
