#!/usr/bin/env python3
# usage: batch.py BATCH.json   -> runs [[name, params], ...] with 2 worker processes
import sys, json, os, subprocess
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
jobs = json.load(open(sys.argv[1]))
def go(j):
    name, par = j
    with open(os.path.join(HERE, f'log_{name}.txt'), 'w') as f:
        subprocess.run([sys.executable, os.path.join(HERE, 'e1.py'), name, json.dumps(par)], stdout=f, stderr=subprocess.STDOUT)
    return name
with ThreadPoolExecutor(2) as ex:
    for n in ex.map(go, jobs): print('done', n, flush=True)
