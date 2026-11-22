#!/usr/bin/env python3
"""긴 실행(long)을 스텝마다 지켜보며 돌린다. 모델(ref_model.py)은 고치지 않는다.

usage: vrun.py SCN SEED [키=값 ...] tag=이름

export_ref.py 의 'b' 경로와 똑같이 설정을 만든다(GB + SCN[SCN] + seed + 키=값). 다른 점은 둘뿐이다:
  gm_every=0.1, vsave=0   모델이 매 스텝 끝에 graphm.quick(상태) 를 부르게 한다 (동역학에는 쓰이지 않는 값)
  graphm.quick 를 바꿔 끼운다: 매 스텝 monitor.step_stats 를 기록하고, 20 시간마다만 본래 quick 을 부르고
                                가벼운 상태(lv_tNNNN.npz: wet, h, age, sage, C, cen, t)를 남긴다
결과: runs/b_SCN_sSEED_TAG/ 에 모델의 보통 출력 + lv_t*.npz + mon.npz(스텝별 숫자, monitor.STAT_KEYS)
      verify/data/mon/ 에 mon.npz 사본
"""
import os, sys, json
for _k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS'): os.environ.setdefault(_k, '1')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.normpath(os.path.join(HERE, '..', '..', 'model'))
sys.path.insert(0, MODEL); sys.path.insert(0, HERE)
import graphm, monitor
import export_ref as E
import ref_model as R


def main():
    scn = sys.argv[1]; seed = int(sys.argv[2]); kv = dict(a.split('=', 1) for a in sys.argv[3:]); tag = kv.pop('tag', '')
    over = dict(E.GB); over.update(E.SCN[scn]); over.update(seed=seed)
    for k, v in kv.items(): over[k] = json.loads(v) if v[:1] in '[{' else (int(v) if k in ('N', 'osc_sub', 'ncyc', 'res_acc', 'reservoir', 'vsave', 'f32') else float(v))   # export_ref.py 와 같은 해석
    over.update(gm_every=0.1, vsave=0)
    name = f'b_{scn}_s{seed}' + (f'_{tag}' if tag else ''); out = os.path.join(MODEL, 'runs', name); os.makedirs(out, exist_ok=True)
    dt = over['dt']; every = int(round(20.0 / dt)); rec = []
    orig = graphm.quick

    def hook(S):
        t = float(S['t']); k = int(round(t / dt))
        rec.append(monitor.step_stats(S['wet'], S['h'], t))
        if k % every == 0:
            np.savez_compressed(os.path.join(out, f'lv_t{int(round(t)):04d}.npz'), wet=S['wet'], h=S['h'], age=S['age'], sage=S['sage'], C=S['C'], cen=S['cen'], t=t)
            return orig(S)
        return {}
    graphm.quick = hook
    R.run(name, over)
    arr = np.array(rec, np.float64)
    np.savez_compressed(os.path.join(out, 'mon.npz'), stats=arr, keys=np.array(monitor.STAT_KEYS))
    dd = os.path.join(HERE, '..', 'data', 'mon'); os.makedirs(dd, exist_ok=True)
    np.savez_compressed(os.path.join(dd, f'{name}.npz'), stats=arr.astype(np.float32), t=arr[:, 0], keys=np.array(monitor.STAT_KEYS))
    print(name, 'monitor rows', arr.shape, flush=True)


if __name__ == '__main__':
    main()
