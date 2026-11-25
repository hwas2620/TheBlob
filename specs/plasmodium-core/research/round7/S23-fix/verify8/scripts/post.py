#!/usr/bin/env python3
"""verify8 보조 집계 (등록 기준 밖; CRITERIA_CHANGES.md). usage: post.py -> judge/SUPP.json"""
import numpy as np, json, os, glob
V = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
R = {}; X = {}
for f in glob.glob(os.path.join(V, 'data', '*.json')):
    r = json.load(open(f)); R[(r['scn'], r['seed'], r['arm'])] = r
for f in glob.glob(os.path.join(V, 'data_extra', '*.json')):
    x = json.load(open(f)); r = R[next(k for k in R if R[k]['run'] == x['run'])]; X[(r['scn'], r['seed'], r['arm'])] = x
pairs = lambda scns: [k[:2] for k in sorted(R) if k[2] == 'v8c' and k[0] in scns and (k[0], k[1], 'v8v') in R]
ALL = ('mig', 'long', 'food3', 'asym3', 'food4', 'slimeall'); FOOD = ('food3', 'asym3', 'food4')
S = {}


def pm(key, scns, tmin_f=lambda r: 60.0):
    rows = []
    for s, sd in pairs(scns):
        v = []
        for a in ('v8c', 'v8v'):
            r = R[(s, sd, a)]; t0 = tmin_f(r); xs = [o[key] for o in X[(s, sd, a)]['snaps'] if o['t'] >= t0 and o.get(key) is not None]
            v.append(float(np.mean(xs)) if xs else np.nan)
        rows.append((s, sd, v[0], v[1]))
    c = np.nansum([x[2] for x in rows]); v = np.nansum([x[3] for x in rows]); lower = sum(x[3] < x[2] for x in rows); nt = sum(x[3] != x[2] for x in rows)
    by = {}
    for s, sd, a, b in rows: by.setdefault(s, []).append((a, b))
    return dict(ctrl_mean=round(c / len(rows), 3), cand_mean=round(v / len(rows), 3), ratio=round(v / c, 4) if c > 0 else None, pairs_lower=lower, pairs_nontie=nt,
                by_scn={k: [round(float(np.nanmean([p[0] for p in vv])), 3), round(float(np.nanmean([p[1] for p in vv])), 3)] for k, vv in by.items()})


first = lambda r: min([x for x in r['metrics']['t_touch'] if x is not None] or [1e9]) + 20.0
S['c3_main'] = {k: pm(k, ALL) for k in ('nf_thread_main', 'nf_tipr_main', 'nf_thread_main_01', 'thread_main')}
S['c6_robust'] = {k: pm(k, FOOD, first) for k in ('rtail_cells', 'rtail_max', 'rtail_n5', 'rtail_old_cells', 'tail_main', 'tail_main_max')}
S['c6_robust_mig'] = {k: pm(k, ('mig', 'long')) for k in ('rtail_cells', 'rtail_max', 'tail_main', 'tail_main_max')}

# 7(b) 고친 시험: t_f 이후 넓이가 지금까지의 최소보다 5% 넘게 다시 늘지 않고, 끝 덩이와의 IoU 가 0.02 넘게 줄지 않음
# 7(d) 부피 기준: 끝 덩이 칸에 든 부피 몫 conc 가 갇힐 때 값에서 끝 값까지 10% -> 90% 오르는 데 걸린 시간 (20 시간 간격 스냅숏, 선형 보간)
rows = []
for k, r in sorted(R.items()):
    if k[2] != 'v8v' or 'scl' not in r: continue
    sc = r['scl']; ts = sc['t_scl']; t90 = (sc['timing'] or {}).get('t90') or 0.0; t_f = ts + t90
    ss = [s for s in r['snaps'] if s['t'] >= t_f]; iou = dict((t, v) for t, v in sc['iou_final'])
    amin = np.inf; ok = True; imax = -1
    for s in ss:
        if s['area'] > 1.05 * amin: ok = False
        amin = min(amin, s['area']); i = iou.get(s['t'], 1.0)
        if i < imax - 0.02: ok = False
        imax = max(imax, i)
    c = np.array(sc['conc']); y = c[:, 1]; t = c[:, 0]; lo, hi = y[0], y[-1]
    def cross(p):
        g = lo + p * (hi - lo); j = np.nonzero(y >= g)[0]
        if not j.size: return None
        j = j[0]
        if j == 0: return float(t[0])
        return float(t[j - 1] + (g - y[j - 1]) / max(y[j] - y[j - 1], 1e-12) * (t[j] - t[j - 1]))
    c10, c50, c90 = cross(0.1), cross(0.5), cross(0.9)
    ser = np.load(os.path.join(V, '..', 'model', 'runs', r['run'], 'series.npz')); a = ser['area']; dt = float(ser['dt']); i0 = int(round(ts / dt))
    flat = None
    for j in range(i0, a.size):
        if a[j] < 0.97 * a[i0]: flat = round((j - i0) * dt, 1); break
    rows.append(dict(run=r['run'], t_scl=ts, T=r['T'], qualified=(r['T'] - ts) >= 300, b_fixed=ok, conc_trap=round(float(lo), 3), conc_t10=None if c10 is None else round(c10 - ts, 1),
                     conc_t50=None if c50 is None else round(c50 - ts, 1), conc_t90=None if c90 is None else round(c90 - ts, 1),
                     conc_10_90=None if (c10 is None or c90 is None) else round(c90 - c10, 1), area_t10=sc['timing']['t10'], area_t90=t90, area_max10=sc['timing']['max10'],
                     area_flat_until=flat, area_final=sc['area_final'], amin=sc['amin'], vol=sc['vol_final'], A_peak_after=sc['timing']['A_max_after'], A0=sc['timing']['A0'],
                     hmax_final=max(p[1] for p in sc['lump_final']['prof']) if sc['lump_final']['prof'] else None))
S['c7_rows'] = rows

# 균핵: 같은 부피 판의 칸 수
S['c7_areas'] = {}
for x in rows: S['c7_areas'].setdefault(str(round(x['vol'])), []).append((x['run'], x['area_final'], x['amin']))
# 주장 2: 시나리오별
S['c2_by'] = {}
J = json.load(open(os.path.join(V, 'judge', 'JUDGE.json')))
for rr in J['c2']['rows']: S['c2_by'].setdefault(rr['scn'], []).append((rr['c_db'], rr['v_db']))
S['c2_by'] = {k: [round(float(np.mean([a for a, b in v])), 4), round(float(np.mean([b for a, b in v])), 4), len(v)] for k, v in S['c2_by'].items()}
json.dump(S, open(os.path.join(V, 'judge', 'SUPP.json'), 'w'), ensure_ascii=False, indent=1)
for k, v in S.items():
    if k != 'c7_rows': print(k, json.dumps(v, ensure_ascii=False))
for x in rows: print(x)
