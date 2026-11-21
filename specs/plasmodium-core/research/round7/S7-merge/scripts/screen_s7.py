#!/usr/bin/env python3
"""[7차 S7] 거르기 비교. 조건은 ../SCREEN.md (실행 전에 커밋). usage: screen_s7.py CAND [CAND ...] [--ctrl s6c]"""
import json, os, sys, subprocess, glob
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', 'stage0'))
REF = os.path.join(STAGE0, 'ref', 'runs'); SUM = os.path.join(HERE, '..', 'summaries'); MET = os.path.join(STAGE0, 'metrics')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S4-fan2', 'scripts')); from judge_s4 import long_stats
sys.path.insert(0, os.path.join(STAGE0, 'ref')); from ref_model import _torus_label
os.makedirs(SUM, exist_ok=True)
SEEDS = dict(long=(111, 112, 113), food4=(111, 112), food3=(111, 112), mig=(111, 112), asym3=(111,))
args = [a for a in sys.argv[1:] if not a.startswith('--')]; C = sys.argv[sys.argv.index('--ctrl') + 1] if '--ctrl' in sys.argv else 's6c'
args = [a for a in args if a != C]
def bm(scn, s, tag):
    f = os.path.join(SUM, f'numpy_b_{scn}_s{s}_{tag}.json'); rd = os.path.join(REF, f'b_{scn}_s{s}_{tag}')
    if not os.path.exists(f) and os.path.exists(os.path.join(rd, 'metrics.json')):
        subprocess.run([sys.executable, os.path.join(MET, 'bmet.py'), rd, '--out', SUM], capture_output=True)
    return json.load(open(f)) if os.path.exists(f) else None
def nbig2(rd):
    n = 0; m = 0
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f)
        if float(Z['t']) < 100: continue
        wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'].astype(float), 0.0); th = wet & (h >= 0.3); lt = _torus_label(th)
        v = np.bincount(lt.ravel(), weights=h.ravel()); v[0] = 0; n += int((v >= 0.1 * h.sum()).sum() >= 2); m += 1
    return n / max(m, 1)
def episodes(rd):
    out = os.path.join(SUM, 'compete_' + os.path.basename(rd) + '.json')
    if not os.path.exists(out):
        subprocess.run([sys.executable, os.path.join(HERE, 'diag_compete.py'), rd], env=dict(os.environ, OUT=out), capture_output=True)
    rows = json.load(open(out))[0]['rows']; eps = []; cur = []
    for x in rows + [None]:
        if x is not None and x['same'] and (not cur or x['t'] - cur[-1]['t'] <= 20): cur.append(x); continue
        if len(cur) >= 3: eps.append((cur[0]['t'], cur[-1]['t'], cur[0]['vB'], cur[-1]['vB']))
        cur = [x] if (x is not None and x['same']) else []
    return eps
for K in args:
    print(f'\n===== {K} (대조 {C}) =====')
    sc = []; sk = []; ok1 = True
    for s in SEEDS['long']:
        rc, rk = os.path.join(REF, f'b_long_s{s}_{C}'), os.path.join(REF, f'b_long_s{s}_{K}')
        bc, bk = bm('long', s, C), bm('long', s, K)
        if not (bc and bk): print('빠짐 long', s); ok1 = False; continue
        lc, lk = long_stats(rc), long_stats(rk); nc, nk = nbig2(rc), nbig2(rk); ek = episodes(rk)
        sc.append((lc['split_frac'], nc)); sk.append((lk['split_frac'], nk))
        drop = [e for e in ek if e[3] - e[2] < -0.05]
        print(f"long s{s}: 갈라진 시간 {lc['split_frac']:.2f} → {lk['split_frac']:.2f} | 몸 밖 최대 {bc['out_frac']:.3f} → {bk['out_frac']:.3f} | 큰 덩어리 ≥2 {nc:.2f} → {nk:.2f} | 끝 넓이 {bc['area_end']} → {bk['area_end']} | 이어진 두 덩어리 구간 {len(ek)}개, 작은 쪽이 0.05 넘게 준 구간 {len(drop)}개 {[(int(a), int(b), round(c, 2), round(d, 2)) for a, b, c, d in drop]}")
        mk = json.load(open(os.path.join(rk, 'metrics.json'))); print(f"        규칙 작동 {mk.get('sup_updates')}번, 실행 시간 {mk['runtime']:.0f}s")
    if sc:
        mc, mk_ = np.mean([a for a, _ in sc]), np.mean([a for a, _ in sk]); bc_, bk_ = np.mean([b for _, b in sc]), np.mean([b for _, b in sk])
        print(f"long 평균: 갈라진 시간 {mc:.3f} → {mk_:.3f} (절반 이하? {mk_ <= 0.5 * mc}), 큰 덩어리 ≥2 {bc_:.3f} → {bk_:.3f} (작아짐? {bk_ < bc_})")
    late = []; pc = pk = 0
    for scn in ('food3', 'asym3', 'food4'):
        for s in SEEDS[scn]:
            c, k = bm(scn, s, C), bm(scn, s, K)
            if not (c and k): print('빠짐', scn, s); continue
            if scn != 'food4': pc += bool(c['pass']); pk += bool(k['pass'])
            for i, (a, b) in enumerate(zip(c['t_touch'], k['t_touch'])):
                if a is not None and (b is None or b > a + 50): late.append((scn, s, i, a, b))
            print(f"{scn} s{s}: 통과 {c['pass']} → {k['pass']}, 굵은 쌍 {c['thick']} → {k['thick']}, 닿음 {c['t_touch']} → {k['t_touch']}")
    print(f'가까운 먹이 통과 {pc} → {pk}, 늦거나 못 닿음 {late}')
    for s in SEEDS['mig']:
        c, k = bm('mig', s, C), bm('mig', s, K)
        if c and k:
            tc = c['t_touch'][0] if isinstance(c['t_touch'], list) else c['t_touch']; tk = k['t_touch'][0] if isinstance(k['t_touch'], list) else k['t_touch']
            print(f"mig s{s}: 닿은 시각 {tc} → {tk} ({'±10% 안' if tc and tk and abs(tk - tc) <= 0.1 * tc else '밖'}), disp300 {c.get('disp300')} → {k.get('disp300')}")
    neg = 0; me = 0.0
    for f in glob.glob(os.path.join(REF, f'b_*_s1??_{K}', 'metrics.json')):
        m = json.load(open(f)); neg += m['neg_end_cellsteps'] > 0; me = max(me, m['mass_err_max'])
    print(f'스텝 끝 음수 있는 실행 {neg}, 부피 오차 최대 {me:.2g}')
