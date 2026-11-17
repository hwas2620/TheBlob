#!/usr/bin/env python3
"""usage: batch.py batchfile.json   -> runs each {name, over} sequentially, then eval_morph on rendered + native outputs."""
import json, sys, os, subprocess, traceback
import e8
HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.join(HERE, '..', 'common', 'eval_morph.py')
for item in json.load(open(sys.argv[1])):
    name = item['name']; out = os.path.join(HERE, 'runs', name)
    if os.path.exists(os.path.join(out, 'eval.json')) and '--force' not in sys.argv: print('skip', name); continue
    try:
        m = e8.run(name, **item['over'])
        print('DONE', name, {k: v for k, v in m.items() if k != 'log'}, flush=True)
        for b, v, e, p in (('body.npy', 'vein.npy', 'eval.json', 'overlay.png'), ('body_native.npy', 'vein_native.npy', 'eval_native.json', 'overlay_native.png')):
            subprocess.run([sys.executable, EV, os.path.join(out, b), os.path.join(out, v), '--out', os.path.join(out, e), '--png', os.path.join(out, p)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except Exception:
        traceback.print_exc(); print('FAILED', name, flush=True)
