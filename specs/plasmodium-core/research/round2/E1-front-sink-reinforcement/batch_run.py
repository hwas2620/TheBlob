#!/usr/bin/env python3
# usage: batch_run.py BATCH.json [workers=2]   -> runs [[name, params], ...]; skips runs that already have metrics.json; 300 s timeout each
import sys, json, os, subprocess
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
jobs = json.load(open(sys.argv[1])); nw = int(sys.argv[2]) if len(sys.argv) > 2 else 2
env = dict(os.environ, OMP_NUM_THREADS='2', NUMBA_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
def go(j):
    name, par = j
    if os.path.exists(os.path.join(HERE, 'runs', name, 'metrics.json')): return name + ' (skipped, exists)'
    with open(os.path.join(HERE, f'log_{name}.txt'), 'w') as f:
        try: subprocess.run([sys.executable, os.path.join(HERE, 'e1.py'), name, json.dumps(par)], stdout=f, stderr=subprocess.STDOUT, timeout=320, env=env)
        except subprocess.TimeoutExpired: f.write('TIMEOUT\n'); return name + ' TIMEOUT'
    return name
with ThreadPoolExecutor(nw) as ex:
    for n in ex.map(go, jobs): print('done', n, flush=True)
