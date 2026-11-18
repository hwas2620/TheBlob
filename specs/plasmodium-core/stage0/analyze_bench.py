#!/usr/bin/env python3
"""속도 측정 결과(시험 페이지의 글 상자를 통째로 붙인 것, 또는 results/bench.json)를 읽어 무엇이 스텝의 시간을 정하는지 따진다.

usage: analyze_bench.py FILE [glcalls.json]
  FILE  글 상자의 내용을 저장한 텍스트(요약 + 빈 줄 + JSON) 또는 run_stage0.cjs 가 쓴 results/*.json
  둘째 인자를 주면 그 파일의 스텝당 GL 호출 수(count=1 로 센 것)를 호출 수 모델에 쓴다. 기본은 results/glcalls.json

내는 것
  1. 기기, 프레임 루프(게임에서 쓸 수 있는 속도), WebGPU
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
FAST_GAIN = 1.7         # dt 0.2 + 맥동 주기 8 (닿는 시각 기준. 6차 V1)


def load(path):
    text = open(path, encoding='utf-8').read()
    try:
        j = json.loads(text)
        return j['result']['bench'] if 'result' in j else j
    except json.JSONDecodeError:
        i = text.index('{"renderer"')
        return json.JSONDecoder().raw_decode(text[i:])[0]


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
    if w.get('ok'):
        print('WebGPU   : %s — 디스패치 하나 %.1fµs (패스를 따로 열면 %.1fµs)' % (w.get('adapter'), w['usPerDispatch'], w['usPerPass']))
        if 'solveRectMs' in w:
            print('           풀이 한 번 흉내 (%d², 디스패치 %d번): 몸 주변만 %.2fms, 전체 격자 %s' % (
                w['solveN'], w['solveDispatches'], w['solveRectMs'], '%.2fms' % w['solveFullMs'] if 'solveFullMs' in w else '-'))
    else:
        print('WebGPU   : 쓸 수 없음 (%s)' % w.get('error'))

    L = b.get('frameLoop')
    if L and L['rows']:
        limit = max(18.5, L['baseMs'] * 1.12)
        print('\n프레임 루프 (%d², 화면 갱신 주기 %.1fms, 지킨 것으로 보는 간격 ≤ %.1fms)' % (L['N'], L['baseMs'], limit))
        print('  프레임당 스텝  간격 평균/중앙/95백분위(ms)  초당 스텝  스텝당 ms(간격/스텝)  전진 px/s: %d² / 256² 환산 / 빠른 설정(%d²)' % (L['N'], L['N']))
        best = None
        for r in L['rows']:
            held = r['msMean'] <= limit
            if held and (best is None or r['stepsPerSec'] > best['stepsPerSec']):
                best = r
            px = CELLS_PER_STEP * r['stepsPerSec'] * MAP_PX / L['N']
            print('  %6d %s     %5.1f / %5.1f / %5.1f        %6.0f       %5.2f            %5.1f / %5.1f / %5.1f' % (
                r['spf'], '*' if held else ' ', r['msMean'], r['msMedian'], r['msP95'], r['stepsPerSec'], r['msMean'] / r['spf'], px, px * L['N'] / 256, px * FAST_GAIN))
        print('  (* = 화면 갱신을 지킴. 256² 환산은 스텝당 시간이 격자와 무관하다고 볼 때의 값)')
        if best:
            print('  → 지키는 최대: 프레임당 %d스텝, 초당 %.0f스텝' % (best['spf'], best['stepsPerSec']))
        if L.get('note'):
            print('  주의:', L['note'])

    print('\n스텝당 시간 (2사이클)  예전 방식 / 차이 방식 / 읽기의 고정 시간(ms) · 풀이 한 번: 예전 / 차이')
    for r in b['rows']:
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
        print('  %-36s 실측(예전/차이)   호출 수 모델   패스 수 모델' % '변형')
        for r in b['rows']:
            if r['N'] != N or r['cycles'] != 2:
                continue
            calls = r.get('glCalls') or gl.get((N, 2, r['variant']))
            m_calls = calls * p['glCall'] / 1000 if calls and 'glCall' in p else None
            m_pass = (r['drawCalls'] * p['tinyAlt'] + (r['passes'] - r['drawCalls']) * p['tinyClear']) / 1000
            print('  %-36s %5.2f / %5.2f      %s        %5.2f' % (r['variant'], r['msPerStep'], r.get('msDiff', float('nan')),
                                                               '%5.2f (%d번)' % (m_calls, calls) if m_calls is not None else '  -  ', m_pass))
        print('  (호출 수 모델은 호출 하나를 가장 가벼운 호출의 비용으로 친 아래쪽 값이다. 그리기와 타깃 전환의 비용은 패스 수 모델 쪽에 들어 있다)')

    g = b.get('groups') or []
    if g:
        tot = sum(x['msPerStep'] for x in g)
        ref = next((r for r in b['rows'] if r['N'] == N and r['cycles'] == 2 and r['variant'] == '합친 패스 + 몸 주변만'), None)
        print('\n묶음별 (%s², 합친 패스 + 몸 주변만, 2사이클): 합 %.2fms%s' % (N, tot, ' — 같은 변형의 실측 %.2f(예전) / %.2f(차이)' % (ref['msPerStep'], ref.get('msDiff', float('nan'))) if ref else ''))
        for x in sorted(g, key=lambda x: -x['msPerStep']):
            print('  %-18s 패스 %3d × %7.1fµs = %6.3fms (%4.1f%%)' % (x['group'], x['passesPerStep'], x['usPerPass'], x['msPerStep'], 100 * x['msPerStep'] / tot if tot else 0))
    if b.get('errors'):
        print('\n끝까지 재지 못한 격자:', b['errors'])


if __name__ == '__main__':
    main()
