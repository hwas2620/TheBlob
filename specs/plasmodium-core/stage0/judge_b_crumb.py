#!/usr/bin/env python3
"""계획 C 의 판정: 외톨이 셀 말리기를 켠 뒤 다시 돈 먹이 시나리오(이름 꼬리 _cd)로 judge_b.py 를 다시 낸다.

usage: judge_b_crumb.py [--json OUT]

다시 돈 것: food3 1~6, asym3 1~3, food4 1~3, food3_256 1~3 (GPU 와 numpy 모두, run_b_crumb.sh).
이 실행들의 채점 요약을 꼬리 없는 이름으로 바꿔 끼우고, 나머지(굶은 이주·방향·점액·지속·384²·90% 조건 끔)는 기존 기록(규칙 이전)을 그대로 쓴다.
"""
import json, glob, os, sys
import judge_b

HERE = os.path.dirname(os.path.abspath(__file__))
SCN = {'food3': [1, 2, 3, 4, 5, 6], 'asym3': [1, 2, 3], 'food4': [1, 2, 3], 'food3_256': [1, 2, 3]}


def load():
    R = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'results', 'b', '*.json'))):
        o = json.load(open(f)); R[(o['origin'], o['run'])] = o
    swapped = 0
    for scn, seeds in SCN.items():
        for s in seeds:
            for origin in ('gpu', 'numpy'):
                base = f'b_{scn}_s{s}'; cd = R.pop((origin, base + '_cd'), None)
                R.pop((origin, base), None)
                if cd is not None:
                    cd = dict(cd, run=base); R[(origin, base)] = cd; swapped += 1
    print(f'(계획 C: 외톨이 셀 말리기를 켜고 다시 돈 실행 {swapped}개를 끼웠다. 기대 {2 * sum(map(len, SCN.values()))}개. 빠진 것은 "없음"으로 센다)')
    return R


judge_b.load = load
if __name__ == '__main__':
    judge_b.main()
