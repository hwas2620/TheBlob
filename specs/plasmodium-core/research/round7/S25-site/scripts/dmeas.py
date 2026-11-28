#!/usr/bin/env python3
"""S25 진단 측정 (판정 아님): 아홉째 검증자의 측정 코드(meas9.py = verify9/scripts/meas.py 복사)로 실행 폴더를 잰다.
usage: dmeas.py tail RUN...   (먹이 판: 첫 먹이 뒤 20 시간마다 엄격 꼬리, 먹이 닿은 시각)
       dmeas.py scl RUN...    (slimeall: 주장 7 (a)~(f))
RUN 은 실행 폴더 경로."""
import sys, os, glob, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meas9 as M

def vs(rd):
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); yield float(Z['t']), Z

def tail(rd):
    met = json.load(open(os.path.join(rd, 'metrics.json'))); tt = [x for x in met['t_touch'] if x is not None]; t0 = min(tt) if tt else None
    if t0 is None: return dict(touch=met['t_touch'], n=None)
    ns = []; sz = []; ne = []
    for t, Z in vs(rd):
        if t < t0 or int(round(t)) % 20: continue
        r = M.snapshot(Z['wet'].astype(bool), Z['h'].astype(float), Z['age'].astype(float), Z['Qgross'].astype(float))
        ns.append(r['tail']['n']); sz += r['tail']['sizes']; ne.append(r['tail_ext']['n'])
    return dict(touch=[None if x is None else round(x, 1) for x in met['t_touch']], last=max(x for x in met['t_touch']) if all(x is not None for x in met['t_touch']) else None,
                n=float(np.mean(ns)) if ns else 0.0, sizes=sz, mean_len=float(np.mean(sz)) if sz else 0.0, n_ext=float(np.mean(ne)) if ne else 0.0, tiphome=met.get('tiphome_cells'))

def scl(rd):
    met = json.load(open(os.path.join(rd, 'metrics.json')))
    snaps = [(t, Z['wet'].astype(bool), Z['h'].astype(float), Z['hmean'].astype(float)) for t, Z in vs(rd)]
    return M.sclerotium(snaps, met.get('t_scl'))

if __name__ == '__main__':
    mode = sys.argv[1]
    for rd in sys.argv[2:]:
        nm = os.path.basename(rd.rstrip('/'))
        if not os.path.exists(os.path.join(rd, 'metrics.json')): print(nm, 'missing'); continue
        if mode == 'tail':
            r = tail(rd)
            if r['n'] is None: print(nm, 'no touch', r['touch']); continue
            print(f"{nm:28s} touch {r['touch']} last {r['last']}  tails/state {r['n']:.2f}  mean_len {r['mean_len']:.1f}  max {max(r['sizes']) if r['sizes'] else 0}  ext/state {r['n_ext']:.2f}  tiphome {r['tiphome']}")
        else:
            s = scl(rd)
            if not s.get('trapped'): print(nm, 'not trapped'); continue
            a, c, d, e, f = s['a'], s['c'], s['d'], s['e'], s['f']
            pc = c['rank_mean'] >= 0.7 and c['peak_dist'] <= 3 and c['area'] >= c['area_min'] - 1 and c['disc_iou'] < 0.9
            pd = d.get('n_out', 0) < 10 or (d['dur'] >= 40 and d['maxwin10'] <= 0.35 and d['rho'] <= -0.5 and d['near_med'] >= d['q75'])
            pf = f['ratio'] >= 1.5 and f['rho'] >= 0.7 and f['mono'] and f['gradual']
            print(f"{nm:30s} t_scl {s['t_scl']}  (a) n_end {a['n_end']} max_after {a['max_bodies_after']} tail {a['tail_max_end']} | (c) rank {c['rank_mean']:.2f} pk {c['peak_dist']:.1f} area {c['area']} (min {c['area_min']:.0f}) iou {c['disc_iou']:.2f} {'OK' if pc else 'NO'}"
                  f" | (d) dur {d.get('dur', float('nan')):.0f} win {d.get('maxwin10', float('nan')):.2f} rho {d.get('rho', float('nan')):.2f} fill {d.get('fill_dur', float('nan'))} {'OK' if pd else 'NO'}"
                  f" | (e) holes {e['holes']} sol {e['solidity']:.2f} | (f) ratio {f['ratio']:.2f} rho {f['rho']:.2f} mono {f['mono']} grad {f['gradual']} {'OK' if pf else 'NO'}")
