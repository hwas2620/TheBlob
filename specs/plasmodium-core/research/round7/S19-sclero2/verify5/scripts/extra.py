#!/usr/bin/env python3
"""verify5: 실행 뒤에 더 본 것 (판정에 쓰지 않는 사후 관찰). usage: extra.py
쓰는 것: verify5/logs/extra.txt, verify5/data/extra.json
1) 이주의 옆 어긋남(유인원 방향에 수직, 셀)의 시간 변화
2) 옮겨 다니는 동안 실 셀의 전도도·흐름 (후보의 실이 hang_C 바닥값으로만 흐르는지)
3) 먹이 실험에서 후보의 굶음 규칙(sup, ret, hang)이 실제로 켜졌는지 (내 실행의 metrics.json)
4) 균핵이 맺히는 빠르기: 후보 t_scl 부터 처음 '모든 몸 균핵' 스냅샷까지, 그 사이 넓이 변화
5) 대조의 갇힌 뒤 멈춤: 마지막 100 시간 단위 동안 젖은 넓이가 바뀐 스냅샷 수
"""
import os, sys, json, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); V5 = os.path.dirname(HERE); S19 = os.path.dirname(V5)
sys.path.insert(0, HERE)
import v5lib as L
DATA = os.path.join(V5, 'data', 'runs'); RUNS = os.path.join(S19, 'model', 'runs')
OUT = {}; LINES = []


def say(*a):
    s = ' '.join(str(x) for x in a); LINES.append(s); print(s)


a = np.radians(27); u = np.array([np.cos(a), np.sin(a)]); nvec = np.array([-np.sin(a), np.cos(a)])
say('## 1) 이주의 옆 어긋남 (셀, + 는 y 가 커지는 쪽), mig 8 + long 12 의 평균')
lat = {}
for arm in 'cy':
    Ls = {t: [] for t in (80, 100, 120, 150, 200, 300, 400)}; mx = []
    for f in sorted(glob.glob(os.path.join(DATA, f'b_mig_s*_v5{arm}.json'))) + sorted(glob.glob(os.path.join(DATA, f'b_long_s*_v5{arm}.json'))):
        d = json.load(open(f)); tr = np.array(d['metrics']['traj'], float); P0 = d['N'] / 2 - 0.5
        for t in Ls:
            i = int(np.argmin(np.abs(tr[:, 0] - t))); Ls[t].append(float((tr[i, 1:3] - P0) @ nvec))
        m = tr[tr[:, 0] <= 400]; mx.append(float(np.max(np.abs((m[:, 1:3] - P0) @ nvec))))
    lat[arm] = dict(mean_by_t={t: round(float(np.mean(v)), 2) for t, v in Ls.items()}, sd_by_t={t: round(float(np.std(v, ddof=1)), 2) for t, v in Ls.items()}, max_abs_mean=round(float(np.mean(mx)), 2), n=len(mx))
    say(' ', '대조' if arm == 'c' else '후보', lat[arm])
OUT['lateral'] = lat

say('\n## 2) long, t = 400, 800, 1200: 나이 >= 20 인 실 셀')
th = {}
for arm in 'cy':
    rows = []
    for rd in sorted(glob.glob(os.path.join(RUNS, f'b_long_s4*_v5{arm}'))):
        for t in (400, 800, 1200):
            Z = np.load(os.path.join(rd, f'vs_t{t:04d}.npz')); w = Z['wet']; C = Z['C']; age = Z['age']
            thr = w & ~L.topen(w, L.S8) & (age >= 20)
            Cn = np.zeros(w.shape)
            for k, d in enumerate(L.DIRS): Cn = np.maximum(Cn, np.maximum(C[k], L.roll_back(C[k], d)))
            F = L.node_flux(Z['Qgross']); p90 = np.percentile(F[w & (age >= 20)], 90)
            rows.append((thr.sum(), thr.sum() / w.sum(), np.mean(np.abs(Cn[thr] - 20) < 0.5), np.median(F[thr]) / p90, np.median(Cn[thr])))
    r = np.array(rows, float)
    th[arm] = dict(thread_cells=round(float(r[:, 0].mean()), 1), thread_share=round(float(r[:, 1].mean()), 4), share_at_C20_floor=round(float(r[:, 2].mean()), 4),
                   median_flux_over_p90=round(float(r[:, 3].mean()), 3), median_Cn=round(float(r[:, 4].mean()), 2), n=len(rows))
    say(' ', '대조' if arm == 'c' else '후보', th[arm])
