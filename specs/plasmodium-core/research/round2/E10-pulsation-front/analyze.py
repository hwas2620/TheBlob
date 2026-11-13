#!/usr/bin/env python3
"""E10 post-hoc analysis.
usage: analyze.py [--tsv results.tsv] [--quiet] run1 run2 ...   (default: all runs)
For each run: vein thickness profile (a) in 6 bands along the travel direction (rear -> front, largest body component) and
(b) in age bins (direction-free; age = time since the cell was wetted = distance behind the front / speed), plus a one-line summary.
Writes runs/NAME/profile.json and (optional) a TSV with one row per run.

thickness-gradient indices (vein cells = node conductance Cn > max(1, 2*D0)):
  slope_dir : least-squares slope of log10(C_p90) per band, rear -> front.  NEGATIVE = rear veins thicker (realistic), POSITIVE = inverted (E7 problem)
  rf_dir    : median C_p90 of the 3 rear bands / median C_p90 of the 3 front bands  (>1 realistic)
  slope_age : slope of log10(C_p90) per age bin, young -> old.  POSITIVE = old (rear) veins thicker (realistic)
  tail_ratio: C_p90 of the oldest age bin (age >= 200) / max C_p90 over the younger bins   (>=1 realistic: thickest veins at the rear)
"""
import sys, os, json, glob, numpy as np
from scipy import ndimage as ndi
HERE = os.path.dirname(os.path.abspath(__file__))
AGE_BINS = [0, 10, 25, 50, 100, 200, 1e9]


def analyse(nm, quiet=False):
    d = os.path.join(HERE, 'runs', nm)
    m = json.load(open(os.path.join(d, 'metrics.json'))); P = json.load(open(os.path.join(d, 'params.json')))
    h = np.load(os.path.join(d, 'body_native.npy')); C = np.load(os.path.join(d, 'vein_native.npy')); age = np.load(os.path.join(d, 'age.npy'))
    wet = h > 0; N = h.shape[0]; Y, X = np.mgrid[0:N, 0:N]
    cd = P.get('c_draw', 0) if P.get('c_draw', 0) > 0 else max(1.0, 2 * P['D0'])
    res = dict(name=nm)
    if wet.sum() < 30: return res
    lab, nl = ndi.label(wet, structure=np.ones((3, 3))); big = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    vm = wet & (C > cd)
    # ---- (a) bands along the travel direction ----
    if 'dir' in m:
        ux, uy = m['dir']; s = X * ux + Y * uy; w = -X * uy + Y * ux
        s0, s1 = s[big].min(), s[big].max(); bands = []
        for b in range(6):
            lo = s0 + (s1 - s0) * b / 6; hi = s0 + (s1 - s0) * (b + 1) / 6
            mb = big & (s >= lo) & (s <= hi); vb = vm & mb
            line = vm & big & (np.abs(s - (lo + hi) / 2) < 0.75); ww = np.sort(w[line])
            ncross = int(1 + (np.diff(ww) > 1.6).sum()) if ww.size else 0
            cv = C[vb]
            bands.append(dict(band=b, cells=int(mb.sum()), sheet=int((mb & (h > 0.5)).sum()), vein=int(vb.sum()), ncross=ncross,
                              Cp50=round(float(np.percentile(cv, 50)), 1) if cv.size else 0, Cp90=round(float(np.percentile(cv, 90)), 1) if cv.size else 0,
                              Cmax=round(float(cv.max()), 1) if cv.size else 0, hmean=round(float(h[mb].mean()), 3) if mb.any() else 0))
        res['bands_rear_to_front'] = bands; res['len_along'] = round(float(s1 - s0), 1)
        ok = [(b['band'], np.log10(b['Cp90'])) for b in bands if b['vein'] >= 5 and b['Cp90'] > 0]
        if len(ok) >= 3:
            xs, ys = zip(*ok); res['slope_dir'] = round(float(np.polyfit(xs, ys, 1)[0]), 3)
        rear = [b['Cp90'] for b in bands[:3] if b['vein'] >= 5]; front = [b['Cp90'] for b in bands[3:] if b['vein'] >= 5]
        if rear and front: res['rf_dir'] = round(float(np.median(rear) / np.median(front)), 3)
        rearm = [b['Cmax'] for b in bands[:3] if b['vein'] >= 1]; frontm = [b['Cmax'] for b in bands[3:] if b['vein'] >= 1]
        if rearm and frontm: res['rf_dir_max'] = round(float(np.max(rearm) / np.max(frontm)), 3)
    # ---- (b) age bins (all wet cells of the largest component) ----
    ab = []
    for i in range(len(AGE_BINS) - 1):
        mb = big & (age >= AGE_BINS[i]) & (age < AGE_BINS[i + 1]); vb = vm & mb; cv = C[vb]
        ab.append(dict(age_lo=AGE_BINS[i], cells=int(mb.sum()), vein=int(vb.sum()), vein_frac=round(float(vb.sum() / max(mb.sum(), 1)), 3),
                       Cp50=round(float(np.percentile(cv, 50)), 1) if cv.size else 0, Cp90=round(float(np.percentile(cv, 90)), 1) if cv.size else 0,
                       Cmax=round(float(cv.max()), 1) if cv.size else 0, hmean=round(float(h[mb].mean()), 3) if mb.any() else 0))
    res['age_bins'] = ab
    ok = [(i, np.log10(b['Cp90'])) for i, b in enumerate(ab) if b['vein'] >= 5 and b['Cp90'] > 0]
    if len(ok) >= 3:
        xs, ys = zip(*ok); res['slope_age'] = round(float(np.polyfit(xs, ys, 1)[0]), 3)
    old = vm & big & (age >= 100); young = vm & big & (age < 50)
    if old.sum() >= 5 and young.sum() >= 5:
        res['of_age'] = round(float(np.percentile(C[old], 90) / np.percentile(C[young], 90)), 3)
        res['of_age_p50'] = round(float(np.percentile(C[old], 50) / np.percentile(C[young], 50)), 3)
    res['vein_cells'] = int((vm & big).sum()); res['n_old_vein'] = int(old.sum())
    # tail ratio: C_p90 of the oldest populated bin (age >= 200, >= 5 vein cells) / max C_p90 over the younger bins.  >= 1 = thickest veins are at the rear (realistic)
    if ab[-1]['vein'] >= 5 and max(b['Cp90'] for b in ab[:-1]) > 0:
        res['tail_ratio'] = round(float(ab[-1]['Cp90'] / max(b['Cp90'] for b in ab[:-1])), 3)
    json.dump(res, open(os.path.join(d, 'profile.json'), 'w'), indent=1)
    if not quiet:
        print(f'== {nm}: slope_dir={res.get("slope_dir")} rf_dir={res.get("rf_dir")} rf_dir_max={res.get("rf_dir_max")} | slope_age={res.get("slope_age")} tail_ratio={res.get("tail_ratio")} (old vein cells {res["n_old_vein"]})')
        if 'bands_rear_to_front' in res:
            print('   bands rear->front  ncross:', [b['ncross'] for b in res['bands_rear_to_front']], ' Cp90:', [b['Cp90'] for b in res['bands_rear_to_front']],
                  ' Cmax:', [b['Cmax'] for b in res['bands_rear_to_front']], ' sheet:', [b['sheet'] for b in res['bands_rear_to_front']])
        print('   age bins young->old  vein:', [b['vein'] for b in ab], ' Cp50:', [b['Cp50'] for b in ab], ' Cp90:', [b['Cp90'] for b in ab], ' Cmax:', [b['Cmax'] for b in ab])
    return res


