#!/usr/bin/env python3
"""계획 D 의 판정: 얇은 칸 줄임(규칙 3 의 s_e)과 외톨이 셀 말리기를 켜고 관문 B 를 모두 다시 돈 실행(이름 꼬리 _th)으로 judge_b.py 를 다시 낸다.

usage: judge_b_thin.py [--json OUT]

run_b_thin.sh 가 돈 실행(GPU 와 numpy)의 채점 요약을 꼬리 없는 이름으로 바꿔 끼운다. 규칙 이전의 기록은 쓰지 않는다(빠진 것은 "없음"으로 센다).
"""
import json, glob, os
import judge_b

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    R = {}; old = 0
    for f in sorted(glob.glob(os.path.join(HERE, 'results', 'b', '*.json'))):
        o = json.load(open(f))
        if o['run'].endswith('_th'): R[(o['origin'], o['run'][:-3])] = dict(o, run=o['run'][:-3])
        else: old += 1
    print(f'(계획 D: 얇은 칸 줄임을 켜고 다시 돈 실행 {len(R)}개만 쓴다. GPU {sum(k[0] == "gpu" for k in R)}, numpy {sum(k[0] == "numpy" for k in R)}. 규칙 이전 기록 {old}개는 쓰지 않는다)')
    return R


judge_b.load = load
if __name__ == '__main__':
    judge_b.main()
