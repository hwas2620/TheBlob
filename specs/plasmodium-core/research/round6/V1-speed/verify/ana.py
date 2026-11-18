#!/usr/bin/env python3
"""[검증자] 내 표. runs/<이름>/metrics.json 과 summ/<이름>.json(vsum.py 가 만든 것)에서 숫자를 읽어 기준·후보를 나란히 찍는다.
usage: ana.py mig NAME...      이주 시험 표 (한 줄에 한 실행)
       ana.py food NAME...     먹이 시험 표
       ana.py pair mig|food TAG SEEDS [A B]   짝 비교: TAG_A_sSEED 대 TAG_B_sSEED (기본 A=base, B=cand)
숫자는 모두 파일에서 직접 읽는다. 없는 것은 '-' 로 찍는다."""
import json, os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))


def met(name):
    f = os.path.join(HERE, 'runs', name, 'metrics.json')
    return json.load(open(f)) if os.path.exists(f) else None


def par(name): return json.load(open(os.path.join(HERE, 'runs', name, 'params.json')))


def summ(name):
    f = os.path.join(HERE, 'summ', name + '.json')
    return json.load(open(f)) if os.path.exists(f) else None


def cdist(M, P, ts):
    """무게중심이 출발점에서 떨어진 거리 d(t) (metrics 의 traj 를 선형 보간). t 가 실행 길이를 넘으면 nan."""
    tr = np.array(M['traj'], float); c0 = P['N'] / 2 - 0.5
    d = np.hypot(tr[:, 1] - c0, tr[:, 2] - c0)
    return [float(np.interp(t, tr[:, 0], d)) if t <= tr[-1, 0] + 1e-9 else float('nan') for t in ts]


def speed(M, P, t1, t2):
    a, b = cdist(M, P, [t1, t2]); return (b - a) / (t2 - t1)


def common(name):
    M = met(name); P = par(name)
    steps = int(round(M['t_end'] / P['dt'])) + 1
    mg = M.get('mg_err') or [float('nan')] * 4
    return dict(name=name, dt=P['dt'], period=P['period'], N=P['N'], T=P['T'], seed=P['seed'], steps=steps, stop=M['stop'] or 'ok', runtime=M['runtime'],
                hmin_in=M['h_min_seen'], hmin_end=M['h_min_end_of_step'], neg_end=M['neg_end_cellsteps'], neg_end_per_step=M['neg_end_cellsteps'] / steps,
                neg_in=M['neg_cellsteps'], mg_med=mg[0], mg_p90=mg[1], mg_max=mg[2], mg_thick=mg[3], mg_n=M.get('mg_err_n'), mass_err=M['mass_err_max'],
                sheet_amp=(M.get('hamp') or {}).get('sheet_rel'), area_end=M['area_end'], t_touch=M['t_touch'], t_cover=M.get('t_cover'), t_exh=M['t_exh'])


def row_mig(name):
    M = met(name)
    if M is None: return None
    P = par(name); o = summ(name) or {}; r = common(name)
    te = M['t_end']
    d = cdist(M, P, [100, 200, 300, 400, te])
    r.update(vein4=o.get('vein4_largest_med'), vein4_min=o.get('vein4_largest_min'), vein30=o.get('vein30_largest_med'), body=o.get('body_largest_vol_min'), ncomp_end=o.get('body_ncomp_end'),
             E4=o.get('vein4_E_med'), E30=o.get('vein30_E_med'), cyc=o.get('cycles4_med'), disp=o.get('disp_track'), dirdeg=o.get('disp_dir_deg'), span=o.get('span_xy'),
             touch=M['t_touch'][0], d100=d[0], d200=d[1], d300=d[2], d400=d[3], dend=d[4], v100_200=speed(M, P, 100, 200), v100_end=speed(M, P, 100, te), win=o.get('window'))
    return r


