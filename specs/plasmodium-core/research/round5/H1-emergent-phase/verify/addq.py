#!/usr/bin/env python3
"""[verify5] 대기열에 실행을 넣는다. usage: addq.py PREFIX NEW=SRC:{"k":v} ...
SRC = 4차 검증자 실행 research4/F1-food-mass/verify/runs/<SRC>/params.json (통째로 가져와 덮어씀). SRC 가 'A:<이름>' 이면 작성자 실행 ../runs/<이름>/params.json."""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); pre = sys.argv[1]
SRC = os.path.join(HERE, '..', '..', '..', 'research4', 'F1-food-mass', 'verify', 'runs')
for i, a in enumerate(sys.argv[2:]):
    new, rest = a.split('=', 1)
    if rest.startswith('A:'): rest = rest[2:]; src, ov = rest.split(':', 1); pf = os.path.join(HERE, '..', 'runs', src, 'params.json')
    else: src, ov = rest.split(':', 1); pf = os.path.join(SRC, src, 'params.json')
    P = json.load(open(pf)); P.update(json.loads(ov)); P['vsave'] = 1
    if os.path.exists(os.path.join(HERE, 'runs', new)): print('이미 있음, 건너뜀:', new); continue
    open(os.path.join(HERE, 'queue', f'{pre}{i:02d}_{new}.job'), 'w').write(new + '\t' + json.dumps(P) + '\t' + os.path.join(HERE, 'h1.py') + '\n')
    print('queued', f'{pre}{i:02d}_{new}')
