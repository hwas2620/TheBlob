"""갈라지는 순간 진단: 오래 돌린 실행에서 몸 밖이 처음 0.10 을 넘는 저장 상태(i)를 찾고,
그 전 상태들(i-1, i-2, ...)에서 두 덩어리를 잇던 목(neck) 칸들의 두께·관(C)·흐름·나이를 몸 전체와 비교한다.
python3 diag_split.py RUN_DIR [RUN_DIR ...]"""
import os, sys, glob, numpy as np
from scipy.ndimage import distance_transform_edt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/metrics'))
import vmet

def lab_of(Z):
    wet = Z['wet'].astype(bool); N = wet.shape[0]
    src, dst, cc, kk = vmet.edge_list(Z['C'].astype(float), wet); nc, lab = vmet.comps(src, dst, N * N)
    lab = lab.reshape(N, N); h = Z['h'].astype(float)
    vol = np.bincount(lab[wet], weights=h[wet], minlength=nc)
    return wet, lab, vol

def node(Z, key):
    a = Z[key].astype(float); return np.max(np.abs(a), axis=0) if a.ndim == 3 else a

def tile_dist(mask):
    """토러스: 3x3 로 붙여 거리 변환 후 가운데를 잘라낸다"""
    N = mask.shape[0]; big = np.tile(~mask, (3, 3)); d = distance_transform_edt(big)
    return d[N:2 * N, N:2 * N]

for rd in sys.argv[1:]:
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))); Zs = [np.load(f) for f in fs]
    offs = []
    for Z in Zs:
        wet, lab, vol = lab_of(Z); offs.append(1 - vol.max() / vol.sum())
    i = next((k for k, o in enumerate(offs) if o >= 0.10), None)
    if i is None: print(os.path.basename(rd), '갈라지지 않음'); continue
    Zi = Zs[i]; wet_i, lab_i, vol_i = lab_of(Zi); order = np.argsort(vol_i)[::-1]; A, B = order[0], order[1]
    tot = vol_i.sum(); dA = tile_dist(wet_i & (lab_i == A)); dB = tile_dist(wet_i & (lab_i == B))
    print(f"\n{os.path.basename(rd)}: 처음 갈라진 t={float(Zi['t']):.0f}  큰 덩어리 {vol_i[A]/tot:.2f}, 둘째 {vol_i[B]/tot:.2f}, 덩어리 사이 최단 거리 {float((dA[wet_i & (lab_i == B)]).min()):.1f}")
    for back in (1, 2, 3, 5, 8):
        if i - back < 0: break
        Z = Zs[i - back]; wet = Z['wet'].astype(bool); h = Z['h'].astype(float)
        Cn = node(Z, 'C'); Qg = node(Z, 'Qgross'); age = Z['age'].astype(float)
        neck = wet & ~wet_i & (dA <= 4) & (dB <= 4)          # 그때 젖어 있다가 i 에서 마른, 두 덩어리 모두와 가까운 칸
        if not neck.any(): neck = wet & (dA + dB <= dA[wet_i & (lab_i == B)].min() + 3) & ~(wet_i & ((lab_i == A) | (lab_i == B)))
        f = lambda a, m: float(np.median(a[m])) if m.any() else float('nan')
        print(f"  t={float(Z['t']):5.0f} 목 칸 {int(neck.sum()):4d}개 | 두께 목 {f(h, neck):.3f} 몸 {f(h, wet):.3f} | 관 C 목 {f(Cn, neck):7.2f} (최대 {float(Cn[neck].max()) if neck.any() else 0:7.1f}) 몸 {f(Cn, wet):6.2f} | 흐름 목 {f(Qg, neck):.4f} 몸 {f(Qg, wet):.4f} | 나이 목 {f(age, neck):5.0f} 몸 {f(age, wet):5.0f}")
