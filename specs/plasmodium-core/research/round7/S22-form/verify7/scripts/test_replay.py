#!/usr/bin/env python3
"""verify7 replay.py 시험: 손으로 만든 가짜 압력 문제(원반 위 무작위 간선 가중치). 정답 풀이를 넣으면 오차 0, MG/PCG 는 작은 오차.
usage: test_replay.py WORKDIR"""
import os, sys, json, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import replay as RP
W_ = sys.argv[1]; rd = os.path.join(W_, 'runs', 'b_mig_s1_v7cm'); os.makedirs(os.path.join(rd, 'mgdump'), exist_ok=True)
N = 64; rng = np.random.default_rng(0); yy, xx = np.mgrid[0:N, 0:N]
wet = np.hypot((xx - 5 + N / 2) % N - N / 2, (yy - 9 + N / 2) % N - N / 2) < 20      # 경계를 넘는 원반
W = np.array([(wet & RP.nb(wet, d)) * np.exp(1.0 * rng.normal(size=(N, N))) * 20 for d in RP.DIRS])
M = np.where(wet, 1 / (20 * 0.1), 0.0); S = np.where(wet, rng.normal(size=(N, N)), 0.0)
pe = RP.exact(list(W), M, S, wet)
# 연산자 검산: M p + sum W (p_i - p_j) = S
res = M * pe
for k, d in enumerate(RP.DIRS): res += W[k] * (pe - RP.nb(pe, d)) + RP.rev(W[k], d) * (pe - RP.rev(pe, d))
print('exact residual', float(np.abs((res - S)[wet]).max()))
assert float(np.abs((res - S)[wet]).max()) < 1e-8
for i in range(3):
    np.savez_compressed(os.path.join(rd, 'mgdump', f'step{(i + 1) * 100:05d}.npz'), W=W, wet=wet, M=M, S=S, p0=(pe if i == 0 else np.zeros((N, N))), t=float(i), scl=False)
json.dump(dict(N=N, dt=0.1, ncyc=2, nc=4), open(os.path.join(rd, 'params.json'), 'w'))
out = os.path.join(W_, 'replay_test.json')
subprocess.run([sys.executable, os.path.join(HERE, 'replay.py'), out, rd], check=True)
R = json.load(open(out))
assert R[0]['p0']['e_flux'] < 1e-8, R[0]          # 정답에서 시작하면 오차 0
assert 0 < R[1]['mg']['e_flux'] < 1 and 0 < R[1]['pcg']['e_flux'] < 1, R[1]
print('REPLAY OK', [(r['mg']['e_flux'], r['pcg']['e_flux']) for r in R])
