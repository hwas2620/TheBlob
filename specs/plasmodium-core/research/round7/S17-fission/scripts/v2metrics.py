"""v2metrics.py RUN [RUN ...] — [S17] S16 둘째 검증자 측정(../S16-dumbbell/verify2/scripts/measure.py 의 frame)을 그대로 써서 주 지표를 낸다.
아령 = 'M=wet|r=3|f=0.10|neck=any' 비율 (이른 창 100~1000, 늦은 창 1000~2000), 죽은 실 = 'line=3|F0.1|smin=4', 가지 끝 = 'L=3|cells', 막 = 'h=0.3|a=40|b=3' (늦은 창 평균).
떨어진 조각 = 'torn10' (몸 부피 10% 이상 조각이 떨어져 있는 비율, 보고만)."""
import sys, os, glob, json, re
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify2', 'scripts'))
import measure as M2
R = os.path.join(HERE, '..', 'model', 'runs')
PK = 'M=wet|r=3|f=0.10|neck=any'
def one(name):
    fs = sorted(glob.glob(os.path.join(R, name, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    fr = [M2.frame(np.load(f)) for f in fs]
    def win(lo, hi, incl): return [x for x in fr if lo <= x['t'] < hi or (incl and x['t'] == hi)]
    E, L = win(100, 1000, False), win(1000, 2000, True)
    return name, dict(db_early=round(float(np.mean([x['db'][PK] for x in E])), 3), db_late=round(float(np.mean([x['db'][PK] for x in L])), 3),
                      dead_late=round(float(np.mean([x['dead']['line=3|F0.1|smin=4'] for x in L])), 1), tip_late=round(float(np.mean([x['tip']['L=3|cells'] for x in L])), 1),
                      film_late=round(float(np.mean([x['film']['h=0.3|a=40|b=3'] for x in L])), 1), torn10=round(float(np.mean([x['db']['torn10'] for x in fr if x['t'] >= 100])), 3))
if __name__ == '__main__':
    with Pool(4) as p:
        for name, r in p.imap(one, sys.argv[1:]): print(name, json.dumps(r), flush=True)
