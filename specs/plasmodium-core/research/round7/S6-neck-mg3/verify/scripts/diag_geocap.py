#!/usr/bin/env python3
"""diag_geocap.py RUN t [t ...] — 탐색: 모델의 이음 찾기는 너비 우선 거리를 N 걸음까지만 잰다(ref_model.py _geo 의 it_ < N).
이음 길이 L 이 N 보다 길면, 각 끝에서 L-N 칸 안쪽 셀은 한쪽 거리가 무한대라 '가장 짧은 길'에 들지 못해 지켜지지 않는다.
같은 저장 상태에서 (가) 모델 그대로(N 걸음 제한) (나) 제한 없이 이음을 찾아, 지켜지는 얇은 셀 수와 길이를 견준다."""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vextract as X
REF = '/home/user/TheBlob/specs/plasmodium-core/stage0/ref'

def find(h, wet, cap):
    N = h.shape[0]; thick = wet & (h >= 0.3); lt = X._torus_label(thick); nt = int(lt.max())
    vt = np.bincount(lt.ravel(), weights=np.where(thick, h, 0.0).ravel(), minlength=nt + 1); vt[0] = 0
    big = [k for k in np.argsort(vt)[::-1] if vt[k] >= 0.1 * float(h[wet].sum())]
    if len(big) < 2: return None
    def geo(src):
        dist = np.where(src, 0.0, np.inf); fr = src.copy(); seen = src.copy(); it = 0
        while fr.any() and it < cap:
            it += 1; m = np.zeros((N, N), bool)
            for d in X.ALL: m |= X.nb(fr, d)
            fr = m & wet & ~seen; dist[fr] = it; seen |= fr
        return dist
    dA = geo(lt == big[0]); out = []
    for kb in big[1:]:
        dB = geo(lt == kb); sm = dA + dB
        if not np.isfinite(sm[wet]).any(): out.append(dict(L=None)); continue
        m = float(np.min(sm[wet])); path = wet & (sm <= m + 1)
        out.append(dict(L=m, path=int(path.sum()), thin=int((path & ~thick).sum())))
    return out


def masks(h, wet, cap):
    N = h.shape[0]; thick = wet & (h >= 0.3); lt = X._torus_label(thick); nt = int(lt.max())
    vt = np.bincount(lt.ravel(), weights=np.where(thick, h, 0.0).ravel(), minlength=nt + 1); vt[0] = 0
    big = [k for k in np.argsort(vt)[::-1] if vt[k] >= 0.1 * float(h[wet].sum())]
    def geo(src):
        dist = np.where(src, 0.0, np.inf); fr = src.copy(); seen = src.copy(); it = 0
        while fr.any() and it < cap:
            it += 1; m = np.zeros((N, N), bool)
            for d in X.ALL: m |= X.nb(fr, d)
            fr = m & wet & ~seen; dist[fr] = it; seen |= fr
        return dist
    dA = geo(lt == big[0]); dB = geo(lt == big[1]); sm = dA + dB; m = float(np.min(sm[wet])); path = wet & (sm <= m + 1)
    return path & ~thick, dA, dB


if __name__ == '__main__':
    run = sys.argv[1]
    for t in sys.argv[2:]:
        Z = np.load(os.path.join(REF, 'runs', run, f'vs_t{int(float(t)):04d}.npz')); h = Z['h'].astype(float); wet = Z['wet'].astype(bool); N = h.shape[0]
        print(run, 't', t, 'model(cap N=%d):' % N, find(h, wet, N), ' no cap:', find(h, wet, 10 * N))
