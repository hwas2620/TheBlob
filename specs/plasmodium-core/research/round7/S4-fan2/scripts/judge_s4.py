#!/usr/bin/env python3
"""[7차 S4] 전진면 경쟁 둘째 시험(R4b) 판정. 기준은 ../CRITERIA.md (실행 전에 커밋).

usage: judge_s4.py [--json FILE]
먼저: bmet.py 로 ref/runs/b_*_s{61..70}_{vs4c,vs4k} 를 ../summaries 에 채점해 둔다.
"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'stage0'))
sys.path.insert(0, os.path.join(STAGE0, 'metrics')); import vmet
sys.path.insert(0, os.path.join(STAGE0, 'ref')); from ref_model import _torus_label
REF = os.path.join(STAGE0, 'ref', 'runs'); SUM = os.path.join(HERE, '..', 'summaries')
C, K = 'vs4c', 'vs4k'
SEEDS = dict(long=range(61, 71), mig=range(61, 65), food3=range(61, 65), asym3=(61, 62), food4=range(61, 67))


def bm(scn, s, tag):
    f = os.path.join(SUM, f'numpy_b_{scn}_s{s}_{tag}.json')
    return json.load(open(f)) if os.path.exists(f) else None


def long_stats(rd):
    """저장 상태마다 몸 밖(정맥 간선 덩어리 기준)과 두 부채 상태(두께 > 0.3 덩어리 중 부피 15% 이상이 둘 이상)."""
    out, two, ts = [], [], []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); wet = Z['wet'].astype(bool); h = Z['h'].astype(float); N = wet.shape[0]
        src, dst, cc, kk = vmet.edge_list(Z['C'].astype(float), wet); nc, lab = vmet.comps(src, dst, N * N); w = wet.ravel()
        vol = np.bincount(lab[w], weights=h.ravel()[w], minlength=nc); out.append(float(1 - vol.max() / vol.sum()))
        lt = _torus_label(wet & (h > 0.3)); vt = np.bincount(lt.ravel(), weights=np.where(lt > 0, h, 0.0).ravel())[1:]
        two.append(int((vt >= 0.15 * h[wet].sum()).sum() >= 2))
        ts.append(float(os.path.basename(f)[4:-4]) if os.path.basename(f)[4:-4].replace('.', '').isdigit() else len(ts) * 20.0)
    dtv = float(np.median(np.diff(ts))) if len(ts) > 1 else 20.0
    run = best = 0
    for x in two:
        run = run + 1 if x else 0; best = max(best, run)
    return dict(n_states=len(out), split_frac=float(np.mean([x >= 0.10 for x in out])), out_mean=float(np.mean(out)),
                two_longest=best * dtv, two_frac=float(np.mean(two)), dt_state=dtv)


def verdict(conf, refu):
    return '확인' if conf else ('반박' if refu else '판정 못 함')


def main():
    R = dict(runs={}, G={})
    # ---- long: G1 G2 G3
    P = []
    for s in SEEDS['long']:
        rc, rk = os.path.join(REF, f'b_long_s{s}_{C}'), os.path.join(REF, f'b_long_s{s}_{K}')
        if not (os.path.exists(os.path.join(rc, 'metrics.json')) and os.path.exists(os.path.join(rk, 'metrics.json'))):
            print(f'빠짐: long s{s}'); continue
        c, k = long_stats(rc), long_stats(rk); bc, bk = bm('long', s, C) or {}, bm('long', s, K) or {}
        c['out_max'] = bc.get('out_frac'); k['out_max'] = bk.get('out_frac')
        P.append((s, c, k)); R['runs'][f'long_s{s}'] = dict(ctrl=c, cand=k)
        print(f"long s{s}: 갈라진 시간 {c['split_frac']:.2f} → {k['split_frac']:.2f} | 두 부채 최장 {c['two_longest']:.0f} → {k['two_longest']:.0f} 시간"
              f" | 몸 밖 최대 {c['out_max']} → {k['out_max']} | 몸 밖 시간평균 {c['out_mean']:.3f} → {k['out_mean']:.3f}")
    if len(P) == 10:
        cm = np.mean([c['split_frac'] for _, c, _ in P]); km = np.mean([k['split_frac'] for _, _, k in P])
        smaller = sum(k['split_frac'] < c['split_frac'] for _, c, k in P); larger = sum(k['split_frac'] > c['split_frac'] for _, c, k in P)
        R['G']['G1'] = dict(ctrl_mean=cm, cand_mean=km, smaller=smaller, larger=larger,
                            verdict=verdict(km <= 0.5 * cm and smaller >= 7, km >= cm or larger >= 6))
        n60 = sum(k['two_longest'] <= 60 for _, _, k in P); n120 = sum(k['two_longest'] > 120 for _, _, k in P)
        R['G']['G2'] = dict(cand_le60=n60, cand_gt120=n120, ctrl_le60=sum(c['two_longest'] <= 60 for _, c, _ in P), verdict=verdict(n60 >= 7, n120 >= 5))
        n10 = sum((k['out_max'] is not None and k['out_max'] < 0.10) for _, _, k in P)
        R['G']['G3'] = dict(cand_lt010=n10, ctrl_lt010=sum((c['out_max'] is not None and c['out_max'] < 0.10) for _, c, _ in P), verdict=verdict(n10 >= 5, n10 <= 1))
    else:
        R['G']['G1'] = R['G']['G2'] = R['G']['G3'] = dict(verdict='실행이 모자람')
    # ---- mig: G4
    keys = (('t_touch', +1), ('disp300', -1), ('veinT', -1), ('vein4', -1), ('gross_net', -1))   # +1: 크면 나쁨, -1: 작으면 나쁨
    def val(o, kk):
        v = o.get(kk); return (v[0] if v else None) if isinstance(v, list) else v
    M = [(s, bm('mig', s, C), bm('mig', s, K)) for s in SEEDS['mig']]
    if all(c and k for _, c, k in M):
        g4 = {}; conf = True; refu = False
        for kk, bad in keys:
            cv = [val(c, kk) for _, c, _ in M]; kv = [val(k, kk) for _, _, k in M]
            if any(x is None for x in cv + kv): g4[kk] = dict(note='값 없음'); conf = False; continue
            w = max(cv) - min(cv); lo, hi = min(cv) - w / 2, max(cv) + w / 2; inb = sum(lo <= x <= hi for x in kv)
            worse = (np.mean(kv) > np.mean(cv)) if bad > 0 else (np.mean(kv) < np.mean(cv))
            g4[kk] = dict(ctrl=cv, cand=kv, band=[lo, hi], inside=inb)
            conf &= inb >= 3; refu |= (inb == 0 and worse)
            print(f"mig {kk:9s} 대조 {['%.3g' % x for x in cv]} 후보 {['%.3g' % x for x in kv]} 띠 [{lo:.3g}, {hi:.3g}] 안 {inb}/4")
        g4['verdict'] = verdict(conf, refu); R['G']['G4'] = g4
    else:
        R['G']['G4'] = dict(verdict='실행이 모자람')
    # ---- food3 + asym3: G5
    F = [(scn, s, bm(scn, s, C), bm(scn, s, K)) for scn in ('food3', 'asym3') for s in SEEDS[scn]]
    if all(c and k for *_, c, k in F):
        same = sum((c['pass'] == k['pass']) and (c['thick'] == k['thick']) for *_, c, k in F)
        lost = sum(c['pass'] for *_, c, _ in F) - sum(k['pass'] for *_, _, k in F)
        late = [(scn, s, i, a, b) for scn, s, c, k in F for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])) if a is not None and (b is None or b > a + 10)]
        for scn, s, c, k in F:
            print(f"{scn} s{s}: 통과 {c['pass']} → {k['pass']}, 굵은 쌍 {c['thick']} → {k['thick']}, 닿음 {c['t_touch']} → {k['t_touch']}")
        R['G']['G5'] = dict(same=same, n=len(F), pass_lost=lost, late=late, verdict=verdict(same >= 5 and not late, lost >= 2))
    else:
        R['G']['G5'] = dict(verdict='실행이 모자람')
    # ---- food4: G6
    F4 = [(s, bm('food4', s, C), bm('food4', s, K)) for s in SEEDS['food4']]
    if all(c and k for _, c, k in F4):
        rc = sum(bool(c['reached']) for _, c, _ in F4); rk = sum(bool(k['reached']) for _, _, k in F4)
        oc = float(np.mean([c['out_frac'] for _, c, _ in F4])); ok = float(np.mean([k['out_frac'] for _, _, k in F4]))
        for s, c, k in F4:
            print(f"food4 s{s}: 모두 닿음 {c['reached']} → {k['reached']}, 닿음 {c['t_touch']} → {k['t_touch']}, 굵은 쌍 {c['thick']} → {k['thick']}, 몸 밖 최대 {c['out_frac']} → {k['out_frac']}")
        R['G']['G6'] = dict(ctrl_reached=rc, cand_reached=rk, ctrl_out=oc, cand_out=ok, verdict=verdict(rk >= rc - 1 and ok <= oc, rk <= rc - 2))
    else:
        R['G']['G6'] = dict(verdict='실행이 모자람')
    # ---- 덧붙임: 음수, 부피
    for tag in (C, K):
        L = [o for o in (json.load(open(f)) for f in glob.glob(os.path.join(SUM, f'numpy_b_*_{tag}.json')))]
        if L:
            print(f"[{tag}] 실행 {len(L)} · 스텝 끝 음수 있는 실행 {sum(1 for o in L if o['neg_end'])} · 스텝 안 최소 {min(o['h_min_in'] for o in L):.3f} · 부피 오차 최대 {max(o['mass_err'] for o in L):.1e}")
    print()
    for g, v in R['G'].items():
        print(g, v.get('verdict'), {k: v[k] for k in v if k not in ('verdict', 'ctrl', 'cand') and not isinstance(v[k], dict)})
    adv = all(R['G'].get(g, {}).get('verdict') == '확인' for g in ('G1', 'G2')) and all(R['G'].get(g, {}).get('verdict') not in ('반박', '실행이 모자람') for g in ('G4', 'G5', 'G6'))
    R['advance'] = adv; print('다음 단계(독립 검증)로:', '간다' if adv else '가지 않는다')
    if '--json' in sys.argv:
        json.dump(R, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1, ensure_ascii=False, default=float)


if __name__ == '__main__':
    main()
