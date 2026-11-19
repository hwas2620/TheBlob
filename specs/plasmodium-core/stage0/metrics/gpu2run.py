#!/usr/bin/env python3
"""GPU 실행의 상태 덤프(dumps/<실행>/)를 numpy 기준 실행과 같은 꼴(runs_gpu/<실행>/)로 바꾼다.

usage: gpu2run.py DUMP_DIR [OUT_DIR] [--keep]
  DUMP_DIR  run_stage0.cjs 가 쓴 폴더 (vs_tNNNN.bin, hfood.bin, series.bin, meta.json)
  OUT_DIR   기본은 ../runs_gpu/<실행 이름>
  --keep    바꾼 뒤에도 덤프를 지우지 않는다 (기본은 지운다. 192² 한 장이 3.4MB 다)

쓰는 것 (ref_model.py 가 runs/<실행>/ 에 쓰는 것과 같은 이름·같은 꼴):
  vs_tNNNN.npz   C[4], wet, h, age, sage, theta, Qgross[4], Qmean[4], Cmean[4], hamp, hmean, t
  G_edges.npy    정적 간선 잡음 (해시 난수에서 다시 만든다. GPU 가 쓰는 것과 같은 값)
  params.json    설정 (numpy 쪽 이름)
  hfood.npy      스텝마다 먹이 원반의 평균 두께, 위상
  series.npz     스텝마다 부피, 넓이, 새로 젖은 셀 수(전체, 가운데의 왼쪽)
  metrics.json   닿은 시각, 떨어진 시각, 부피 오차, 음수 두께, 유량 오차

배열의 색인은 [y, x] 이고 덤프의 평면 안에서는 y·N + x 다(관문 A 의 기준 자료와 같다).
"""
import glob, json, os, shutil, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'ref'))

# src/stage0/gateB.ts 의 DUMP_PLANES 와 같아야 한다
PLANES = ['C0', 'C1', 'C2', 'C3', 'wet', 'h', 'age', 'sage', 'theta',
          'Qgross0', 'Qgross1', 'Qgross2', 'Qgross3', 'Qmean0', 'Qmean1', 'Qmean2', 'Qmean3', 'Cmean0', 'Cmean1', 'Cmean2', 'Cmean3', 'hamp', 'hmean']


def read_dump(path, N):
    a = np.fromfile(path, '<f4')
    if a.size != len(PLANES) * N * N: raise SystemExit(f'{path}: 길이가 다르다 ({a.size} != {len(PLANES) * N * N})')
    a = a.reshape(len(PLANES), N, N)
    return dict(C=a[0:4], wet=a[4] > 0.5, h=a[5], age=a[6], sage=a[7], theta=a[8], Qgross=a[9:13], Qmean=a[13:17], Cmean=a[17:21], hamp=a[21], hmean=a[22])


def edge_noise(seed, N, edge_sigma):
    from ref_model import hash_normal
    return np.array([np.exp(edge_sigma * hash_normal(seed, k, N * N).reshape(N, N)) for k in range(4)], np.float32)


def convert(dump_dir, out_dir, keep=False):
    meta = json.load(open(os.path.join(dump_dir, 'meta.json')))
    if meta.get('planes') != PLANES: raise SystemExit('덤프의 평면 순서가 변환기와 다르다')
    P = meta['params']; N = P['N']; nf = meta['nf']
    os.makedirs(out_dir, exist_ok=True)
    for f in glob.glob(os.path.join(out_dir, 'vs_t*.npz')): os.remove(f)
    files = sorted(glob.glob(os.path.join(dump_dir, 'vs_t*.bin')))
    for f in files:
        t = int(os.path.basename(f)[4:8]); S = read_dump(f, N)
        np.savez_compressed(os.path.join(out_dir, f'vs_t{t:04d}.npz'), t=float(t), **S)
    np.save(os.path.join(out_dir, 'G_edges.npy'), edge_noise(P['seed'], N, P['edge_sigma']))
    json.dump(P, open(os.path.join(out_dir, 'params.json'), 'w'), indent=1)
    if nf > 0:
        np.save(os.path.join(out_dir, 'hfood.npy'), np.fromfile(os.path.join(dump_dir, 'hfood.bin'), '<f4').reshape(-1, 2 * nf))
    s = np.fromfile(os.path.join(dump_dir, 'series.bin'), '<f4').reshape(-1, 4)
    np.savez_compressed(os.path.join(out_dir, 'series.npz'), vol=s[:, 0].astype(np.float64), area=s[:, 1].astype(np.int32), new=s[:, 2].astype(np.int32), newl=s[:, 3].astype(np.int32), dt=P['dt'])
    m = dict(meta['metrics']); m.update(name=meta['name'], origin='gpu', t_end=round((meta['steps_done'] - 1) * P['dt'], 2), dumped=meta['dumped'])
    json.dump(m, open(os.path.join(out_dir, 'metrics.json'), 'w'), indent=1)
    if not keep: shutil.rmtree(dump_dir)
    return len(files)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--keep']
    if not args: raise SystemExit(__doc__)
    d = args[0].rstrip('/'); out = args[1] if len(args) > 1 else os.path.join(HERE, '..', 'runs_gpu', os.path.basename(d))
    n = convert(d, out, keep='--keep' in sys.argv)
    print(f'{os.path.basename(d)}: 상태 {n}장 → {os.path.normpath(out)}')
