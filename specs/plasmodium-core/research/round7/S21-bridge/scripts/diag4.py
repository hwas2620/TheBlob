"""[7차 S21] 진단 4 풀이: 이주 방향 치우침과 맥동 무늬. 꼬리표마다 mig(27°)·dir0(0°)·dir45(45°), 시드 491~498.
mig의 s21c·s21g 자리에는 S20의 s20c·s20z(같은 모델 설정)를 읽는다. python3 diag4.py"""
import os, sys, glob, re, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..', 'model', 'runs'); R20 = os.path.join(HERE, '..', '..', 'S20-look', 'model', 'runs')
def rd(scn, s, tag):
    if scn == 'mig' and tag in ('s21c', 's21g'): return os.path.join(R20, f'b_mig_s{s}_' + {'s21c': 's20c', 's21g': 's20z'}[tag]) if tag == 's21c' else os.path.join(R, f'b_mig_s{s}_s21g')
    return os.path.join(R, f'b_{scn}_s{s}_{tag}')
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
S8 = range(491, 499); out = []; summ = []
for tag in ('s21c', 's21cr', 's21c0', 's21g', 's21gr', 's21g0'):
    row = []
    for scn, tgt in (('mig', 27), ('dir0', 0), ('dir45', 45)):
        try:
            e = [direction(scn, tag, s, tgt) for s in S8]; tt = [met(scn, s, tag)['t_touch'][0] for s in S8]; hh = sum(health(scn, s, tag) for s in S8)
        except Exception as ex: out.append(f'{tag} {scn}: 없음 ({ex.__class__.__name__})'); row.append('-'); continue
        out.append(f'{tag} {scn}: 방향 오차 {[round(x, 1) for x in e]} 부호 평균 {np.mean(e):+.1f} 절댓값 평균 {np.mean(np.abs(e)):.1f}; 닿은 시각 평균 {np.mean([x if x is not None else 500 for x in tt]):.1f} (못 닿음 {sum(x is None for x in tt)}), 건강 {hh}/8')
        row.append(f'{np.mean(e):+.1f} / {np.mean(np.abs(e)):.1f}')
    summ.append(f'| `{tag}` | ' + ' | '.join(row) + ' |')
print('\n'.join(out)); print('\n| 꼬리표 | mig 27° 부호 평균 / 절댓값 평균 | dir0 | dir45 |\n|---|---|---|---|'); print('\n'.join(summ))
