#!/usr/bin/env python3
"""verify3 판정. data/frames/*.json.gz (measure.py 출력) 를 읽어 CRITERIA.md 의 규칙대로 판정한다.

usage: judge.py trap    갇힌 시각만 계산해 data/trap.json, fig/trap_F.png 를 쓴다 (덩이 지표를 보기 전에 확인)
       judge.py all     모든 주장을 판정해 data/verdict.json, data/summary_*.json 을 쓰고 표를 출력한다
"""
import sys, os, json, gzip, glob
import numpy as np
from scipy.stats import wilcoxon

V3 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FR = os.path.join(V3, 'data', 'frames')
ARMS = ('x17c', 'x17fs')
SEEDS = dict(long=range(351, 365), food4=range(351, 357), food3=range(351, 359), asym3=range(351, 359), mig=range(351, 359))
HTS = (0.4, 0.5, 0.6, 0.7); MS = (0.05, 0.10, 0.20)
_cache = {}


def load(scn, seed, arm):
    k = (scn, seed, arm)
    if k not in _cache:
        p = os.path.join(FR, f'b_{scn}_s{seed}_{arm}.json.gz')
        _cache[k] = json.load(gzip.open(p, 'rt')) if os.path.exists(p) else None
    return _cache[k]


def wil(d, alt):
    """짝 차이 d (후보 − 대조) 의 Wilcoxon 한쪽 p. alt='less' 면 후보가 작다는 쪽"""
    d = np.asarray(d, float); d = d[np.isfinite(d)]
    if d.size == 0 or np.all(d == 0): return 1.0
    try:
        return float(wilcoxon(d, alternative=alt, zero_method='wilcox').pvalue)
    except ValueError:
        return 1.0


# ───────────────────────── 2절: 갇힌 시각
def trap_one(R, rel=0.3):
    t = np.array([f['t'] for f in R['frames']]); F = np.array([f['F'] for f in R['frames']])
    early = (t >= 100) & (t <= 400); Fe = float(np.median(F[early]))
    Fb = np.array([F[max(0, i - 4):i + 1].mean() for i in range(len(F))])
    idx = np.nonzero((t >= 200) & (Fb < rel * Fe))[0]
    return (float(t[idx[0]]) if idx.size else None), Fe


def trap_U(R, thr=0.15):
    t = np.array([f['t'] for f in R['frames']]); U = np.array([f['U'] for f in R['frames']])
    idx = np.nonzero(U < thr)[0]
    return float(t[idx[0]]) if idx.size else None


def trap_table():
    out = {}
    for s in SEEDS['long']:
        for a in ARMS:
            R = load('long', s, a)
            if R is None: continue
            tt = {}
            for rel in (0.2, 0.3, 0.4):
                tt[f'F{rel}'], Fe = trap_one(R, rel)
            tt['U0.15'] = trap_U(R); tt['F_early'] = Fe
            fr = R['frames']; ti = {f['t']: f for f in fr}
            tp = tt['F0.3']
            tt['U_at_trap'] = ti[tp]['U'] if tp is not None else None
            tt['U_end'] = fr[-1]['U']
            out[f'{s}_{a}'] = tt
    return out


def wins(trap, s, a, Tend=2000.0):
    """창 이름 → (t0, t1) : t0 <= t < t1 이 옮겨 다니는 때"""
    def tv(x): return Tend + 1 if x is None else x
    k = f'{s}_{a}'; o = f'{s}_{"x17fs" if a == "x17c" else "x17c"}'
    return {'primary': (100, tv(trap[k]['F0.3'])), 'F0.2': (100, tv(trap[k]['F0.2'])), 'F0.4': (100, tv(trap[k]['F0.4'])),
            'U0.15': (100, tv(trap[k]['U0.15'])), 'fix800': (100, 800), 'fix1200': (100, 1200),
            'pairmin': (100, min(tv(trap[k]['F0.3']), tv(trap[o]['F0.3'])))}


def trapped_win(trap, s, a, Tend=2000.0):
    tp = trap[f'{s}_{a}']['F0.3']
    return None if tp is None else (tp, Tend + 1)


# ───────────────────────── 주장 2 지표 (판 하나)
def mb_frame(f, ht, m):
    for b in f.get('bodies', []):
        fr = b[f'b{ht}']
        if len(fr) >= 2 and fr[1] >= m: return True
    return False


