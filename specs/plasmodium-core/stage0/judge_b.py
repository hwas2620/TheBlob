#!/usr/bin/env python3
"""관문 B 의 판정: 채점 요약(results/b/gpu_*.json, results/b/numpy_*.json)을 모아 B1~B7 을 기준별로 낸다.

usage: judge_b.py [--json OUT]

먼저   GPU:    bash run_b.sh                      (실행마다 metrics/bmet.py 가 results/b/gpu_<실행>.json 을 쓴다)
       numpy:  bash ref/run_b_ref.sh  그리고  python3 metrics/bmet.py ref/runs/b_* --out results/b

줄마다 판정이 둘이다 (plan-B.md Step 7).
  같은가   GPU 구현이 numpy 와 같은 결과를 내는가. 같은 시드 묶음에서
           · 기준을 넘은 실행 수가 numpy 와 1개 넘게 다르지 않고
           · 연속 지표의 GPU 중앙값이 numpy 의 시드 범위(최소~최대) 안에 든다
             (범위의 양쪽을 numpy 중앙값의 5%만큼 넓혀 본다. 시드가 2~6개라 범위 자체가 표본에 따라 흔들린다)
  기준     모델이 spec 의 문턱을 넘는가 (GPU 쪽 값으로 본다. numpy 쪽도 함께 적는다)

판정에 쓰는 시드는 아래 EXPECT 에 정해 둔 것뿐이다. 거기 있는 실행이 없거나, 끝까지 돌지 못했거나(스텝 수가 모자라다, NaN),
값이 비어 있으면 그 칸은 "없음"으로 적고 불통과로 센다. 그런 칸이 있는 줄의 "같은가"는 판정하지 않는다.
지표의 정의는 metrics/bmet.py 의 머리말에 있다.
"""
import glob, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = []          # 구조화한 판정 (RESULT-B 를 만들 때 쓴다)

# 판정에 쓰는 실행: (시나리오, 이름 꼬리) → 시드
EXPECT = {
    ('mig', ''): [1, 2, 3, 4, 5], ('long', ''): [1, 2], ('mig256', ''): [1, 2, 3], ('mig', 'N384'): [1, 2], ('mig2x', ''): [1, 2],
    ('food3', ''): [1, 2, 3, 4, 5, 6], ('asym3', ''): [1, 2, 3], ('food4', ''): [1, 2, 3], ('food3_256', ''): [1, 2, 3], ('food3', 'N384'): [1], ('food3', 'g0'): [1, 2],
    ('slimehalf', ''): [1, 2, 3], ('slimeall', ''): [1, 2, 3],
}
DIR_ANGLES = (0, 13, 27, 34, 45); DIR_SEEDS = (1, 2)
SEGMENTS = 5      # 지속 실행의 구간 수 (200~400, 400~800, 800~1200, 1200~1600, 1600~2000)


def load():
    R = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'results', 'b', '*.json'))):
        o = json.load(open(f)); R[(o['origin'], o['run'])] = o
    return R


R = {}


def run(origin, scn, seed, tag=''):
    """온전한 실행만 돌려준다. 없거나 끝까지 돌지 못했으면 None"""
    r = R.get((origin, f'b_{scn}_s{seed}' + (f'_{tag}' if tag else '')))
    return r if r is not None and r.get('complete', False) else None


def runs(origin, scn, tag='', seeds=None):
    return [run(origin, scn, s, tag) for s in (seeds if seeds is not None else EXPECT[(scn, tag)])]


def col(origin, scn, tag, fn, seeds=None):
    """시드 순서대로의 값. 실행이 없거나 값이 비면 None"""
    out = []
    for r in runs(origin, scn, tag, seeds):
        v = fn(r) if r is not None else None
        out.append(None if v is None or (isinstance(v, float) and not math.isfinite(v)) else v)
    return out


def key(k):
    return lambda r: r.get(k)