def row(nm, res):
    m = json.load(open(os.path.join(HERE, 'runs', nm, 'metrics.json'))); e = m.get('eval_primary', {}); fl = m.get('flux', {}); ha = m.get('hamp', {}); lk = m.get('lock', {})
    return [nm, m.get('t_end'), m.get('disp'), m.get('late_speed'), m.get('area_end'), m.get('growth_polarisation'), m.get('active_front_patches'), m.get('front_rear_ext_ratio'),
            m.get('sheet_area_frac'), m.get('body_components'), m.get('vol_frac_largest'),
            e.get('branch_points'), e.get('loops'), e.get('vein_largest_frac'), e.get('width_ratio_p90_p10'), e.get('strength_ratio_p90_p10'), str(e.get('verdict', {}).get('all_three'))[0],
            ha.get('sheet_mean'), ha.get('thin_mean'), fl.get('gross_over_net_vein'), fl.get('frac_vein_edges_reversing'), lk.get('R'), lk.get('phase_deg'), m.get('new_mod_index'),
            m.get('phase_lead_old_minus_young_turns'), res.get('slope_dir'), res.get('rf_dir'), res.get('slope_age'), res.get('tail_ratio'),
            '%.1e' % m.get('mass_err_max', 0), round(m.get('h_min_seen', 0), 3), (m.get('stop') or '-').replace(' ', '_')]


COLS = ['run', 't_end', 'disp', 'vlate', 'area', 'pol', 'patch', 'F/R_ext', 'sh_frac', 'comp', 'Vbig', 'bp', 'loops', 'vlarg', 'wr', 'sr', 'all3',
        'hampSh', 'hampTh', 'G/Nvein', 'revfr', 'lockR', 'lockPh', 'modIx', 'phTurn', 'slopeDir', 'rfDir', 'slopeAge', 'tailR', 'mass_err', 'h_min', 'stop']

if __name__ == '__main__':
    args = sys.argv[1:]; tsv = None; quiet = False
    if '--quiet' in args: quiet = True; args.remove('--quiet')
    if args and args[0] == '--tsv': tsv = args[1]; args = args[2:]
    if not args: args = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, 'runs', '*')) if os.path.exists(os.path.join(p, 'metrics.json')))
    rows = []
    for nm in args:
        try: rows.append(row(nm, analyse(nm, quiet)))
        except Exception as ex: print(nm, 'failed', repr(ex))
    fmt = lambda r: ' '.join(('%-16s' if i == 0 else '%7s') % (x if x is not None else '-') for i, x in enumerate(r))
    print(fmt(COLS))
    for r in rows: print(fmt(r))
    if tsv:
        with open(os.path.join(HERE, tsv), 'w') as f:
            f.write('\t'.join(COLS) + '\n')
            for r in rows: f.write('\t'.join(str(x) for x in r) + '\n')
