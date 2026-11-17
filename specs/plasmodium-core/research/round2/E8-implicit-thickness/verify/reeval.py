#!/usr/bin/env python3
"""independent re-scoring of stored body.npy/vein.npy with the common script (as a module), 3 thresholds"""
import sys, os, json, importlib.util, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('em', os.path.join(HERE, '..', '..', 'common', 'eval_morph.py')); em = importlib.util.module_from_spec(spec); spec.loader.exec_module(em)
def score(body, vein):
    bthr = 0.05 * float(np.percentile(body, 99.5)); o = {}
    for r in (0.2, 0.35, 0.5):
        m, _ = em.analyse(body.astype(float), vein.astype(float), bthr, r); v = em.verdict(m)
        o[r] = dict(BP=m.get('branch_points'), loops=m.get('loops'), ends=m.get('endpoints'), va=m.get('vein_area_frac'), vl=m.get('vein_largest_frac'), ncomp=m.get('vein_components'),
                    w10=m.get('width_p10'), w50=m.get('width_p50'), w90=m.get('width_p90'), wr=m.get('width_ratio_p90_p10'), sr=m.get('strength_ratio_p90_p10'),
                    bcomp=m.get('body_components'), blf=m.get('body_largest_frac'), circ=m.get('body_circularity'), sol=m.get('body_solidity'), all3=v.get('all_three'), net=v.get('network_like'), hier=v.get('hierarchical'))
    return o
if __name__ == '__main__':
    for d in sys.argv[1:]:
        b = np.load(os.path.join(d, 'body.npy')); v = np.load(os.path.join(d, 'vein.npy'))
        o = score(b, v)
        for r in o: print(os.path.basename(d.rstrip('/')), 'rendered rel', r, o[r])
        bn = np.load(os.path.join(d, 'body_native.npy')); vn = np.load(os.path.join(d, 'vein_native.npy'))
        o = score(bn, vn ** 0.25)
        for r in o: print(os.path.basename(d.rstrip('/')), 'native^0.25 rel', r, o[r])
        o = score(bn, np.log10(np.maximum(vn, 1e-3)) + 3)
        for r in o: print(os.path.basename(d.rstrip('/')), 'native log rel', r, o[r])