def row_food(name):
    M = met(name)
    if M is None: return None
    P = par(name); o = summ(name) or {}; r = common(name)
    pm = o.get('pathminC_med'); vm = o.get('vein_medC_med')
    thick = sum(v >= 5 * vm for v in pm.values()) if (pm and vm is not None) else None
    r.update(thick=thick, npair=len(pm) if pm else 0, pathC=list(pm.values()) if pm else None, veinmed=vm, vein4=o.get('vein4_largest_med'), vein4_min=o.get('vein4_largest_min'),
             body=o.get('body_largest_vol_min'), body_all=o.get('body_largest_vol_min_all'), body_end=o.get('body_largest_vol_end'), same4=list((o.get('same4') or {}).values()),
             bott=list((o.get('bottleneck_med') or {}).values()), touch=[round(x, 1) if x is not None else None for x in (o.get('t_touch') or M['t_touch'])],
             exh=M['t_exh'], win=o.get('window'), disp=o.get('disp_track'), cyc=o.get('cycles4_med'), pulse=o.get('pulse'), note=o.get('note'))
    return r


def f(x, n=3):
    if x is None: return '-'
    if isinstance(x, (list, tuple)): return '/'.join(f(v, n) for v in x)
    if isinstance(x, str): return x
    if isinstance(x, (int, np.integer)): return str(x)
    if x != x: return 'nan'
    return f'{x:.{n}f}'


def print_mig(names):
    print('이름 | 스텝 | 정맥최대 C>4 중앙/최소 | 몸최대(창) | 닿음 | 이동(추적) d100/d200/d300/d400/d끝 | 속도 100~200 / 100~끝 | 스텝안 최소 h | 스텝끝 최소 h | 끝음수(셀·스텝) /스텝 | 유량오차 중앙/90%/최대 | 정맥간선 C>4/C>30 | 순환 | 넓이 | 시트진폭 | 멈춤')
    for n in names:
        r = row_mig(n)
        if r is None: print(n, '(아직 없음)'); continue
        print(f"{n:16s} | {r['steps']} | {f(r['vein4'])}/{f(r['vein4_min'])} | {f(r['body'])} | {f(r['touch'],1)} | {f(r['d100'],1)}/{f(r['d200'],1)}/{f(r['d300'],1)}/{f(r['d400'],1)}/{f(r['dend'],1)} | {f(r['v100_200'],3)} / {f(r['v100_end'],3)} | "
              f"{r['hmin_in']:.4f} | {r['hmin_end']:.4f} | {r['neg_end']} {r['neg_end_per_step']:.3f} | {f(r['mg_med'])}/{f(r['mg_p90'])}/{f(r['mg_max'])} | {f(r['E4'],0)}/{f(r['E30'],0)} | {f(r['cyc'],0)} | {r['area_end']} | {f(r['sheet_amp'],4)} | {r['stop']}")


def print_food(names):
    print('이름 | 스텝 | 굵은 쌍 | 경로최소C | 정맥중앙C | 정맥최대 C>4 | 몸최대 창/전체/끝 | 닿음 | 떨어짐 | 스텝안 최소 h | 스텝끝 최소 h | 끝음수(셀·스텝) /스텝 | 유량오차 중앙/90%/최대 | 넓이 | 멈춤')
    for n in names:
        r = row_food(n)
        if r is None: print(n, '(아직 없음)'); continue
        print(f"{n:16s} | {r['steps']} | {f(r['thick'])}/{r['npair']} | {f(r['pathC'],0)} | {f(r['veinmed'],1)} | {f(r['vein4'])} | {f(r['body'])}/{f(r['body_all'])}/{f(r['body_end'])} | {f(r['touch'],1)} | {f(r['exh'],1)} | "
              f"{r['hmin_in']:.4f} | {r['hmin_end']:.4f} | {r['neg_end']} {r['neg_end_per_step']:.3f} | {f(r['mg_med'])}/{f(r['mg_p90'])}/{f(r['mg_max'])} | {r['area_end']} | {r['stop']}" + (f" | {r['note']}" if r.get('note') else ''))


