"""[7차 S21] 진단 3 풀이: s21g(= s20z + tip_home=1)가 이주·먹이를 망치지 않는지, 이주 방향 치우침이 대각선 끌림인지(dir0·dir45).
기준선 s20c·s20z는 ../../S20-look/model/runs 에서 읽는다. python3 diag3.py"""
import os, sys, glob, re, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..', 'model', 'runs'); R20 = os.path.join(HERE, '..', '..', 'S20-look', 'model', 'runs')
def rd(scn, s, tag): return os.path.join(R20 if tag.startswith('s20') else R, f'b_{scn}_s{s}_{tag}')
def met(scn, s, tag): return json.load(open(os.path.join(rd(scn, s, tag), 'metrics.json')))
def frames(d): return sorted(glob.glob(os.path.join(d, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
def health(scn, s, tag):
    b = met(scn, s, tag); return b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and abs(b['V_crumb']) / b['V0'] < 0.001 and b.get('stop', '') in ('', None, 'touched')
def direction(scn, tag, s, tgt):
    fs = frames(rd(scn, s, tag)); c0 = np.load(fs[0])['cen']; c1 = None
    for f in fs:
        Z = np.load(f)
        if float(Z['t']) <= 200: c1 = Z['cen']
    N = np.load(fs[0])['wet'].shape[0]; dd = ((c1 - c0 + N / 2) % N) - N / 2; a = np.arctan2(dd[1], dd[0])
    return float(np.degrees((a - np.radians(tgt) + np.pi) % (2 * np.pi) - np.pi))
out = []; S8 = range(491, 499)
for tag in ('s20c', 's20z', 's21g'):
    e = [direction('mig', tag, s, 27) for s in S8]; tt = [met('mig', s, tag)['t_touch'][0] for s in S8]
    hh = '' if tag.startswith('s20') else f', 건강 {sum(health("mig", s, tag) for s in S8)}/8'
    out.append(f'mig {tag}: 방향 오차 {[round(x, 1) for x in e]} 부호 평균 {np.mean(e):+.1f} 절댓값 평균 {np.mean(np.abs(e)):.1f}; 닿은 시각 평균 {np.mean([x if x is not None else 400 for x in tt]):.1f} {tt}{hh}')
for tag in ('s20z', 's21g'):
    ss = range(491, 497); tt = [met('food4', s, tag)['t_touch'] for s in ss]
    allr = sum(all(x is not None for x in r) for r in tt); last = [max(x if x is not None else 700 for x in r) for r in tt]
    hh = '' if tag.startswith('s20') else f', 건강 {sum(health("food4", s, tag) for s in ss)}/{len(ss)}'
    out.append(f'food4 {tag} (491~496): 모두 닿음 {allr}/6, 마지막 먹이 {[round(x, 1) for x in last]}{hh}')
    out.append(f'   {[[None if x is None else round(x) for x in r] for r in tt]}')
for scn, tgt in (('dir0', 0), ('dir45', 45)):
    for tag in ('s21c', 's21g'):
        e = [direction(scn, tag, s, tgt) for s in S8]; tt = [met(scn, s, tag)['t_touch'][0] for s in S8]
        out.append(f'{scn} {tag}: 방향 오차 {[round(x, 1) for x in e]} 부호 평균 {np.mean(e):+.1f} 절댓값 평균 {np.mean(np.abs(e)):.1f}; 닿은 시각 {tt}, 건강 {sum(health(scn, s, tag) for s in S8)}/8')
print('\n'.join(out))
