#!/usr/bin/env python3
"""[verify] 단순 대기열 실행기. queue/*.job (한 줄: 이름<TAB>JSON[<TAB>프로그램 경로]) 를 이름순으로 최대 3개씩 돌린다.
queue/STOP 파일이 있고 대기열이 비면 끝난다. 실행 시각은 sched_times.txt 에 남긴다."""
import os, subprocess, time, glob, sys
HERE = os.path.dirname(os.path.abspath(__file__)); Q = os.path.join(HERE, 'queue'); MAXP = int(sys.argv[1]) if len(sys.argv) > 1 else 3
env = dict(os.environ, NUMBA_NUM_THREADS='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
running = []; tl = open(os.path.join(HERE, 'sched_times.txt'), 'a')
while True:
    still = []
    for p, n, t0 in running:
        if p.poll() is None: still.append((p, n, t0))
        else: tl.write(f'{n}\t{t0:.0f}\t{time.time():.0f}\t{time.time() - t0:.0f}\n'); tl.flush()
    running = still
    while len(running) < MAXP:
        fs = sorted(glob.glob(os.path.join(Q, '*.job')))
        if not fs: break
        f = fs[0]; parts = open(f).read().rstrip('\n').split('\t')
        os.rename(f, f[:-4] + '.started')
        name, js = parts[0], parts[1]; prog = parts[2] if len(parts) > 2 else os.path.join(HERE, 'f1.py')
        log = open(os.path.join(os.path.dirname(prog), 'logs', name + '.log'), 'w')
        p = subprocess.Popen(['python3', prog, name, js], stdout=log, stderr=subprocess.STDOUT, env=env, cwd=os.path.dirname(prog))
        running.append((p, name, time.time()))
    if not running and os.path.exists(os.path.join(Q, 'STOP')): break
    time.sleep(1.0)
