#!/usr/bin/env python3
"""[S7 독립 검증] 판정. 기준은 ../CRITERIA.md (실행 전에 적음).

usage: vjudge.py   -> data/judge.json, 화면에 판정 표
먼저: vlong.py (long 40 실행), vfate.py v7c / v7k (long 시드 151~170). food·mig 의 bmet 채점은 없으면 여기서 만든다(data/bmet/).
"""
import json, os, subprocess, sys
import numpy as np
from vcommon import rundir, VER, STAGE0

C, K = 'v7c', 'v7k'
SEEDS = dict(long=range(151, 171), food4=range(151, 159), food3=range(151, 157), asym3=range(151, 155), mig=range(151, 157))
BM = os.path.join(VER, 'data', 'bmet')


def verdict(conf, refu):
    return '확인' if conf else ('반박' if refu else '판정 못 함')


def bm(scn, s, tag):
    rd = rundir(scn, s, tag); f = os.path.join(BM, f'numpy_b_{scn}_s{s}_{tag}.json')
    if not os.path.exists(f) and os.path.exists(os.path.join(rd, 'metrics.json')):
        os.makedirs(BM, exist_ok=True)
        subprocess.run([sys.executable, os.path.join(STAGE0, 'metrics', 'bmet.py'), rd, '--out', BM], capture_output=True)
    return json.load(open(f)) if os.path.exists(f) else None


def longrows(s, tag):
    f = os.path.join(VER, 'data', 'long', f'b_long_s{s}_{tag}.json')
    return json.load(open(f)) if os.path.exists(f) else None


def lstat(o):
    r = [x for x in o['rows'] if x['t'] >= 100]; late = [x for x in r if x['t'] >= 1600]; mid = [x for x in r if x['t'] >= 400]
    return dict(split=float(np.mean([x['out'] >= 0.10 for x in r])), piece_max=float(max(x['piece'] for x in r)),
                nbig2=float(np.mean([x['nbig'] >= 2 for x in r])), conn2=float(np.mean([x['conn2'] for x in r])), lobe2=float(np.mean([x['nlobe'] >= 2 for x in r])), fan2=float(np.mean([x['nfan'] >= 2 for x in r])),
                lobe2_r1=float(np.mean([x['nlobe1'] >= 2 for x in r])), lobe2_r3=float(np.mean([x['nlobe3'] >= 2 for x in r])),
                thin_late=float(np.mean([x['thin'] for x in late])), thin_400=float(np.mean([x['thin'] for x in mid])), thin_vol=float(np.mean([x['thin_vol'] for x in mid])),
                debris=float(np.mean([x['debris'] for x in r])), area_end=o['rows'][-1]['area'], out_mean=float(np.mean([x['out'] for x in r])),
                ncomp_late=float(np.mean([x['ncomp'] for x in late])), lab_ok=all(o['lab_check']))


