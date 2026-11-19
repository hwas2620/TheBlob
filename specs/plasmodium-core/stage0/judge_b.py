#!/usr/bin/env python3
"""관문 B 의 판정: 채점 요약(results/b/gpu_*.json, results/b/numpy_*.json)을 모아 B1~B7 을 기준별로 낸다.

usage: judge_b.py [--json OUT]

먼저   GPU:    bash run_b.sh                      (실행마다 metrics/bmet.py 가 results/b/gpu_<실행>.json 을 쓴다)
       numpy:  bash ref/run_b_ref.sh  그리고  python3 metrics/bmet.py ref/runs/b_* --out results/b

줄마다 판정이 둘이다 (plan-B.md Step 7).
  같은가   GPU 구현이 numpy 와 같은 결과를 내는가. 같은 시드 묶음에서
           · 기준을 넘은 실행 수가 numpy 와 1개 넘게 다르지 않고
           · 연속 지표의 GPU 중앙값이 numpy 의 시드 범위(최소~최대) 안에 든다
           (범위가 좁은 지표는 범위의 양쪽을 중앙값의 5%만큼 넓혀 본다. 시드가 2~6개라 범위 자체가 표본에 따라 흔들린다)
  기준     모델이 spec 의 문턱을 넘는가 (GPU 쪽 값으로 본다. numpy 쪽도 함께 적는다)
지표의 정의는 metrics/bmet.py 의 머리말에 있다.
"""
import glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = []          # 구조화한 판정 (RESULT-B 를 만들 때 쓴다)


def load():
    R = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'results', 'b', '*.json'))):
        o = json.load(open(f)); R[(o['origin'], o['run'])] = o
    return R


def runs(R, origin, scn, tag=''):
    """시나리오 scn 의 실행들 (시드 순). tag 가 있으면 이름 꼬리가 그것인 실행만, 없으면 꼬리 없는 실행만"""
    out = []
    for (og, name), o in R.items():
        if og != origin or o.get('scn') != scn: continue
        tail = name[len(f"b_{scn}_s{o['seed']}"):].lstrip('_')
        if tail == tag: out.append(o)
    return sorted(out, key=lambda o: o['seed'])


def f(x, fmt='%.3g'):
    if x is None: return '-'
    if isinstance(x, bool): return '예' if x else '아니오'
    return fmt % x


def vals(rs, key):
    return [r[key] for r in rs if r.get(key) is not None]


def med(v): return float(np.median(v)) if len(v) else None


def within(g, n, slack=0.05):
    """GPU 값들의 중앙이 numpy 값들의 범위 안인가 (범위의 양쪽을 numpy 중앙값의 slack 만큼 넓힌다)"""
    if not g or not n: return None
    m = med(g); lo, hi = min(n), max(n); w = slack * abs(med(n))
    return bool(lo - w <= m <= hi + w)


def mark(v, yes='통과', no='불통과'):
    return '-' if v is None else (yes if v else no)


def same_mark(v): return mark(v, '같음', '다름')


def line(crit, what, g, n, thr, ok_fn, key=None, fmt='%.3g', cont=True):
    """기준 한 줄: GPU·numpy 의 시드별 값, 문턱을 넘은 수, 판정 둘"""
    gp = [bool(ok_fn(v)) for v in g]; np_ = [bool(ok_fn(v)) for v in n]
    same_cnt = abs(sum(gp) - sum(np_)) <= 1 if g and n and len(g) == len(n) else None
    same_val = within(g, n) if cont else True
    same = None if same_cnt is None or same_val is None else bool(same_cnt and same_val)
    crit_ok = bool(g) and all(gp)
    show = lambda v: '-' if not v else ' / '.join(fmt % x for x in v)
    print(f'  {what:34s} 문턱 {thr}')
    print(f'      GPU   {show(g)}   → {sum(gp)}/{len(gp)}')
    print(f'      numpy {show(n)}   → {sum(np_)}/{len(np_)}')
    print(f'      같은가: {same_mark(same)}' + (f' (넘은 수 {"같음" if same_cnt else "다름"}, 중앙값이 numpy 범위 {"안" if same_val else "밖"})' if same is not None and cont else '') + f'   기준: {mark(crit_ok)}')
    OUT.append(dict(crit=crit, what=what, thr=thr, gpu=g, numpy=n, gpu_pass=sum(gp), numpy_pass=sum(np_), n_gpu=len(gp), n_numpy=len(np_), same=same, ok=crit_ok, key=key))
    return same, crit_ok


