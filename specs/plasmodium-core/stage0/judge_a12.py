#!/usr/bin/env python3
"""관문 A 의 A1·A2 판정: GPU 긴 실행(results/a12_*.json)을 numpy 기준(ref/a12_*.json)과 견준다.

usage: judge_a12.py            모든 결과를 판정해 표로 낸다
       judge_a12.py --traj R   실행 R 의 궤적을 기준과 나란히 낸다

기준 (plan.md Step 6):
  A1  NaN 없음, 스텝 끝 음수 두께 0, 최대 전도도 ≤ numpy 멀티그리드 실행의 3배
  A2  유량 오차(50스텝마다) 중앙 ≤ 0.15, 99백분위 ≤ 0.4.
      이동 거리와 유인원에 닿는 시각이 numpy 직접 풀이 실행의 ±10% 안.

이동 거리는 토러스의 최소 상 무게중심으로 잰다. 몸이 무게중심에서 격자 절반(N/2)까지 퍼지면 이 값은 뜻이 없다.
192² 에서는 출발점 근처에 남은 꼬리 때문에 t≈360 부터 그렇게 된다(numpy 저장 상태: t=250 에 70셀, t=500 에 95셀로 포화).
그래서 192² 는 t=0~300, 384² 이상은 t=0~400 으로 판정하고, 계획에 적은 t=0~400 값은 192² 에서도 그대로 함께 적는다.
"""
import glob, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    return json.load(open(path)) if os.path.exists(path) else None


def at(traj, t):
    for r in traj:
        if abs(r[0] - t) < 1e-6:
            return r
    return None


def disp(traj, t0, t1):
    a, b = at(traj, t0), at(traj, t1)
    return math.hypot(b[1] - a[1], b[2] - a[2]) if a and b else None


def ref(N, seed, solver, tag=None):
    return load(os.path.join(HERE, 'ref', f'a12_N{N}_s{seed}_{solver}' + (f'_{tag}' if tag else '') + '.json'))


def pct(a, b):
    return None if a is None or b is None or b == 0 else (a / b - 1) * 100


def fmt(x, f='%.1f'):
    return '-' if x is None else f % x


def judge(path):
    j = load(path)
    a = j['result']['a12']
    N, seed = a['N'], a['seed']
    full = a['stepsDone'] == a['steps']
    dt = (a.get('over') or {}).get('dt', 0.1)
    mg, ex = ref(N, seed, 'mg', a.get('tag')), ref(N, seed, 'exact', a.get('tag'))
    tw = 300 if N <= 192 else 400
    rows = dict(name=j['name'], N=N, seed=seed, cycles=a['cycles'], tri=a['tri'], tag=a.get('tag'), variant=a.get('variantName', '기준형'), steps=a['stepsDone'], draws=a['drawCallsPerStep'])
    # A1
    cref = mg['Cmax_run'] if mg else None
    a1 = full and not a['nan'] and a['negEndSteps'] == 0 and (cref is None or a['cMaxRun'] <= 3 * cref)
    rows.update(nan=a['nan'], negEnd=a['negEndSteps'], hMinIn=a['hMinInStep'], cMax=a['cMaxRun'], cMaxRef=cref, volErr=a['volumeRelErr'], A1=a1)
    # A2: 유량 오차
    fe = a['fluxErr']
    a2f = fe['n'] > 0 and fe['median'] <= 0.15 and fe['p99'] <= 0.4
    rows.update(fluxMed=fe['median'], fluxP99=fe['p99'], fluxMedRef=mg['flux_err']['median'] if mg and mg.get('flux_err') else None, fluxP99Ref=mg['flux_err']['p99'] if mg and mg.get('flux_err') else None, A2flux=a2f)
    # A2: 이동 (삼각 격자를 켠 실행은 견줄 기준이 없다)
    dw, d400 = disp(a['traj'], 0, tw), disp(a['traj'], 0, 400)
    rows.update(tw=tw, dw=dw, d400=d400, touch=a['tTouch'], tWrap=a.get('tWrap'))
    if not a['tri'] and a['steps'] * dt >= tw:
        for tag, r in (('Ex', ex), ('Mg', mg)):
            if r:
                rows['dw' + tag] = disp(r['traj'], 0, tw)
                rows['d400' + tag] = disp(r['traj'], 0, 400)
                rows['touch' + tag] = r['t_touch'][0]
        e_dw, e_touch = pct(dw, rows.get('dwEx')), pct(a['tTouch'], rows.get('touchEx'))
        rows.update(e_dw=e_dw, e_touch=e_touch, e_d400=pct(d400, rows.get('d400Ex')), m_dw=pct(dw, rows.get('dwMg')), m_touch=pct(a['tTouch'], rows.get('touchMg')))
        rows['A2move'] = None if e_dw is None or e_touch is None else (abs(e_dw) <= 10 and abs(e_touch) <= 10)
        rows['A2move400'] = None if rows['e_d400'] is None or e_touch is None else (abs(rows['e_d400']) <= 10 and abs(e_touch) <= 10)
    return rows


