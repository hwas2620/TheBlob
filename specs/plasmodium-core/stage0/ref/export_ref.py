#!/usr/bin/env python3
"""0단계 관문 A 의 numpy 기준 자료를 만든다.

usage: export_ref.py PART [...]
  check        noise='np' 로 돌린 ref_model 이 5차의 h1.py 와 같은 결과를 내는지 (h1.py 경로를 둘째 인자로)
  dumps192     192², 시드 1: 스텝 일치용 상태(스텝 0, 1, 10, 50, 2000, 2001, 2010)와 풀이 재생용 상태(스텝 1000, 1500, 2000)
  dumps384     384², 시드 1: 풀이 재생용 상태(스텝 2000)
  a12 N SEED SOLVER [T] [키=값 …] [tag=이름]   A1·A2 기준 실행 (SOLVER = mg | exact). 요약을 a12_N{N}_s{SEED}_{SOLVER}[_이름].json 에 쓴다.
                          키=값 은 모델 설정을 덮어쓴다 (예: dt=0.2 period=8 osc_sub=8 tag=dt2p8)
  b SCN SEED [키=값 …] [tag=이름]   관문 B 의 기준 실행. SCN 은 아래 SCN 표의 이름. runs/b_{SCN}_s{SEED}[_이름]/ 에 상태(vs_t*.npz)를 남긴다
  dumpsfood    192², 대칭 먹이 셋, 시드 1: 먹이가 있는 스텝 일치용 상태 (닿기 직전, 먹는 중, 첫 먹이가 떨어진 직후에서 +0, +1, +10, +50 스텝)
  dumpscrumb [S]           외톨이 셀 말리기의 스텝 일치용 (192², 대칭 먹이 셋, 시드 1): S 까지 규칙 없이, S 부터 규칙을 켜고 +0, +1, +10, +50 스텝
  dumpsfood2 six|fade [S]   먹이 스텝 일치의 나머지 길 (192², 시드 1). S 를 주지 않으면 먼저 한 번 돌려 닿은 시각·떨어진 시각만 찍는다
                 six   줄지 않는 먹이 여섯(60° 간격, 거리 30)을 먹는다 → 스텝 S, S+1, S+10
                 fade  금방 떨어지는 먹이 셋(양 20, 유인장이 사라지는 시간 1) → 스텝 S, S+1, S+10, S+120 (유인장의 세기가 1e-4 아래에서 멈춘 뒤까지)

상태 파일은 public/stage0/ref/ 에 float32 .bin.gz 로, 목록은 manifest.json 에 쓴다.
기준 설정은 5차 검증의 "굶은 이주"에서 마름의 부피 나눔만 spec 대로 두께 비례(dry_weight='h')로 바꾼 것이다. 잡음은 해시 난수(noise='hash').
"""
import json, os, sys
# 실행 여럿을 나란히 돌릴 때 스레드가 서로 다투지 않게 한다. numba 의 병렬 커널(mgt.py)이 CPU 를 다 잡으려 들면 한 스텝이 80배까지 느려진다
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'): os.environ.setdefault(_k, '1')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'public', 'stage0', 'ref'))
sys.path.insert(0, HERE)

GA = dict(N=192, T=400, dt=0.1, seed=1,
          foods=[[27, 70]], food_sigma=60.0, food_amp=0.5, food_r=4.0, reservoir=0, eat=0.0, gain=0.0, food_M=0.0,
          bridge_keep=1, bridge_break=1.0, wet_rho=0.92, curv='gauss', curv_sigma=2.0, curv_ref=0.33, curv_gain=8.0, dry_weight='h', neg_dry=1,
          solver='mg', ncyc=2, nc=4, extrap=0.5, check_every=20, noise='hash', gm_every=1e9, nsnap=4, vsave=0)


