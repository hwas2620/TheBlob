#!/usr/bin/env python3
"""[S7 독립 검증] 주장 2b: "이어진 두 덩어리 상태"가 시작된 뒤 진 쪽이 어디로 가는가 (대조와 후보를 똑같이).

usage: vfate.py TAG SEED [SEED ...] [--dt 20,40,60,100]   -> data/fate_<TAG>.json

에피소드 = 큰 두꺼운 덩어리 둘 이상이 같은 젖은 덩어리 안에 있는 저장 상태가 연달아 이어진 구간. 시작 t0 >= 100, t0 + Δ <= 끝.
t0: 그 젖은 덩어리의 칸을 젖은 칸을 따라 잰 가장 가까운 큰 덩어리에 나눈다 (몫 j).
t1 = t0 + Δ: t0부터 계속 젖어 있던 칸에 t0 의 몫 번호를 붙이고, t1 의 젖은 칸을 따라 가장 가까운 그런 칸의 번호로 넓힌다.
r_j = V_j(t1)/V_j(t0), a_j = A_j(t1)/A_j(t0), s_j = t1 에서 몫 j 의 젖은 칸 가운데 h < 0.3 의 비율. 진 쪽 L = r 가 가장 작은 몫, 이긴 쪽 W = r 가 가장 큰 몫.
분류 (이 순서): split(진 쪽 t1 부피의 반 이상이 이긴 쪽 본체가 아닌 젖은 덩어리에) / persist(t1 도 이어진 두 덩어리 상태)
              / merge(a_L <= 0.5) / thin(a_L > 0.5, s_L >= 0.5) / other
"""
import json, os, sys
import numpy as np
from vcommon import states, load, _torus_label, comp_vols, big_parts, partition, food_field, params, rundir, VER, TH

KEYS = ('wet', 'h', 'age')


def conn_parts(S):
    """이어진 두 덩어리 상태면 (젖은 라벨, 씨앗 라벨 배열, 큰 덩어리 수) 아니면 None"""
    wet, h = S['wet'], S['h']; V = float(h.sum())
    lt, big, vb = big_parts(wet, h, V)
    if len(big) < 2: return None
    lw = _torus_label(wet)
    owner = {k: int(np.bincount(lw[lt == k]).argmax()) for k in big}
    groups = {}
    for k in big: groups.setdefault(owner[k], []).append(k)
    gs = [g for g in groups.values() if len(g) >= 2]
    if not gs: return None
    vol = lambda g: sum(float(h[lt == k].sum()) for k in g)
    g = max(gs, key=vol)
    seeds = np.zeros(wet.shape, np.int64)
    for j, k in enumerate(g): seeds[lt == k] = j + 1
    return lw, seeds, len(g)


