#!/usr/bin/env python3
"""[검증자] 음수 두께가 어디서 생기는지: negrec.npy (스텝마다 가장 음수인 셀 5개까지: step, h, 유량 전 h, hstar, p, sage, age, Cn, resmask, tube, 젖은 이웃 수, 먹이까지 거리, 그 스텝의 음수 셀 수).
"새 음수" = 유량 전에는 0 이상이었다가 이 스텝의 유량으로 음수가 된 셀. "남은 음수" = 유량 전부터 음수(마르지 못하고 남은 셀).
usage: negana.py NAME ..."""
import numpy as np, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
print('이름 | 스텝 수 | 음수가 있던 스텝 | 새 음수 기록 수 | 새 음수의 최소 h | 새 음수 중 정맥 셀(Cn>30) 비율, 그 최소 h | 새 음수 중 젖은 이웃 2개 이하 비율 | 새 음수의 먹이까지 거리 중앙 | 남은 음수 기록 수(젖은 이웃 0~1개 비율) | 남은 음수의 최소 h')
for n in sys.argv[1:]:
    rd = os.path.join(HERE, 'runs', n); f = os.path.join(rd, 'negrec.npy'); P = json.load(open(os.path.join(rd, 'params.json'))); M = json.load(open(os.path.join(rd, 'metrics.json')))
    steps = int(round(M['t_end'] / P['dt'])) + 1
    if not os.path.exists(f): print(f'{n:16s} | {steps} | 0 | 음수 기록 없음'); continue
    a = np.load(f); new = a[a[:, 2] >= 0]; old = a[a[:, 2] < 0]
    vn = new[new[:, 7] > 30]
    s = f"{n:16s} | {steps} | {np.unique(a[:, 0]).size} | {len(new)} | " + (f"{new[:, 1].min():.4f} | {len(vn) / len(new):.2f}, {vn[:, 1].min() if len(vn) else float('nan'):.4f} | {(new[:, 10] <= 2).mean():.2f} | {np.median(new[:, 11]):.1f}" if len(new) else '- | - | - | -')
    s += ' | ' + (f"{len(old)} ({(old[:, 10] <= 1).mean():.2f}) | {old[:, 1].min():.4f}" if len(old) else '0 | -')
    print(s)
