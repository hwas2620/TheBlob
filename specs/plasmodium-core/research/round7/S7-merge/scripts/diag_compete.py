"""지금 모델에서 부채끼리 경쟁이 일어나는가: 두꺼운 몸(h>=0.3)이 큰 덩어리 둘 이상일 때,
작은 쪽(B)에서 큰 쪽(A)으로 물질이 흘러가는가.
저장 상태(vs_t*.npz)마다: 젖은 몸을 A·B에 가까운 쪽으로 나누고(젖은 칸을 따라 잰 거리), 경계를 넘는 순 흐름(Qmean)을 잰다.
python3 diag_compete.py RUN_DIR [...]  → 표준 출력에 한 줄씩, 끝에 요약"""
import os, sys, glob, json, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../stage0/ref'))
from ref_model import _torus_label, DIRS, ALL, nb
TH, BIG = 0.3, 0.1
def geo(src, wet):
    dist = np.where(src, 0.0, np.inf); fr = src.copy(); seen = src.copy(); it = 0
    while fr.any():
        it += 1; m = np.zeros_like(wet)
        for d in ALL: m |= nb(fr, d)
        fr = m & wet & ~seen; dist[fr] = it; seen |= fr
    return dist
out = []
for rd in sys.argv[1:]:
    rows = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); t = float(Z['t']); wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); Qm = Z['Qmean'].astype(float)
        V = h.sum(); th = wet & (h >= TH); lt = _torus_label(th); nt = int(lt.max())
        if nt < 2: continue
        vt = np.bincount(lt.ravel(), weights=h.ravel(), minlength=nt + 1); vt[0] = 0
        big = [k for k in np.argsort(vt)[::-1] if vt[k] >= BIG * V]
        if len(big) < 2: continue
        A, B = lt == big[0], lt == big[1]
        lw = _torus_label(wet); same = lw[A][0] == lw[B][0]
        dA, dB = geo(A, wet), geo(B, wet)
        rA = wet & (dA < dB); rB = wet & ~rA & np.isfinite(dB)        # 같은 거리인 칸은 B 쪽에 넣는다
        net = 0.0; gross = 0.0; shut = 0.0; Qg = Z['Qgross'].astype(float); Cb = 0.0
        for k, d in enumerate(DIRS):
            q = Qm[k]; cut = (rB & nb(rA, d)) | (rA & nb(rB, d))
            net += q[rB & nb(rA, d)].sum() - q[rA & nb(rB, d)].sum()      # B→A 가 +
            gross += np.abs(q[cut]).sum(); shut += Qg[k][cut].sum(); Cb = max(Cb, float(Z['C'][k][cut].max()) if cut.any() else 0.0)
        th_ = Z['theta'].astype(float); dph = float(np.angle(np.exp(1j * th_[A]).mean() * np.conj(np.exp(1j * th_[B]).mean())))
        VB = h[rB].sum(); VA = h[rA].sum()
        link = float(np.nanmin((dA + dB)[wet])) if same else -1
        rows.append(dict(t=t, vA=vt[big[0]] / V, vB=vt[big[1]] / V, nbig=len(big), same=bool(same), sideA=VA / V, sideB=VB / V,
                         net=net, gross=gross, shut=shut, Ccut=Cb, dphase=dph, drain20=(net * 20 / VB) if VB > 0 else 0.0, link=link))
    for r in rows:
        print(os.path.basename(rd), 't=%4d nbig=%d same=%d vA=%.2f vB=%.2f sideB=%.2f link=%4d net=%+.3f |Qg|=%.3f Ccut=%5.1f dphase=%+.2f drainB/20t=%+.3f' % (
            r['t'], r['nbig'], r['same'], r['vA'], r['vB'], r['sideB'], r['link'], r['net'], r['shut'], r['Ccut'], r['dphase'], r['drain20']))
    out.append(dict(run=os.path.basename(rd), rows=rows))
c = [r for o in out for r in o['rows'] if r['same']]
if c:
    dr = np.array([r['drain20'] for r in c]); nr = np.array([r['net'] / max(r['gross'], 1e-12) for r in c])
    sh = np.array([r['shut'] for r in c]); dp = np.abs([r['dphase'] for r in c])
    print('왕복 흐름(Qgross) 경계 합: 중앙 %.3f, 사분위 %.3f ~ %.3f. 두 덩어리의 위상차 |Δθ| 중앙 %.2f rad' % (np.median(sh), np.percentile(sh, 25), np.percentile(sh, 75), np.median(dp)))
    print('\n요약: 이어진 상태 %d개. 작은 쪽 → 큰 쪽 순 흐름이 + 인 몫 %.2f. 20 시간에 작은 쪽 부피가 빠져나가는 비율: 중앙 %+.3f, 사분위 %+.3f ~ %+.3f. 순/총 중앙 %+.2f' % (
        len(c), (dr > 0).mean(), np.median(dr), np.percentile(dr, 25), np.percentile(dr, 75), np.median(nr)))
json.dump(out, open(os.environ.get('OUT', '/dev/null'), 'w'))