def main():
    R = dict(G={}, long={}, notes={})
    # ---------------- 주장 1, 2a, 5 (long)
    P = []
    for s in SEEDS['long']:
        c, k = longrows(s, C), longrows(s, K)
        if c and k: P.append((s, lstat(c), lstat(k)))
    R['long'] = {f's{s}': dict(ctrl=c, cand=k) for s, c, k in P}
    n = len(P); R['n_long_pairs'] = n
    print(f'long 쌍 {n}')
    for s, c, k in P:
        print(f"s{s}: 갈라짐 {c['split']:.2f}->{k['split']:.2f} | 조각최대 {c['piece_max']:.3f}->{k['piece_max']:.3f} | 큰덩어리≥2 {c['nbig2']:.2f}->{k['nbig2']:.2f}"
              f" | 엽≥2 {c['lobe2']:.2f}->{k['lobe2']:.2f} | 부채≥2 {c['fan2']:.2f}->{k['fan2']:.2f} | 늦은얇은칸 {c['thin_late']:.0f}->{k['thin_late']:.0f} | 찌꺼기 {c['debris']:.3f}->{k['debris']:.3f} | 끝넓이 {c['area_end']}->{k['area_end']}")
    if n == 20:
        mean = lambda key, i: float(np.mean([p[i][key] for p in P]))
        sm = lambda key: sum(k[key] < c[key] for _, c, k in P); lg = lambda key: sum(k[key] > c[key] for _, c, k in P)
        g = {}
        cm, km = mean('split', 1), mean('split', 2)
        g['1a'] = dict(ctrl=cm, cand=km, smaller=sm('split'), larger=lg('split'), verdict=verdict(km <= 0.5 * cm and sm('split') >= 14, km >= 0.8 * cm or lg('split') >= 10))
        nk = sum(k['piece_max'] < 0.10 for _, _, k in P); nc = sum(c['piece_max'] < 0.10 for _, c, _ in P)
        g['1b'] = dict(ctrl=nc, cand=nk, verdict=verdict(nk >= 14 and nk >= nc + 6, nk <= 8 or nk <= nc + 2))
        cm, km = mean('nbig2', 1), mean('nbig2', 2)
        g['1c'] = dict(ctrl=cm, cand=km, smaller=sm('nbig2'), larger=lg('nbig2'), verdict=verdict(km <= 0.5 * cm and sm('nbig2') >= 14, km >= 0.8 * cm))
        cm, km = mean('lobe2', 1), mean('lobe2', 2)
        g['2a'] = dict(ctrl=cm, cand=km, smaller=sm('lobe2'), larger=lg('lobe2'), verdict=verdict(km <= 0.5 * cm, km >= 0.8 * cm))
        cm, km = mean('fan2', 1), mean('fan2', 2)
        g["2a'"] = dict(ctrl=cm, cand=km, smaller=sm('fan2'), larger=lg('fan2'), verdict=verdict(km <= 0.5 * cm, km >= 0.8 * cm))
        g['2a_sens'] = dict(r1_ctrl=mean('lobe2_r1', 1), r1_cand=mean('lobe2_r1', 2), r3_ctrl=mean('lobe2_r3', 1), r3_cand=mean('lobe2_r3', 2))
        tc, tk = mean('thin_late', 1), mean('thin_late', 2); dc, dk = mean('debris', 1), mean('debris', 2)
        g['5'] = dict(thin_ctrl=tc, thin_cand=tk, thin_ratio=tk / tc, thin_larger=lg('thin_late'), debris_ctrl=dc, debris_cand=dk, debris_ratio=dk / dc, debris_larger=lg('debris'),
                      thin400_ratio=mean('thin_400', 2) / mean('thin_400', 1), thinvol_ctrl=mean('thin_vol', 1), thinvol_cand=mean('thin_vol', 2),
                      area_end_ctrl=mean('area_end', 1), area_end_cand=mean('area_end', 2), ncomp_late_ctrl=mean('ncomp_late', 1), ncomp_late_cand=mean('ncomp_late', 2),
                      verdict=verdict(tk / tc <= 1.25 and dk / dc <= 1.25, tk / tc >= 1.5 or dk / dc >= 1.5))
        g['extra'] = dict(conn2_ctrl=mean('conn2', 1), conn2_cand=mean('conn2', 2), out_mean_ctrl=mean('out_mean', 1), out_mean_cand=mean('out_mean', 2),
                          lab_ok=all(c['lab_ok'] and k['lab_ok'] for _, c, k in P))
        R['G'].update(g)
    # ---------------- 주장 2b (에피소드)
    fates = {}
    for tag in (C, K):
        f = os.path.join(VER, 'data', f'fate_{tag}.json')
        if os.path.exists(f): fates[tag] = json.load(open(f))
    if K in fates:
        tab = {}
        for tag, E in fates.items():
            for dT in sorted(set(e['dT'] for e in E)):
                Ed = [e for e in E if e['dT'] == dT]
                cnt = {c: sum(e['cls'] == c for e in Ed) for c in ('merge', 'thin', 'persist', 'split', 'other')}
                gl = [e['winner_gain_over_loser_loss'] for e in Ed if e['winner_gain_over_loser_loss'] is not None]
                tab[f'{tag}_{dT}'] = dict(n=len(Ed), **cnt, loser_larger=sum(e['loser_larger'] for e in Ed),
                                          loser_toward_food=sum(bool(e['loser_toward_food']) for e in Ed),
                                          rL_med=float(np.median([e['parts'][e['L']]['r'] for e in Ed])) if Ed else None,
                                          aL_med=float(np.median([e['parts'][e['L']]['a'] for e in Ed])) if Ed else None,
                                          gain_over_loss_med=float(np.median(gl)) if gl else None)
        R['fate'] = tab
        Ek = [e for e in fates[K] if e['dT'] == 60]; ne = len(Ek)
        if ne >= 8:
            mg = sum(e['cls'] == 'merge' for e in Ek) / ne; th = sum(e['cls'] == 'thin' for e in Ek) / ne
            v2b = verdict(mg >= 0.6 and th <= 0.2, mg <= 0.3 or th >= 0.4)
        else:
            mg = th = None; v2b = '판정 못 함'
        R['G']['2b'] = dict(n=ne, merge=mg, thin=th, verdict=v2b)
        for k_, v in tab.items(): print('운명', k_, v)
    # ---------------- 주장 3
    F = [(scn, s, bm(scn, s, C), bm(scn, s, K)) for scn in ('food3', 'asym3') for s in SEEDS[scn]]
    F = [x for x in F if x[2] and x[3]]
    if len(F) == 10:
        pc = sum(bool(c['pass']) for *_, c, _ in F); pk = sum(bool(k['pass']) for *_, _, k in F)
        late = [(scn, s, i, a, b) for scn, s, c, k in F for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if a is not None and (b is None or b > a + 50)]
        early = [(scn, s, i, a, b) for scn, s, c, k in F for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if b is not None and (a is None or a > b + 50)]
        for scn, s, c, k in F: print(f"{scn} s{s}: 통과 {c['pass']}->{k['pass']} 닿음 {c['t_touch']}->{k['t_touch']} 몸최소 {c['body_min']}->{k['body_min']}")
        R['G']['3near'] = dict(ctrl_pass=pc, cand_pass=pk, late=late, early=early, verdict=verdict(pk >= pc - 1 and len(late) <= 1, pk <= pc - 3 or len(late) >= 3))
    F4 = [(s, bm('food4', s, C), bm('food4', s, K)) for s in SEEDS['food4']]; F4 = [x for x in F4 if x[1] and x[2]]
    if len(F4) == 8:
        rc = sum(bool(c['reached']) for _, c, _ in F4); rk = sum(bool(k['reached']) for _, _, k in F4)
        late = [(s, i, a, b) for s, c, k in F4 for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if a is not None and (b is None or b > a + 50)]
        early = [(s, i, a, b) for s, c, k in F4 for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if b is not None and (a is None or a > b + 50)]
        for s, c, k in F4: print(f"food4 s{s}: 모두닿음 {c['reached']}->{k['reached']} 닿음 {c['t_touch']}->{k['t_touch']} 몸밖최대 {c['out_frac']}->{k['out_frac']} 통과 {c['pass']}->{k['pass']}")
        R['G']['3food4'] = dict(ctrl_reached=rc, cand_reached=rk, late=late, early=early, ctrl_pass=sum(bool(c['pass']) for _, c, _ in F4), cand_pass=sum(bool(k['pass']) for _, _, k in F4),
                                verdict=verdict(rk >= rc - 1 and len(late) - len(early) <= 1, rk <= rc - 3 or len(late) - len(early) >= 4))
    M = [(s, bm('mig', s, C), bm('mig', s, K)) for s in SEEDS['mig']]; M = [x for x in M if x[1] and x[2]]
    if len(M) == 6:
        tt = [(s, c['t_touch'][0], k['t_touch'][0]) for s, c, k in M]
        ok = sum(1 for _, a, b in tt if a is not None and b is not None and abs(b - a) <= 0.15 * a) + sum(1 for _, a, b in tt if a is None and b is None)
        lost = sum(1 for _, a, b in tt if a is not None and b is None)
        bad = sum(1 for _, a, b in tt if a is not None and (b is None or b > 1.25 * a))
        dc = float(np.mean([c['disp300'] for _, c, _ in M])); dk = float(np.mean([k['disp300'] for _, _, k in M]))
        for s, c, k in M: print(f"mig s{s}: 닿음 {c['t_touch']}->{k['t_touch']} disp300 {c['disp300']}->{k['disp300']} veinT {c.get('veinT')}->{k.get('veinT')}")
        R['G']['3mig'] = dict(touch=tt, within15=ok, lost=lost, bad=bad, disp_ctrl=dc, disp_cand=dk,
                              verdict=verdict(ok >= 5 and lost == 0 and dk >= 0.85 * dc, bad >= 2 or dk < 0.7 * dc))
    # ---------------- 주장 4
    mets = {}
    for scn, ss in SEEDS.items():
        for s in ss:
            for tag in (C, K):
                f = os.path.join(rundir(scn, s, tag), 'metrics.json')
                if os.path.exists(f):
                    m = json.load(open(f)); mets[(scn, s, tag)] = dict(neg=m['neg_end_steps'], negc=m['neg_end_cellsteps'], me=m['mass_err_max'], hmin=m['h_min_seen'],
                                                                       hmin_end=m['h_min_end_of_step'], sup=m.get('sup_updates'), stop=m['stop'], steps=m['steps_done'], crumb=m.get('V_crumb'))
    R['runs4'] = {f'{a}_s{b}_{c}': v for (a, b, c), v in mets.items()}
    nC = [v for (a, b, c), v in mets.items() if c == C]; nK = [v for (a, b, c), v in mets.items() if c == K]
    if len(nC) == 44 and len(nK) == 44:
        negc = sum(v['neg'] > 0 for v in nC); negk = sum(v['neg'] > 0 for v in nK); mec = max(v['me'] for v in nC); mek = max(v['me'] for v in nK)
        R['G']['4'] = dict(ctrl_neg_runs=negc, cand_neg_runs=negk, ctrl_mass_err=mec, cand_mass_err=mek, ctrl_hmin_in=min(v['hmin'] for v in nC), cand_hmin_in=min(v['hmin'] for v in nK),
                           ctrl_inneg_runs=sum(v['hmin'] < 0 for v in nC), cand_inneg_runs=sum(v['hmin'] < 0 for v in nK),
                           ctrl_stop=[v['stop'] for v in nC if v['stop']], cand_stop=[v['stop'] for v in nK if v['stop']],
                           verdict=verdict(negk <= negc and mek < 1e-10 and mek <= 10 * mec, negk >= negc + 2 or mek >= 1e-10))
        R['sup_updates'] = {f'{a}_s{b}': v['sup'] for (a, b, c), v in mets.items() if c == K}
    else:
        R['notes']['claim4'] = f'실행 수 {len(nC)}, {len(nK)}'
    # ---------------- 주장별 판정
    def comb(keys):
        vs = [R['G'].get(k, {}).get('verdict') for k in keys]
        if any(v is None for v in vs): return '실행이 모자람'
        return '맞음' if all(v == '확인' for v in vs) else ('틀림' if any(v == '반박' for v in vs) else '판정 못 함')
    # 주장 2 (CRITERIA_CHANGES.md 2): 2b 반박이면 틀림. 아니면 2a 와 2a′ 가 같으면 그 판정, 다르면 2a 자리는 판정 못 함
    va, vf, vb = R['G'].get('2a', {}).get('verdict'), R['G'].get("2a'", {}).get('verdict'), R['G'].get('2b', {}).get('verdict')
    if None in (va, vf, vb): c2 = '실행이 모자람'
    elif vb == '반박': c2 = '틀림'
    else:
        vA = va if va == vf else '판정 못 함'
        c2 = '맞음' if (vA == '확인' and vb == '확인') else ('틀림' if '반박' in (vA, vb) else '판정 못 함')
    R['claim2_slot2a'] = (va if va == vf else '판정 못 함') if None not in (va, vf) else None
    R['claims'] = {'1': comb(['1a', '1b', '1c']), '2': c2, '2_pre_registered_only': comb(['2a', '2b']), '3': comb(['3near', '3food4', '3mig']), '4': comb(['4']), '5': comb(['5'])}
    print()
    for g in sorted(R['G']):
        v = R['G'][g]; print(g, v.get('verdict'), {kk: (round(x, 4) if isinstance(x, float) else x) for kk, x in v.items() if kk != 'verdict' and not isinstance(x, (list, dict))})
    print('주장', R['claims'])
    json.dump(R, open(os.path.join(VER, 'data', 'judge.json'), 'w'), indent=1, ensure_ascii=False, default=float)


if __name__ == '__main__':
    main()
