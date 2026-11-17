#!/usr/bin/env python3
"""[verify] 대기열에 실행을 넣는다. usage: addq.py PREFIX  NEW=SRC:{"k":v}  ...   (SRC = ../runs/<SRC>/params.json 을 통째로 가져오고 덮어쓴다)"""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); pre = sys.argv[1]
for i, a in enumerate(sys.argv[2:]):
    new, rest = a.split('=', 1); src, ov = rest.split(':', 1)
    P = json.load(open(os.path.join(HERE, '..', 'runs', src, 'params.json')))
    P.update(json.loads(ov)); P.setdefault('vsave', 1)
    if os.path.exists(os.path.join(HERE, 'runs', new)): print('이미 있음, 건너뜀:', new); continue
    open(os.path.join(HERE, 'queue', f'{pre}{i:02d}_{new}.job'), 'w').write(new + '\t' + json.dumps(P) + '\n')
    print('queued', f'{pre}{i:02d}_{new}')
