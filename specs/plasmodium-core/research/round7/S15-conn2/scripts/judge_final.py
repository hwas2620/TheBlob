#!/usr/bin/env python3
"""[7차 S15] 결승 판정 (찢어지지 않는 몸, 마르는 칸 덩어리 단위 + 전체 연결 오그라듦 + 묶은 S7). 기준은 ../CRITERIA.md (실행 전에 커밋).
S14 judge_final.py를 바탕으로, 시드(231~240)와 대조 꼬리표(s15c)를 바꾸고, G5에 늦음 수를 더했다.
관문 아닌 기록: food4 먹이별 평균 늦음, 처음 닿은 것이 떨어진 조각이었던 수, long 끝 덩이 수.

usage: judge_final.py s15dc [--ctrl s15c] [--json FILE]
실행은 ../model/runs/b_*_s{231..240}_{ctrl,CAND}. bmet.py 채점은 ../summaries 에 만든다.
"""
import json, os, sys, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'stage0'))
REF = os.path.join(HERE, '..', 'model', 'runs'); SUM = os.path.join(HERE, '..', 'summaries'); MET = os.path.join(STAGE0, 'metrics')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S4-fan2', 'scripts')); from judge_s4 import long_stats
import glob
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import _torus_label, RING, nb
SEEDS = dict(long=range(231, 241), mig=range(231, 235), food3=range(231, 235), asym3=(231, 232), food4=range(231, 241))


def extra_long(rd):
    """t >= 100 저장 상태에서: 두꺼운 몸(h >= 0.3)의 큰 덩어리(몸 부피의 10% 이상)가 둘 이상인 몫, t >= 1600 얇은 젖은 칸(h < 0.3) 수의 평균,
    가장 큰 젖은 덩어리 밖의 덩어리 하나가 가진 부피 몫의 최대(작은 조각 여럿의 합이 아니라 조각 하나)."""
    nb2 = []; thin = []; piece = 0.0; outl = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); t = float(Z['t'])
        if t < 100: continue
        wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); V = h.sum()
        lt = _torus_label(wet & (h >= 0.3)); vt = np.bincount(lt.ravel(), weights=h.ravel()); vt[0] = 0; nb2.append(int((vt >= 0.1 * V).sum() >= 2))
        if t >= 1600: thin.append(int((wet & (h < 0.3)).sum()))
        lw = _torus_label(wet); vw = np.sort(np.bincount(lw.ravel(), weights=h.ravel())[1:])[::-1]
        if len(vw) > 1: piece = max(piece, float(vw[1] / V))
        if t >= 1600: outl.append(float(1 - vw[0] / V))
    Z = np.load(os.path.join(rd, 'vs_t2000.npz')); w = Z['wet'].astype(bool); hh = np.where(w, Z['h'].astype(float), 0.0)
    xb = [~nb(w, d) for d in RING]; Nc = np.zeros(w.shape, np.int8)
    for q in (0, 2, 4, 6): Nc += xb[q].astype(np.int8) - (xb[q] & xb[q + 1] & xb[(q + 2) % 8]).astype(np.int8)
    th = w & (hh >= 0.3); lt = _torus_label(th); vt = np.bincount(lt.ravel(), weights=hh.ravel()); vt[0] = 0; big = lt == vt.argmax()
    per = int((big & ~(nb(big, (1, 0)) & nb(big, (-1, 0)) & nb(big, (0, 1)) & nb(big, (0, -1)))).sum())
    core = w.copy()      # [S15] 끝 덩이 수: 젖은 칸을 한 칸 깎아(8이웃이 모두 젖은 칸만 남김) 관을 지운 뒤, 몸 부피의 5% 이상을 가진 덩어리 수
    for d in RING: core &= nb(w, d)
    lc = _torus_label(core); vc = np.bincount(lc.ravel(), weights=hh.ravel()); vc[0] = 0
    return dict(nbig2=float(np.mean(nb2)), thin_late=float(np.mean(thin)) if thin else 0.0, piece_max=piece, out_late=float(np.mean(outl)),
                line_end=int((w & (Nc > 1)).sum()), thread_end=int((w & (hh < 0.3) & (Nc > 1)).sum()), ncomp_end=int(_torus_label(w).max()),
                round_end=float(per / np.sqrt(max(big.sum(), 1))), lumps_end=int((vc >= 0.05 * hh.sum()).sum()))