def mark(v):
    return '-' if v is None else ('통과' if v else '불합격')


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--traj':
        j = load(os.path.join(HERE, 'results', sys.argv[2] + '.json'))
        a = j['result']['a12']
        c0 = a['N'] / 2 - 0.5
        mg, ex = ref(a['N'], a['seed'], 'mg', a.get('tag')), ref(a['N'], a['seed'], 'exact', a.get('tag'))
        dt = (a.get('over') or {}).get('dt', 0.1)
        print('t      GPU      numpy 멀티그리드   numpy 직접 풀이   (출발점에서의 거리, 셀)   GPU 몸의 범위')
        for t in range(0, int(round(a['stepsDone'] * dt)) + 1, 20):
            g = at(a['traj'], t)
            d = lambda r: fmt(math.hypot(at(r['traj'], t)[1] - c0, at(r['traj'], t)[2] - c0), '%6.1f') if r and at(r['traj'], t) else '     -'
            print('%4d  %6.1f   %s            %s            %s' % (t, math.hypot(g[1] - c0, g[2] - c0), d(mg), d(ex), fmt(g[4], '%.0f') if len(g) > 4 else '-'))
        return
    rows = [judge(p) for p in sorted(glob.glob(os.path.join(HERE, 'results', 'a12_*.json')))]
    print('A1 안정성')
    print('%-24s %-22s %6s %4s %9s %10s %7s %8s %9s  %s' % ('실행', '변형', '스텝', 'NaN', '스텝끝음수', '스텝안최소', '최대C', '기준C', '부피오차', 'A1'))
    for r in rows:
        print('%-24s %-22s %6d %4s %9d %10.1e %7.0f %8s %9.1e  %s' % (r['name'], r['variant'] + (' 삼각' if r['tri'] else ''), r['steps'], '있음' if r['nan'] else '없음', r['negEnd'], r['hMinIn'], r['cMax'], fmt(r['cMaxRef'], '%.0f'), r['volErr'], mark(r['A1'])))
    print('\nA2 정확도 — 유량 오차 (괄호는 numpy 멀티그리드 실행의 값)')
    for r in rows:
        print('%-24s 중앙 %.3f (%s)  99백분위 %.3f (%s)  %s' % (r['name'], r['fluxMed'], fmt(r['fluxMedRef'], '%.3f'), r['fluxP99'], fmt(r['fluxP99Ref'], '%.3f'), mark(r['A2flux'])))
    print('\nA2 정확도 — 이동 (직접 풀이 대비 %, 괄호는 numpy 멀티그리드 대비 %)')
    print('%-24s %5s %8s %16s %8s %16s %10s %9s %9s' % ('실행', '구간', '이동(셀)', '직접/멀티 대비', '닿은 시각', '직접/멀티 대비', '0~400 대비', '판정', '0~400 판정'))
    for r in rows:
        if 'A2move' not in r:
            print('%-24s (견줄 기준 없음) 이동 0~%d %s셀, 0~400 %s셀, 닿은 시각 %s' % (r['name'], r['tw'], fmt(r['dw']), fmt(r['d400']), fmt(r['touch'], '%.0f')))
            continue
        print('%-24s 0~%d %8s %7s%% (%5s%%) %8s %7s%% (%5s%%) %9s%% %9s %9s' % (r['name'], r['tw'], fmt(r['dw']), fmt(r['e_dw'], '%+.1f'), fmt(r['m_dw'], '%+.1f'), fmt(r['touch'], '%.0f'), fmt(r['e_touch'], '%+.1f'), fmt(r['m_touch'], '%+.1f'),
                                                                                fmt(r['e_d400'], '%+.1f'), mark(r['A2move']), mark(r['A2move400'])))
    # 변형끼리 궤적이 같은지 (같은 격자·시드·사이클)
    print('\n변형 사이의 궤적 차이 (같은 격자·시드·사이클의 기준형 대비, 무게중심 좌표의 최대 차이)')
    base = {(r['N'], r['seed'], r['cycles'], r['tri'], r['tag']): r['name'] for r in rows if r['variant'] == '기준형'}
    for r in rows:
        k = (r['N'], r['seed'], r['cycles'], r['tri'], r['tag'])
        if r['variant'] == '기준형' or k not in base:
            continue
        a = load(os.path.join(HERE, 'results', r['name'] + '.json'))['result']['a12']['traj']
        b = load(os.path.join(HERE, 'results', base[k] + '.json'))['result']['a12']['traj']
        n = min(len(a), len(b))
        dmax = max(max(abs(a[i][1] - b[i][1]), abs(a[i][2] - b[i][2])) for i in range(n))
        same = next((a[i][0] for i in range(n) if abs(a[i][1] - b[i][1]) > 1e-9 or abs(a[i][2] - b[i][2]) > 1e-9 or a[i][3] != b[i][3]), None)
        print('%-24s vs %-20s 최대 차이 %.3g셀, 처음 달라진 시각 %s (기록 %d개)' % (r['name'], base[k], dmax, '없음(끝까지 같음)' if same is None else same, n))


if __name__ == '__main__':
    main()
