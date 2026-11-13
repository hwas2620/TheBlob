#!/usr/bin/env python3
# usage: phasestat.py run ...  -> phase structure inside the largest wet component (isolated wet specks free-run and are excluded)
import sys, os, json, numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
for nm in sys.argv[1:]:
    d = os.path.join(HERE, 'runs', nm); th = np.load(os.path.join(d, 'theta.npy')); h = np.load(os.path.join(d, 'body_native.npy')); age = np.load(os.path.join(d, 'age.npy'))
    m = json.load(open(os.path.join(d, 'metrics.json'))); wet = h > 0; N = h.shape[0]; Y, X = np.mgrid[0:N, 0:N]
    lab, nl = ndi.label(wet, structure=np.ones((3, 3))); big = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    t_ = th[big]; a_ = age[big]
    res = dict(n_big=int(big.sum()), n_wet=int(wet.sum()), theta_range_turns=round(float((t_.max() - t_.min()) / (2 * np.pi)), 2),
               age_theta_corr=round(float(np.corrcoef(a_, t_)[0, 1]), 3))
    bins = [(0, 10), (10, 25), (25, 50), (50, 100), (100, 200), (200, 1e9)]
    ref = t_[a_ < 10].mean() if (a_ < 10).any() else t_.min()
    res['lead_over_youngest_turns_by_age'] = [round(float((t_[(a_ >= lo) & (a_ < hi)].mean() - ref) / (2 * np.pi)), 3) if ((a_ >= lo) & (a_ < hi)).sum() >= 5 else None for lo, hi in bins]
    if 'dir' in m:
        ux, uy = m['dir']; s = (X * ux + Y * uy)[big]; s0, s1 = s.min(), s.max(); b = np.minimum(((s - s0) / (s1 - s0 + 1e-9) * 6).astype(int), 5)
        res['lead_over_front_band_turns_rear_to_front'] = [round(float((t_[b == i].mean() - t_[b == 5].mean()) / (2 * np.pi)), 3) if (b == i).sum() >= 5 else None for i in range(6)]
        res['s_theta_corr'] = round(float(np.corrcoef(s, t_)[0, 1]), 3)
    json.dump(res, open(os.path.join(d, 'phasestat.json'), 'w'), indent=1); print(nm, json.dumps(res))