def main():
    R = load()
    if not R: raise SystemExit('채점 요약이 없다 (results/b/*.json)')
    G = lambda scn, tag='': runs(R, 'gpu', scn, tag); Nn = lambda scn, tag='': runs(R, 'numpy', scn, tag)
    print(f'채점한 실행: GPU {sum(1 for k in R if k[0] == "gpu")}개, numpy {sum(1 for k in R if k[0] == "numpy")}개\n')

    # ───────── B1 질량 ─────────
    print('B1 질량 — 총 부피 상대 오차 ≤ 0.1%, 스텝 끝 음수 두께 셀 0, 최대 연결 성분 밖 부피 ≤ 10%')
    print('  (1만 스텝 넘는 실행은 지속 실행(2만 스텝)이다. 나머지 시나리오도 함께 적는다)')
    print('  %-12s %-6s %3s %7s %11s %11s %12s %11s %9s' % ('시나리오', '출처', '수', '스텝', '부피 오차', '끝 음수(스텝)', '스텝 안 최소', '몸 밖 부피', '통과'))
    b1 = {}
    for scn, tag in (('long', ''), ('mig', ''), ('food3', ''), ('asym3', ''), ('food4', ''), ('mig256', ''), ('food3_256', ''), ('mig', 'N384'), ('food3', 'N384'), ('mig2x', ''), ('slimehalf', ''), ('slimeall', '')):
        for origin, rs in (('gpu', G(scn, tag)), ('numpy', Nn(scn, tag))):
            if not rs: continue
            ok = [((r.get('mass_err') or 0) <= 1e-3 and (r.get('neg_end') or 0) == 0 and (r.get('out_frac') or 0) <= 0.10) for r in rs]
            b1[(scn, tag, origin)] = (sum(ok), len(ok))
            print('  %-12s %-6s %3d %7d %11.1e %11s %12.4f %11.3f %6d/%d' % (scn + ('·' + tag if tag else ''), origin, len(rs), max(r['steps'] for r in rs), max(r.get('mass_err') or 0 for r in rs),
                  '/'.join(str(r.get('neg_end')) for r in rs), min(r.get('h_min_in') or 0 for r in rs), max(r.get('out_frac') or 0 for r in rs), sum(ok), len(ok)))
    for scn, tag in (('long', ''), ('mig', ''), ('food3', '')):
        g, n = G(scn, tag), Nn(scn, tag)
        if g and n:
            line('B1', f'부피 오차 [{scn}]', vals(g, 'mass_err'), vals(n, 'mass_err'), '≤ 1e-3', lambda v: v <= 1e-3, fmt='%.1e', cont=False)
            line('B1', f'스텝 끝 음수 두께인 스텝 수 [{scn}]', vals(g, 'neg_end'), vals(n, 'neg_end'), '= 0', lambda v: v == 0, fmt='%d', cont=False)
            line('B1', f'몸 밖 부피 [{scn}]', vals(g, 'out_frac'), vals(n, 'out_frac'), '≤ 0.10', lambda v: v <= 0.10, fmt='%.3f', cont=False)

    # ───────── B2 전진면 ─────────
    print('\nB2 전진면 — 한 방향 이주 4/5 이상, 방향별 도달 시각 최대/최소 ≤ 1.1, 정맥 현의 격자 방향 비율 ≤ 0.45')
    g, n = G('mig'), Nn('mig')
    mv = lambda rs: [(r.get('disp300') or 0) for r in rs]
    ang = lambda rs: [(r.get('disp_angle') if r.get('disp_angle') is not None else 999) for r in rs]
    gm = [d >= 20 and a <= 30 for d, a in zip(mv(g), ang(g))]; nm = [d >= 20 and a <= 30 for d, a in zip(mv(n), ang(n))]
    print(f'  한 방향 이주 (이동 t=0~300 ≥ 20셀, 유인원 방향과의 각 ≤ 30°)')
    print('      GPU   ' + ' / '.join('%.1f셀 %.0f°' % (d, a) for d, a in zip(mv(g), ang(g))) + f'   → {sum(gm)}/{len(gm)}')
    print('      numpy ' + ' / '.join('%.1f셀 %.0f°' % (d, a) for d, a in zip(mv(n), ang(n))) + f'   → {sum(nm)}/{len(nm)}')
    sm = (abs(sum(gm) - sum(nm)) <= 1 and within(mv(g), mv(n))) if g and n else None
    print(f'      같은가: {same_mark(sm)}   기준(4/5 이상): {mark(bool(gm) and sum(gm) >= 0.8 * len(gm))}')
    OUT.append(dict(crit='B2', what='한 방향 이주', thr='이동 ≥ 20셀, 각 ≤ 30°, 시드의 4/5', gpu=[[d, a] for d, a in zip(mv(g), ang(g))], numpy=[[d, a] for d, a in zip(mv(n), ang(n))], gpu_pass=sum(gm), numpy_pass=sum(nm), n_gpu=len(gm), n_numpy=len(nm), same=sm, ok=bool(gm) and sum(gm) >= 0.8 * len(gm)))
    print('  유인원(거리 70셀)에 닿은 시각 — 방향별')
    ratios = {'gpu': [], 'numpy': []}; tt = {}
    for origin, get in (('gpu', G), ('numpy', Nn)):
        for seed in (1, 2):
            row = []
            for a in (0, 13, 27, 34, 45):
                rs = [r for r in get(f'dir{a}') if r['seed'] == seed]
                row.append(rs[0]['t_touch'][0] if rs and rs[0].get('t_touch') and rs[0]['t_touch'][0] is not None else None)
            tt[(origin, seed)] = row
            if all(v is not None for v in row): ratios[origin].append(max(row) / min(row))
            print(f'      {origin:5s} 시드 {seed}: 0°/13°/27°/34°/45° = ' + ' / '.join(f(v, '%.1f') for v in row) + (f'   최대/최소 {max(row) / min(row):.3f}' if all(v is not None for v in row) else '   (닿지 못한 방향이 있다)'))
    line('B2', '도달 시각의 최대/최소', ratios['gpu'], ratios['numpy'], '≤ 1.1', lambda v: v <= 1.1, fmt='%.3f')
    OUT[-1]['t_touch'] = {f'{k[0]}_s{k[1]}': v for k, v in tt.items()}
    line('B2', '정맥 현의 격자 방향 비율', vals(g, 'chord'), vals(n, 'chord'), '≤ 0.45', lambda v: v <= 0.45)

    # ───────── B3 정맥 ─────────
    print('\nB3 정맥 (시간 평균 전도도. 굶은 이주, t ≥ 200 의 중앙) — 최대 연결 성분 ≥ 0.8, Strahler ≥ 4, 반지름 p90/p10 ≥ 2, 전진면에서 멀수록 굵음')
    for scn, tag, label in (('mig', '', '192²'), ('mig256', '', '256²·P=128'), ('mig', 'N384', '384²'), ('mig2x', '', '384²·몸 2배')):
        g, n = G(scn, tag), Nn(scn, tag)
        if not g and not n: continue
        print(f' [{label}]')
        line('B3', f'최대 연결 성분 [{label}]', vals(g, 'veinT'), vals(n, 'veinT'), '≥ 0.8', lambda v: v >= 0.8)
        line('B3', f'  (견줌) 그 순간 전도도로 [{label}]', vals(g, 'vein4'), vals(n, 'vein4'), '≥ 0.8', lambda v: v >= 0.8)
        line('B3', f'Strahler 차수 [{label}]', vals(g, 'strahler'), vals(n, 'strahler'), '≥ 4', lambda v: v >= 4, fmt='%.0f', cont=False)
        line('B3', f'반지름 p90/p10 [{label}]', vals(g, 'rad_ratio'), vals(n, 'rad_ratio'), '≥ 2', lambda v: v >= 2)
        line('B3', f'먼 절반/가까운 절반의 전도도 [{label}]', vals(g, 'rear_ratio'), vals(n, 'rear_ratio'), '> 1', lambda v: v > 1)
        line('B3', f'거리와 굵기의 상관 [{label}]', vals(g, 'rear_rho'), vals(n, 'rear_rho'), '> 0', lambda v: v > 0)

    # ───────── B4 맥동 ─────────
    print('\nB4 맥동 (굶은 이주) — 정맥 총유량/순유량 ≥ 3, 시트 두께 진폭 ≥ 3%, 뒤→앞 위상 지연 0.5~2바퀴 (몸 길이 2배에서도)')
    g, n = G('mig'), Nn('mig')
    line('B4', '정맥 총유량/순유량', vals(g, 'gross_net'), vals(n, 'gross_net'), '≥ 3', lambda v: v >= 3)
    line('B4', '시트 두께 진폭/평균', vals(g, 'sheet_amp'), vals(n, 'sheet_amp'), '≥ 0.03', lambda v: v >= 0.03)
    lag300 = lambda rs: [next((l[1] for l in (r.get('lag') or []) if abs(l[0] - 300) < 1e-6), None) for r in rs]
    len300 = lambda rs: [next((l[2] for l in (r.get('lag') or []) if abs(l[0] - 300) < 1e-6), None) for r in rs]
    for scn, label in (('mig', '기본 몸 192²'), ('mig2x', '몸 2배 384²')):
        g, n = G(scn), Nn(scn)
        if not g and not n: continue
        gl = [v for v in lag300(g) if v is not None]; nl = [v for v in lag300(n) if v is not None]
        line('B4', f'위상 지연 t=300 (바퀴) [{label}]', gl, nl, '0.5~2', lambda v: 0.5 <= v <= 2)
        print('      몸 길이(셀): GPU ' + ' / '.join(f(v, '%.0f') for v in len300(g)) + '   numpy ' + ' / '.join(f(v, '%.0f') for v in len300(n)))
    for origin, get in (('GPU', G), ('numpy', Nn)):
        rs = get('mig')
        if rs: print(f'      {origin} 시드 {rs[0]["seed"]} 의 시각별 [t, 지연, 몸 길이]: ' + ' '.join('[%d %.2f %.0f]' % (l[0], l[1], l[2]) for l in rs[0].get('lag') or []))

    # ───────── B5 먹이 ─────────
    print('\nB5 먹이 — 모든 먹이에 닿음, 먹는 동안 같은 정맥 성분인 시간 ≥ 0.9, 경로 최소 전도도(중앙) ≥ 5 × 정맥 중앙, 몸 최대 성분 ≥ 0.9')
    for scn, tag, label, quorum in (('food3', '', '대칭 셋 192²', 5 / 6), ('asym3', '', '비대칭 셋', 2 / 3), ('food4', '', '긴 배치 넷 256²', 2 / 3), ('food3_256', '', '대칭 셋 256²·P=128', 2 / 3), ('food3', 'N384', '대칭 셋 384²', 1.0), ('food3', 'g0', '대칭 셋, 90% 조건 끔', 1.0)):
        g, n = G(scn, tag), Nn(scn, tag)
        if not g and not n: continue
        print(f' [{label}]')
        for origin, rs in (('GPU', g), ('numpy', n)):
            for r in rs:
                pm = r.get('pathminC') or {}; ratio = r.get('ratio') or {}; same = r.get('same4') or {}
                print('      %-5s 시드 %d: 닿음 %s · 경로 최소 C %s · 정맥 중앙 %s · 배율 %s · 굵은 쌍 %d/%d · 같은 성분 %s · 몸 %s · %s%s' % (
                    origin, r['seed'], '/'.join(f(v, '%.0f') for v in (r.get('t_touch_v') or [])), '/'.join(f(v, '%.0f') for v in pm.values()) or '-', f(r.get('vein_medC'), '%.1f'),
                    '/'.join(f(v, '%.1f') for v in ratio.values()) or '-', r.get('thick', 0), r.get('pairs', 0), '/'.join(f(v, '%.2f') for v in same.values()) or '-', f(r.get('body_min'), '%.3f'), mark(r.get('pass')),
                    f' ({r["note"]})' if r.get('note') else ''))
        gp = [bool(r.get('pass')) for r in g]; np_ = [bool(r.get('pass')) for r in n]
        allr = lambda rs: [v for r in rs for v in (r.get('ratio') or {}).values()]
        same_cnt = abs(sum(gp) - sum(np_)) <= 1 if g and n and len(g) == len(n) else None
        same_val = within(allr(g), allr(n)) if allr(g) and allr(n) else None
        same = None if same_cnt is None else bool(same_cnt and (same_val is None or same_val))
        thick = lambda rs: (sum(r.get('thick', 0) for r in rs), sum(r.get('pairs', 0) for r in rs))
        ok = bool(gp) and sum(gp) >= quorum * len(gp) - 1e-9
        print(f'      통과한 시드: GPU {sum(gp)}/{len(gp)}, numpy {sum(np_)}/{len(np_)} · 굵은 쌍: GPU {thick(g)[0]}/{thick(g)[1]}, numpy {thick(n)[0]}/{thick(n)[1]} · 배율의 중앙: GPU {f(med(allr(g)), "%.1f")}, numpy {f(med(allr(n)), "%.1f")} (numpy 범위 {f(min(allr(n), default=None), "%.1f")}~{f(max(allr(n), default=None), "%.1f")})')
        print(f'      같은가: {same_mark(same)}   기준(시드의 {quorum:.2f} 이상): {mark(ok)}')
        OUT.append(dict(crit='B5', what=label, thr='시드마다 세 조건 모두', gpu_pass=sum(gp), numpy_pass=sum(np_), n_gpu=len(gp), n_numpy=len(np_), thick_gpu=thick(g), thick_numpy=thick(n), ratio_med_gpu=med(allr(g)), ratio_med_numpy=med(allr(n)), same=same, ok=ok))

    # ───────── B6 점액 ─────────
    print('\nB6 점액 — 빈 땅과 흔적 가운데 빈 땅 쪽 전진 ≥ 80%, 사방이 흔적이어도 멈추지 않음')
    g, n = G('slimehalf'), Nn('slimehalf')
    line('B6', '빈 땅 쪽에 새로 젖은 비율 (t ≥ 20)', vals(g, 'frac_empty'), vals(n, 'frac_empty'), '≥ 0.8', lambda v: v >= 0.8)
    print('      처음 퍼지는 구간까지 넣으면: GPU ' + ' / '.join(f(v, '%.3f') for v in vals(g, 'frac_empty_all')) + '   numpy ' + ' / '.join(f(v, '%.3f') for v in vals(n, 'frac_empty_all'))
          + '   · 새로 젖은 셀 수(t ≥ 20): GPU ' + ' / '.join(str(v) for v in vals(g, 'new_after20')) + '   numpy ' + ' / '.join(str(v) for v in vals(n, 'new_after20')))
    g, n = G('slimeall'), Nn('slimeall')
    line('B6', '사방이 흔적: 뒤쪽 절반에 새로 젖은 셀', vals(g, 'late_new'), vals(n, 'late_new'), '≥ 100', lambda v: v >= 100, fmt='%d')

    # ───────── B7 지속 ─────────
    print('\nB7 지속 (500주기 = 2만 스텝, 192² 토러스) — 사라지거나 얼어붙지 않고 B1·B3 유지')
    g, n = G('long'), Nn('long')
    line('B7', '끝의 넓이', vals(g, 'area_end'), vals(n, 'area_end'), '> 0', lambda v: v > 0, fmt='%d')
    line('B7', '젖음이 바뀌는 셀의 비율 (끝 400 시간)', vals(g, 'turnover'), vals(n, 'turnover'), '> 0.02', lambda v: v > 0.02)
    for origin, rs in (('GPU', g), ('numpy', n)):
        for r in rs:
            print(f'      {origin:5s} 시드 {r["seed"]} 구간별 [구간: 정맥 최대 성분 / Strahler / 반지름비 / 진폭 / 총·순 / 몸 밖 / 넓이]')
            for s in r.get('segments') or []:
                print('            %4d~%4d: %s / %s / %s / %s / %s / %s / %d' % (s['t'][0], s['t'][1], f(s['veinT'], '%.3f'), f(s['strahler'], '%.0f'), f(s['rad_ratio'], '%.2f'), f(s['sheet_amp'], '%.3f'), f(s['gross_net'], '%.2f'), f(s['out_frac'], '%.3f'), s['area']))
    seg_ok = lambda r: [bool((s['veinT'] or 0) >= 0.8 and (s['strahler'] or 0) >= 4 and (s['rad_ratio'] or 0) >= 2) for s in (r.get('segments') or [])]
    gs = [sum(seg_ok(r)) / max(len(seg_ok(r)), 1) for r in g]; ns = [sum(seg_ok(r)) / max(len(seg_ok(r)), 1) for r in n]
    line('B7', 'B3 을 채운 구간의 비율', gs, ns, '= 1', lambda v: v >= 1 - 1e-9, fmt='%.2f')
    amp_last = lambda rs: [(r['segments'][-1]['sheet_amp'] if r.get('segments') and r['segments'][-1]['sheet_amp'] is not None else 0.0) for r in rs]
    line('B7', '마지막 구간의 시트 두께 진폭', amp_last(g), amp_last(n), '≥ 0.03', lambda v: v >= 0.03)
    b1l = lambda rs: [bool((r.get('mass_err') or 0) <= 1e-3 and (r.get('neg_end') or 0) == 0 and (r.get('out_frac') or 0) <= 0.10) for r in rs]
    print(f'      B1 (부피·음수·몸 밖): GPU {sum(b1l(g))}/{len(g)}, numpy {sum(b1l(n))}/{len(n)}')

    # ───────── 요약 ─────────
    print('\n요약 — 기준별로 GPU 가 numpy 와 같은가 / 모델이 기준을 넘는가')
    for c in ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'):
        rows = [o for o in OUT if o['crit'] == c and '(견줌)' not in o['what']]
        same = [o['same'] for o in rows if o['same'] is not None]; ok = [o['ok'] for o in rows]
        print(f'  {c}: 같은가 {sum(same)}/{len(same)} 줄, 기준 {sum(ok)}/{len(ok)} 줄' + ('' if all(ok) else '   ← 넘지 못한 줄: ' + ', '.join(o['what'].strip() for o in rows if not o['ok'])) + ('' if all(same) else '   ← 다른 줄: ' + ', '.join(o['what'].strip() for o in rows if o['same'] is False)))
    if '--json' in sys.argv:
        json.dump(OUT, open(sys.argv[sys.argv.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