OUT['threads'] = th

say('\n## 3) 먹이·이주 실행에서 후보의 굶음 규칙이 켜진 정도 (metrics.json)')
act = {}
for scn in ('food4', 'food3', 'asym3', 'mig'):
    rr = []
    for rd in sorted(glob.glob(os.path.join(RUNS, f'b_{scn}_s4*_v5y'))):
        m = json.load(open(os.path.join(rd, 'metrics.json')))
        ex = [v for v in m['t_exh'] if v is not None]
        rr.append(dict(sup_updates=m['sup_updates'], sup_fed_skips=m['sup_fed_skips'], ret_cellsteps=m['ret_cellsteps'], hang_cellsteps=m['hang_cellsteps'],
                       first_exhaust=min(ex) if ex else None, last_touch=max([v for v in m['t_touch'] if v is not None], default=None)))
    act[scn] = dict(n=len(rr), fed_skips_mean=float(np.mean([x['sup_fed_skips'] for x in rr])), ret_cellsteps_mean=float(np.mean([x['ret_cellsteps'] for x in rr])),
                    runs_with_any_ret=sum(1 for x in rr if x['ret_cellsteps'] > 0), first_exhaust_min=min([x['first_exhaust'] for x in rr if x['first_exhaust'] is not None], default=None),
                    last_touch_max=max([x['last_touch'] for x in rr if x['last_touch'] is not None], default=None))
    say(' ', scn, act[scn])
OUT['starvation_rules_in_food_runs'] = act

say('\n## 4) 후보 균핵이 맺히는 빠르기 (long)')
fm = []
for f in sorted(glob.glob(os.path.join(DATA, 'b_long_s*_v5y.json'))):
    d = json.load(open(f)); ts = d['metrics']['t_scl']
    if ts is None: continue
    sn = d['snaps']; prev = [x for x in sn if x['t'] <= ts]
    form = next((x for x in sn if x['t'] >= ts and x['all_scl']), None)
    if not prev or form is None: continue
    fm.append(dict(seed=d['seed'], t_scl=round(ts, 1), t_form=form['t'], dt=round(form['t'] - ts, 1), area_before=prev[-1]['area'], area_after=form['area'], hv_after=max(b['hv'] for b in form['bodies'])))
for x in fm: say(' ', x)
say('  맺힘까지 걸린 시간(시간 단위): 중앙값', float(np.median([x['dt'] for x in fm])), ' 범위', min(x['dt'] for x in fm), '~', max(x['dt'] for x in fm))
OUT['formation'] = fm

say('\n## 5) 대조: 마지막 100 시간 단위(1900~2000) 동안 젖은 넓이가 바뀐 스냅샷 수 (5 개 간격 중)')
fr = []
for f in sorted(glob.glob(os.path.join(DATA, 'b_long_s*_v5c.json'))):
    d = json.load(open(f)); ar = [x['area'] for x in d['snaps'] if x['t'] >= 1900]
    p90 = [round(x['dead']['flux_p90'], 3) for x in d['snaps'] if x['t'] in (1600.0, 2000.0)]
    fr.append(dict(seed=d['seed'], changes=int(sum(1 for i in range(1, len(ar)) if ar[i] != ar[i - 1])), flux_p90_1600_2000=p90))
for x in fr: say(' ', x)
OUT['ctrl_frozen'] = fr

open(os.path.join(V5, 'logs', 'extra.txt'), 'w').write('\n'.join(LINES) + '\n')
json.dump(OUT, open(os.path.join(V5, 'data', 'extra.json'), 'w'), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
