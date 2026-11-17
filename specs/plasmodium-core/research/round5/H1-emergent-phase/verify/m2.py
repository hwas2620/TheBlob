#!/usr/bin/env python3
"""[verify5] M2 점검: 작성자의 phana.py 정의(창 [t0,t1], 몸 평균 위상 기울기의 가로 성분 |perp| 시간 평균)를 그대로 다시 계산하고
정맥 최대 성분(C>4, t>=200 중앙)과의 Spearman 상관을 전체/변형 안/변형 평균으로 나눠 본다. usage: m2.py ROOT [t0 t1]"""
import json, os, sys, glob, numpy as np
from scipy.stats import spearmanr, pearsonr
ROOT = sys.argv[1]; t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0; t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 400.0
def diag(r):
    f = os.path.join(ROOT, 'runs', r, 'ph_ser.npy')
    if not os.path.exists(f): return None
    A = np.load(f).astype(float); P = json.load(open(os.path.join(ROOT, 'runs', r, 'params.json')))
    B = A[(A[:, 0] >= t0) & (A[:, 0] <= t1)]
    d = B[-1, 6:8] - B[0, 6:8]; disp = float(np.hypot(*d)); ax = np.arctan2(d[1], d[0]) if disp >= 5 else 0.0
    gx = B[:, 2].copy(); gy = B[:, 3].copy()
    if P.get('wave_lambda', 0) > 0:      # phana.py 와 같음: 손으로 넣은 기울기를 더함 (tri, ph_noise 는 더하지 않는다!)
        al = np.radians(P.get('wave_a0', 0.0)) + (2 * np.pi * B[:, 0] / P['wave_Trot'] if P['wave_Trot'] > 0 else 0.0)
        k = 2 * np.pi / P['wave_lambda']; gx += k * np.cos(al); gy += k * np.sin(al)
    perp = -gx * np.sin(ax) + gy * np.cos(ax); par = gx * np.cos(ax) + gy * np.sin(ax)
    raw_perp = -B[:, 2] * np.sin(ax) + B[:, 3] * np.cos(ax)
    return dict(absperp=100 * np.abs(perp).mean(), abspar=100 * np.abs(par).mean(), raw_absperp=100 * np.abs(raw_perp).mean(), mtime=os.path.getmtime(f),
                locrms=100 * np.sqrt(B[:, 4] ** 2 + B[:, 5] ** 2).mean(), R=B[:, 1].mean())
rows = []
for d in sorted(glob.glob(os.path.join(ROOT, 'runs', 'Ym_*'))):
    r = os.path.basename(d); sf = os.path.join(ROOT, 'summ', r + '.json')
    if not os.path.exists(sf): continue
    D = diag(r)
    if D is None: continue
    o = json.load(open(sf)); var = '_'.join(r.split('_')[1:-1]); seed = int(r.split('_s')[-1])
    rows.append(dict(run=r, var=var, seed=seed, v4=o['vein4_largest_med'], **D))
rows.sort(key=lambda x: x['mtime'])
if __name__ == '__main__':
    def sp(sel, key='absperp'):
        a = [x[key] for x in sel]; b = [x['v4'] for x in sel]
        if len(sel) < 4 or len(set(a)) < 2 or len(set(b)) < 2: return float('nan'), len(sel)
        return spearmanr(a, b)[0], len(sel)
    print(f'Ym 실행 {len(rows)}개 (창 {t0:.0f}~{t1:.0f})')
    cls = lambda v: 'wave' if v == 'wave' else 'base' if v == 'base' else 'tri' if v.startswith('tri') else 'mech' if v.startswith('m') else 'phn' if v.startswith('p') else 'omn'
    for x in rows: x['cls'] = cls(x['var'])
    print('전체 Spearman(|perp| 시간평균, 정맥최대): %.3f (n=%d)' % sp(rows))
    for c in ('base', 'wave', 'tri', 'omn', 'phn', 'mech'):
        sel = [x for x in rows if x['cls'] == c]
        if sel: print(f"  {c:5s} n={len(sel):2d} | |perp|x100 범위 {min(x['absperp'] for x in sel):.2f}~{max(x['absperp'] for x in sel):.2f} 중앙 {np.median([x['absperp'] for x in sel]):.2f} | 정맥최대 범위 {min(x['v4'] for x in sel):.2f}~{max(x['v4'] for x in sel):.2f} 중앙 {np.median([x['v4'] for x in sel]):.2f} | 변형 안 Spearman {sp(sel)[0]:+.2f}")
    for name, sel in (('wave 제외', [x for x in rows if x['cls'] != 'wave']), ('tri 제외', [x for x in rows if x['cls'] != 'tri']), ('wave·tri 제외', [x for x in rows if x['cls'] not in ('wave', 'tri')]),
                      ('base+omn 만', [x for x in rows if x['cls'] in ('base', 'omn')]), ('omn 만', [x for x in rows if x['cls'] == 'omn']), ('base+wave 만', [x for x in rows if x['cls'] in ('base', 'wave')])):
        print('  %-14s Spearman %.3f (n=%d)' % ((name,) + sp(sel)))
    # 시간순으로 앞에서부터 n개(작성자가 47개로 계산했을 시점의 후보)
    print('시간순 앞 n개의 Spearman: ' + ' '.join('%d:%.2f' % (n, sp(rows[:n])[0]) for n in range(30, len(rows) + 1)))
    print('tri 를 빼고 시간순 앞 n개: ' + ' '.join('%d:%.2f' % (n, sp([x for x in rows if x['cls'] != 'tri'][:n])[0]) for n in range(30, len([x for x in rows if x['cls'] != 'tri']) + 1)))
    json.dump(rows, open('m2_rows.json', 'w'), indent=0)
