#!/usr/bin/env python3
"""직접 정의한 굵기 위계 지표 (공통 eval 의 width_ratio 는 접합부의 뭉친 곳을 굵은 관으로 세므로 보완용).
  1) 정맥 마스크 = 몸 안 vein > 0.35·p99 (eval_morph 와 동일), 뼈대화.
  2) 접합점(이웃>=3)을 그 지점 반폭(EDT)+2px 만큼 부풀려 뼈대에서 제거 → 가지(segment)로 분리.
  3) 길이 >= 6px 인 가지마다 폭 중앙값(2·EDT)과 세기 중앙값을 구함.
  seg_wr = 가지 폭 중앙값의 (길이 가중) p90/p10,  seg_sr = 가지 세기 중앙값의 p90/p10.
  age.npy 가 있으면 front(age<1/3)/rear(age>=2/3) 구역별 가지 폭 중앙값도 낸다 (없으면 원반 가정: age=1-r/R).
사용: hier.py RUN1 RUN2 ...   → 표 출력 + runs/<run>/hier.json"""
import os, sys, json, warnings
warnings.filterwarnings('ignore')
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize, remove_small_objects, remove_small_holes
HERE = os.path.dirname(os.path.abspath(__file__))

def wq(v, w, q):
    o = np.argsort(v); v = v[o]; w = w[o]; c = np.cumsum(w) / w.sum()
    return float(v[np.searchsorted(c, q).clip(0, len(v) - 1)])

def analyse(d):
    body = np.load(os.path.join(d, 'body.npy')); vein = np.load(os.path.join(d, 'vein.npy'))
    bm = body > 0
    p99 = np.percentile(vein[bm], 99)
    vm = bm & (vein > 0.35 * p99)
    vm = remove_small_holes(remove_small_objects(vm, 8), 6)
    sk = skeletonize(vm)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode='constant') - sk
    junc = sk & (nb >= 3)
    dt = ndi.distance_transform_edt(vm)
    # 접합점 주변 제거: 접합점까지의 거리 < 그 접합점의 반폭 + 2
    cut = np.zeros_like(sk)
    jy, jx = np.nonzero(junc)
    for y, x in zip(jy, jx):
        r = int(np.ceil(dt[y, x] + 2))
        y0, y1, x0, x1 = max(y - r, 0), y + r + 1, max(x - r, 0), x + r + 1
        yy, xx = np.ogrid[y0:min(y1, sk.shape[0]), x0:min(x1, sk.shape[1])]
        cut[y0:y1, x0:x1] |= ((yy - y) ** 2 + (xx - x) ** 2) <= r * r
    seg = sk & ~cut
    lab, n = ndi.label(seg, structure=np.ones((3, 3)))
    if n == 0:
        return dict(n_seg=0)
    idx = np.arange(1, n + 1)
    length = ndi.sum(seg, lab, idx)
    wmed = ndi.median(2 * dt, lab, idx); smed = ndi.median(vein, lab, idx)
    cy = ndi.mean(np.indices(sk.shape)[0].astype(float), lab, idx); cx = ndi.mean(np.indices(sk.shape)[1].astype(float), lab, idx)
    k = length >= 6
    if k.sum() < 5:
        return dict(n_seg=int(k.sum()))
    L = length[k]; W = wmed[k]; S = smed[k]
    out = dict(n_seg=int(k.sum()), seg_w_p10=round(wq(W, L, .1), 2), seg_w_p50=round(wq(W, L, .5), 2), seg_w_p90=round(wq(W, L, .9), 2),
               seg_s_p10=round(wq(S, L, .1), 2), seg_s_p90=round(wq(S, L, .9), 2))
    out['seg_wr'] = round(out['seg_w_p90'] / max(out['seg_w_p10'], 1e-6), 2)
    out['seg_sr'] = round(out['seg_s_p90'] / max(out['seg_s_p10'], 1e-6), 2)
    ap = os.path.join(d, 'age.npy')
    if os.path.exists(ap):
        age = np.load(ap)
    else:
        N = body.shape[0]; yy, xx = np.mgrid[0:N, 0:N]
        ys, xs = np.nonzero(bm); c_y, c_x = ys.mean(), xs.mean(); R = np.sqrt(bm.sum() / np.pi)
        age = np.clip(1 - np.hypot(yy - c_y, xx - c_x) / R, 0, 1)
    a = age[cy[k].round().astype(int).clip(0, sk.shape[0] - 1), cx[k].round().astype(int).clip(0, sk.shape[1] - 1)]
    for name, lo, hi in (('front', 0, 1 / 3), ('mid', 1 / 3, 2 / 3), ('rear', 2 / 3, 1.01)):
        q = (a >= lo) & (a < hi)
        if q.sum() >= 3:
            out[f'seg_w_{name}'] = round(wq(W[q], L[q], .5), 2); out[f'seg_s_{name}'] = round(wq(S[q], L[q], .5), 2)
            out[f'seg_len_{name}'] = round(float(np.median(L[q])), 1); out[f'n_{name}'] = int(q.sum())
    if 'seg_w_front' in out and 'seg_w_rear' in out:
        out['seg_w_rear_over_front'] = round(out['seg_w_rear'] / max(out['seg_w_front'], 1e-6), 2)
        out['seg_len_rear_over_front'] = round(out['seg_len_rear'] / max(out['seg_len_front'], 1e-6), 2)
    return out

if __name__ == '__main__':
    cols = ['n_seg', 'seg_w_p10', 'seg_w_p50', 'seg_w_p90', 'seg_wr', 'seg_sr', 'seg_w_front', 'seg_w_mid', 'seg_w_rear', 'seg_w_rear_over_front',
            'seg_len_front', 'seg_len_rear', 'seg_len_rear_over_front']
    print('| run | ' + ' | '.join(cols) + ' |'); print('|' + '---|' * (len(cols) + 1))
    for nm in sys.argv[1:]:
        d = os.path.join(HERE, 'runs', nm)
        try:
            o = analyse(d)
        except Exception as e:
            print(f'| {nm} | 오류 {e} |'); continue
        json.dump(o, open(os.path.join(d, 'hier.json'), 'w'), indent=1)
        print(f'| {nm} | ' + ' | '.join(str(o.get(c, '-')) for c in cols) + ' |')
