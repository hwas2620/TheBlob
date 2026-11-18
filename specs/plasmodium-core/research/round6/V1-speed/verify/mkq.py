#!/usr/bin/env python3
"""[검증자] 대기열 만들기. plan.txt 의 T0~T7 을 queue/*.job 으로 적는다(이름순 = 우선순위).
한 줄: 이름<TAB>설정 JSON<TAB>h1.py 의 절대 경로.  jobs.tsv 에 (이름, 블록, 시험 종류, 설정 이름, 시드)도 남긴다."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
H1 = '/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research5/H1-emergent-phase/runs'
BM = json.load(open(os.path.join(H1, 'Ym_tri96d_s21', 'params.json')))
B3 = json.load(open(os.path.join(H1, 'Y3_tri96d_s21', 'params.json')))
CAND = {"dt": 0.2, "period": 8.0, "osc_sub": 8}
CTRL = {"dt": 0.2, "osc_sub": 8}
SET = dict(base={}, cand=CAND, ctrl=CTRL)
YX = dict(N=384, R_init=24.0, foods=[[20, 80], [140, 80], [260, 80]], food_sigma=50.0, food_r=10.0, food_M=4800, T=560)
MX = dict(N=384, R_init=24.0, foods=[[27, 140]], food_sigma=120.0, T=700)
A3 = dict(foods=[[0, 35], [100, 45], [200, 40]])
S3 = dict(foods=[[330, 45], [30, 45], [90, 45]])
jobs = []   # (prefix, name, block, kind, setting, seed, params)


def add(pre, name, block, kind, setting, seed, base, extra=None):
    P = dict(base); P.update(extra or {}); P.update(SET[setting]); P.update(seed=seed, vsave=1, neg_diag=1)
    jobs.append((pre, name, block, kind, setting, seed, P))


add('a00', 'Yx_base_s82', 'T3', 'food', 'base', 82, B3, YX)
add('a01', 'Mx_base_s81', 'T3', 'mig', 'base', 81, BM, MX)
add('a02', 'R0_Y3_cand_s21', 'T0', 'food', 'cand', 21, B3)
add('a03', 'Yx_cand_s82', 'T3', 'food', 'cand', 82, B3, YX)
add('a04', 'Mx_cand_s81', 'T3', 'mig', 'cand', 81, BM, MX)
i = 0
for s in range(61, 67):
    for kind, tag, base in (('food', 'Y3', B3), ('mig', 'Ym', BM)):
        for st in ('base', 'cand'):
            add('b%02d' % i, '%s_%s_s%d' % (tag, st, s), 'T1', kind, st, s, base); i += 1
add('d00', 'Y3_ctrl_s61', 'T4', 'food', 'ctrl', 61, B3)
add('d01', 'Y3_ctrl_s62', 'T4', 'food', 'ctrl', 62, B3)
i = 0
for tag, lay, seeds in (('A3', A3, (71, 72, 73)), ('S3', S3, (74, 75))):
    for s in seeds:
        for st in ('base', 'cand'):
            add('e%02d' % i, '%s_%s_s%d' % (tag, st, s), 'T2', 'food', st, s, B3, lay); i += 1
i = 0
for kind, tag, base in (('mig', 'Ym', BM), ('food', 'Y3', B3)):
    for st in ('base', 'cand'):
        add('f%02d' % i, '%s_%s_s61k7' % (tag, st), 'T7', kind, st, 61, base, dict(check_every=7)); i += 1
add('g00', 'YmL_base_s92', 'T5', 'mig', 'base', 92, BM, dict(T=800))
add('g01', 'YmL_cand_s92', 'T5', 'mig', 'cand', 92, BM, dict(T=800))
add('g02', 'Y3L_base_s91', 'T5', 'food', 'base', 91, B3, dict(T=960))
add('g03', 'Y3L_cand_s91', 'T5', 'food', 'cand', 91, B3, dict(T=960))

os.makedirs(os.path.join(HERE, 'queue'), exist_ok=True)
with open(os.path.join(HERE, 'jobs.tsv'), 'w') as jt:
    for pre, name, block, kind, setting, seed, P in jobs:
        jt.write('\t'.join([name, block, kind, setting, str(seed), pre]) + '\n')
        if os.path.exists(os.path.join(HERE, 'runs', name)): print('이미 있음, 건너뜀:', name); continue
        open(os.path.join(HERE, 'queue', '%s_%s.job' % (pre, name)), 'w').write(name + '\t' + json.dumps(P) + '\t' + os.path.join(HERE, 'h1.py') + '\n')
print(len(jobs), 'jobs')
