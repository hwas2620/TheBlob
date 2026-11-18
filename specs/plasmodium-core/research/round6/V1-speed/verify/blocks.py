#!/usr/bin/env python3
"""[검증자] 보고서용 블록 요약표. 블록(시험×격자)마다 기준·후보(·대조)를 한 줄씩. 모든 수는 metrics.json / summ/*.json 에서 읽는다(ana.py 의 row_* 사용)."""
import numpy as np, ana
rng = lambda a, n=3: ('%.*f' % (n, a[0])) if len(a) == 1 else ('%.*f~%.*f' % (n, np.nanmin(a), n, np.nanmax(a)))
med = lambda a, n=3: '%.*f' % (n, np.nanmedian(a))
BL = [('이주 192² (T1)', 'mig', 'Ym', [61, 62, 63, 64, 65, 66], ('base', 'cand')),
      ('이주 192² 긴 실행 T=800 (T5)', 'mig', 'YmL', [92], ('base', 'cand')),
      ('이주 384² 몸 2배 (T3)', 'mig', 'Mx', [81], ('base', 'cand')),
      ('대칭 먹이 셋 192² (T1)', 'food', 'Y3', [61, 62, 63, 64, 65, 66], ('base', 'cand')),
      ('대칭 먹이 셋 192² 대조 (T4)', 'food', 'Y3', [61, 62], ('base', 'cand', 'ctrl')),
      ('비대칭 먹이 셋 A3 192² (T2)', 'food', 'A3', [71, 72, 73], ('base', 'cand')),
      ('한쪽 먹이 셋 S3 192² (T2)', 'food', 'S3', [74, 75], ('base', 'cand')),
      ('대칭 먹이 셋, 격자만 384² (Yu)', 'food', 'Yu', [84], ('base', 'cand')),
      ('대칭 먹이 셋 384² 몸·배치 2배 (Yx)', 'food', 'Yx', [82, 83], ('base', 'cand'))]
for title, kind, tag, seeds, sets in BL:
    print('## %s — 시드 %s' % (title, ','.join(map(str, seeds))))
    if kind == 'mig': print('설정 | 실행 수 | 정맥 최대 성분(>=0.8 인 수) | 몸 최대 성분 | 스텝 안 최소 h | 스텝 끝 최소 h | 끝음수 셀·스텝(합) | 유량 오차 중앙(시드 범위; 시드 중앙) | 90% | 닿는 시각(중앙) | 무게중심 이동 t=400 / 끝(중앙)')
    else: print('설정 | 실행 수 | 굵은 쌍 | 정맥 최대 성분(창) | 몸 최대 성분(창; <0.9 인 수) | 스텝 안 최소 h | 스텝 끝 최소 h | 끝음수 셀·스텝(합) | 유량 오차 중앙(시드 범위; 시드 중앙) | 90% | 먹이에 닿는 시각 첫/마지막(중앙) | 첫 먹이가 떨어지는 시각(중앙)')
    for st in sets:
        R = [(ana.row_mig if kind == 'mig' else ana.row_food)('%s_%s_s%d' % (tag, st, s)) for s in seeds]; R = [r for r in R if r]
        g = lambda k: np.array([np.nan if r[k] is None else r[k] for r in R], float)
        c = '%s | %d | ' % ({'base': '기준', 'cand': '후보', 'ctrl': '대조(dt 만)'}[st], len(R))
        if kind == 'mig':
            v = g('vein4'); c += '%s (%d/%d) | %s | ' % (rng(v), int((v >= 0.8).sum()), len(R), rng(g('body')))
        else:
            c += '%d/%d | %s | %s (%d/%d) | ' % (sum(r['thick'] or 0 for r in R), sum(r['npair'] for r in R), rng(g('vein4')), rng(g('body')), int((g('body') < 0.9).sum()), len(R))
        c += '%s (중앙 %s) | %s (중앙 %s) | %d | %s; %s | %s | ' % (rng(g('hmin_in'), 4), med(g('hmin_in'), 4), rng(g('hmin_end'), 4), med(g('hmin_end'), 4), int(g('neg_end').sum()), rng(g('mg_med')), med(g('mg_med')), rng(g('mg_p90')))
        if kind == 'mig': c += '%s (%s) | %s / %s' % (med(g('touch'), 1), rng(g('touch'), 1), med(g('d400'), 1), med(g('dend'), 1))
        else:
            first = np.array([min(x for x in r['touch'] if x is not None) for r in R]); last = np.array([max(x for x in r['touch'] if x is not None) for r in R]); ex = np.array([min(x for x in r['exh'] if x is not None) for r in R])
            c += '%s / %s | %s' % (med(first, 1), med(last, 1), med(ex, 1))
        print(c)
    print()