def episode(S0, S1, dT, cf):
    cp = conn_parts(S0); lw0, seeds0, n = cp
    reg0 = partition(S0['wet'], seeds0)
    h0, h1 = S0['h'], S1['h']; wet1 = S1['wet']
    orig = S0['wet'] & wet1 & (S1['age'] >= dT - 0.5)
    seeds1 = np.where(orig, reg0, 0)
    reg1 = partition(wet1, seeds1)
    lw1 = _torus_label(wet1)
    P = []
    for j in range(1, n + 1):
        m0 = reg0 == j; m1 = reg1 == j
        V0 = float(h0[m0].sum()); A0 = int(m0.sum()); V1 = float(h1[m1].sum()); A1 = int(m1.sum())
        thk0 = m0 & (h0 >= TH)
        mo = orig & m0; V1o = float(h1[mo].sum()); A1o = int(mo.sum())
        P.append(dict(V0=V0, A0=A0, V1=V1, A1=A1, r=V1 / max(V0, 1e-12), a=A1 / max(A0, 1), s=float((m1 & (h1 < TH)).sum() / max(A1, 1)) if A1 else None,
                      r_o=V1o / max(V0, 1e-12), a_o=A1o / max(A0, 1), s_o=float((mo & (h1 < TH)).sum() / max(A1o, 1)) if A1o else None,
                      thick0=float(h0[thk0].sum()), c0=float((h0 * cf)[thk0].sum() / max(h0[thk0].sum(), 1e-12)) if cf is not None else None,
                      orig_area=int((orig & m0).sum()) / max(A0, 1)))
    L = int(np.argmin([p['r'] for p in P])); W = int(np.argmax([p['r'] for p in P]))
    mL = reg1 == L + 1; mW = reg1 == W + 1
    split = False
    if P[W]['V1'] > 0 and P[L]['V1'] > 0:
        cw = np.bincount(lw1[mW], weights=h1[mW]).argmax()
        split = float(h1[mL & (lw1 != cw)].sum()) >= 0.5 * P[L]['V1']
    persist = conn_parts(S1) is not None
    if split: cls = 'split'
    elif persist: cls = 'persist'
    elif P[L]['a'] <= 0.5: cls = 'merge'
    elif (P[L]['s'] or 0) >= 0.5: cls = 'thin'
    else: cls = 'other'
    # 민감도 변형 (판정 아님): 새로 젖은 칸을 빼고 t0부터 계속 젖어 있던 칸만으로 잰다
    Lo = L      # 진 쪽은 주 방법으로 정한다 (계속 젖은 칸만으로 정하면 앞으로 나아가는 이긴 쪽이 진 쪽으로 잡힌다)
    if split: cls_o = 'split'
    elif persist: cls_o = 'persist'
    elif P[Lo]['a_o'] <= 0.5: cls_o = 'merge'
    elif (P[Lo]['s_o'] or 0) >= 0.5: cls_o = 'thin'
    else: cls_o = 'other'
    dVL = P[L]['V1'] - P[L]['V0']; dVW = P[W]['V1'] - P[W]['V0']
    V = float(h0.sum())
    return dict(n=n, L=L, W=W, cls=cls, cls_o=cls_o, Lo=Lo, parts=P, loser_larger=bool(P[L]['thick0'] > max(p['thick0'] for i, p in enumerate(P) if i != L)),
                loser_toward_food=(bool(P[L]['c0'] > P[W]['c0']) if cf is not None else None),
                dVL_over_V=dVL / V, dVW_over_V=dVW / V, winner_gain_over_loser_loss=(dVW / -dVL if dVL < 0 else None),
                thin_V_frac_t1=float(h1[wet1 & (h1 < TH)].sum() / max(h1.sum(), 1e-12)))


def run(tag, seeds, dts):
    out = []
    for s in seeds:
        rd = rundir('long', s, tag)
        if not os.path.exists(os.path.join(rd, 'metrics.json')): print('빠짐', rd); continue
        cf = food_field(params(rd))
        lst = states(rd); tt = [t for t, _ in lst]; fmap = dict(lst)
        cache = {}
        def get(t):
            if t not in cache: cache[t] = load(fmap[t], KEYS)
            return cache[t]
        flag = {}
        for t in tt:
            if t >= 100 - 20: flag[t] = conn_parts(get(t)) is not None
        starts = [t for t in tt if t >= 100 and flag.get(t) and not flag.get(t - 20, False)]
        for t0 in starts:
            run_len = 0; t = t0
            while flag.get(t): run_len += 1; t += 20
            for dT in dts:
                if t0 + dT not in fmap: continue
                e = episode(get(t0), get(t0 + dT), dT, cf)
                e.update(seed=s, tag=tag, t0=t0, dT=dT, run_states=run_len); out.append(e)
        cache.clear()
        print(tag, s, 'episodes', len(starts), flush=True)
    return out


if __name__ == '__main__':
    a = sys.argv[1:]; dts = (20, 40, 60, 100)
    if '--dt' in a: i = a.index('--dt'); dts = tuple(int(x) for x in a[i + 1].split(',')); a = a[:i] + a[i + 2:]
    tag = a[0]; seeds = [int(x) for x in a[1:]]
    res = run(tag, seeds, dts)
    os.makedirs(os.path.join(VER, 'data'), exist_ok=True)
    json.dump(res, open(os.path.join(VER, 'data', f'fate_{tag}.json'), 'w'), indent=0)
    for dT in dts:
        E = [e for e in res if e['dT'] == dT]
        if not E: continue
        cnt = {c: sum(e['cls'] == c for e in E) for c in ('merge', 'thin', 'persist', 'split', 'other')}
        print(f'Δ={dT}: {len(E)} episodes', cnt)
