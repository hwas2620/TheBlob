#!/usr/bin/env python3
# usage: summarize.py [prefix ...]   -> table of runs whose name starts with any prefix
import sys, json, os, glob, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); pre = sys.argv[1:] or ['']
def iou(a, b):
    try:
        va = np.load(os.path.join(HERE, 'runs', a, 'vein_native.npy')) > 1.0; vb = np.load(os.path.join(HERE, 'runs', b, 'vein_native.npy')) > 1.0
        if va.shape != vb.shape: return None
        return round(float((va & vb).sum() / max((va | vb).sum(), 1)), 2)
    except Exception: return None
print(f"{'run':26s} | {'bp':>4s} {'loop':>4s} {'vlarg':>5s} {'wr':>4s} {'sr':>4s} ok | veins@.25/.5/.75/.9R | {'nVE':>5s} {'Cmax':>7s} | {'ferr_mean':>9s} {'late':>6s} {'max':>6s} {'kirch':>6s} | {'fineEq':>6s} {'draws':>6s} | IoU | note")
for d in sorted(glob.glob(os.path.join(HERE, 'runs', '*')), key=os.path.getmtime):
    n = os.path.basename(d)
    if not any(n.startswith(p) for p in pre) or not os.path.exists(os.path.join(d, 'metrics.json')): continue
    m = json.load(open(os.path.join(d, 'metrics.json'))); e = m.get('eval_primary', {}); P = json.load(open(os.path.join(d, 'params.json')))
    r = m.get('rings_final') or {}; rv = '/'.join(str((r.get(k) or {}).get('veins', '-')) for k in ('0.25', '0.5', '0.75', '0.9'))
    c = m.get('gpu_cost_per_step') or {}; kl = m.get('kirchhoff_l1') or []
    kmean = round(float(np.mean([x[1] for x in kl])), 3) if kl else '-'
    ref = None
    for cand in (f"b0_exact_s{P['seed']}", f"b3_ref512_s{P['seed']}"):
        if os.path.exists(os.path.join(HERE, 'runs', cand, 'params.json')) and json.load(open(os.path.join(HERE, 'runs', cand, 'params.json')))['N'] == P['N']: ref = cand
    io = iou(n, ref) if ref and ref != n else '-'
    note = ('BLOWUP@step%d(R=%s/%s)' % (m['diverged']['step'], m['diverged'].get('R', '?'), m.get('R_final', '?'))) if m.get('diverged') else ''
    if 'pcg_its_mean' in m: note += f" its={m['pcg_its_mean']}/{m['pcg_its_max']}"
    ok = 'T' if (e.get('verdict') or {}).get('all_three') else 'F'
    print(f"{n:26s} | {e.get('branch_points', '-'):>4} {e.get('loops', '-'):>4} {e.get('vein_largest_frac', '-'):>5} {e.get('width_ratio_p90_p10', '-'):>4} {e.get('strength_ratio_p90_p10', '-'):>4} {ok:>2} | {rv:>19s} | "
          f"{m.get('n_vein_edges_C_gt1', '-'):>5} {m['log'][-1]['Cmax'] if m['log'] else 0:7.0f} | {m.get('flux_err_mean', '-'):>9} {m.get('flux_err_late', '-'):>6} {m.get('flux_err_max', '-'):>6} {kmean:>6} | "
          f"{c.get('fine_eq', '-'):>6} {c.get('draws', '-'):>6} | {io} | {note} t={m['runtime']}")