def f(x, fmt='%.3g'):
    if x is None: return '없음'
    if isinstance(x, bool): return '예' if x else '아니오'
    return '∞' if isinstance(x, float) and math.isinf(x) else fmt % x


def have(v): return [x for x in v if x is not None]


def med(v):
    v = have(v)
    return float(np.median(v)) if v else None


def within(g, n, slack=0.05):
    """GPU 값들의 중앙이 numpy 값들의 범위 안인가 (범위의 양쪽을 numpy 중앙값의 slack 만큼 넓힌다)"""
    m = med(g); lo, hi = min(n), max(n); w = slack * abs(med(n))
    return bool(lo - w <= m <= hi + w)


def mark(v, yes='통과', no='불통과'):
    return '판정 불가' if v is None else (yes if v else no)


def same_mark(v): return mark(v, '같음', '다름')


def judge(crit, what, g, n, thr, ok_fn, fmt='%.3g', cont=True, quorum=1.0):
    """기준 한 줄. g, n 은 시드 순서대로의 값(None = 없음). 돌려줌: (같은가, 기준)"""
    gp = [v is not None and bool(ok_fn(v)) for v in g]; np_ = [v is not None and bool(ok_fn(v)) for v in n]
    full = bool(g) and bool(n) and len(g) == len(n) and None not in g and None not in n
    same_cnt = abs(sum(gp) - sum(np_)) <= 1 if full else None
    same_val = (within(g, n) if cont else True) if full else None
    same = bool(same_cnt and same_val) if full else None
    crit_ok = (sum(gp) >= quorum * len(gp) - 1e-9) if g else None
    show = lambda v: '(실행 없음)' if not v else ' / '.join(f(x, fmt) for x in v)
    print(f'  {what:36s} 문턱 {thr}')
    print(f'      GPU   {show(g)}   → {sum(gp)}/{len(gp)}')
    print(f'      numpy {show(n)}   → {sum(np_)}/{len(np_)}')
    why = '' if not full else (f' (넘은 수 {"같음" if same_cnt else "다름"}' + (f', GPU 중앙 {f(med(g), fmt)} 이 numpy 범위 {f(min(n), fmt)}~{f(max(n), fmt)} {"안" if same_val else "밖"}' if cont else '') + ')')
    print(f'      같은가: {same_mark(same)}{why}   기준: {mark(crit_ok)}' + ('' if None not in g else '  (없는 값은 불통과로 셌다)'))
    OUT.append(dict(crit=crit, what=what.strip(), thr=thr, gpu=g, numpy=n, gpu_pass=sum(gp), numpy_pass=sum(np_), n_gpu=len(gp), n_numpy=len(np_), same=same, ok=crit_ok, fmt=fmt, cont=cont))
    return same, crit_ok


def line(crit, what, scn, tag, fn, thr, ok_fn, fmt='%.3g', cont=True, quorum=1.0):
    return judge(crit, what, col('gpu', scn, tag, fn), col('numpy', scn, tag, fn), thr, ok_fn, fmt, cont, quorum)


def b1_ok(r):
    return r is not None and r.get('mass_err') is not None and r['mass_err'] <= 1e-3 and r.get('neg_end') == 0 and r.get('out_frac') is not None and r['out_frac'] <= 0.10


