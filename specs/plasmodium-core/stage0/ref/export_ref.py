#!/usr/bin/env python3
"""0단계 관문 A 의 numpy 기준 자료를 만든다.

usage: export_ref.py PART [...]
  check        noise='np' 로 돌린 ref_model 이 5차의 h1.py 와 같은 결과를 내는지 (h1.py 경로를 둘째 인자로)
  dumps192     192², 시드 1: 스텝 일치용 상태(스텝 0, 1, 10, 50, 2000, 2001, 2010)와 풀이 재생용 상태(스텝 1000, 1500, 2000)
  dumps384     384², 시드 1: 풀이 재생용 상태(스텝 2000)
  a12 N SEED SOLVER [T] [키=값 …] [tag=이름]   A1·A2 기준 실행 (SOLVER = mg | exact). 요약을 a12_N{N}_s{SEED}_{SOLVER}[_이름].json 에 쓴다.
                          키=값 은 모델 설정을 덮어쓴다 (예: dt=0.2 period=8 osc_sub=8 tag=dt2p8)

상태 파일은 public/stage0/ref/ 에 float32 .bin.gz 로, 목록은 manifest.json 에 쓴다.
기준 설정은 5차 검증의 "굶은 이주"에서 마름의 부피 나눔만 spec 대로 두께 비례(dry_weight='h')로 바꾼 것이다. 잡음은 해시 난수(noise='hash').
"""
import json, os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'public', 'stage0', 'ref'))
sys.path.insert(0, HERE)

GA = dict(N=192, T=400, dt=0.1, seed=1,
          foods=[[27, 70]], food_sigma=60.0, food_amp=0.5, food_r=4.0, reservoir=0, eat=0.0, gain=0.0, food_M=0.0,
          bridge_keep=1, bridge_break=1.0, wet_rho=0.92, curv='gauss', curv_sigma=2.0, curv_ref=0.33, curv_gain=8.0, dry_weight='h', neg_dry=1,
          solver='mg', ncyc=2, nc=4, extrap=0.5, check_every=20, noise='hash', gm_every=1e9, nsnap=4, vsave=0)


def summarise(name, P, tag=''):
    m = json.load(open(os.path.join(HERE, 'runs', name, 'metrics.json')))
    tr = np.array([[a[0], a[1], a[2], a[3]] for a in m['traj']], float)
    at = lambda t: tr[np.argmin(np.abs(tr[:, 0] - t))]
    d = lambda t0, t1: float(np.hypot(*(at(t1)[1:3] - at(t0)[1:3])))
    errs = json.load(open(os.path.join(HERE, 'runs', name, 'mg_err_series.json')))
    e = np.array([x[1] for x in errs], float) if errs else np.zeros(0)
    out = dict(name=name, N=P['N'], seed=P['seed'], solver=P['solver'], ncyc=P.get('ncyc'), T=m['t_end'], stop=m['stop'],
               disp_100_300=d(100, 300), disp_0_400=d(0, 400), disp_end=m['disp'], t_touch=m['t_touch'], area_end=m['area_end'],
               Cmax_run=float(max(x['Cmax'] for x in m['log'])), Cmax_series=[[x['t'], round(x['Cmax'], 2)] for x in m['log'][::4]],
               traj=[[a[0], a[1], a[2], a[3]] for a in m['traj'][::4]],
               mass_err_max=m['mass_err_max'], h_min_seen=m['h_min_seen'], h_min_end_of_step=m['h_min_end_of_step'], neg_end_cellsteps=m['neg_end_cellsteps'],
               flux_err=dict(n=int(e.size), median=float(np.median(e)), p90=float(np.percentile(e, 90)), p99=float(np.percentile(e, 99)), max=float(e.max())) if e.size else None,
               runtime=m['runtime'])
    if tag: out.update(tag=tag, dt=P['dt'], period=P.get('period'), eps=P.get('eps'), osc_sub=P.get('osc_sub'))
    json.dump(out, open(os.path.join(HERE, f"a12_N{P['N']}_s{P['seed']}_{P['solver']}" + (f'_{tag}' if tag else '') + '.json'), 'w'), indent=1)
    print(name, {k: out[k] for k in ('disp_100_300', 'disp_0_400', 't_touch', 'Cmax_run', 'h_min_seen', 'neg_end_cellsteps', 'flux_err', 'runtime')})


def main():
    import ref_model as R
    part = sys.argv[1]
    if part == 'check':
        import importlib.util
        spec = importlib.util.spec_from_file_location('h1', sys.argv[2]); h1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(h1)
        over = dict(GA); over.update(noise='np', T=40, dry_weight='equal'); o2 = dict(over); o2.pop('noise')
        R.run('chk_ref', over); h1.run('chk_h1', o2)
        a = os.path.join(HERE, 'runs', 'chk_ref'); b = os.path.join(os.path.dirname(sys.argv[2]), 'runs', 'chk_h1')
        for f in ('h.npy', 'C_edges.npy', 'theta.npy', 'wet.npy'):
            x = np.load(os.path.join(a, f)); y = np.load(os.path.join(b, f)); print(f, 'identical' if np.array_equal(x, y, equal_nan=True) else 'DIFFERENT')
    elif part == 'dumps192':
        over = dict(GA); over.update(T=205, dump_dir=PUB, dump_state_steps=(0, 1, 10, 50, 2000, 2001, 2010), dump_solver_steps=(1000, 1500, 2000), check_every=0)
        R.run('dumps192', over)
    elif part == 'dumps384':
        over = dict(GA); over.update(N=384, T=200.1, dump_dir=PUB, dump_solver_steps=(2000,), check_every=0)
        R.run('dumps384', over)
    elif part == 'a12':
        N = int(sys.argv[2]); seed = int(sys.argv[3]); solver = sys.argv[4]
        rest = sys.argv[5:]; T = float(rest.pop(0)) if rest and '=' not in rest[0] else 1000.0
        kv = dict(a.split('=', 1) for a in rest); tag = kv.pop('tag', '')
        over = dict(GA); over.update(N=N, seed=seed, solver=solver, T=T)
        over.update({k: (int(v) if k == 'osc_sub' else float(v)) for k, v in kv.items()})
        name = f'a12_N{N}_s{seed}_{solver}' + (f'_{tag}' if tag else ''); R.run(name, over); summarise(name, over, tag)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
