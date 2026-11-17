#!/usr/bin/env python3
"""[verify] 실험자 실행의 params.json 을 통째로 가져와 시드 등만 바꾼 실행 목록을 만든다.
usage: mkjobs.py OUT.txt  NEW=SRC:{"k":v,...}  ...      (SRC = ../runs/<SRC>/params.json)"""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
out = open(sys.argv[1], 'w')
for a in sys.argv[2:]:
    new, rest = a.split('=', 1); src, ov = rest.split(':', 1)
    P = json.load(open(os.path.join(HERE, '..', 'runs', src, 'params.json')))
    P.update(json.loads(ov)); P.setdefault('vsave', 1)
    out.write(new + '\t' + json.dumps(P) + '\n')
out.close()