# ── 관문 B ──
# 위상 무늬 (나) 흘러가는 삼각 격자. GPU 쪽(config.ts 의 OSCILLATOR)과 같은 값
TRI = dict(tri_k=2 * np.pi / 100, tri_P=96, tri_T=80.0, tri_v=0.24)
# 규칙 8 의 값: 5차 기준 먹이 실행(Y3_tri96d)의 것 + spec 의 "쉬는 두께의 90% 이상 차 있을 때만" (res_gate)
FOOD = dict(reservoir=1, eat=0.05, gain=1.0, food_M=1200.0, food_fade=10.0, h_res=4.0, res_acc=2, res_tau=30.0, res_gate=0.9, food_sigma=25.0, food_amp=1.0, food_r=5.0)
# crumb_dry=1: 규칙 6 의 외톨이 셀 말리기 (2026-11-20 spec 반영, 계획 C). 이 줄 이전에 돌린 관문 B 기록(results/b)은 이 규칙 없이 돈 것이다
GB = dict(GA, **TRI, vsave=1, gm_every=20.0, crumb_dry=1)
SCN = {
    'mig': dict(T=400),                                                          # 굶은 이주: GA 의 유인원 하나 (27°, 70셀)
    'dir0': dict(foods=[[0, 70]], T=500, stop_touch=1), 'dir13': dict(foods=[[13, 70]], T=500, stop_touch=1), 'dir27': dict(foods=[[27, 70]], T=500, stop_touch=1),
    'dir34': dict(foods=[[34, 70]], T=500, stop_touch=1), 'dir45': dict(foods=[[45, 70]], T=500, stop_touch=1),       # 방향별 도달 시각 (B2)
    'food3': dict(FOOD, foods=[[20, 40], [140, 40], [260, 40]], T=480),         # 대칭 먹이 셋 (5차 Y3)
    'asym3': dict(FOOD, foods=[[0, 35], [100, 45], [200, 40]], T=480),          # 비대칭 먹이 셋 (5차 A3)
    'food4': dict(FOOD, N=256, tri_P=128, foods=[[10, 45], [100, 75], [215, 60], [300, 40]], T=700, eat=0.02, ncyc=3),   # 4차의 긴 배치 (F1 9-2절). 256² 라 무늬의 주기를 128 로
    'long': dict(T=2000),                                                        # 지속: 굶은 이주를 500주기
    'mig2x': dict(N=384, R_init=24.0, T=400),                                    # 몸 길이 2배 (처음 원반의 반지름 2배 = 부피 4배): 위상 지연이 유지되는지 (B4)
    'slimehalf': dict(foods=[], slime0='half', T=200), 'slimeall': dict(foods=[], slime0='all', T=200),   # 점액 기피 (B6): 유인원 없이, 몸 둘레의 왼쪽 절반 또는 사방이 흔적
    'mig256': dict(N=256, tri_P=128, T=400), 'food3_256': dict(FOOD, N=256, tri_P=128, foods=[[20, 40], [140, 40], [260, 40]], T=480),   # 게임 격자 후보
}


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
    elif part == 'b':
        scn = sys.argv[2]; seed = int(sys.argv[3]); kv = dict(a.split('=', 1) for a in sys.argv[4:]); tag = kv.pop('tag', '')
        over = dict(GB); over.update(SCN[scn]); over.update(seed=seed)
        for k, v in kv.items(): over[k] = json.loads(v) if v[:1] in '[{' else (int(v) if k in ('N', 'osc_sub', 'ncyc', 'res_acc', 'reservoir', 'vsave', 'f32') else float(v))
        R.run(f'b_{scn}_s{seed}' + (f'_{tag}' if tag else ''), over)
    elif part == 'dumpsfood':
        s0 = [int(a) for a in sys.argv[2:5]]           # 세 시점의 스텝 (닿기 직전, 먹는 중, 첫 먹이가 떨어진 직후). 먼저 b food3 1 을 돌려 metrics.json 의 t_touch, t_exh 를 보고 정한다
        steps = tuple(s + d for s in s0 for d in (0, 1, 10, 50))
        over = dict(GB); over.update(SCN['food3']); over.update(seed=1, T=(max(steps) + 2) * GA['dt'], vsave=0, gm_every=1e9, dump_dir=PUB, dump_state_steps=steps, dump_food=1, dump_tag='foodstate', check_every=0)
        R.run('dumpsfood', over)
    elif part == 'dumpscrumb':
        # 외톨이 셀 말리기의 스텝 일치용 (계획 C): 지금 규칙으로 S 스텝까지 돌려 외딴 음수 셀이 있는 상태를 만들고, S 부터 규칙을 켠다
        S = int(sys.argv[2]) if len(sys.argv) > 2 else 3790
        steps = tuple(S + d for d in (0, 1, 10, 50))
        over = dict(GB); over.update(SCN['food3']); over.update(seed=1, crumb_dry=1, crumb_from=S, T=(max(steps) + 2) * GA['dt'], vsave=0, gm_every=1e9,
                                                           dump_dir=PUB, dump_state_steps=steps, dump_food=1, dump_tag='foodcrumbstate', check_every=0)
        m = R.run('dumpscrumb', over); print('V_crumb', m.get('V_crumb'), 'crumb_cells', m.get('crumb_cells'))
    elif part == 'dumpsfood2':
        case = sys.argv[2]; S = int(sys.argv[3]) if len(sys.argv) > 3 else None
        extra = {'six': dict(foods=[[a, 30] for a in range(0, 360, 60)], food_M=0.0), 'fade': dict(foods=[[20, 40], [140, 40], [260, 40]], food_M=20.0, food_fade=1.0)}[case]
        steps = () if S is None else tuple(S + d for d in ((0, 1, 10) if case == 'six' else (0, 1, 10, 120)))
        over = dict(GB); over.update(FOOD); over.update(extra); over.update(seed=1, T=(max(steps) + 2) * GA['dt'] if steps else 130.0, vsave=0, gm_every=1e9, check_every=0)
        if steps: over.update(dump_dir=PUB, dump_state_steps=steps, dump_food=1, dump_tag={'six': 'food6state', 'fade': 'foodfadestate'}[case])
        m = R.run('dumpsfood2_' + case, over); print('t_touch', m['t_touch'], 't_cover', m['t_cover'], 't_exh', m['t_exh'])
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
