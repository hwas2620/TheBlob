#!/usr/bin/env python3
"""[S7 독립 검증] 규칙 기록(sup_log) 진단과 부호 맞춤 (판정에 쓰지 않음).

usage: vsup.py   -> data/sup_diag.json

실행마다 (후보 v7k):
  updates       규칙이 큰 덩어리 둘 이상을 찾은 횟수 (1 시간마다)
  zero_frac     그 가운데 모든 e 가 0 인 비율 (두 덩어리 사이에 경계가 없음)
  big_donor     e 가 0 이 아닌 기록 가운데 가장 큰 덩어리가 내보내는 쪽(e > 0)인 비율
  flip          1 시간 간격으로 이웃한 두 기록에서 가장 큰 덩어리의 e 부호가 바뀐 비율
  mult          늙는 배율 1 + 5000 * max(e) 의 분포 (중앙, 90%, 최대)
부호 맞춤 (long): 저장 상태(20 시간마다)에 큰 덩어리가 둘 이상이고 같은 시각의 sup_log 줄이 있으면,
  내 나눔(vcommon.partition)과 저장된 창 평균 흐름 Qmean 으로 경계 순 유출을 재고 그 부호를 sup_log 의 e 부호와 견준다.
"""
import json, os
import numpy as np
from vcommon import states, load, big_parts, partition, rundir, VER, D4

SEEDS = dict(long=range(151, 171), food4=range(151, 159), food3=range(151, 157), asym3=range(151, 155), mig=range(151, 157))


def border_outflow(reg, Qm, n):
    N = reg.shape[0]; out = np.zeros(n + 1)
    for k, (dx, dy) in enumerate(D4):
        nb = np.roll(reg, (-dy, -dx), (0, 1)); m = (reg > 0) & (nb > 0) & (reg != nb)
        q = Qm[k][m]
        np.add.at(out, reg[m], q); np.add.at(out, nb[m], -q)
    return out[1:]


def main():
    R = dict(runs={}, sign=[])
    for scn, ss in SEEDS.items():
        for s in ss:
            rd = rundir(scn, s, 'v7k'); mf = os.path.join(rd, 'metrics.json')
            if not os.path.exists(mf): continue
            m = json.load(open(mf)); L = m['sup_log']
            nz = [r for r in L if any(abs(e) > 0 for e in r[2])]
            flips = []; prev = None
            for r in L:
                if prev is not None and abs(r[0] - prev[0] - 1.0) < 1e-6 and r[2][0] != 0 and prev[2][0] != 0:
                    flips.append(np.sign(r[2][0]) != np.sign(prev[2][0]))
                prev = r
            mult = [1 + 5000 * max(0.0, max(r[2])) for r in nz]
            R['runs'][f'{scn}_s{s}'] = dict(updates=m['sup_updates'], zero_frac=(1 - len(nz) / len(L)) if L else None,
                                            big_donor=(float(np.mean([r[2][0] > 0 for r in nz])) if nz else None),
                                            flip=(float(np.mean(flips)) if flips else None), nflip=len(flips),
                                            mult=([float(np.median(mult)), float(np.percentile(mult, 90)), float(max(mult))] if mult else None),
                                            nz=len(nz), first_t=(L[0][0] if L else None), t_touch=m.get('t_touch'))
            if scn != 'long': continue
            bylt = {round(r[0], 2): r for r in L}
            for t, f in states(rd, 100):
                if float(t) not in bylt: continue
                r = bylt[float(t)]
                if not any(abs(e) > 0 for e in r[2]): continue
                S = load(f, ('wet', 'h', 'Qmean')); wet, h = S['wet'], S['h']; V = float(h.sum())
                lt, big, vb = big_parts(wet, h, V)
                if len(big) != len(r[1]): continue
                seeds = np.zeros(wet.shape, np.int64)
                for j, k in enumerate(big): seeds[lt == k] = j + 1
                reg = partition(wet, seeds)
                ex = border_outflow(reg, S['Qmean'].astype(float), len(big))
                for j in range(len(big)):
                    if r[2][j] == 0 or ex[j] == 0: continue
                    R['sign'].append(dict(seed=s, t=t, part=j, frac=round(vb[j] / V, 4), frac_log=r[1][j], e_log=r[2][j], out_Qmean=float(ex[j]),
                                          agree=bool(np.sign(r[2][j]) == np.sign(ex[j]))))
    json.dump(R, open(os.path.join(VER, 'data', 'sup_diag.json'), 'w'), indent=1)
    for k, v in R['runs'].items():
        print(k, {kk: (round(x, 3) if isinstance(x, float) else x) for kk, x in v.items() if kk not in ('t_touch',)})
    if R['sign']:
        print('부호 맞춤:', sum(x['agree'] for x in R['sign']), '/', len(R['sign']))


if __name__ == '__main__':
    main()
