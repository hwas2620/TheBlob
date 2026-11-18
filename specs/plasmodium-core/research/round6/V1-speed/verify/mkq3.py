#!/usr/bin/env python3
"""[검증자] 계획 변경 2(실행 중, 경과 약 18분): 384² 에서 몸과 배치를 2배로 키운 시험(Yx, Mx)은 기준 설정도 작성자 기준을 통과하지 못했다
(Yx 기준: 굵은 쌍 0/3. Mx 기준: 몸이 고리 모양으로 퍼지고 정맥 연결 0.52). 그래서 "격자만 384² 로 키우고 몸·배치는 192² 시험 그대로"인 먹이 셋 시험(Yu)을
기준·후보 한 쌍 더 돌린다(시드 84). 시간을 맞추려고 Y3L(먹이 시험의 긴 실행)은 버린다."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
H1 = '/tmp/claude-0/-home-user-TheBlob/8793727d-910e-5228-bac9-9dbfa028fd5b/scratchpad/research5/H1-emergent-phase/runs'
B3 = json.load(open(os.path.join(H1, 'Y3_tri96d_s21', 'params.json')))
CAND = {"dt": 0.2, "period": 8.0, "osc_sub": 8}
for pre, name, st in (('b11a', 'Yu_base_s84', {}), ('b11b', 'Yu_cand_s84', CAND)):
    P = dict(B3); P.update(N=384); P.update(st); P.update(seed=84, vsave=1, neg_diag=1)
    open(os.path.join(HERE, 'queue', '%s_%s.job' % (pre, name)), 'w').write(name + '\t' + json.dumps(P) + '\t' + os.path.join(HERE, 'h1.py') + '\n')
    open(os.path.join(HERE, 'jobs.tsv'), 'a').write('\t'.join([name, 'T3c', 'food', 'cand' if st else 'base', '84', pre]) + '\n')
for f in sorted(os.listdir(os.path.join(HERE, 'queue'))):
    if f.startswith('g02') or f.startswith('g03'):
        if f.endswith('.job'): os.rename(os.path.join(HERE, 'queue', f), os.path.join(HERE, 'queue_dropped', f)); print('dropped', f)