def bm(scn, s, tag):
    f = os.path.join(SUM, f'numpy_b_{scn}_s{s}_{tag}.json'); rd = os.path.join(REF, f'b_{scn}_s{s}_{tag}')
    if not os.path.exists(f) and os.path.exists(os.path.join(rd, 'metrics.json')):
        subprocess.run([sys.executable, os.path.join(MET, 'bmet.py'), rd, '--out', SUM], capture_output=True)
    return json.load(open(f)) if os.path.exists(f) else None


def touch_by_piece(s, i, tag):
    """food4 먹이 i에 처음 닿은 뒤 첫 저장 상태(20 시간마다)에서, 먹이 원(반지름 5) 안의 젖은 칸이 가장 큰 젖은 덩어리에 없고 다른 덩어리에만 있으면 1."""
    rd = os.path.join(REF, f'b_food4_s{s}_{tag}'); m = json.load(open(os.path.join(rd, 'metrics.json'))); tt = m['t_touch'][i]
    if tt is None: return 0
    f = os.path.join(rd, f'vs_t{int(np.ceil(tt / 20) * 20):04d}.npz')
    if not os.path.exists(f): return 0
    Z = np.load(f); w = Z['wet'].astype(bool); h = np.where(w, Z['h'].astype(float), 0.0); N = w.shape[0]; fx, fy = m['foods'][i]
    Y, X = np.mgrid[0:N, 0:N]; mi = lambda d: (d + N / 2) % N - N / 2; disc = (np.hypot(mi(X - fx), mi(Y - fy)) < 5.0) & w      # food_r = 5 (export_ref.py FOOD)
    lw = _torus_label(w); v = np.bincount(lw.ravel(), weights=h.ravel()); v[0] = 0; labs = set(np.unique(lw[disc]).tolist()) - {0}
    return int(bool(labs) and int(v.argmax()) not in labs)


def verdict(conf, refu):
    return '확인' if conf else ('반박' if refu else '판정 못 함')