def main():
    global R
    R = load()
    if not R: raise SystemExit('채점 요약이 없다 (results/b/*.json)')
    bad = sorted(name for (og, name), r in R.items() if not r.get('complete', False))
    print(f'채점한 실행: GPU {sum(1 for k in R if k[0] == "gpu")}개, numpy {sum(1 for k in R if k[0] == "numpy")}개' + (f' · 끝까지 돌지 못한 실행(판정에서 "없음"): {", ".join(bad)}' if bad else '') + '\n')

    # ───────── B1 질량 ─────────
    print('B1 질량 — 총 부피 상대 오차 ≤ 0.1%, 스텝 끝 음수 두께 셀 0, 최대 연결 성분 밖 부피 ≤ 10%')
    print('  (1만 스텝 넘는 실행은 지속 실행(2만 스텝)이다. 나머지 시나리오도 함께 적는다. "스텝 안 최소"는 음수가 아니면 0 으로 적는다)')
    print('  %-12s %-6s %5s %7s %10s %-24s %12s %10s %7s' % ('시나리오', '출처', '온전', '스텝', '부피 오차', '끝 음수(스텝 수)', '스텝 안 최소', '몸 밖 부피', '통과'))
    for (scn, tag) in (('long', ''), ('mig', ''), ('food3', ''), ('asym3', ''), ('food4', ''), ('mig256', ''), ('food3_256', ''), ('mig', 'N384'), ('food3', 'N384'), ('mig2x', ''), ('slimehalf', ''), ('slimeall', '')):
        for origin in ('gpu', 'numpy'):
            rs = runs(origin, scn, tag); ok = [b1_ok(r) for r in rs]; v = have(rs)
            if not v:
                print('  %-12s %-6s %5s' % (scn + ('·' + tag if tag else ''), origin, f'0/{len(rs)}')); continue
            print('  %-12s %-6s %5s %7d %10.1e %-24s %12.4f %10.3f %5d/%d' % (scn + ('·' + tag if tag else ''), origin, f'{len(v)}/{len(rs)}', max(r['steps'] for r in v), max(r['mass_err'] for r in v),
                  '/'.join('없음' if r is None else str(r.get('neg_end')) for r in rs), min(min(r.get('h_min_in') or 0, 0) for r in v), max(r.get('out_frac') or 0 for r in v), sum(ok), len(ok)))
    for scn in ('long', 'mig', 'food3'):
        line('B1', f'부피 오차 [{scn}]', scn, '', key('mass_err'), '≤ 1e-3', lambda v: v <= 1e-3, fmt='%.1e', cont=False)
        line('B1', f'스텝 끝 음수 두께인 스텝 수 [{scn}]', scn, '', key('neg_end'), '= 0', lambda v: v == 0, fmt='%d', cont=False)
        line('B1', f'몸 밖 부피 [{scn}]', scn, '', key('out_frac'), '≤ 0.10', lambda v: v <= 0.10, fmt='%.3f', cont=False)

    # ───────── B2 전진면 ─────────
    print('\nB2 전진면 — 한 방향 이주 4/5 이상, 방향별 도달 시각 최대/최소 ≤ 1.1, 정맥 현의 격자 방향 비율 ≤ 0.45')
    mvok = lambda r: None if r.get('disp300') is None or r.get('disp_angle') is None else (1.0 if (r['disp300'] >= 20 and r['disp_angle'] <= 30) else 0.0)
    for origin in ('gpu', 'numpy'):
        print(f'      {origin:5s} 이동 t=0~300 과 유인원 방향과의 각: ' + ' / '.join('없음' if r is None else '%.1f셀 %.0f°' % (r.get('disp300') or 0, r.get('disp_angle') if r.get('disp_angle') is not None else 999) for r in runs(origin, 'mig')))
    line('B2', '한 방향 이주 (이동 ≥ 20셀, 각 ≤ 30°)', 'mig', '', mvok, '시드의 4/5 이상', lambda v: v > 0.5, fmt='%.0f', cont=False, quorum=0.8)
    line('B2', '  이동 거리 t=0~300 (셀)', 'mig', '', key('disp300'), '≥ 20', lambda v: v >= 20)
    print('  유인원(거리 70셀)에 닿은 시각 — 방향별')
    ratios = {'gpu': [], 'numpy': []}; tt = {}
    for origin in ('gpu', 'numpy'):
        for seed in DIR_SEEDS:
            row = []
            for a in DIR_ANGLES:
                r = run(origin, f'dir{a}', seed)
                row.append(r['t_touch'][0] if r and r.get('t_touch') and r['t_touch'][0] is not None else None)
            tt[(origin, seed)] = row
            ratio = (max(row) / min(row)) if None not in row else float('inf')      # 닿지 못했거나 실행이 없는 방향이 있으면 불통과
            ratios[origin].append(ratio)
            print(f'      {origin:5s} 시드 {seed}: ' + '/'.join(f'{a}°' for a in DIR_ANGLES) + ' = ' + ' / '.join(f(v, '%.1f') for v in row) + f'   최대/최소 {f(ratio, "%.3f")}')
    judge('B2', '도달 시각의 최대/최소', ratios['gpu'], ratios['numpy'], '≤ 1.1', lambda v: v <= 1.1, fmt='%.3f')
    OUT[-1]['t_touch'] = {f'{k[0]}_s{k[1]}': v for k, v in tt.items()}
    line('B2', '정맥 현의 격자 방향 비율', 'mig', '', key('chord'), '≤ 0.45', lambda v: v <= 0.45)

    # ───────── B3 정맥 ─────────
    print('\nB3 정맥 (시간 평균 전도도. 굶은 이주, t ≥ 200 의 중앙) — 최대 연결 성분 ≥ 0.8, Strahler ≥ 4, 반지름 p90/p10 ≥ 2, 전진면에서 멀수록 굵음')
    for scn, tag, label in (('mig', '', '192²'), ('mig256', '', '256²·P=128'), ('mig', 'N384', '384²'), ('mig2x', '', '384²·몸 2배')):
        print(f' [{label}]')
        line('B3', f'최대 연결 성분 [{label}]', scn, tag, key('veinT'), '≥ 0.8', lambda v: v >= 0.8)
        line('B3', f'  (견줌) 그 순간 전도도로 [{label}]', scn, tag, key('vein4'), '≥ 0.8', lambda v: v >= 0.8)
        line('B3', f'Strahler 차수 [{label}]', scn, tag, key('strahler'), '≥ 4', lambda v: v >= 4, fmt='%.0f', cont=False)
        line('B3', f'반지름 p90/p10 [{label}]', scn, tag, key('rad_ratio'), '≥ 2', lambda v: v >= 2)
        line('B3', f'먼 절반/가까운 절반의 전도도 [{label}]', scn, tag, key('rear_ratio'), '> 1', lambda v: v > 1)
        line('B3', f'거리와 굵기의 상관 [{label}]', scn, tag, key('rear_rho'), '> 0', lambda v: v > 0)

    # ───────── B4 맥동 ─────────
    print('\nB4 맥동 (굶은 이주) — 정맥 총유량/순유량 ≥ 3, 시트 두께 진폭 ≥ 3%, 뒤→앞 위상 지연 0.5~2바퀴 (몸 길이 2배에서도)')
    line('B4', '정맥 총유량/순유량', 'mig', '', key('gross_net'), '≥ 3', lambda v: v >= 3)
    line('B4', '시트 두께 진폭/평균', 'mig', '', key('sheet_amp'), '≥ 0.03', lambda v: v >= 0.03)
    lag_at = lambda t: (lambda r: next((l[1] for l in (r.get('lag') or []) if abs(l[0] - t) < 1e-6), None))
    len_at = lambda t: (lambda r: next((l[2] for l in (r.get('lag') or []) if abs(l[0] - t) < 1e-6), None))
    for scn, label in (('mig', '기본 몸 192²'), ('mig2x', '몸 2배 384²')):
        line('B4', f'위상 지연 t=300 (바퀴) [{label}]', scn, '', lag_at(300), '0.5~2', lambda v: 0.5 <= v <= 2)
        print('      몸 길이(셀): GPU ' + ' / '.join(f(v, '%.0f') for v in col('gpu', scn, '', len_at(300))) + '   numpy ' + ' / '.join(f(v, '%.0f') for v in col('numpy', scn, '', len_at(300))))
        for origin in ('gpu', 'numpy'):
            r = run(origin, scn, 1)
            if r: print(f'      {origin:5s} 시드 1 의 시각별 [t 지연 몸길이]: ' + ' '.join('[%d %.2f %.0f]' % (l[0], l[1], l[2]) for l in r.get('lag') or []))

    # ───────── B5 먹이 ─────────
    print('\nB5 먹이 — 모든 먹이에 닿음, 먹는 동안 같은 정맥 성분인 시간 ≥ 0.9, 경로 최소 전도도(중앙) ≥ 5 × 정맥 중앙, 몸 최대 성분 ≥ 0.9')
    for scn, tag, label, quorum in (('food3', '', '대칭 셋 192²', 5 / 6), ('asym3', '', '비대칭 셋', 2 / 3), ('food4', '', '긴 배치 넷 256²', 2 / 3), ('food3_256', '', '대칭 셋 256²·P=128', 2 / 3), ('food3', 'N384', '대칭 셋 384²', 1.0), ('food3', 'g0', '대칭 셋, 90% 조건 끔', 1.0)):
        print(f' [{label}]')
        seeds = EXPECT[(scn, tag)]; side = {}
        for origin in ('gpu', 'numpy'):
            rs = runs(origin, scn, tag); side[origin] = rs
            for seed, r in zip(seeds, rs):
                if r is None:
                    print(f'      {origin:5s} 시드 {seed}: 없음'); continue
                pm = r.get('pathminC') or {}; ratio = r.get('ratio') or {}; same = r.get('same4') or {}
                print('      %-5s 시드 %d: 닿음 %s · 경로 최소 C %s · 정맥 중앙 %s · 배율 %s · 굵은 쌍 %d/%d · 같은 성분 %s · 몸 %s · 스텝 끝 음수 %s스텝 · %s%s' % (
                    origin, seed, '/'.join(f(v, '%.0f') for v in (r.get('t_touch_v') or [])), '/'.join(f(v, '%.0f') for v in pm.values()) or '-', f(r.get('vein_medC'), '%.1f'),
                    '/'.join(f(v, '%.1f') for v in ratio.values()) or '-', r.get('thick', 0), r.get('pairs', 0), '/'.join(f(v, '%.2f') for v in same.values()) or '-', f(r.get('body_min'), '%.3f'),
                    f(r.get('neg_end'), '%d'), mark(bool(r.get('pass'))), f' ({r["note"]})' if r.get('note') else ''))
        g, n = side['gpu'], side['numpy']
        gp = [r is not None and bool(r.get('pass')) for r in g]; np_ = [r is not None and bool(r.get('pass')) for r in n]
        # 시드마다 가장 가는 쌍의 배율(경로 최소 전도도 ÷ 정맥 중앙)이 판정을 정하는 값이다. 닿지 못한 실행은 0
        minr = lambda rs: [None if r is None else (min(r['ratio'].values()) if r.get('ratio') and len(r['ratio']) == r.get('pairs') else 0.0) for r in rs]
        full = None not in g and None not in n
        same = bool(abs(sum(gp) - sum(np_)) <= 1 and within(minr(g), minr(n))) if full else None
        thick = lambda rs: (sum(r.get('thick', 0) for r in have(rs)), sum(r.get('pairs', 0) for r in have(rs)))
        ok = (sum(gp) >= quorum * len(gp) - 1e-9) if gp else None
        print(f'      통과한 시드: GPU {sum(gp)}/{len(gp)}, numpy {sum(np_)}/{len(np_)} · 굵은 쌍: GPU {thick(g)[0]}/{thick(g)[1]}, numpy {thick(n)[0]}/{thick(n)[1]}'
              f' · 시드별 가장 가는 쌍의 배율: GPU {" / ".join(f(v, "%.1f") for v in minr(g))}, numpy {" / ".join(f(v, "%.1f") for v in minr(n))}')
        print(f'      같은가: {same_mark(same)}   기준(시드의 {quorum:.2f} 이상): {mark(ok)}')
        OUT.append(dict(crit='B5', what=label, thr='시드마다 세 조건 모두', gpu_pass=sum(gp), numpy_pass=sum(np_), n_gpu=len(gp), n_numpy=len(np_), thick_gpu=thick(g), thick_numpy=thick(n), minratio_gpu=minr(g), minratio_numpy=minr(n), same=same, ok=ok))

    # ───────── B6 점액 ─────────
    print('\nB6 점액 — 빈 땅과 흔적 가운데 빈 땅 쪽 전진 ≥ 80%, 사방이 흔적이어도 멈추지 않음')
    line('B6', '빈 땅 쪽에 새로 젖은 비율 (t ≥ 20)', 'slimehalf', '', key('frac_empty'), '≥ 0.8', lambda v: v >= 0.8)
    print('      처음 퍼지는 구간까지 넣으면: GPU ' + ' / '.join(f(v, '%.3f') for v in col('gpu', 'slimehalf', '', key('frac_empty_all'))) + '   numpy ' + ' / '.join(f(v, '%.3f') for v in col('numpy', 'slimehalf', '', key('frac_empty_all')))
          + '   · 새로 젖은 셀 수(t ≥ 20): GPU ' + ' / '.join(f(v, '%d') for v in col('gpu', 'slimehalf', '', key('new_after20'))) + '   numpy ' + ' / '.join(f(v, '%d') for v in col('numpy', 'slimehalf', '', key('new_after20'))))
    line('B6', '사방이 흔적: 뒤쪽 절반에 새로 젖은 셀', 'slimeall', '', key('late_new'), '≥ 100', lambda v: v >= 100, fmt='%d')

    # ───────── B7 지속 ─────────
    print('\nB7 지속 (500주기 = 2만 스텝, 192² 토러스) — 사라지거나 얼어붙지 않고 B1·B3 유지')
    line('B7', '끝의 넓이', 'long', '', key('area_end'), '> 0', lambda v: v > 0, fmt='%d')
    line('B7', '젖음이 바뀌는 셀의 비율 (끝 400 시간)', 'long', '', key('turnover'), '> 0.02', lambda v: v > 0.02)
    for origin in ('gpu', 'numpy'):
        for seed, r in zip(EXPECT[('long', '')], runs(origin, 'long')):
            if r is None:
                print(f'      {origin:5s} 시드 {seed}: 없음'); continue
            print(f'      {origin:5s} 시드 {seed} 구간별 [구간: 정맥 최대 성분 / Strahler / 반지름비 / 진폭 / 총·순 / 몸 밖 / 넓이]')
            for s in r.get('segments') or []:
                print('            %4d~%4d: %s / %s / %s / %s / %s / %s / %d' % (s['t'][0], s['t'][1], f(s['veinT'], '%.3f'), f(s['strahler'], '%.0f'), f(s['rad_ratio'], '%.2f'), f(s['sheet_amp'], '%.3f'), f(s['gross_net'], '%.2f'), f(s['out_frac'], '%.3f'), s['area']))
    seg_frac = lambda r: sum(1 for s in (r.get('segments') or []) if (s['veinT'] or 0) >= 0.8 and (s['strahler'] or 0) >= 4 and (s['rad_ratio'] or 0) >= 2) / SEGMENTS      # 없는 구간은 못 채운 것으로 센다
    line('B7', 'B3 을 채운 구간의 비율', 'long', '', seg_frac, '= 1', lambda v: v >= 1 - 1e-9, fmt='%.2f')
    amp_last = lambda r: (r['segments'][-1]['sheet_amp'] if r.get('segments') and len(r['segments']) == SEGMENTS else None)
    line('B7', '마지막 구간의 시트 두께 진폭', 'long', '', amp_last, '≥ 0.03', lambda v: v >= 0.03)
    line('B7', 'B1 (부피·음수·몸 밖)을 채움', 'long', '', lambda r: 1.0 if b1_ok(r) else 0.0, '= 1', lambda v: v > 0.5, fmt='%.0f', cont=False)

    # ───────── 덧붙임: 판정에 쓰지 않는 추가 시드 ─────────
    METRICS = (('gross_net', '정맥 총유량/순유량'), ('veinT', '정맥 최대 성분(시간 평균)'), ('rad_ratio', '반지름 p90/p10'), ('sheet_amp', '시트 두께 진폭'), ('disp300', '이동 t=0~300'), ('chord', '현의 격자 방향 비율'), ('rear_ratio', '먼/가까운 절반의 전도도'))

    def paired(title, crit, a_of, b_of, seeds, a_name, b_name):
        print(f'\n{title}')
        print('  %-26s %10s %10s %10s %9s %7s %14s %s' % ('지표', f'{a_name} 평균', f'{b_name} 평균', '차이 평균', '표준편차', 't', f'{a_name} 가 큰 수', f'{a_name} 중앙이 {b_name} 범위 안인가'))
        for k, label in METRICS:
            pr = [(a_of(s_).get(k), b_of(s_).get(k)) for s_ in seeds]; pr = [(x, y) for x, y in pr if x is not None and y is not None]
            if len(pr) < 3: continue
            a = np.array([p_[0] for p_ in pr], float); b = np.array([p_[1] for p_ in pr], float); d = a - b; sd = d.std(ddof=1); t = d.mean() / (sd / np.sqrt(d.size)) if sd > 0 else float('nan')
            inside = bool(b.min() <= np.median(a) <= b.max())
            print('  %-26s %10.3f %10.3f %+10.3f %9.3f %7.2f %11d/%d   %s (%s 범위 %.3g~%.3g, %s 중앙 %.3g)' % (label, a.mean(), b.mean(), d.mean(), sd, t, int((d > 0).sum()), d.size, '안' if inside else '밖', b_name, b.min(), b.max(), a_name, np.median(a)))
            OUT.append(dict(crit=crit, what=label, n=int(d.size), a=a_name, b=b_name, a_mean=float(a.mean()), b_mean=float(b.mean()), diff_mean=float(d.mean()), diff_sd=float(sd), t=float(t), a_higher=int((d > 0).sum()),
                            b_min=float(b.min()), b_max=float(b.max()), a_median=float(np.median(a)), inside=inside))

    extra = sorted(s_ for s_ in range(1, 100) if run('gpu', 'mig', s_) and run('numpy', 'mig', s_))
    if len(extra) > len(EXPECT[('mig', '')]):
        paired(f'덧붙임 1 — 굶은 이주의 시드 {len(extra)}개(판정에 쓰지 않은 것 포함)로 본 GPU − numpy 의 짝 차이', 'extra', lambda s_: run('gpu', 'mig', s_), lambda s_: run('numpy', 'mig', s_), extra, 'GPU', 'numpy')
    # 대조 실험: numpy 기준 모델을 float32 로 (f32 = 저장 상태만 반올림, f32s = 압력 풀이의 반복값도 float32)
    for tag, what in (('f32', '저장 상태를 스텝마다 float32 로 반올림'), ('f32s', '저장 상태 반올림 + 압력 풀이도 float32')):
        ss = sorted(s_ for s_ in range(1, 100) if run('numpy', 'mig', s_, tag) and run('numpy', 'mig', s_))
        if not ss: continue
        paired(f'덧붙임 2 ({tag}) — 대조 실험: numpy 를 float32 로 돌린 실행({what}) − 그대로의 numpy (굶은 이주, 시드 {len(ss)}개)', f'extra_{tag}', lambda s_, tag=tag: run('numpy', 'mig', s_, tag), lambda s_: run('numpy', 'mig', s_), ss, tag, 'numpy')
        both = [s_ for s_ in ss if run('gpu', 'mig', s_)]
        if both: paired(f'           같은 시드의 GPU − {tag} (시드 {len(both)}개)', f'extra_gpu_{tag}', lambda s_: run('gpu', 'mig', s_), lambda s_, tag=tag: run('numpy', 'mig', s_, tag), both, 'GPU', tag)
    longs = sorted(s_ for s_ in range(1, 100) if run('gpu', 'long', s_) or run('numpy', 'long', s_))
    if len(longs) > len(EXPECT[('long', '')]):
        print(f'\n덧붙임 3 — 지속 실행의 시드를 늘려 본 것 (판정 뒤에 더했다. 시드 {longs})')
        print('  %-6s %4s %8s %10s %16s %12s %12s %14s' % ('출처', '시드', '끝 넓이', '젖음 바뀜', 'B3 채운 구간/5', '정맥 최소', '몸 밖 최대', '끝 구간 진폭'))
        agg = {}
        for origin in ('gpu', 'numpy'):
            for s_ in longs:
                r = run(origin, 'long', s_)
                if r is None: continue
                segs = r.get('segments') or []
                row = dict(area=r.get('area_end'), turnover=r.get('turnover'), seg_ok=sum(1 for g_ in segs if (g_['veinT'] or 0) >= 0.8 and (g_['strahler'] or 0) >= 4 and (g_['rad_ratio'] or 0) >= 2),
                           vein_min=min((g_['veinT'] or 0) for g_ in segs) if segs else None, out_max=r.get('out_frac'), amp=segs[-1]['sheet_amp'] if len(segs) == SEGMENTS else None)
                agg.setdefault(origin, []).append(row)
                print('  %-6s %4d %8s %10s %16s %12s %12s %14s' % (origin, s_, f(row['area'], '%d'), f(row['turnover'], '%.3f'), f'{row["seg_ok"]}/{SEGMENTS}', f(row['vein_min'], '%.3f'), f(row['out_max'], '%.3f'), f(row['amp'], '%.3f')))
        for k, label in (('area', '끝 넓이'), ('turnover', '젖음이 바뀌는 셀의 비율'), ('seg_ok', 'B3 을 채운 구간 수'), ('vein_min', '구간별 정맥 최대 성분의 최소'), ('out_max', '몸 밖 부피의 최대'), ('amp', '끝 구간의 진폭')):
            g_ = have([r_[k] for r_ in agg.get('gpu', [])]); n_ = have([r_[k] for r_ in agg.get('numpy', [])])
            if len(g_) >= 3 and len(n_) >= 3:
                inside = within(g_, n_)
                print(f'  {label}: GPU 중앙 {f(med(g_))} (범위 {f(min(g_))}~{f(max(g_))}), numpy 중앙 {f(med(n_))} (범위 {f(min(n_))}~{f(max(n_))}) → GPU 중앙이 numpy 범위(±5%) {"안" if inside else "밖"}')
                OUT.append(dict(crit='extra_long', what=label, n_gpu=len(g_), n_numpy=len(n_), gpu=g_, numpy=n_, gpu_median=med(g_), numpy_median=med(n_), inside=inside))

    # ───────── 요약 ─────────
    print('\n요약 — 기준별로 GPU 가 numpy 와 같은가 / 모델이 기준을 넘는가 ("(견줌)" 줄과 들여 쓴 보조 줄은 뺀다)')
    for c in ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'):
        rows = [o for o in OUT if o['crit'] == c and '(견줌)' not in o['what'] and not o['what'].startswith('이동 거리')]
        same = [o['same'] for o in rows]; ok = [o['ok'] for o in rows]
        print(f'  {c}: 같은가 {sum(1 for v in same if v)}/{len(same)} 줄' + (f' (판정 불가 {sum(1 for v in same if v is None)})' if None in same else '') + f', 기준 {sum(1 for v in ok if v)}/{len(ok)} 줄'
              + ('' if all(v for v in ok) else '   ← 넘지 못한 줄: ' + ', '.join(o['what'] for o in rows if not o['ok']))
              + ('' if not any(v is False for v in same) else '   ← 다른 줄: ' + ', '.join(o['what'] for o in rows if o['same'] is False)))
    if '--json' in sys.argv:
        json.dump(OUT, open(sys.argv[sys.argv.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
