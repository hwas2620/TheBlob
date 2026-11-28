"""S25 후보 실행이 S24 후보 실행과 비트까지 같은지: 끝 배열(.npy)·중간 장면(vs_t*.npz)·metrics(먹이 닿은 시각, 궤적)"""
import sys, os, glob, json, numpy as np
a, b = sys.argv[1], sys.argv[2]; bad = []
for f in sorted(glob.glob(os.path.join(a, '*.npy'))):
    g = os.path.join(b, os.path.basename(f))
    if not os.path.exists(g) or not np.array_equal(np.load(f), np.load(g), equal_nan=True): bad.append(os.path.basename(f))
nv = 0
for f in sorted(glob.glob(os.path.join(a, 'vs_t*.npz'))):
    g = os.path.join(b, os.path.basename(f)); nv += 1
    if not os.path.exists(g): bad.append(os.path.basename(f)); continue
    A, B = np.load(f), np.load(g)
    for k in A.files:
        if not np.array_equal(A[k], B[k], equal_nan=(A[k].dtype.kind == "f")): bad.append(os.path.basename(f) + ':' + k)
ma, mb = json.load(open(os.path.join(a, 'metrics.json'))), json.load(open(os.path.join(b, 'metrics.json')))
for k in ('t_touch', 'traj', 'V_end', 'area_end', 't_scl', 'mass_err_max'):
    if ma.get(k) != mb.get(k): bad.append('metrics:' + k)
print(os.path.basename(a), 'vs', os.path.basename(b), f'npy+{nv} vs files:', 'BIT-IDENTICAL' if not bad else f'DIFFER {bad[:10]}')
