#!/usr/bin/env python3
"""형태 평가 공통 스크립트 — 모든 실험을 같은 기준으로 채점한다.

사용법:
  python3 eval_morph.py BODY.npy VEIN.npy [--body-thr X] [--vein-rel R] [--out eval.json] [--png overlay.png]

BODY.npy : 2D float 배열. 원형질이 있는 정도(두께 h, 점유 등). 0 = 없음.
VEIN.npy : 2D float 배열. 같은 크기. 관(정맥)의 세기(전도도 D, trail, 유량 등). 클수록 굵은 관.

정맥 마스크 = 몸 안에서 VEIN > vein_rel * (몸 안 VEIN의 99퍼센타일).  기본 vein_rel = 0.35
세 가지 상대 임계값(0.2 / 0.35 / 0.5)에 대해 모두 계산하고, 기본값 결과를 primary 로 보고한다.
"""
import sys, json, argparse, warnings
warnings.filterwarnings("ignore")
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize, remove_small_objects, remove_small_holes
from skimage.measure import label, regionprops, euler_number, perimeter

def analyse(body, vein, body_thr, vein_rel):
    bm = body > body_thr
    out = {'vein_rel': vein_rel}
    area = int(bm.sum())
    out['body_area'] = area
    if area < 50:
        out['error'] = 'body too small'; return out, None
    lab = label(bm, connectivity=2)
    props = sorted(regionprops(lab), key=lambda r: -r.area)
    big = props[0]
    P = perimeter(lab == big.label)
    out['body_components'] = len(props)
    out['body_largest_frac'] = round(big.area / area, 3)
    out['body_circularity'] = round(float(4*np.pi*big.area / max(P*P, 1)), 3)   # 1 = 원, 작을수록 들쭉날쭉/가지형
    out['body_solidity'] = round(float(big.solidity), 3)                         # 1 = 볼록, 작을수록 오목/가지형
    out['body_fill_frac'] = round(area / bm.size, 4)
    vin = vein[bm]
    p99 = float(np.percentile(vin, 99)) if vin.size else 0.0
    out['vein_p50_over_p99'] = round(float(np.percentile(vin, 50)) / max(p99, 1e-12), 3)  # 낮을수록 관/비관 대비가 큼
    vm = bm & (vein > vein_rel * p99) & (p99 > 0)
    vm = remove_small_objects(vm, 8)
    vm = remove_small_holes(vm, 6)
    va = int(vm.sum())
    out['vein_area_frac'] = round(va / area, 4)
    if va < 20:
        out.update(branch_points=0, endpoints=0, loops=0, skeleton_len=0, vein_components=0,
                   vein_largest_frac=0.0, width_p10=0, width_p50=0, width_p90=0, width_ratio_p90_p10=0, width_cv=0)
        return out, (bm, vm, np.zeros_like(vm), np.zeros_like(vm))
    vlab = label(vm, connectivity=2)
    sizes = np.bincount(vlab.ravel())[1:]
    out['vein_components'] = int(len(sizes))
    out['vein_largest_frac'] = round(float(sizes.max() / va), 3)
    out['loops'] = int(len(sizes) - euler_number(vm, connectivity=2))            # 닫힌 고리 수 (구멍 수)
    sk = skeletonize(vm)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - sk
    ends = sk & (nb == 1)
    junc = sk & (nb >= 3)
    jl, nj = ndi.label(ndi.binary_dilation(junc, iterations=1), structure=np.ones((3, 3)))
    out['skeleton_len'] = int(sk.sum())
    out['branch_points'] = int(nj)
    out['endpoints'] = int(ends.sum())
    out['branch_points_per_1000px_body'] = round(nj / area * 1000, 3)
    dt = ndi.distance_transform_edt(vm)
    w = 2 * dt[sk]
    w = w[w > 0]
    p10, p50, p90 = [float(x) for x in np.percentile(w, [10, 50, 90])]
    out.update(width_p10=round(p10, 2), width_p50=round(p50, 2), width_p90=round(p90, 2),
               width_ratio_p90_p10=round(p90 / max(p10, 1e-6), 2), width_cv=round(float(w.std() / max(w.mean(), 1e-6)), 3))
    # 관 세기의 위계: 뼈대 위 VEIN 값 분포
    vs = vein[sk]
    out['strength_ratio_p90_p10'] = round(float(np.percentile(vs, 90) / max(np.percentile(vs, 10), 1e-12)), 2)
    return out, (bm, vm, sk, junc)

def verdict(m):
    """기계적 판정(참고용). 최종 판단은 이미지를 직접 보고 한다."""
    if 'error' in m: return {'network_like': False, 'branched': False, 'hierarchical': False, 'note': m['error']}
    net = 0.03 <= m['vein_area_frac'] <= 0.55 and m.get('vein_largest_frac', 0) >= 0.6
    br = m.get('branch_points', 0) >= 8
    hi = m.get('width_ratio_p90_p10', 0) >= 2.0 or m.get('strength_ratio_p90_p10', 0) >= 3.0
    return {'network_like': bool(net), 'branched': bool(br), 'hierarchical': bool(hi),
            'all_three': bool(net and br and hi)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('body'); ap.add_argument('vein')
    ap.add_argument('--body-thr', type=float, default=None)
    ap.add_argument('--vein-rel', type=float, default=0.35)
    ap.add_argument('--out', default=None); ap.add_argument('--png', default=None)
    a = ap.parse_args()
    body = np.load(a.body).astype(np.float64); vein = np.load(a.vein).astype(np.float64)
    assert body.ndim == 2 and body.shape == vein.shape, 'BODY/VEIN 은 같은 크기의 2D 배열이어야 함'
    bthr = a.body_thr if a.body_thr is not None else 0.05 * float(np.percentile(body, 99.5))
    res = {'shape': list(body.shape), 'body_thr': bthr, 'sweeps': {}}
    masks = None
    for r in sorted({0.2, 0.35, 0.5, a.vein_rel}):
        m, mk = analyse(body, vein, bthr, r)
        m['verdict'] = verdict(m)
        res['sweeps'][str(r)] = m
        if abs(r - a.vein_rel) < 1e-9: res['primary'] = m; masks = mk
    if a.png and masks is not None:
        from PIL import Image
        bm, vm, sk, junc = masks
        img = np.zeros(body.shape + (3,), np.uint8)
        img[bm] = (70, 70, 70); img[vm] = (230, 200, 60); img[sk] = (255, 60, 60)
        img[ndi.binary_dilation(junc, iterations=1)] = (60, 140, 255)
        im = Image.fromarray(img)
        s = max(1, min(4, 1024 // max(body.shape)))
        if s > 1: im = im.resize((body.shape[1]*s, body.shape[0]*s), Image.NEAREST)
        elif max(body.shape) > 1024:
            f = 1024 / max(body.shape); im = im.resize((int(body.shape[1]*f), int(body.shape[0]*f)), Image.BILINEAR)
        im.save(a.png)
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if a.out: open(a.out, 'w').write(txt)
    print(json.dumps({'primary': res.get('primary'), 'verdict_by_rel': {k: v['verdict'] for k, v in res['sweeps'].items()}}, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main()
