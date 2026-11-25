"""S23 진단 4 보기: 방울 모양 두께(s23w = s23z + scl_tgcap=1)를 같은 시드의 s23z(첫 거르기 실행)와 견준다. 균핵 측정은 sclform.py (거르기와 같음).
python3 d4look.py [꼬리표=s23w]
- 갇히기 전 마지막 장면이 비트까지 같은지 (방울 모양은 갇힐 때만 작용)
- 끝 덩이: 넓이, 원판 IoU, 짙던 자리 IoU(S1), 두께 CV·±10%(S3), 한 장면 최대 몫(S2), 오름 90%(L3), 얇은 칸 몫(T4), 구멍(S6), 볼록 껍질 대비 넓이(S7), 축비(L2)
"""
import os, sys, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'model'))
import sclform
from scipy import ndimage as nd
from scipy.spatial import ConvexHull
from ref_model import _torus_label
RUNS = os.path.join(HERE, '..', 'model', 'runs')

def recentre(m):
    N_ = m.shape[0]; ys, xs = np.nonzero(m)
    cy = int(np.angle(np.exp(2j * np.pi * ys / N_).mean()) * N_ / (2 * np.pi)) % N_; cx = int(np.angle(np.exp(2j * np.pi * xs / N_).mean()) * N_ / (2 * np.pi)) % N_
    return np.roll(m, (N_ // 2 - cy, N_ // 2 - cx), (0, 1))

def shape(d):
    w = np.load(os.path.join(d, 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(d, 'h.npy')), 0.0)
    lab = _torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel()); vol[0] = 0; big = recentre(lab == int(np.argmax(vol)))
    holes = int((nd.binary_fill_holes(big) & ~big).sum()); ys, xs = np.nonzero(big)
    pts = np.concatenate([np.c_[xs + a, ys + b] for a in (0, 1) for b in (0, 1)]); conv = float(big.sum() / ConvexHull(pts).volume)
    return holes, conv

def main(tag):
    rows = []
    for scn, ss in (('slimeall', range(731, 737)), ('long', range(721, 727))):
        for s in ss:
            dw = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}'); dz = os.path.join(RUNS, f'b_{scn}_s{s}_s23z')
            if not os.path.exists(os.path.join(dw, 'metrics.json')): continue
            mw = json.load(open(os.path.join(dw, 'metrics.json'))); mz = json.load(open(os.path.join(dz, 'metrics.json')))
            tf = int(mz['t_scl'] // 20 * 20); same = all(np.array_equal(np.load(os.path.join(dw, f'vs_t{tf:04d}.npz'))[k], np.load(os.path.join(dz, f'vs_t{tf:04d}.npz'))[k]) for k in ('h', 'wet'))
            for nm, d, m in (('s23z', dz, mz), (tag, dw, mw)):
                r = sclform.run(d); ho, cv = shape(d)
                rows.append((scn, s, nm, r, ho, cv, m))
                print(f"{scn:8s} {s} {nm:5s} 갇힘 {m['t_scl']:7.1f} (앞 장면 같음 {same}) 넓이 {r.get('area'):4d} 원판 {r.get('disc_iou', 0):.2f} 짙던 {r.get('iou_mass', 0):.2f} CV {r.get('h_cv', 0):.2f} ±10% {r.get('h_in10', 0):.2f} "
                      f"한 장면 {(r.get('max_share') or 0):.2f} 오름90 {r.get('t90')} 얇은 {r.get('thin_frac', 0):.3f} 축비 {1 / max(r.get('aspect', 1), 1e-9):.2f} 구멍 {ho} 볼록 {cv:.2f} hmax {r.get('h_p90', 0):.2f}(p90)")
    for nm in ('s23z', tag):
        R = [x for x in rows if x[2] == nm]
        if not R: continue
        cvs = [x[3].get('h_cv', 0) for x in R]; ins = [x[3].get('h_in10', 1) for x in R]; im = [x[3].get('iou_mass', 0) for x in R]
        print(f"{nm:5s}: CV 중앙 {np.median(cvs):.3f} 최소 {min(cvs):.3f}  ±10% 중앙 {np.median(ins):.3f}  짙던 IoU 평균 {np.mean(im):.3f}  한 장면 최대 {max((x[3].get('max_share') or 0) for x in R):.2f}  오름90 중앙 {np.median([x[3]['t90'] for x in R if x[3].get('t90') is not None]):.0f}"
              f"  얇은 최대 {max(x[3].get('thin_frac', 0) for x in R):.3f}  구멍 최대 {max(x[4] for x in R)}  볼록 최소 {min(x[5] for x in R):.2f}  축비 ≤ 0.9 {sum(1 / max(x[3].get('aspect', 1), 1e-9) <= 0.9 for x in R)}/{len(R)}")

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 's23w')
