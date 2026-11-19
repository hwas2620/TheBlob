#!/usr/bin/env python3
"""속도 측정 결과(시험 페이지의 글 상자를 통째로 붙인 것, 또는 results/bench.json)를 읽어 무엇이 스텝의 시간을 정하는지 따진다.

usage: analyze_bench.py FILE [glcalls.json]
  FILE  글 상자의 내용을 저장한 텍스트(요약 + 빈 줄 + JSON) 또는 run_stage0.cjs 가 쓴 results/*.json
  둘째 인자를 주면 그 파일의 스텝당 GL 호출 수(count=1 로 센 것)를 호출 수 모델에 쓴다. 기본은 results/glcalls.json

내는 것
  1. 기기, 프레임 루프(게임에서 쓸 수 있는 속도: 몸 주변만 / 전체 격자 / 지속), WebGPU(잰 경우)
  2. 스텝당 시간: 예전 방식 / 차이 방식 / 읽기의 고정 시간
  3. 비용 모델 셋의 예측과 실측의 비교 (384², 2사이클)
       호출 수 모델   GL 호출 수 × 호출 하나의 비용 (+ 텍스처 묶기의 웃돈)
       패스 수 모델   패스 수 × 작은 타깃에 번갈아 그리는 패스 하나의 비용
       묶음 합        묶음별 (패스 수 × 패스당 시간)의 합
  4. 묶음별 몫
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_PX = 1500
CELLS_PER_STEP = 0.02   # dt 0.1
FAST_GAIN = 1.6         # dt 0.2 + 맥동 주기 8 (독립 검증의 앞면 속도 기준 1.61. 재는 법에 따라 1.47~1.75)
FAST_TAG = 'dt 0.2 + 주기 8'   # 이 줄만 스텝당 전진이 다르다 (다른 꼬리표의 줄은 기준 설정과 같다)


def load(path):
    text = open(path, encoding='utf-8').read()
    try:
        j = json.loads(text)
        return j['result']['bench'] if 'result' in j else j
    except json.JSONDecodeError:
        # 글 상자의 내용: 요약 줄들, 빈 줄, 그리고 '{"' 로 시작하는 JSON 한 줄
        i = text.index('\n{"') + 1
        return json.JSONDecoder().raw_decode(text[i:])[0]


def print_loop(L):
    """프레임 루프 하나(오름, 전체 격자, 지속. v4 까지는 내림·읽기 대조도)를 표로 낸다"""
    limit = max(18.5, L['baseMs'] * 1.12)
    print('\n프레임 루프 (%d², 화면 갱신 주기 %.1fms, 지킨 것으로 보는 간격 ≤ %.1fms)' % (L['N'], L['baseMs'], limit))
    print('  시험      프레임당 스텝  간격 평균/중앙/95백분위(ms)  늦은 프레임  그린 넓이  초당 스텝  스텝당 ms  전진 px/s: %d² / 256² 환산 / 빠른 설정(%d²)' % (L['N'], L['N']))

    def line(r):
        held = r['msMean'] <= limit
        px = CELLS_PER_STEP * r['stepsPerSec'] * MAP_PX / L['N']
        late = '%4.0f%%' % (r['late'] * 100) if 'late' in r else '    -'
        area = '%4.0f%%' % (r['area'] * 100) if 'area' in r else '    -'
        print('  %-8s %6d %s     %5.1f / %5.1f / %5.1f        %s      %s     %6.0f     %5.2f       %5.1f / %5.1f / %5.1f' % (
            r.get('label', '오름'), r['spf'], '*' if held else ' ', r['msMean'], r['msMedian'], r['msP95'], late, area, r['stepsPerSec'], r['msMean'] / r['spf'], px, px * L['N'] / 256, px * FAST_GAIN))
        return held

    def best_of(rows):
        best = None
        for r in rows:
            if line(r) and (best is None or r['stepsPerSec'] > best['stepsPerSec']):
                best = r
        return best
    best = best_of(L['rows'])
    best_full = best_of(L.get('full', []))
    for r in L.get('down', []):
        line(r)
    for r in L.get('readback', []):
        line(r)
    print('  (* = 화면 갱신을 지킴. 256² 환산은 스텝당 시간이 격자와 무관하다고 볼 때의 값)')
    if best:
        print('  → 오름 시험(몸 주변만)에서 지킨 최대: 프레임당 %d스텝, 초당 %.0f스텝, 전진 %.0fpx/s' % (best['spf'], best['stepsPerSec'], CELLS_PER_STEP * best['stepsPerSec'] * MAP_PX / L['N']))
    if L.get('full'):
        if best_full:
            print('  → 전체 격자에서 지킨 최대: 프레임당 %d스텝, 초당 %.0f스텝, 전진 %.0fpx/s' % (best_full['spf'], best_full['stepsPerSec'], CELLS_PER_STEP * best_full['stepsPerSec'] * MAP_PX / L['N']))
        else:
            print('  → 전체 격자에서는 지킨 설정이 없다')
    for S in (L.get('sustainedHard'), L.get('sustained')):
        if not S:
            continue
        v5 = bool(S['windows']) and 'box' in S['windows'][0]
        print('  지속 %.0f초%s (프레임당 %d스텝) — 2초마다 초당 스텝 / 늦은 프레임%% / 그린 넓이%%%s:' % (
            S['seconds'], ' [%s]' % S['label'] if S.get('label') else '', S['spf'], ' / 상자만의 넓이% / 여유(셀)' if v5 else ''))
        print('    ' + ', '.join(
            '%.0f/%.0f/%s' % (w['stepsPerSec'], w['late'] * 100, '%.0f' % (w['area'] * 100) if 'area' in w else '-')
            + ('/%.0f/%.0f' % (w['box'] * 100, w['margin']) if v5 else '') for w in S['windows']))
        if 'marginUse' in S:
            print('    여유 사용률 최대 %.0f%% (완만한 구간 %.0f%%), 넘친 횟수 %d' % (S['marginUse'] * 100, S.get('marginUseSoft', 0) * 100, S.get('marginOverruns', 0)))
    if L.get('note'):
        print('  주의:', L['note'])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    b = load(sys.argv[1])
    gl_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'results', 'glcalls.json')
    gl = {}
    if os.path.exists(gl_path):
        for r in load(gl_path)['rows']:
            if 'glCalls' in r:
                gl[(r['N'], r['cycles'], r['variant'])] = r['glCalls']

    print('GPU      :', b['renderer'])
    print('브라우저 :', b['userAgent'])
    w = b.get('webgpu') or {}
    if 'webgpu' not in b:
        pass   # v5 부터는 webgpu=1 로 열었을 때만 잰다
    elif w.get('ok'):
        print('WebGPU   : %s — 디스패치 하나 %.1fµs (패스를 따로 열면 %.1fµs)' % (w.get('adapter'), w['usPerDispatch'], w['usPerPass']))
        if 'solveRectMs' in w:
            print('           풀이 한 번 흉내 (%d², 디스패치 %d번): 몸 주변만 %.2fms, 전체 격자 %s%s' % (
                w['solveN'], w['solveDispatches'], w['solveRectMs'], '%.2fms' % w['solveFullMs'] if 'solveFullMs' in w else '-',
                ', 쉬지 않고 돌리면 몸 주변만 %.2fms' % w['solveRectSustainedMs'] if 'solveRectSustainedMs' in w else ''))
    else:
        print('WebGPU   : 쓸 수 없음 (%s)' % w.get('error'))

    v4 = b.get('version', 3) >= 4
    for L in (b.get('frameLoopSmall'), b.get('frameLoop')) if b.get('version', 3) >= 5 else (b.get('frameLoop'), b.get('frameLoopSmall')):
        if L and L['rows']:
            print_loop(L)

    if v4:
        print('\n지속 측정 (구성마다 쉬지 않고 %.1f초) — 스텝당 ms · 초당 스텝 · 풀이 한 번 ms · 전진 px/s' % (b.get('sustainMs', 0) / 1000))
        for r in b['rows']:
            name = r['variant'] + ('' if r['cycles'] == 2 else ' (%d사이클)' % r['cycles']) + (' [%s]' % r['tag'] if r.get('tag') else '')
            gain = FAST_GAIN if r.get('tag') == FAST_TAG else 1
            print('  %4d² %-52s 패스 %3d  %6.2f  %6.0f  %5.2f  %6.1f' % (r['N'], name, r['passes'], r['msPerStep'], r['stepsPerSec'], r['msSolve'], r['pxPerSec'] * gain))

    if not v4:
        print('\n스텝당 시간 (2사이클)  예전 방식 / 차이 방식 / 읽기의 고정 시간(ms) · 풀이 한 번: 예전 / 차이')
    for r in ([] if v4 else b['rows']):
        if r['cycles'] != 2:
            continue
        print('  %4d² %-36s 패스 %3d  %6.2f / %6.2f / %5.2f  ·  %5.2f / %5.2f' % (
            r['N'], r['variant'], r['passes'], r['msPerStep'], r.get('msDiff', float('nan')), r.get('msFixed', float('nan')), r['msSolve'], r.get('msSolveDiff', float('nan'))))

    u = b.get('unitsAB')
    if u:
        print('\n텍스처 유닛 배정 A/B (%s², 가장 빠른 방식): 고정 %.2f / 순서대로 %.2fms (차이 방식 %.2f / %.2f) → 고정이 %+.0f%%' % (
            b.get('profileN'), u['fixedMs'], u['orderMs'], u['fixedDiff'], u['orderDiff'], 100 * (u['fixedMs'] / u['orderMs'] - 1)))

    p = b.get('probes')
    if p:
        print('\n탐침 (µs): 작은 타깃 번갈아 %.1f, 같은 타깃 %.1f, 프로그램만 번갈아 %.1f, 지우기 %.1f, 격자 크기 R32F %.1f / RGBA32F %.1f / 두 장 %.1f' % (
            p['tinyAlt'], p['tinySame'], p.get('tinyProg', float('nan')), p['tinyClear'], p['bigR32F'], p['bigRGBA'], p['bigMRT']))
        if 'glCall' in p:
            print('           GL 호출 하나 %.2f, 텍스처 묶기 하나 %.2f, 쉬는 읽기 한 번 %.0f' % (p['glCall'], p['bindTex'], p.get('syncIdle', float('nan'))))

    N = b.get('profileN')
    if p and N:
        print('\n비용 모델의 예측 (%d², 2사이클, ms/스텝)' % N)
        print('  %-36s %s   호출 수 모델   패스 수 모델' % ('변형', '실측(지속)      ' if v4 else '실측(예전/차이)'))
        for r in b['rows']:
            if r['N'] != N or r['cycles'] != 2 or r.get('tag'):
                continue
            calls = r.get('glCalls') or gl.get((N, 2, r['variant']))
            m_calls = calls * p['glCall'] / 1000 if calls and 'glCall' in p else None
            m_pass = (r['drawCalls'] * p['tinyAlt'] + (r['passes'] - r['drawCalls']) * p['tinyClear']) / 1000
            print('  %-36s %s      %s        %5.2f' % (r['variant'], '%5.2f        ' % r['msPerStep'] if v4 else '%5.2f / %5.2f' % (r['msPerStep'], r.get('msDiff', float('nan'))),
                                                               '%5.2f (%d번)' % (m_calls, calls) if m_calls is not None else '  -  ', m_pass))
        print('  (호출 수 모델은 호출 하나를 가장 가벼운 호출의 비용으로 친 아래쪽 값이다. 그리기와 타깃 전환의 비용은 패스 수 모델 쪽에 들어 있다)')

    g = b.get('groups') or []
    if g:
        tot = sum(x['msPerStep'] for x in g)
        ref = next((r for r in b['rows'] if r['N'] == N and r['cycles'] == 2 and r['variant'] == '합친 패스 + 몸 주변만' and not r.get('tag')), None)
        meas = '' if not ref else (' — 같은 변형의 지속 측정 %.2fms (묶음별은 짧게 몰아서 잰 값이라 더 크게 나온다)' % ref['msPerStep'] if v4
                                  else ' — 같은 변형의 실측 %.2f(예전) / %.2f(차이)' % (ref['msPerStep'], ref.get('msDiff', float('nan'))))
        print('\n묶음별 (%s², 합친 패스 + 몸 주변만, 2사이클): 합 %.2fms%s' % (N, tot, meas))
        for x in sorted(g, key=lambda x: -x['msPerStep']):
            print('  %-18s 패스 %3d × %7.1fµs = %6.3fms (%4.1f%%)' % (x['group'], x['passesPerStep'], x['usPerPass'], x['msPerStep'], 100 * x['msPerStep'] / tot if tot else 0))
    if b.get('errors'):
        print('\n끝까지 재지 못한 격자:', b['errors'])


if __name__ == '__main__':
    main()
