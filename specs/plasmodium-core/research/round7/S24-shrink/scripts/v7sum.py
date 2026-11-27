import json, glob, os, sys, numpy as np
D = sys.argv[1]; tags = sys.argv[2:]
R = {t: [json.load(open(f)) for f in sorted(glob.glob(os.path.join(D, f'*_{t}.json')))] for t in tags}
for t in tags:
    rows = R[t]; sc = []; far_runs = []; tail = []; crumbs = []
    g = {'mig': [], 'food': []}
    for r in rows:
        ts = r.get('t_scl'); nfar = 0
        for f in r['frames']:
            if f['t'] < 40: continue
            if f['t'] >= 60: crumbs.append(f['n_crumb'])
            if ts is not None and f['t'] > ts: continue
            sc.append(f); tail.append(f['n_tail30'] > 0); nfar += f['n_far100'] > 0
            if r['scn'] == 'mig' and f['t'] <= 400: g['mig'].append(f)
            if r['scn'] in ('food3', 'asym3', 'food4'): g['food'].append(f)
        far_runs.append((r['scn'], r['seed'], nfar))
    q = np.mean(tail); nf = sum(x[2] for x in far_runs); bad = [x for x in far_runs if x[2] >= 2]
    print(f"{t}: 장면 {len(sc)}  긴 꼬리(L≥30) 장면 몫 q {q:.3f}  >100 외가닥 장면 {nf}  두 장면 이상 실행 {len(bad)} {bad[:8]}  부스러기 장면 몫 {np.mean(np.array(crumbs) > 0):.3f}")
    for k, F in g.items():
        if F: print(f"   {k}: 흐름 없는 실 {np.mean([f['dead_thread_frac'] for f in F]):.4f}  얇은 막 {np.mean([f['film_frac'] for f in F]):.4f}  흐름 없는 끝 {np.mean([f['dead_tips'] for f in F]):.2f}  (장면 {len(F)})")
    kinds = {}
    for f in sc:
        for k in (f.get('far100_kinds') or []): kinds[k] = kinds.get(k, 0) + 1
    print('   >100 종류', kinds, ' 긴 꼬리 장면을 시나리오별:', {s: round(float(np.mean([fr['n_tail30'] > 0 for r in rows if r['scn'] == s for fr in r['frames'] if fr['t'] >= 40 and (r.get('t_scl') is None or fr['t'] <= r['t_scl'])])), 3) for s in sorted(set(r['scn'] for r in rows))})
