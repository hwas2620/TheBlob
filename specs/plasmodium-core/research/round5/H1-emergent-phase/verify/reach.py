#!/usr/bin/env python3
"""[verify5] 퍼짐의 방향별 치우침: Y3 실행의 t=T 저장 상태에서 시작점(격자 중심 95.5) 기준 방향별(22.5도 통) 젖은 셀의 최대 반지름. 변형별 시드 평균.
usage: reach.py ROOT T seeds 변형 ..."""
import numpy as np, sys, os, json
ROOT = sys.argv[1]; T = int(sys.argv[2]); seeds = [int(x) for x in sys.argv[3].split(',')]
N = 192; c0 = 95.5; yy, xx = np.indices((N, N)); dx = xx - c0; dy = yy - c0; rr = np.hypot(dx, dy); ang = np.degrees(np.arctan2(dy, dx)) % 360
bins = np.arange(0, 360, 22.5)
def reach(wet): return np.array([rr[wet & (np.abs(((ang - a + 180) % 360) - 180) <= 11.25)].max() for a in bins])
print('방향(도)   ' + ' '.join('%5.0f' % a for a in bins) + ' | 평균  | 4겹 지수 R4 | cos1 sin1 성분')
res = {}
for v in sys.argv[4:]:
    R = []
    for s in seeds:
        f = os.path.join(ROOT, 'runs', f'Y3_{v}_s{s}', f'vs_t{T:04d}.npz')
        if os.path.exists(f): R.append(reach(np.load(f)['wet'].astype(bool)))
    if not R: continue
    R = np.array(R); m = R.mean(0); res[v] = R
    a = np.radians(bins); r4 = (R * np.cos(4 * a)).sum(1) / R.sum(1); c1 = 2 * (R * np.cos(a)).mean(1); s1 = 2 * (R * np.sin(a)).mean(1)
    print(f'{v:9s} ' + ' '.join('%5.1f' % x for x in m) + f' | {m.mean():5.1f} | {r4.mean():+.4f}±{r4.std():.4f} | {c1.mean():+.2f} {s1.mean():+.2f}  (n={len(R)})')
if 'base' in res:
    for v in res:
        if v == 'base' or len(res[v]) != len(res['base']): continue
        d = (res[v] - res['base']).mean(0); sd = (res[v] - res['base']).std(0) / np.sqrt(len(res[v]))
        print(f'{v}-base  ' + ' '.join('%+5.1f' % x for x in d)); print('  (표준오차) ' + ' '.join('%5.1f' % x for x in sd))
