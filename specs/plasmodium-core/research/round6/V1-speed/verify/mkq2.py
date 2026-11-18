#!/usr/bin/env python3
"""[검증자] 계획 변경(실행 중, 경과 약 13분): 384² 먹이 시험의 후보 실행(Yx_cand_s82)에서 스텝 안 두께 −16.6 이 나왔고 기준 실행은 −0.014 였다.
한 시드로는 우연인지 알 수 없으므로 같은 설정의 둘째 시드(83)를 기준·후보로 더 돌린다. 시간을 맞추려고 T7(유량 오차 표본 위상 점검)은 버린다."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
H1 = '/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research5/H1-emergent-phase/runs'
B3 = json.load(open(os.path.join(H1, 'Y3_tri96d_s21', 'params.json')))
YX = dict(N=384, R_init=24.0, foods=[[20, 80], [140, 80], [260, 80]], food_sigma=50.0, food_r=10.0, food_M=4800, T=560)
CAND = {"dt": 0.2, "period": 8.0, "osc_sub": 8}
for pre, name, st in (('a05', 'Yx_cand_s83', CAND), ('a06', 'Yx_base_s83', {})):
    P = dict(B3); P.update(YX); P.update(st); P.update(seed=83, vsave=1, neg_diag=1)
    open(os.path.join(HERE, 'queue', '%s_%s.job' % (pre, name)), 'w').write(name + '\t' + json.dumps(P) + '\t' + os.path.join(HERE, 'h1.py') + '\n')
    open(os.path.join(HERE, 'jobs.tsv'), 'a').write('\t'.join([name, 'T3b', 'food', 'cand' if st else 'base', '83', pre]) + '\n')
os.makedirs(os.path.join(HERE, 'queue_dropped'), exist_ok=True)
for f in sorted(os.listdir(os.path.join(HERE, 'queue'))):
    if f.startswith('f0') and f.endswith('.job'): os.rename(os.path.join(HERE, 'queue', f), os.path.join(HERE, 'queue_dropped', f)); print('dropped', f)
