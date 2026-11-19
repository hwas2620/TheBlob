#!/usr/bin/env python3
"""판정 도구의 확인: GPU 의 덤프 경로와 구간 통계가 numpy 와 맞는지 본다.

먼저   node run_stage0.cjs bstats "test=bstats"          (dumps/bstats/ 에 roundtrip.bin, vs_t0200.bin, vs_t0220.bin)
       ref/ 에서 python3 export_ref.py b food3 1           (runs/b_food3_s1/ 의 vs_t0200.npz, vs_t0220.npz)
usage: check_dump.py

1) roundtrip.bin  numpy 상태(스텝 2000)를 GPU 에 넣고 그대로 내보낸 것 → 넣은 값과 비트 단위로 같아야 한다 (덤프 경로와 평면 순서의 확인)
2) vs_t0200       한 스텝 뒤의 상태 → numpy 의 t=200 상태와 스텝 일치 수준으로 같아야 한다
3) vs_t0220       201스텝 뒤. 구간 통계(스텝 2000~2199 의 유량·전도도 평균, 2160~2199 의 두께 진폭·평균)를 numpy 의 같은 구간과 견준다.
                  궤적이 float32 때문에 조금 갈라지므로 차이는 0 이 아니다. 상대 차이(L2)와 상관을 낸다.
"""
import gzip, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gpu2run import read_dump

N = 192
D = os.path.join(HERE, '..', 'dumps', 'bstats')
REF = os.path.join(HERE, '..', 'ref', 'runs', 'b_food3_s1')
PUB = os.path.join(HERE, '..', '..', '..', '..', 'public', 'stage0', 'ref')


def rel(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); d = np.sqrt(((a - b) ** 2).sum()); n = np.sqrt((b ** 2).sum())
    return d / n if n > 0 else d


def corr(a, b):
    a = np.asarray(a, float).ravel(); b = np.asarray(b, float).ravel()
    return float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else float('nan')


def main():
    ok = True
    # 1) 넣은 그대로
    man = json.load(open(os.path.join(PUB, 'manifest.json')))
    f = next(e for e in man['files'] if e['kind'] == 'foodstate' and e['step'] == 2000)
    raw = np.frombuffer(gzip.open(os.path.join(PUB, f['file'])).read(), '<f4'); n = N * N
    src = {e['name']: raw[e['offset']:e['offset'] + e['ch'] * n].reshape((e['ch'], N, N) if e['ch'] > 1 else (N, N)) for e in f['fields']}
    S = read_dump(os.path.join(D, 'roundtrip.bin'), N)
    same = {k: bool(np.array_equal(S[k], src[k] > 0.5 if k == 'wet' else src[k])) for k in ('C', 'wet', 'h', 'age', 'sage', 'theta')}
    print('1) 넣은 그대로 내보내기:', '모두 비트 단위로 같음' if all(same.values()) else same)
    ok &= all(same.values())
    # 2), 3)
    for t, strict in ((200, True), (220, False)):
        S = read_dump(os.path.join(D, f'vs_t{t:04d}.bin'), N); R = np.load(os.path.join(REF, f'vs_t{t:04d}.npz'))
        wet_mis = int((S['wet'] != R['wet']).sum()); both = S['wet'] & R['wet']
        print(f'{2 if strict else 3}) t={t}: 젖은 마스크 불일치 {wet_mis}/{int(R["wet"].sum())}, h 최대 차이 {np.abs(S["h"] - R["h"]).max():.2e}, C 상대 차이 {rel(S["C"], R["C"]):.2e}, age 최대 차이 {np.abs(S["age"] - R["age"])[both].max():.2e}')
        if strict:
            ok &= wet_mis == 0 and np.abs(S['h'] - R['h']).max() < 1e-3
            continue
        for k in ('Qgross', 'Qmean', 'Cmean'):
            print(f'   {k:7s} 상대 차이(L2) {rel(S[k], R[k]):.3e}, 상관 {corr(S[k], R[k]):.6f}, 합 GPU {float(np.abs(S[k]).sum()):.4f} / numpy {float(np.abs(R[k]).sum()):.4f}')
            ok &= rel(S[k], R[k]) < 0.05
        m = (S['hmean'] > 0) & (R['hmean'] > 0)
        print(f'   hmean   상대 차이(L2) {rel(S["hmean"][m], R["hmean"][m]):.3e}  (구간 내내 젖은 셀: GPU {int((S["hmean"] > 0).sum())} / numpy {int((R["hmean"] > 0).sum())})')
        print(f'   hamp    상대 차이(L2) {rel(S["hamp"][m], R["hamp"][m]):.3e}, 상관 {corr(S["hamp"][m], R["hamp"][m]):.6f}')
        ok &= rel(S['hmean'][m], R['hmean'][m]) < 0.01 and rel(S['hamp'][m], R['hamp'][m]) < 0.05
    print('→', '통과' if ok else '실패')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