def pair(kind, tag, seeds, A='base', B='cand', suffix=''):
    """짝 비교 요약: 판정 기준에 쓰는 수와 (B/A) 비."""
    RA = []; RB = []
    for s in seeds:
        a = (row_mig if kind == 'mig' else row_food)(f'{tag}_{A}_s{s}{suffix}'); b = (row_mig if kind == 'mig' else row_food)(f'{tag}_{B}_s{s}{suffix}')
        if a is None or b is None: print(f'  시드 {s}: 아직 없음'); continue
        RA.append(a); RB.append(b)
    if not RA: return
    g = lambda R, k: np.array([np.nan if r[k] is None else r[k] for r in R], float)
    n = len(RA); print(f'== {tag} ({kind}) {A} 대 {B}, 시드 {[r["seed"] for r in RA]} (n={n}) ==')
    if kind == 'mig':
        va = g(RA, 'vein4'); vb = g(RB, 'vein4')
        print(f'  1a 정맥 최대 성분 >=0.8 인 시드 수: {A} {int((va >= 0.8).sum())}/{n}  {B} {int((vb >= 0.8).sum())}/{n}   (값 {A} {f(list(va))} | {B} {f(list(vb))})')
    else:
        ta = sum(r['thick'] or 0 for r in RA); tb = sum(r['thick'] or 0 for r in RB); na = sum(r['npair'] for r in RA); nb_ = sum(r['npair'] for r in RB)
        print(f'  1b 굵은 쌍: {A} {ta}/{na}  {B} {tb}/{nb_}')
        pa = np.concatenate([r['pathC'] or [np.nan] for r in RA]); pb = np.concatenate([r['pathC'] or [np.nan] for r in RB])
        print(f'     경로 최소 C 범위(중앙): {A} {np.nanmin(pa):.0f}~{np.nanmax(pa):.0f} ({np.nanmedian(pa):.0f})  {B} {np.nanmin(pb):.0f}~{np.nanmax(pb):.0f} ({np.nanmedian(pb):.0f});  정맥 중앙 C: {A} {f(list(g(RA,"veinmed")),1)} | {B} {f(list(g(RB,"veinmed")),1)}')
    ba = g(RA, 'body'); bb = g(RB, 'body')
    print(f'  1c 몸이 갈라진 실행(<0.9): {A} {int((ba < 0.9).sum())}/{n}  {B} {int((bb < 0.9).sum())}/{n}   (몸 최대 성분 {A} {np.nanmin(ba):.3f}~{np.nanmax(ba):.3f} | {B} {np.nanmin(bb):.3f}~{np.nanmax(bb):.3f})')
    for k, lab in (('neg_end', '1d(i) 끝음수 셀·스텝(실행 전체)'), ('neg_end_per_step', '1d(ii) 끝음수 셀·스텝/스텝'), ('hmin_end', '1d(iii) 스텝 끝 최소 h'), ('hmin_in', '2b 스텝 안 최소 h'), ('neg_in', '   스텝 안 음수 셀·스텝(실행 전체)')):
        a = g(RA, k); b = g(RB, k)
        worse = int((b > a).sum()) if k.startswith('neg') else int((b < a).sum())
        print(f'  {lab}: {A} {f(list(a), 4 if "hmin" in k else 2)} | {B} {f(list(b), 4 if "hmin" in k else 2)}  합 {a.sum():.4g} 대 {b.sum():.4g} (비 {b.sum() / a.sum() if a.sum() != 0 else float("nan"):.2f}), 중앙 {np.median(a):.4g} 대 {np.median(b):.4g} (비 {np.median(b) / np.median(a) if np.median(a) != 0 else float("nan"):.2f}), {B} 가 더 나쁜 시드 {worse}/{n}')
    for k, lab in (('mg_med', '1e/2a 유량 오차 중앙'), ('mg_p90', '2a 유량 오차 90%'), ('mg_max', '   유량 오차 최대')):
        a = g(RA, k); b = g(RB, k)
        print(f'  {lab}: {A} {f(list(a))} | {B} {f(list(b))}  시드 중앙 {np.median(a):.3f} 대 {np.median(b):.3f}, 짝 비의 중앙 {np.median(b / a):.2f} (범위 {np.min(b / a):.2f}~{np.max(b / a):.2f}), {B}>0.15: {int((b > 0.15).sum())}/{n}, {A}>0.15: {int((a > 0.15).sum())}/{n}, {B} 중앙 > {A} 최대: {bool(np.median(b) > a.max())}')
    if kind == 'mig':
        ta = g(RA, 'touch'); tb = g(RB, 'touch')
        print(f'  3a 닿는 시각: {A} {f(list(ta),1)} | {B} {f(list(tb),1)}  중앙 {np.nanmedian(ta):.1f} 대 {np.nanmedian(tb):.1f};  스텝당 전진 비 = (dtB/dtA)×tA/tB: 짝별 {f(list(RB[0]["dt"] / RA[0]["dt"] * ta / tb), 2)}  중앙 {np.nanmedian(RB[0]["dt"] / RA[0]["dt"] * ta / tb):.2f}')
        for k, lab in (('v100_200', '3b 무게중심 속도 t=100~200'), ('v100_end', '3b 무게중심 속도 t=100~끝')):
            a = g(RA, k); b = g(RB, k)
            print(f'  {lab}: {A} {f(list(a))} | {B} {f(list(b))}  중앙 {np.median(a):.3f} 대 {np.median(b):.3f};  스텝당 전진 비: 짝별 {f(list(RB[0]["dt"] / RA[0]["dt"] * b / a), 2)}  중앙 {np.median(RB[0]["dt"] / RA[0]["dt"] * b / a):.2f}, 중앙값끼리 {RB[0]["dt"] / RA[0]["dt"] * np.median(b) / np.median(a):.2f}')
        for k, lab in (('d200', '   무게중심 이동 d(200)'), ('d400', '   무게중심 이동 d(400)'), ('dend', '   무게중심 이동 d(끝)'), ('E4', '   정맥 간선 수 C>4'), ('E30', '   정맥 간선 수 C>30'), ('cyc', '   순환 수'), ('area_end', '   끝 넓이'), ('sheet_amp', '   시트 맥동 진폭'), ('dirdeg', '   이동 방향(도)'), ('vein4_min', '   정맥 최대 성분의 최소(창)')):
            a = g(RA, k); b = g(RB, k)
            print(f'  {lab}: {A} {np.nanmin(a):.4g}~{np.nanmax(a):.4g} (중앙 {np.nanmedian(a):.4g}) | {B} {np.nanmin(b):.4g}~{np.nanmax(b):.4g} (중앙 {np.nanmedian(b):.4g})  {B}>{A} 인 시드 {int((b > a).sum())}/{n}')
    else:
        for i, lab in ((0, '첫'), (-1, '마지막')):
            a = np.array([sorted([x for x in r['touch'] if x is not None])[i] if any(x is not None for x in r['touch']) else np.nan for r in RA]); b = np.array([sorted([x for x in r['touch'] if x is not None])[i] if any(x is not None for x in r['touch']) else np.nan for r in RB])
            print(f'     {lab} 먹이에 닿는 시각: {A} {f(list(a),1)} | {B} {f(list(b),1)}  중앙 {np.nanmedian(a):.1f} 대 {np.nanmedian(b):.1f}; 스텝당 비 중앙 {np.nanmedian(RB[0]["dt"] / RA[0]["dt"] * a / b):.2f}')
        na_ = [sum(x is None for x in r['touch']) for r in RA]; nb2 = [sum(x is None for x in r['touch']) for r in RB]
        print(f'     닿지 못한 먹이 수: {A} {na_} | {B} {nb2}')
        for k, lab in (('vein4', '   정맥 최대 성분 C>4(창)'), ('body_all', '   몸 최대 성분 최소(전체 시간)'), ('body_end', '   몸 최대 성분(끝)'), ('area_end', '   끝 넓이'), ('cyc', '   순환 수'), ('sheet_amp', '   시트 맥동 진폭'), ('disp', '   무게중심 이동(끝)')):
            a = g(RA, k); b = g(RB, k)
            print(f'  {lab}: {A} {np.nanmin(a):.4g}~{np.nanmax(a):.4g} (중앙 {np.nanmedian(a):.4g}) | {B} {np.nanmin(b):.4g}~{np.nanmax(b):.4g} (중앙 {np.nanmedian(b):.4g})  {B}>{A} 인 시드 {int((b > a).sum())}/{n}')
        ea = [min([x for x in r['exh'] if x is not None], default=np.nan) for r in RA]; eb = [min([x for x in r['exh'] if x is not None], default=np.nan) for r in RB]
        print(f'     첫 먹이가 떨어지는 시각: {A} {f(ea,1)} | {B} {f(eb,1)}')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'mig': print_mig(sys.argv[2:])
    elif cmd == 'food': print_food(sys.argv[2:])
    elif cmd == 'pair':
        kind, tag = sys.argv[2], sys.argv[3]; seeds = [int(x) for x in sys.argv[4].split(',')]
        A = sys.argv[5] if len(sys.argv) > 5 else 'base'; B = sys.argv[6] if len(sys.argv) > 6 else 'cand'; suf = sys.argv[7] if len(sys.argv) > 7 else ''
        pair(kind, tag, seeds, A, B, suf)
