#!/usr/bin/env python3
"""[S7 독립 검증] 진단 다시 돌리기(gm_every=4)로 에피소드의 시간 변화를 본다 (판정에 쓰지 않음).

usage: vseries.py TAG SEED [--same TAG2]   (예: v7kf 157 --same v7k)
  --same: 20 시간마다 겹치는 상태가 TAG2 실행과 같은지(움직임이 저장 간격에 따라 바뀌지 않는지) 견준다.
에피소드마다(이어진 두 덩어리 상태가 시작된 t0, 4 시간 간격) t0 ~ t0+160 에서 몫별(젖은 칸을 따라 잰 나눔을 계속 젖은 칸에서 넓힘)
부피 몫 V_j/V, 넓이 A_j, 얇은 몫 s_j, 큰 두꺼운 덩어리 수를 재고, 같은 시간의 규칙 기록(sup_log)의 e 를 붙인다.
-> data/series_<TAG>_s<SEED>.json, fig/series_<TAG>_s<SEED>_t<t0>.png
"""
import json, os, sys
import numpy as np
from vcommon import states, load, big_parts, partition, rundir, VER, TH, lobes
import vfate
from vfig import lineplot, FIG


def main(tag, seed, same=None):
    rd = rundir('long', seed, tag); lst = states(rd); fmap = dict(lst); tt = [t for t, _ in lst]
    out = dict(run=os.path.basename(rd), same=None, episodes=[])
    if same:
        rd2 = rundir('long', seed, same); dmax = 0.0; nchk = 0
        for t in tt:
            f2 = os.path.join(rd2, f'vs_t{t:04d}.npz')
            if t % 20 == 0 and os.path.exists(f2):
                a = np.load(fmap[t]); b = np.load(f2)
                dmax = max(dmax, float(np.abs(a['h'] - b['h']).max()), float((a['wet'] != b['wet']).sum())); nchk += 1
        out['same'] = dict(other=same, compared=nchk, max_abs_diff=dmax)
        print('같은지:', out['same'])
    met = json.load(open(os.path.join(rd, 'metrics.json'))); sup = {round(r[0], 2): r for r in met['sup_log']}
    cache = {}
    def get(t):
        if t not in cache: cache[t] = load(fmap[t], ('wet', 'h', 'age'))
        return cache[t]
    flag = {t: vfate.conn_parts(get(t)) is not None for t in tt if t >= 96}
    starts = [t for t in tt if t >= 100 and flag.get(t) and not flag.get(t - 4, False)]
    # 4 시간 안에 다시 시작되는 것은 한 에피소드로 (앞의 것에서 160 시간 안이면 건너뜀)
    keep = []
    for t in starts:
        if not keep or t - keep[-1] > 160: keep.append(t)
    for t0 in keep:
        S0 = get(t0); lw0, seeds0, n = vfate.conn_parts(S0); reg0 = partition(S0['wet'], seeds0)
        rows = []
        for dT in range(0, 164, 4):
            t = t0 + dT
            if t not in fmap: break
            S = get(t); wet, h = S['wet'], S['h']; V = float(h.sum())
            reg = reg0 if dT == 0 else partition(wet, np.where(S0['wet'] & wet & (S['age'] >= dT - 0.5), reg0, 0))
            lt, big, vb = big_parts(wet, h, V)
            r = dict(t=t, nbig=len(big), nlobe=lobes(wet, h, V), V=[float(h[reg == j].sum() / V) for j in range(1, n + 1)], A=[int((reg == j).sum()) for j in range(1, n + 1)],
                     s=[float((wet & (reg == j) & (h < TH)).sum() / max(int((reg == j).sum()), 1)) for j in range(1, n + 1)],
                     thin_all=int((wet & (h < TH)).sum()), e=[sup[float(t + k)][2] for k in range(4) if float(t + k) in sup])
            rows.append(r)
        if len(rows) < 16: continue
        i60 = 15
        r60 = [rows[i60]['V'][j] / max(rows[0]['V'][j], 1e-12) for j in range(n)]
        L = int(np.argmin(r60)); W = int(np.argmax(r60))
        act = [t for t in range(t0, t0 + 164) if float(t) in sup and any(abs(x) > 0 for x in sup[float(t)][2])]
        out['episodes'].append(dict(t0=t0, n=n, L=L, W=W, rows=rows, rule_active_t=act))
        ts = [r['t'] for r in rows]
        lineplot(os.path.join(FIG, f'series_{tag}_s{seed}_t{t0}.png'), [
            ('loser V/body', ts, [r['V'][L] for r in rows], (220, 30, 30)),
            ('winner V/body', ts, [r['V'][W] for r in rows], (30, 160, 30)),
            ('loser area/area(t0)', ts, [r['A'][L] / max(rows[0]['A'][L], 1) for r in rows], (240, 140, 20)),
            ('loser thin share', ts, [r['s'][L] for r in rows], (40, 90, 230)),
            ('big thick parts / 4', ts, [r['nbig'] / 4 for r in rows], (120, 120, 120)),
            ('big lobes / 4', ts, [r['nlobe'] / 4 for r in rows], (160, 60, 200)),
        ], xlabel='t', ylim=(0, 1.2), title=f'{tag} s{seed} episode t0={t0}: grey lines = rule active (|e|>0)', vlines=act)
        print(tag, seed, 't0', t0, 'L', L, 'V_L', round(rows[0]['V'][L], 3), '->', round(rows[15]['V'][L], 3), '->', round(rows[-1]['V'][L], 3),
              '| V_W', round(rows[0]['V'][W], 3), '->', round(rows[15]['V'][W], 3), '->', round(rows[-1]['V'][W], 3),
              '| A_L', rows[0]['A'][L], '->', rows[15]['A'][L], '->', rows[-1]['A'][L], '| s_L', round(rows[15]['s'][L], 2), round(rows[-1]['s'][L], 2), '| 규칙 작동', len(act))
    json.dump(out, open(os.path.join(VER, 'data', f'series_{tag}_s{seed}.json'), 'w'))


if __name__ == '__main__':
    a = sys.argv[1:]; same = None
    if '--same' in a: i = a.index('--same'); same = a[i + 1]; a = a[:i] + a[i + 2:]
    main(a[0], int(a[1]), same)