def judge(C, K):
    R = dict(cand=K, ctrl=C, runs={}, G={})
    print(f'\n===== 후보 {K} (대조 {C}) =====')
    # ---- long: G1 갈라진 시간, G2 몸 밖 최대
    P = []
    for s in SEEDS['long']:
        rc, rk = os.path.join(REF, f'b_long_s{s}_{C}'), os.path.join(REF, f'b_long_s{s}_{K}')
        bc, bk = bm('long', s, C), bm('long', s, K)
        if not (bc and bk): print(f'빠짐: long s{s}'); continue
        sf = os.path.join(SUM, f'long_stats_s{s}_{{}}.json')
        def ls(rd, tag):
            f = sf.format(tag)
            if not os.path.exists(f): json.dump(long_stats(rd), open(f, 'w'))
            return json.load(open(f))
        c, k = ls(rc, C), ls(rk, K); c['out_max'] = bc['out_frac']; k['out_max'] = bk['out_frac']; c['area_end'] = bc['area_end']; k['area_end'] = bk['area_end']
        ef = os.path.join(SUM, f'long_extra3_s{s}_{{}}.json')
        for o, rd_, tg in ((c, rc, C), (k, rk, K)):
            if not os.path.exists(ef.format(tg)): json.dump(extra_long(rd_), open(ef.format(tg), 'w'))
            o.update(json.load(open(ef.format(tg))))
        P.append((s, c, k)); R['runs'][f'long_s{s}'] = dict(ctrl=c, cand=k)
        print(f"long s{s}: 큰 덩어리 ≥2 {c['nbig2']:.2f} → {k['nbig2']:.2f} | 떨어진 조각 하나 최대 {c['piece_max']:.3f} → {k['piece_max']:.3f} | 늦은 얇은 넓이 {c['thin_late']:.0f} → {k['thin_late']:.0f}")
        print(f"long s{s}: 갈라진 시간 {c['split_frac']:.2f} → {k['split_frac']:.2f} | 몸 밖 최대 {c['out_max']:.3f} → {k['out_max']:.3f} | 늦은 몸 밖 {c['out_late']:.3f} → {k['out_late']:.3f} | 끝 줄 칸 {c['line_end']} → {k['line_end']} (실 {c['thread_end']} → {k['thread_end']}) | 끝 넓이 {c['area_end']} → {k['area_end']} | 끝 덩어리 {c['ncomp_end']} → {k['ncomp_end']} | 둘레/√넓이 {c['round_end']:.1f} → {k['round_end']:.1f}")
    if len(P) == len(SEEDS['long']):
        mean = lambda key, j: float(np.mean([x[j][key] for x in P]))
        cm, km = mean('split_frac', 1), mean('split_frac', 2); worse = sum(k['split_frac'] > c['split_frac'] + 0.05 for _, c, k in P)
        R['G']['F1'] = dict(ctrl_mean=cm, cand_mean=km, worse_pairs=worse, verdict=verdict(km <= 0.5 * cm and worse == 0, km >= cm))
        cm, km = mean('out_late', 1), mean('out_late', 2)
        R['G']['F2'] = dict(ctrl_mean=cm, cand_mean=km, verdict=verdict(km <= 0.5 * cm, km >= cm))
        cm, km = mean('nbig2', 1), mean('nbig2', 2)
        R['G']['F3'] = dict(ctrl_mean=cm, cand_mean=km, verdict=verdict(km <= 0.5 * cm, km >= cm))
        cm, km = mean('thin_late', 1), mean('thin_late', 2)
        R['G']['F4'] = dict(ctrl_mean=cm, cand_mean=km, ratio=km / cm, verdict=verdict(km <= cm, km > 1.3 * cm))
        cm, km = mean('line_end', 1), mean('line_end', 2)
        R['G']['F5'] = dict(ctrl_mean=cm, cand_mean=km, ratio=km / cm, verdict=verdict(km <= cm, km > 1.3 * cm))
        R['extra'] = dict(area_ratio=mean('area_end', 2) / mean('area_end', 1), thread=(mean('thread_end', 1), mean('thread_end', 2)), round_end=(mean('round_end', 1), mean('round_end', 2)), lumps_end=([c['lumps_end'] for _, c, _ in P], [k['lumps_end'] for _, _, k in P]),
                          piece_max_lt010=(sum(c['piece_max'] < 0.10 for _, c, _ in P), sum(k['piece_max'] < 0.10 for _, _, k in P)), ncomp_end_cand=[k['ncomp_end'] for _, _, k in P])
        print(f"(관문 아님) 끝 넓이 {R['extra']['area_ratio']:.2f}배, 끝 실 칸 {R['extra']['thread'][0]:.0f} → {R['extra']['thread'][1]:.0f}, 둘레/√넓이 {R['extra']['round_end'][0]:.1f} → {R['extra']['round_end'][1]:.1f}, 조각 하나 최대 < 0.10 {R['extra']['piece_max_lt010']}, 후보 끝 덩어리 수 {R['extra']['ncomp_end_cand']}")
        print(f"(관문 아님) 끝 덩이 수 (한 칸 깎은 뒤 부피 5% 이상) 대조 {R['extra']['lumps_end'][0]} 후보 {R['extra']['lumps_end'][1]}")
    else:
        R['G']['F1'] = R['G']['F2'] = R['G']['F3'] = R['G']['F4'] = R['G']['F5'] = dict(verdict='실행이 모자람')
    # ---- mig: G3
    keys = (('t_touch', +1), ('disp300', -1), ('veinT', -1), ('vein4', -1), ('gross_net', -1))
    val = lambda o, kk: ((o.get(kk) or [None])[0] if isinstance(o.get(kk), list) else o.get(kk))
    M = [(s, bm('mig', s, C), bm('mig', s, K)) for s in SEEDS['mig']]
    if all(c and k for _, c, k in M):
        g = {}; conf = True; refu = False
        for kk, bad in keys:
            cv = [val(c, kk) for _, c, _ in M]; kv = [val(k, kk) for _, _, k in M]
            if any(x is None for x in cv + kv): g[kk] = dict(note='값 없음'); conf = False; continue
            w = max(cv) - min(cv); lo, hi = min(cv) - w / 2, max(cv) + w / 2; inb = sum(lo <= x <= hi for x in kv)
            worse = (np.mean(kv) > np.mean(cv)) if bad > 0 else (np.mean(kv) < np.mean(cv))
            g[kk] = dict(ctrl=cv, cand=kv, band=[lo, hi], inside=inb); conf &= inb >= 3; refu |= (inb == 0 and worse)
            print(f"mig {kk:9s} 대조 {['%.3g' % x for x in cv]} 후보 {['%.3g' % x for x in kv]} 띠 [{lo:.3g}, {hi:.3g}] 안 {inb}/4")
        g['verdict'] = verdict(conf, refu); R['G']['G3'] = g
    else:
        R['G']['G3'] = dict(verdict='실행이 모자람')
    # ---- food3 + asym3: G4
    F = [(scn, s, bm(scn, s, C), bm(scn, s, K)) for scn in ('food3', 'asym3') for s in SEEDS[scn]]
    if all(c and k for *_, c, k in F):
        pc = sum(bool(c['pass']) for *_, c, _ in F); pk = sum(bool(k['pass']) for *_, _, k in F)
        late = [(scn, s, i, a, b) for scn, s, c, k in F for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if a is not None and (b is None or b > a + 50)]
        for scn, s, c, k in F:
            print(f"{scn} s{s}: 통과 {c['pass']} → {k['pass']}, 굵은 쌍 {c['thick']} → {k['thick']}, 닿음 {c['t_touch']} → {k['t_touch']}")
        R['G']['G4'] = dict(ctrl_pass=pc, cand_pass=pk, late=late, verdict=verdict(pk >= pc and len(late) <= 1, pk <= pc - 2 or len(late) >= 3))
    else:
        R['G']['G4'] = dict(verdict='실행이 모자람')
    # ---- food4: G5
    F4 = [(s, bm('food4', s, C), bm('food4', s, K)) for s in SEEDS['food4']]
    if all(c and k for _, c, k in F4):
        rc = sum(bool(c['reached']) for _, c, _ in F4); rk = sum(bool(k['reached']) for _, _, k in F4)
        oc = float(np.mean([c['out_frac'] for _, c, _ in F4])); ok = float(np.mean([k['out_frac'] for _, _, k in F4]))
        for s, c, k in F4:
            print(f"food4 s{s}: 모두 닿음 {c['reached']} → {k['reached']}, 닿음 {c['t_touch']} → {k['t_touch']}, 몸 밖 최대 {c['out_frac']} → {k['out_frac']}")
        per = [(sum(1 for _, c, _ in F4 if c['t_touch'][i] is None), sum(1 for _, _, k in F4 if k['t_touch'][i] is None)) for i in range(len(F4[0][1]['t_touch']))]
        print(f"(관문 아님) food4 먹이별로 놓친 실행 수 (대조, 후보): {per}")
        late5 = [(s, i, a, b) for s, c, k in F4 for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if a is not None and (b is None or b > a + 50)]
        nfood = len(F4[0][1]['t_touch'])
        delay = [float(np.mean(d)) if (d := [k['t_touch'][i] - c['t_touch'][i] for _, c, k in F4 if c['t_touch'][i] is not None and k['t_touch'][i] is not None]) else None for i in range(nfood)]
        frag = [(sum(touch_by_piece(s, i, C) for s in SEEDS['food4']), sum(touch_by_piece(s, i, K) for s in SEEDS['food4'])) for i in range(nfood)]
        print(f"food4 늦음 (대조가 닿은 먹이를 50 시간 넘게 늦거나 못 닿음): {len(late5)} {late5}")
        print(f"(관문 아님) food4 먹이별 평균 늦음 (둘 다 닿은 쌍, 후보 − 대조): {[None if x is None else round(x, 1) for x in delay]}")
        print(f"(관문 아님) food4 먹이별로 처음 닿은 것이 떨어진 조각인 실행 수 (대조, 후보): {frag}")
        R['G']['G5'] = dict(ctrl_reached=rc, cand_reached=rk, ctrl_out=oc, cand_out=ok, late=late5, delay=delay, frag=frag,
                            verdict=verdict(rk >= rc - 1 and ok <= oc and len(late5) <= 2, rk <= rc - 2 or len(late5) >= 4))
    else:
        R['G']['G5'] = dict(verdict='실행이 모자람')
    # ---- G6: 부피 장부와 스텝 끝 음수
    allk = [bm(scn, s, K) for scn, ss in SEEDS.items() for s in ss]; allc = [bm(scn, s, C) for scn, ss in SEEDS.items() for s in ss]
    if all(allk) and all(allc):
        nk = sum(1 for o in allk if o['neg_end']); nc_ = sum(1 for o in allc if o['neg_end']); mk = max(o['mass_err'] for o in allk)
        mk_ = lambda scn, s: json.load(open(os.path.join(REF, f'b_{scn}_s{s}_{K}', 'metrics.json')))
        crumb = max(mk_(scn, s)['V_crumb'] / mk_(scn, s)['V0'] for scn, ss in SEEDS.items() for s in ss)
        onec = sum(int(_torus_label(np.load(os.path.join(REF, f'b_{scn}_s{s}_{K}', 'wet.npy')).astype(bool)).max()) == 1 for scn, ss in SEEDS.items() for s in ss)
        print(f"[{K}] 버린 부피 최대 {crumb:.2g}, 끝 젖은 덩어리 1개인 실행 {onec}/{len(allk)}")
        print(f"[{K}] 실행 {len(allk)} · 스텝 끝 음수 있는 실행 {nk} (대조 {nc_}) · 스텝 안 최소 {min(o['h_min_in'] for o in allk):.3f} · 부피 오차 최대 {mk:.1e}")
        R['G']['G6'] = dict(cand_neg_runs=nk, ctrl_neg_runs=nc_, mass_err=mk, crumb_max=crumb, one_comp_runs=onec, verdict=verdict(nk == 0 and mk < 1e-10 and crumb < 0.01 and onec == len(allk), nk > nc_ + 1 or mk >= 1e-10 or crumb >= 0.01 or onec < len(allk)))
    else:
        R['G']['G6'] = dict(verdict='실행이 모자람')
    for g in sorted(R['G']):
        v = R['G'][g]; print(g, v.get('verdict'), {kk: v[kk] for kk in v if kk not in ('verdict',) and not isinstance(v[kk], (dict, list))})
    adv = all(R['G'].get(g, {}).get('verdict') == '확인' for g in ('F1', 'F2', 'F3', 'F4', 'F5', 'G6')) and all(R['G'].get(g, {}).get('verdict') not in ('반박', '실행이 모자람') for g in ('G3', 'G4', 'G5'))
    R['advance'] = adv; print('다음 단계(독립 검증)로:', '간다' if adv else '가지 않는다')
    return R


if __name__ == '__main__':
    a = sys.argv[1:]; C = a[a.index('--ctrl') + 1] if '--ctrl' in a else 's15c'; out = a[a.index('--json') + 1] if '--json' in a else None
    cands = [x for i, x in enumerate(a) if not x.startswith('--') and (i == 0 or a[i - 1] not in ('--ctrl', '--json'))]
    res = [judge(C, K) for K in cands]
    if out: json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False, default=float)
