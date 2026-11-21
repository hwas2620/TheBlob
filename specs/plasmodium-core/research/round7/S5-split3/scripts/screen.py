"""S5 거르기 요약: 꼬리표마다 오래 돌린 실행(갈라진 시간·두 부채·몸 밖 최대·넓이), 가까운 먹이 셋, 먼 먹이 넷, 굶은 이주를 한 줄로.
python3 screen.py TAG [TAG ...] [--seeds 81,82,83]   (요약 json 은 ../summaries/numpy_b_{scn}_s{seed}_{tag}.json, 없으면 bmet 로 만든다)"""
import os, sys, json, glob, subprocess, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); SUM = os.path.join(HERE, '../summaries')
REF = os.path.abspath(os.path.join(HERE, '../../../../stage0/ref/runs')); MET = os.path.abspath(os.path.join(HERE, '../../../../stage0/metrics'))
sys.path.insert(0, os.path.join(HERE, '../../S4-fan2/scripts')); sys.path.insert(0, MET)
from judge_s4 import long_stats

def bm(scn, s, tag):
    f = os.path.join(SUM, f'numpy_b_{scn}_s{s}_{tag}.json'); rd = os.path.join(REF, f'b_{scn}_s{s}_{tag}')
    if not os.path.exists(f):
        if not os.path.exists(os.path.join(rd, 'metrics.json')): return None
        subprocess.run([sys.executable, os.path.join(MET, 'bmet.py'), rd, '--out', SUM], capture_output=True)
    return json.load(open(f)) if os.path.exists(f) else None

args = [a for a in sys.argv[1:] if not a.startswith('--')]
seeds = [int(x) for x in (sys.argv[sys.argv.index('--seeds') + 1].split(',') if '--seeds' in sys.argv else '81,82,83'.split(','))]
args = [a for a in args if not a.replace(',', '').isdigit()]
fs = seeds[0]
print(f"{'꼬리표':6s} | 갈라진시간 두부채최장 몸밖최대 끝넓이 | 먹이셋 통과 굵은쌍 닿음 | 먹이넷 닿음 | 이주 닿음 disp300 왕복비 veinT")
for tag in args:
    L = []
    for s in seeds:
        rd = os.path.join(REF, f'b_long_s{s}_{tag}'); b = bm('long', s, tag)
        if b is None: continue
        st = long_stats(rd); L.append((st['split_frac'], st['two_longest'], b['out_frac'], b['area_end']))
    L = np.array(L) if L else np.full((1, 4), np.nan)
    f3 = bm('food3', fs, tag); f4 = bm('food4', fs, tag); mg = bm('mig', fs, tag)
    t = lambda v: '-' if v is None else '%.0f' % v
    s3 = f"{str(f3['pass'])[:1]} {f3['thick']} {'/'.join(t(x) for x in f3['t_touch'])}" if f3 else '-'
    s4 = '/'.join(t(x) for x in f4['t_touch']) if f4 else '-'
    sm = f"{t(mg['t_touch'][0])} {mg['disp300']:.1f} {mg['gross_net']:.2f} {mg['veinT']:.2f}" if mg else '-'
    print(f"{tag:6s} | {np.nanmean(L[:,0]):.2f} ({','.join('%.2f' % x for x in L[:,0])}) {np.nanmean(L[:,1]):4.0f} {np.nanmean(L[:,2]):.2f} {np.nanmean(L[:,3]):5.0f} n={len(L)} | {s3} | {s4} | {sm}")
