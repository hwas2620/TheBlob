#!/usr/bin/env python3
"""[검증자] 시간에 따른 지표. 저장된 상태(vs_t*.npz)마다 vmet.analyse_state 를 돌리고, 유량 오차 기록(mg_err_series.json)·음수 셀 기록(negrec.npy)·
위상 기록(ph_ser.npy)을 시간 창으로 묶는다. 결과는 tser/<이름>.json 에 저장.
usage: tser.py mig|food NAME ...  [--win a,b,c,...]   (창 경계. 기본: 0,100,200,300,400,500,...)"""
import json, os, sys, numpy as np, vmet
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(os.path.join(HERE, 'tser'), exist_ok=True)


def rows_of(name, kind):
    cache = os.path.join(HERE, 'tser', name + '.json')
    if os.path.exists(cache): return json.load(open(cache))
    rd = os.path.join(HERE, 'runs', name)
    states, G, P = vmet.load_states(rd)
    rows = []
    for S in states:
        r = vmet.analyse_state(S, G, P, do_path=(kind == 'food'))
        wet = S['wet'].astype(bool); h = S['h'].astype(float)
        r['neg_cells'] = int((wet & (h < 0)).sum()); r['thin_cells'] = int((wet & (h < 0.15)).sum())
        r['hmean'] = float(h[wet].mean()) if wet.any() else 0.0; r['Cmax'] = float(S['C'].max())
        for pk, pv in r['pairs'].items():
            if pv.get('path'): pv['minC'] = pv['path'].get('minC')
            pv.pop('path', None)
        rows.append(r)
    mg = json.load(open(os.path.join(rd, 'mg_err_series.json')))
    out = dict(name=name, dt=P['dt'], period=P['period'], rows=rows, mg=[[e[0] * P['dt'], e[1], e[2], int(e[0])] for e in mg])
    f = os.path.join(rd, 'negrec.npy')
    if os.path.exists(f):
        a = np.load(f)     # step, h, h_before, hstar, p, sage, age, Cn, resmask, tube, n_wet_nb, dist_food, n_neg
        # 스텝마다 가장 음수인 셀 하나(그 스텝의 기록 가운데 h 가 최소인 것)만 남긴다
        st = a[:, 0].astype(int); o = np.lexsort((a[:, 1], st)); a = a[o]; st = a[:, 0].astype(int); first = np.r_[True, st[1:] != st[:-1]]
        b = a[first]
        out['neg'] = [[float(x[0] * P['dt']), float(x[1]), float(x[2]), float(x[5]), float(x[6]), float(x[7]), float(x[8]), float(x[10]), float(x[11]), float(x[12])] for x in b]   # t, h, h_before, sage, age, Cn, resmask, nwet, dist_food, n_neg
    else: out['neg'] = []
    f = os.path.join(rd, 'ph_ser.npy')
    if os.path.exists(f):
        a = np.load(f); out['ph'] = [[float(x[0]), float(x[1]), float(x[4]), float(x[5]), float(x[8])] for x in a[::5]]     # t, R, rms dθ/dx, rms dθ/dy, cv h
    json.dump(out, open(cache, 'w'))
    return out


def show(name, kind, wins):
    o = rows_of(name, kind); rows = o['rows']; mg = np.array(o['mg']) if o['mg'] else np.zeros((0, 4)); ng = np.array(o['neg']) if o['neg'] else np.zeros((0, 10)); ph = np.array(o.get('ph') or np.zeros((0, 5)))
    print(f'--- {name} (dt {o["dt"]}, 주기 {o["period"]})')
    print('  창 | 상태 수 | 몸최대 부피 최소 | 몸 조각 수(끝) | 정맥최대 C>4 중앙/최소 | 정맥간선 C>4 중앙 | 넓이(끝) | 평균 h(끝) | 저장 시점의 음수 셀 최대 | 유량오차 중앙/90%/최대 (n) | 스텝 안 음수: 스텝 수, 최소 h, 음수 셀 수 합 | 위상 R 평균' + (' | 굵은 쌍 수(중앙 경로최소C>=5×정맥중앙C)' if kind == 'food' else ''))
    for a, b in zip(wins[:-1], wins[1:]):
        W = [r for r in rows if a < r['t'] <= b + 1e-6]
        if not W: continue
        m = mg[(mg[:, 0] > a) & (mg[:, 0] <= b)] if mg.size else mg; n_ = ng[(ng[:, 0] > a) & (ng[:, 0] <= b)] if ng.size else ng; p_ = ph[(ph[:, 0] > a) & (ph[:, 0] <= b)] if ph.size else ph
        s = f"  {a:4.0f}~{b:4.0f} | {len(W):2d} | {min(r['body_largest_vol'] for r in W):.3f} | {W[-1]['body_ncomp']:3d} | {np.median([r['vein4_largest'] for r in W]):.3f}/{min(r['vein4_largest'] for r in W):.3f} | {np.median([r['vein4_E'] for r in W]):.0f} | {W[-1]['area']} | {W[-1]['hmean']:.3f} | {max(r['neg_cells'] for r in W)} | "
        s += (f"{np.median(m[:, 1]):.3f}/{np.percentile(m[:, 1], 90):.3f}/{m[:, 1].max():.3f} ({len(m)})" if len(m) else '-') + ' | '
        s += (f"{len(n_)}, {n_[:, 1].min():.4f}, {int(n_[:, 9].sum())}" if len(n_) else '0, -, 0') + ' | ' + (f"{p_[:, 1].mean():.3f}" if len(p_) else '-')
        if kind == 'food':
            pk = sorted(W[0]['pairs']); vm = np.median([r['vein_medC'] for r in W])
            pc = [np.median([(r['pairs'][k].get('minC') or 0.0) for r in W]) for k in pk]
            s += f" | {sum(x >= 5 * vm for x in pc)}/{len(pk)} ({'/'.join('%.0f' % x for x in pc)}; 정맥중앙 {vm:.1f})"
        print(s)


if __name__ == '__main__':
    kind = sys.argv[1]; args = sys.argv[2:]; wins = None
    if '--win' in args:
        i = args.index('--win'); wins = [float(x) for x in args[i + 1].split(',')]; args = args[:i] + args[i + 2:]
    for n in args:
        if not os.path.exists(os.path.join(HERE, 'runs', n, 'metrics.json')): print(n, '(아직 없음)'); continue
        P = json.load(open(os.path.join(HERE, 'runs', n, 'params.json')))
        show(n, kind, wins or list(np.arange(0, P['T'] + 1, 100)) + ([P['T']] if P['T'] % 100 else []))
