#!/usr/bin/env python3
"""machine-generated result table from runs/*/{params,metrics,eval,eval_native}.json  ->  stdout + summary_table.tsv"""
import json, os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
pat = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '*'
rows = []
cols = ['name', 'stage', 'N', 'seed', 'phase', 'dR', 'gamma', 'law', 'sig_het', 'Q0', 'mass_err', 'h_amp', 'lam_meas', 'n80', 'Cc_p50', 'Cc_p99', 'area',
        'BP', 'loops', 'v_area', 'v_largest', 'w_ratio', 's_ratio', 'all3', 'BP_nat', 'loops_nat', 'v_area_nat', 'all3_nat', 'runtime']
for d in sorted(glob.glob(os.path.join(HERE, 'runs', pat))):
    try:
        P = json.load(open(os.path.join(d, 'params.json'))); M = json.load(open(os.path.join(d, 'metrics.json')))
    except Exception: continue
    def ev(fn):
        try:
            E = json.load(open(os.path.join(d, fn))); pr = E.get('primary', E); vd = pr.get('verdict', {})
            return pr, vd
        except Exception: return {}, {}
    pr, vd = ev('eval.json'); pn, vn = ev('eval_native.json')
    L = M['log'][-1]
    r = dict(name=os.path.basename(d), stage=P['stage'], N=P['N'], seed=P['seed'], phase=P['phase'], dR=P['delta_over_R'], gamma=P['gamma'], law=P['law'],
             sig_het=P['sig_het'], Q0='%.3g' % M['Q0'] if M.get('Q0') else '-', mass_err='%.1e' % M['max_mass_err'],
             h_amp='%.3f' % M.get('h_amp_mean_over_hstar', float('nan')), lam_meas='%.0f' % (M.get('wave_len_measured_cells') or float('nan')),
             n80=L['n80'], Cc_p50='%.2g' % L['Cc_p50'], Cc_p99='%.3g' % L['Cc_p99'], area=L['area'],
             BP=pr.get('branch_points'), loops=pr.get('loops'), v_area=pr.get('vein_area_frac'), v_largest=pr.get('vein_largest_frac'),
             w_ratio=pr.get('width_ratio_p90_p10'), s_ratio=pr.get('strength_ratio_p90_p10'), all3=vd.get('all_three'),
             BP_nat=pn.get('branch_points'), loops_nat=pn.get('loops'), v_area_nat=pn.get('vein_area_frac'), all3_nat=vn.get('all_three'), runtime=M['runtime'])
    rows.append(r)
lines = ['\t'.join(cols)] + ['\t'.join(str(r.get(c)) for c in cols) for r in rows]
keep = [c for c in cols if c not in ('stage', 'N', 'law', 'runtime', 'area')] if '--wide' not in sys.argv else cols
for r in [dict(zip(cols, cols))] + rows: print(' '.join(str(r.get(c)).ljust(max(len(c), 6) + 1) for c in keep))
open(os.path.join(HERE, 'summary_table.tsv'), 'w').write('\n'.join(lines) + '\n')
