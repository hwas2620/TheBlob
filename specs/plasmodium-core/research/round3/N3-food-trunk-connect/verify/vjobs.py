#!/usr/bin/env python3
"""verifier re-runs, one process, sequential.  outputs under verify/runs/"""
import time, json, sys
import n3v
JOBS = [
 ('V1_hres4_bk_s11', dict(seed=11, T=480, foods=[[27, 40], [117, 40]], reservoir=1, h_res=4.0, food_r=5.0, bridge_keep=1)),
 ('V2_hres4_bk_s12_newfood', dict(seed=12, T=480, foods=[[160, 38], [250, 44]], reservoir=1, h_res=4.0, food_r=5.0, bridge_keep=1)),
 ('V3_inj_a200_s11', dict(seed=11, T=320, foods=[[200, 45]], reservoir=1, eat=0.1, gain=1.0, food_M=600)),
 ('V4_osc_pt1_s3', dict(seed=3, T=256, foods=[[0, 60]], phase_mode='osc', pulse_tube=1)),
 ('V4_osc_pt0_s3', dict(seed=3, T=256, foods=[[0, 60]], phase_mode='osc', pulse_tube=0)),
 ('V5_inj2_s11', dict(seed=11, T=480, foods=[[27, 40], [117, 40]], reservoir=1, eat=0.1, gain=1.0, food_M=400)),
]
sel = sys.argv[1:]
tt = {}
for name, over in JOBS:
    if sel and name not in sel: continue
    t0 = time.time(); n3v.run(name, over); tt[name] = round(time.time() - t0, 1)
    json.dump(tt, open('vjobs_times_%s.json' % ('all' if not sel else '_'.join(sel)[:40]), 'w'))
print('TIMES', tt, sum(tt.values()))
