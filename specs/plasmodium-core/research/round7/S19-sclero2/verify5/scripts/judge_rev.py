#!/usr/bin/env python3
"""verify5: 바뀐 기준(CRITERIA_CHANGES.md)으로 판정. judge.py 의 규칙은 그대로 두고, 갇힘 시각만 T_trap2 로 바꿔 끼운다.
usage: judge_rev.py   → verify5/logs/judge_rev.txt, verify5/data/judge_rev.json
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); V5 = os.path.dirname(HERE)
sys.argv = sys.argv[:1]
import judge
_load = judge.load


def load2():
    R = _load()
    for r in R.values():
        r['T_trap_orig'] = r.get('T_trap'); r['T_trap'] = r.get('T_trap2'); r['split'] = r.get('split2')
    return R


judge.load = load2
judge.OUT_TXT = os.path.join(V5, 'logs', 'judge_rev.txt'); judge.OUT_JSON = os.path.join(V5, 'data', 'judge_rev.json')
judge.say('# [바뀐 기준 1] 갇힘 시각 = T_trap2 (CRITERIA_CHANGES.md)')
judge.main()