def db_frame(f, ht, m, wthr):
    for b in f.get('bodies', []):
        fr = b[f'b{ht}']
        if len(fr) >= 2 and fr[1] >= m and b[f'w{ht}'] is not None and b[f'w{ht}'] <= wthr: return True
    return False


def mbgeo_frame(f, m):
    for b in f.get('bodies', []):
        fr = b['geo']
        if len(fr) >= 2 and fr[1] >= m: return True
    return False


def dbgeo_frame(f, m, wthr=2):
    for b in f.get('bodies', []):
        fr = b['geo']
        if len(fr) >= 2 and fr[1] >= m and b['wgeo'] is not None and b['wgeo'] <= wthr: return True
    return False


def win_frames(R, w):
    return [f for f in R['frames'] if w[0] <= f['t'] < w[1]]


def frac(fs, fn):
    return float(np.mean([fn(f) for f in fs])) if fs else np.nan


def meanv(fs, fn):
    v = [fn(f) for f in fs]; v = [x for x in v if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else np.nan


def paired(trap, fn_run, wname='primary'):
    """fn_run(R, w) → 실행 값. 짝마다 (대조, 후보)"""
    c = []; x = []; seeds = []
    for s in SEEDS['long']:
        Rc = load('long', s, 'x17c'); Rx = load('long', s, 'x17fs')
        if Rc is None or Rx is None: continue
        wc = wins(trap, s, 'x17c')[wname]; wx = wins(trap, s, 'x17fs')[wname]
        c.append(fn_run(Rc, wc)); x.append(fn_run(Rx, wx)); seeds.append(s)
    return np.array(c, float), np.array(x, float), seeds


def cmp_stat(c, x, alt='less'):
    d = x - c; ok = np.isfinite(d)
    return dict(ctrl_mean=float(np.nanmean(c)), cand_mean=float(np.nanmean(x)), diff_mean=float(np.nanmean(d)), diff_median=float(np.nanmedian(d)),
                n=int(ok.sum()), n_cand_lower=int((d[ok] < 0).sum()), n_cand_higher=int((d[ok] > 0).sum()), p_less=wil(d[ok], 'less'), p_greater=wil(d[ok], 'greater'))


# ───────────────────────── 주장 1: 부스러기
def crumb_scan(R, c, rel=False):
    """판마다 부스러기 목록 → (부스러기 판 수, 사건 목록[(시작 t, 판 수, 최소 f)])"""
    N = R['N']; evs = []; prev = []; nfr = 0; fmin = None
    frames = R['frames'] + [dict(t=R['metrics']['t_end'] + 0.001, small=R['end']['small'], end=True)]
    off = np.arange(-3, 4)
    for f in frames:
        cur = []
        for p in f['small']:
            v = p['frel'] if rel else p['f']
            if v < c: cur.append(p)
        if cur: nfr += 1
        new_prev = []
        for p in cur:
            if 'dil' not in p:      # 체스판 거리 3 만큼 넓힌 셀 집합 (앞 판의 조각과 같은 조각인지 보는 데 씀)
                ys, xs = np.divmod(np.asarray(p['idx'], np.int64), N)
                yy = (ys[:, None, None] + off[None, :, None]) % N; xx = (xs[:, None, None] + off[None, None, :]) % N
                p['dil'] = np.unique((yy * N + xx).ravel())
            md = p['dil']
            ev = None
            for (pm, e) in prev:
                if np.intersect1d(pm, md, assume_unique=True).size: ev = e; break
            v = p['frel'] if rel else p['f']
            if ev is None:
                ev = [f['t'], 0, v]; evs.append(ev)
            ev[1] += 1; ev[2] = min(ev[2], v)
            fmin = v if fmin is None else min(fmin, v)
            new_prev.append((md, ev))
        prev = new_prev
    return nfr, evs, fmin


def claim1():
    res = {}; rows = []
    for c in (0.01, 0.02, 0.03, 0.05, 0.10):
        for rel in (False, True):
            key = f'c{c}' + ('_rel' if rel else '')
            for a in ARMS:
                tot_fr = 0; nev = 0; maxlife = 0; fmin = None; runs_with = []
                for scn, ss in SEEDS.items():
                    for s in ss:
                        R = load(scn, s, a)
                        if R is None: continue
                        nfr, evs, fm = crumb_scan(R, c, rel)
                        tot_fr += nfr; nev += len(evs)
                        if evs: runs_with.append(f'{scn}_{s}'); maxlife = max(maxlife, max(e[1] for e in evs))
                        if fm is not None: fmin = fm if fmin is None else min(fmin, fm)
                res[f'{key}_{a}'] = dict(crumb_frames=tot_fr, events=nev, max_life_frames=maxlife, f_min=fmin, runs=runs_with)
    # 판정 (후보, 기본 c = 5%, 전체 부피 기준)
    x5 = res['c0.05_x17fs']; x2 = res['c0.02_x17fs']
    if x5['crumb_frames'] == 0: v = '맞음'
    elif x2['crumb_frames'] > 0 or x5['max_life_frames'] >= 2: v = '틀림'
    else: v = '판정 못 함'
    return v, res


# ───────────────────────── 주장 3 지표
def c3v(f, kind, key, per_area=False):
    c = f.get('c3')
    if c is None: return None
    if kind == 'film': return c['film'][key]
    v = c['dead_thr' if kind == 'thr' else 'dead_tip'][key]
    return v / c['area'] if per_area else v


def run_val_c3(kind, key, per_area=False):
    return lambda R, w: meanv(win_frames(R, w), lambda f: c3v(f, kind, key, per_area))


def verdict_dir(st, variants_ok_frac, alpha=0.05):
    if st['cand_mean'] >= st['ctrl_mean']: return '틀림'
    if st['p_less'] < alpha and variants_ok_frac >= 0.75: return '맞음'
    return '판정 못 함'


def claim2(trap):
    out = {}
    prim = paired(trap, lambda R, w: frac(win_frames(R, w), lambda f: mb_frame(f, 0.5, 0.10)))
    dbp = paired(trap, lambda R, w: frac(win_frames(R, w), lambda f: db_frame(f, 0.5, 0.10, 2)))
    out['MB_primary'] = cmp_stat(prim[0], prim[1]); out['MB_primary']['per_seed'] = dict(zip(map(str, prim[2]), zip(prim[0].tolist(), prim[1].tolist())))
    out['DB_primary'] = cmp_stat(dbp[0], dbp[1]); out['DB_primary']['per_seed'] = dict(zip(map(str, dbp[2]), zip(dbp[0].tolist(), dbp[1].tolist())))
    sens = {}
    for ht in HTS:
        for m in MS:
            c, x, _ = paired(trap, lambda R, w, ht=ht, m=m: frac(win_frames(R, w), lambda f: mb_frame(f, ht, m)))
            sens[f'MB_h{ht}_m{m}'] = cmp_stat(c, x)
    for m in MS:
        c, x, _ = paired(trap, lambda R, w, m=m: frac(win_frames(R, w), lambda f: mbgeo_frame(f, m)))
        sens[f'MBgeo_m{m}'] = cmp_stat(c, x)
    for wn in ('F0.2', 'F0.4', 'U0.15', 'fix800', 'fix1200', 'pairmin'):
        c, x, _ = paired(trap, lambda R, w: frac(win_frames(R, w), lambda f: mb_frame(f, 0.5, 0.10)), wn)
        sens[f'MB_win_{wn}'] = cmp_stat(c, x)
    dsens = {}
    for wthr in (1, 2, 3):
        for ht in HTS:
            c, x, _ = paired(trap, lambda R, w, ht=ht, wthr=wthr: frac(win_frames(R, w), lambda f: db_frame(f, ht, 0.10, wthr)))
            dsens[f'DB_h{ht}_w{wthr}'] = cmp_stat(c, x)
    for m in MS:
        c, x, _ = paired(trap, lambda R, w, m=m: frac(win_frames(R, w), lambda f: dbgeo_frame(f, m)))
        dsens[f'DBgeo_m{m}'] = cmp_stat(c, x)
    okf = float(np.mean([v['cand_mean'] < v['ctrl_mean'] for v in sens.values()]))
    out['MB_sens'] = sens; out['MB_sens_frac_cand_lower'] = okf
    out['DB_sens'] = dsens; out['DB_sens_frac_cand_lower_or_equal'] = float(np.mean([v['cand_mean'] <= v['ctrl_mean'] for v in dsens.values()]))
    mb = out['MB_primary']; db = out['DB_primary']
    if mb['cand_mean'] >= mb['ctrl_mean'] or (db['cand_mean'] > db['ctrl_mean'] and db['p_greater'] < 0.05): v = '틀림'
    elif mb['p_less'] < 0.05 and db['cand_mean'] <= db['ctrl_mean'] and okf >= 0.75: v = '맞음'
    else: v = '판정 못 함'
    # 판정 밖: 판 전체 큰 덩이 수, 몸 수, 큰 몸 수
    ab = paired(trap, lambda R, w: frac(win_frames(R, w), lambda f: sum(1 for x in f.get('allblobs', []) if x >= 0.10) >= 2))
    out['context_allboard_2blobs'] = cmp_stat(ab[0], ab[1])
    nb = paired(trap, lambda R, w: meanv(win_frames(R, w), lambda f: f['nb']))
    out['context_nbodies_mean'] = cmp_stat(nb[0], nb[1])
    nbb = paired(trap, lambda R, w: meanv(win_frames(R, w), lambda f: sum(1 for x in f['fb'] if x >= 0.10)))
    out['context_nbig_bodies_mean'] = cmp_stat(nbb[0], nbb[1])
    return v, out


def claim3(trap):
    out = {}; verd = {}
    # 3a 막
    st = paired(trap, run_val_c3('film', '0.3_60')); prim = cmp_stat(st[0], st[1]); prim['per_seed'] = dict(zip(map(str, st[2]), zip(st[0].tolist(), st[1].tolist())))
    sens = {}
    for hf in (0.2, 0.3, 0.4):
        for am in (40, 60, 100):
            c, x, _ = paired(trap, run_val_c3('film', f'{hf}_{am}')); sens[f'film_{hf}_{am}'] = cmp_stat(c, x)
    for wn in ('F0.2', 'F0.4', 'U0.15', 'fix800', 'fix1200', 'pairmin'):
        c, x, _ = paired(trap, run_val_c3('film', '0.3_60'), wn); sens[f'film_win_{wn}'] = cmp_stat(c, x)
    okf = float(np.mean([v['cand_mean'] < v['ctrl_mean'] for v in sens.values()]))
    out['3a_film'] = dict(primary=prim, sens=sens, sens_frac_cand_lower=okf); verd['3a'] = verdict_dir(prim, okf)
    # 3b 죽은 실, 3c 죽은 가지 끝
    for tag, kind in (('3b_dead_thread', 'thr'), ('3c_dead_tip', 'tip')):
        st = paired(trap, run_val_c3(kind, 'med_0.1')); prim = cmp_stat(st[0], st[1]); prim['per_seed'] = dict(zip(map(str, st[2]), zip(st[0].tolist(), st[1].tolist())))
        sens = {}
        for rn in ('med', 'p90'):
            for f in (0.03, 0.1, 0.3):
                c, x, _ = paired(trap, run_val_c3(kind, f'{rn}_{f}')); sens[f'{kind}_{rn}_{f}'] = cmp_stat(c, x)
                if kind == 'thr':
                    c, x, _ = paired(trap, run_val_c3(kind, f'{rn}_{f}', True)); sens[f'{kind}_{rn}_{f}_perarea'] = cmp_stat(c, x)
        for wn in ('F0.2', 'F0.4', 'U0.15', 'fix800', 'fix1200', 'pairmin'):
            c, x, _ = paired(trap, run_val_c3(kind, 'med_0.1'), wn); sens[f'{kind}_win_{wn}'] = cmp_stat(c, x)
        okf = float(np.mean([v['cand_mean'] < v['ctrl_mean'] for v in sens.values()]))
        out[tag] = dict(primary=prim, sens=sens, sens_frac_cand_lower=okf); verd[tag[:2]] = verdict_dir(prim, okf)
    vs = list(verd.values())
    v = '맞음' if all(x == '맞음' for x in vs) else ('틀림' if any(x == '틀림' for x in vs) else '판정 못 함')
    out['sub_verdicts'] = verd
    return v, out


# ───────────────────────── 주장 4
def claim4(margin=0.10, use_cover=False):
    out = {}; fails = []; hard = []
    for scn in ('food3', 'asym3', 'food4', 'mig'):
        rows = []
        for s in SEEDS[scn]:
            Rc = load(scn, s, 'x17c'); Rx = load(scn, s, 'x17fs')
            if Rc is None or Rx is None: continue
            r = {}
            for a, R in (('c', Rc), ('x', Rx)):
                M = R['metrics']; T = float(R['T'])
                tt = M['t_cover'] if use_cover else M['t_touch']
                r[f'n_{a}'] = sum(1 for v in M['t_touch'] if v is not None)
                r[f'mtt_{a}'] = float(np.mean([T if v is None else v for v in tt]))
                r[f'disp_{a}'] = M['disp']
                if scn != 'mig': r[f'E_{a}'] = float(sum(R['food_M'] - (v if v is not None else 0.0) for v in M['fM_end']))
            r['seed'] = s; rows.append(r)
        nc = sum(r['n_c'] for r in rows); nx = sum(r['n_x'] for r in rows)
        mc = np.array([r['mtt_c'] for r in rows]); mx = np.array([r['mtt_x'] for r in rows])
        so = dict(seeds=[r['seed'] for r in rows], n_touch_ctrl=nc, n_touch_cand=nx, mtt=cmp_stat(mc, mx), rows=rows)
        checks = {}
        checks['i_touch'] = dict(ok=nx >= nc - 1, hard=nx < nc - 2)
        dm = float(np.mean(mx - mc)); lim = margin * float(np.mean(mc))
        checks['ii_mtt'] = dict(ok=dm <= lim, diff=dm, limit=lim, hard=(dm > lim and so['mtt']['p_greater'] < 0.05))
        if scn != 'mig':
            ec = np.array([r['E_c'] for r in rows]); ex = np.array([r['E_x'] for r in rows]); so['E'] = cmp_stat(ec, ex)
            okE = ex.mean() >= (1 - margin) * ec.mean()
            checks['iii_eaten'] = dict(ok=bool(okE), ratio=float(ex.mean() / max(ec.mean(), 1e-12)), hard=(not okE and so['E']['p_less'] < 0.05))
        else:
            dc = np.array([r['disp_c'] for r in rows]); dx = np.array([r['disp_x'] for r in rows]); so['disp'] = cmp_stat(dc, dx)
            okD = dx.mean() >= (1 - margin) * dc.mean()
            checks['iv_disp'] = dict(ok=bool(okD), ratio=float(dx.mean() / max(dc.mean(), 1e-12)), hard=(not okD and so['disp']['p_less'] < 0.05))
        so['checks'] = checks
        for k, cdict in checks.items():
            if not cdict['ok']: fails.append(f'{scn}:{k}')
            if cdict['hard']: hard.append(f'{scn}:{k}')
        out[scn] = so
    v = '맞음' if not fails else ('틀림' if hard else '판정 못 함')
    return v, out, fails, hard


# ───────────────────────── 주장 5
def health(arm):
    rows = []; bad = []
    for scn, ss in SEEDS.items():
        for s in ss:
            R = load(scn, s, arm)
            if R is None: bad.append(f'{scn}_{s}:missing'); continue
            M = R['metrics']; Vt = M['V0'] + (M['Vinj'] or 0.0)
            endcr = [p['f'] for p in R['end']['small'] if p['f'] < 0.05]
            r = dict(run=f'{scn}_{s}', stop=M['stop'], neg_end=M['neg_end_cellsteps'], mass_err=M['mass_err_max'], vcr_rel=M['V_crumb'] / Vt,
                     end_crumbs=len(endcr), end_nb=R['end']['nb'], end_fb=R['end']['fb'][:4], fission_runs=M['fission_runs'])
            fl = []
            if M['stop'] != '': fl.append('stop')
            if M['neg_end_cellsteps'] != 0: fl.append('neg')
            if not (M['mass_err_max'] < 1e-10): fl.append('mass')
            if not (r['vcr_rel'] < 1e-3): fl.append('vcrumb')
            if endcr: fl.append('endcrumb')
            r['fail'] = fl; rows.append(r)
            if fl: bad.append(f"{r['run']}:{','.join(fl)}")
    return rows, bad


def claim5():
    rx, bx = health('x17fs'); rc, bc = health('x17c')
    agg = lambda rows: dict(n=len(rows), max_mass_err=max(r['mass_err'] for r in rows), max_vcr_rel=max(r['vcr_rel'] for r in rows),
                            neg_runs=sum(1 for r in rows if r['neg_end'] > 0), endcrumb_runs=sum(1 for r in rows if r['end_crumbs'] > 0),
                            stop_runs=sum(1 for r in rows if r['stop'] != ''))
    return ('맞음' if not bx else '틀림'), dict(cand=agg(rx), ctrl=agg(rc), cand_fail=bx, ctrl_fail=bc, cand_rows=rx, ctrl_rows=rc)


# ───────────────────────── 갇힌 때
def trapped(trap):
    out = {}
    for a in ARMS:
        vals = dict(MB=[], DB=[], film=[], dead_thr=[], dead_tip=[], nb=[], crumbs5=[], frames=[])
        for s in SEEDS['long']:
            R = load('long', s, a)
            if R is None: continue
            w = trapped_win(trap, s, a)
            if w is None: continue
            fs = win_frames(R, w)
            if not fs: continue
            vals['frames'].append(len(fs))
            vals['MB'].append(frac(fs, lambda f: mb_frame(f, 0.5, 0.10))); vals['DB'].append(frac(fs, lambda f: db_frame(f, 0.5, 0.10, 2)))
            vals['film'].append(meanv(fs, lambda f: c3v(f, 'film', '0.3_60'))); vals['dead_thr'].append(meanv(fs, lambda f: c3v(f, 'thr', 'med_0.1')))
            vals['dead_tip'].append(meanv(fs, lambda f: c3v(f, 'tip', 'med_0.1'))); vals['nb'].append(meanv(fs, lambda f: f['nb']))
            vals['crumbs5'].append(frac(fs, lambda f: any(p['f'] < 0.05 for p in f['small'])))
        out[a] = {k: (dict(n=len(v), mean=float(np.mean(v)) if v else None) if k != 'frames' else dict(runs=len(v), total=int(sum(v)))) for k, v in vals.items()}
    return out


def extras():
    """몸마다 부피 보존: 1:1 로 이어지는 몸의 20 시간 사이 부피 변화 (떨어진 몸이 둘 이상일 때)"""
    out = {}
    for a in ARMS:
        worst = 0.0; nfr = 0; where = None
        for scn, ss in SEEDS.items():
            for s in ss:
                R = load(scn, s, a)
                if R is None: continue
                for f in R['frames']:
                    for vnow, vprev in f.get('dvol', []):
                        if vprev > 0.03 * f['V']:
                            r = abs(vnow - vprev) / vprev; nfr += 1
                            if r > worst: worst = r; where = f'{scn}_{s}_t{f["t"]}'
        out[a] = dict(pairs=nfr, worst_rel_change=worst, where=where)
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    trap = trap_table()
    json.dump(trap, open(os.path.join(V3, 'data', 'trap.json'), 'w'), indent=1)
    if mode == 'trap':
        for k, v in trap.items(): print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()})
        return
    v1, r1 = claim1(); v2, r2 = claim2(trap); v3, r3 = claim3(trap); v4, r4, f4, h4 = claim4()
    s4 = {}
    for mg in (0.05, 0.15):
        vv, _, ff, hh = claim4(mg); s4[f'margin{mg}'] = dict(verdict=vv, fails=ff, hard=hh)
    vv, _, ff, hh = claim4(0.10, True); s4['cover'] = dict(verdict=vv, fails=ff, hard=hh)
    v5, r5 = claim5(); tr = trapped(trap); ex = extras()
    verdict = {'claim1': v1, 'claim2': v2, 'claim3': v3, 'claim3_sub': r3['sub_verdicts'], 'claim4': v4, 'claim4_fails': f4, 'claim4_hard': h4, 'claim4_sens': s4, 'claim5': v5,
               'criteria_sha256': open(os.path.join(V3, 'criteria_sha256.txt')).read().split()[0]}
    json.dump(verdict, open(os.path.join(V3, 'data', 'verdict.json'), 'w'), indent=1, ensure_ascii=False)
    for nm, obj in (('claim1', r1), ('claim2', r2), ('claim3', r3), ('claim4', r4), ('claim5', r5), ('trapped', tr), ('extras', ex)):
        json.dump(obj, open(os.path.join(V3, 'data', f'summary_{nm}.json'), 'w'), indent=1, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    P = print
    P('=== verify3 판정 ===  criteria sha256', verdict['criteria_sha256'][:16])
    P('\n[갇힌 시각 t_trap (F 0.3 규칙)]')
    for s in SEEDS['long']:
        a = trap.get(f'{s}_x17c', {}); b = trap.get(f'{s}_x17fs', {})
        P(f'  s{s}: x17c {a.get("F0.3")} (U {a.get("U_at_trap") and round(a["U_at_trap"], 3)})   x17fs {b.get("F0.3")} (U {b.get("U_at_trap") and round(b["U_at_trap"], 3)})')
    P('\n[주장 1 부스러기]  판정:', v1)
    for c in (0.01, 0.02, 0.03, 0.05, 0.10):
        for rel in ('', '_rel'):
            A = r1[f'c{c}{rel}_x17c']; B = r1[f'c{c}{rel}_x17fs']
            P(f'  c={c}{rel:4s} 대조 판 {A["crumb_frames"]:5d} 사건 {A["events"]:5d} 최장 {A["max_life_frames"]:3d} | 후보 판 {B["crumb_frames"]:4d} 사건 {B["events"]:3d} 최장 {B["max_life_frames"]:3d} 최소f {B["f_min"]} 실행 {B["runs"][:6]}')
    P('\n[주장 2 여러 덩이 / 아령 (long, 옮겨 다니는 때)]  판정:', v2)
    for k in ('MB_primary', 'DB_primary'):
        x = r2[k]; P(f'  {k}: 대조 {x["ctrl_mean"]:.3f} → 후보 {x["cand_mean"]:.3f}  (후보 낮음 {x["n_cand_lower"]}/{x["n"]}, 높음 {x["n_cand_higher"]}, p_less {x["p_less"]:.4f}, p_greater {x["p_greater"]:.4f})')
    P(f'  MB 민감도에서 후보가 낮은 비율 {r2["MB_sens_frac_cand_lower"]:.2f}; DB 민감도에서 후보 ≤ 대조 비율 {r2["DB_sens_frac_cand_lower_or_equal"]:.2f}')
    for k, x in r2['MB_sens'].items(): P(f'    {k:22s} {x["ctrl_mean"]:.3f} → {x["cand_mean"]:.3f}  p_less {x["p_less"]:.3f}')
    for k, x in r2['DB_sens'].items(): P(f'    {k:22s} {x["ctrl_mean"]:.3f} → {x["cand_mean"]:.3f}  p_less {x["p_less"]:.3f} p_greater {x["p_greater"]:.3f}')
    for k in ('context_allboard_2blobs', 'context_nbodies_mean', 'context_nbig_bodies_mean'):
        x = r2[k]; P(f'  (참고) {k}: {x["ctrl_mean"]:.3f} → {x["cand_mean"]:.3f}')
    P('\n[주장 3 가장 큰 몸의 막 / 죽은 실 / 죽은 가지 끝]  판정:', v3, r3['sub_verdicts'])
    for k in ('3a_film', '3b_dead_thread', '3c_dead_tip'):
        x = r3[k]['primary']; P(f'  {k}: 대조 {x["ctrl_mean"]:.4f} → 후보 {x["cand_mean"]:.4f}  (낮음 {x["n_cand_lower"]}/{x["n"]}, p_less {x["p_less"]:.4f}); 민감도 같은 방향 {r3[k]["sens_frac_cand_lower"]:.2f}')
        for kk, y in r3[k]['sens'].items(): P(f'    {kk:26s} {y["ctrl_mean"]:.4f} → {y["cand_mean"]:.4f}  p_less {y["p_less"]:.3f}')
    P('\n[주장 4 먹이 찾기 / 이주]  판정:', v4, '깨진 조건', f4, '유의', h4)
    for scn, so in r4.items():
        x = so['mtt']; extra = (f" 먹은 양 {so['E']['ctrl_mean']:.0f} → {so['E']['cand_mean']:.0f}" if 'E' in so else f" disp {so['disp']['ctrl_mean']:.1f} → {so['disp']['cand_mean']:.1f}")
        P(f'  {scn}: 닿은 먹이 {so["n_touch_ctrl"]} → {so["n_touch_cand"]}, MTT {x["ctrl_mean"]:.1f} → {x["cand_mean"]:.1f} (p_greater {x["p_greater"]:.3f}){extra}')
    P('  민감도:', s4)
    P('\n[주장 5 건강]  판정:', v5)
    P('  후보', r5['cand'], '어긴 것', r5['cand_fail'])
    P('  대조', r5['ctrl'], '어긴 것', r5['ctrl_fail'][:10])
    P('\n[갇힌 때 (주장 밖)]')
    for a in ARMS: P(' ', a, tr[a])
    P('\n[몸마다 부피 보존 (주장 밖)]', ex)


if __name__ == '__main__':
    main()
