#!/usr/bin/env python3
"""verify7 보충 측정 (CRITERIA_CHANGES.md 1절): 저장 상태마다 v7extra.frame_trees -> data/<실행>.extra.json
usage: measure_extra.py RUN_DIR [...]"""
import json, os, sys, glob, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v7extra as X
OUT = os.environ.get('V7_DATA') or os.path.normpath(os.path.join(HERE, '..', 'data'))
for rd in sys.argv[1:]:
    rd = rd.rstrip('/'); name = os.path.basename(rd); fr = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0])):
        Z = np.load(f); d = X.frame_trees(Z['wet'].astype(bool), Z['h'].astype(float)); d['t'] = float(Z['t']); fr.append(d)
    json.dump(dict(name=name, frames=fr), open(os.path.join(OUT, name + '.extra.json'), 'w'))
    print(name, 'extra frames', len(fr), flush=True)
