#!/usr/bin/env python3
"""RESULT-A.tmpl.md 의 자리표시({{…}})를 판정 출력(judge_a12.py)과 측정 기록(results/bench.json, results/glcalls.json, results/margin_*.json)으로 채워 RESULT-A.md 를 쓴다.

usage: python3 make_result.py      (이 폴더의 RESULT-A.tmpl.md → RESULT-A.md)
글을 고칠 때는 RESULT-A.md 가 아니라 RESULT-A.tmpl.md 를 고치고 이 스크립트를 다시 돌린다.
"""
import glob, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
tmpl = open(os.path.join(ROOT, 'RESULT-A.tmpl.md'), encoding='utf-8').read()
judge = subprocess.run([sys.executable, os.path.join(ROOT, 'judge_a12.py')], capture_output=True, text=True).stdout.rstrip('\n')

runs = {}
for p in sorted(glob.glob(os.path.join(ROOT, 'results', 'a12_*.json'))):
    j = json.load(open(p)); runs[j['name']] = j['result']['a12']
# 기준 설정의 1만 스텝 실행만 센다 (다시 돌린 것과 다른 설정(tag)의 실행은 뺀다)
full = {k: a for k, a in runs.items() if a['stepsDone'] >= 10000 and not k.endswith(('_final', '_zero')) and not a.get('tag')}
n_a1 = len(full)
fm = [a['fluxErr']['median'] for a in full.values() if a['cycles'] == 2]
fp = [a['fluxErr']['p99'] for a in full.values() if a['cycles'] == 2]
print('1만 스텝 실행', n_a1, '유량 오차 중앙', min(fm), max(fm), '99백분위', min(fp), max(fp))

bench = json.load(open(os.path.join(ROOT, 'results', 'bench.json')))['result']['bench']
V = ['기준형', '합친 패스', '합친 패스 + 두 번 스무딩', '합친 패스 + 몸 주변만 + 두 번 스무딩']
draws = {}
for r in bench['rows']:
    if r['cycles'] == 2 and not r.get('tag'): draws[(r['N'], r['variant'])] = r
glc = json.load(open(os.path.join(ROOT, 'results', 'glcalls.json')))['result']['bench']
differ = []
for r in glc['rows']:
    if r['cycles'] == 2 and not r.get('tag'):
        k = (r['N'], r['variant'])
        if k in draws and draws[k]['drawCalls'] != r['drawCalls']: differ.append((k, draws[k]['drawCalls'], r['drawCalls']))
        draws[k] = r
print('bench.json 과 드로콜 수가 다른 줄:', differ)
sizes = sorted({k[0] for k in draws})
lines = ['| 계산 방식 | ' + ' | '.join(f'{n}²' for n in sizes) + ' |', '|---|' + '---|' * len(sizes)]
names = {'기준형': '기준형', '합친 패스': '합친 패스', '합친 패스 + 몸 주변만': '합친 패스 + 몸 주변만', '합친 패스 + 두 번 스무딩': '합친 패스 + 두 번 스무딩 (전체 격자)',
         '합친 패스 + 몸 주변만 + 두 번 스무딩': '합친 패스 + 몸 주변만 + 두 번 스무딩'}
for v in ['기준형', '합친 패스', '합친 패스 + 몸 주변만', '합친 패스 + 두 번 스무딩', '합친 패스 + 몸 주변만 + 두 번 스무딩']:
    cells = []
    for n in sizes:
        r = draws.get((n, v))
        cells.append('-' if not r else (f"{r['drawCalls']}" + (f" + 지우기 {r['passes'] - r['drawCalls']}" if r.get('passes', r['drawCalls']) > r['drawCalls'] else '')
                                        + (f" (그린 영역 {r['activeFraction'] * 100:.0f}%)" if r['activeFraction'] < 0.999 else '')))
    lines.append(f'| {names[v]} | ' + ' | '.join(cells) + ' |')
btab = '\n'.join(lines) + f"\n\n속도 측정 모드로 센 값이다(`results/glcalls.json`" + (". 256²와 384²는 `results/bench.json`의 값과 같다" if not differ else ". `results/bench.json`은 더 오래 돌려 가위 사각형의 여유가 더 크고, 그래서 두 번 스무딩을 쓰는 레벨 수가 달라 드로콜 수가 다른 줄이 있다: " + ', '.join(f"{k[0]}² {k[1]} {a}" for k, a, b in differ)) + f"). 몸은 굶은 이주의 400스텝째 것(약 1900셀)이다."
gl_lines = ['| 계산 방식 | ' + ' | '.join(f'{n}²' for n in sizes) + ' |', '|---|' + '---|' * len(sizes)]
for v in ['기준형', '합친 패스', '합친 패스 + 몸 주변만', '합친 패스 + 두 번 스무딩', '합친 패스 + 몸 주변만 + 두 번 스무딩']:
    gl_lines.append(f'| {names[v]} | ' + ' | '.join(str(draws[(n, v)]['glCalls']) if (n, v) in draws and 'glCalls' in draws[(n, v)] else '-' for n in sizes) + ' |')
byname = sorted(glc['glByName'].items(), key=lambda kv: -kv[1])
tot = sum(v for _, v in byname)
gl_byname = ', '.join(f'`{k}` {v:g}' for k, v in byname if v >= 10) + f", 나머지 {sum(v for _, v in byname if v < 10):g} (합 {tot:g})"
gl_vals = [draws[k]['glCalls'] for k in draws if 'glCalls' in draws[k]]
gl_min, gl_max = str(round(min(gl_vals), -1)), str(round(max(gl_vals), -1))
gl_texpct = round(100 * (glc['glByName'].get('bindTexture', 0) + glc['glByName'].get('activeTexture', 0)) / tot)
num = dict(NRUN=str(n_a1), FLUX_MED=f'{min(fm):.2f}~{max(fm):.2f}', FLUX_P99=f'{min(fp):.2f}~{max(fp):.2f}')
for n in (256, 384, 512, 768):
    num[f'D{n}'] = [str(draws[(n, v)]['drawCalls']) if (n, v) in draws else '-' for v in V]
sw = {(r['N'], r['variant']): r for r in bench['rows'] if r['cycles'] == 2 and not r.get('tag')}

# 여유 규칙의 대조 실행: 같은 실행을 가위 사각형만 바꿔 돌린 것 (results/margin_*.json). 끝 상태 요약이 묶음 안에서 모두 같아야 한다
MARGIN = [
    ('굶은 이주', [('margin_a_full', '전체 격자 (가위 없음)'), ('margin_a_hard_sync', '옛 여유, 그 자리에서 읽기 (8스텝마다)'), ('margin_a_hard_y24', '옛 여유, 멈춤 없이 읽기 (24스텝마다 도착)'),
                   ('margin_a_soft_y12', '새 여유, 멈춤 없이 읽기 (12스텝마다 도착)'), ('margin_a_soft_y24', '새 여유, 멈춤 없이 읽기 (24스텝마다 도착)'), ('margin_a_soft_y48', '새 여유, 멈춤 없이 읽기 (48스텝마다 도착)')]),
    ('먹이 셋 (규칙 8)', [('margin_b_hard_sync', '옛 여유, 그 자리에서 읽기 (8스텝마다)'), ('margin_b_soft_y24', '새 여유, 멈춤 없이 읽기 (24스텝마다 도착)'), ('margin_b_soft_y48', '새 여유, 멈춤 없이 읽기 (48스텝마다 도착)')]),
]
mlines = ['| 실행 | 가위 사각형 | 그린 넓이 평균 | 여유 사용률 최대 | 그중 새 규칙이 덜 허용한 구간 (n > 16) | 넘친 횟수 | 끝 상태 요약 |', '|---|---|---|---|---|---|---|']
msame = []
for what, group in MARGIN:
    hashes = set()
    for name, label in group:
        j = json.load(open(os.path.join(ROOT, 'results', name + '.json')))
        assert j['done'] and j['ok'], name
        a = j['result'].get('a12') or j['result']['b']
        assert a['stepsDone'] == a['steps'] and not a['nan'], name
        hashes.add(a['stateHash'])
        scissor = '없음' not in label
        soft = f"{a['marginUseSoft'] * 100:.0f}%" if a.get('softMargin') else '-'
        mlines.append(f"| {what} {a['stepsDone']}스텝 | {label} | {a['activeFractionMean'] * 100:.1f}% | " + (f"{a['marginUse'] * 100:.0f}% | {soft} | {a['marginOverruns']}" if scissor else '- | - | -') + f" | `{a['stateHash']}` |")
    msame.append(len(hashes) == 1)
    print(what, '끝 상태 요약', hashes)
assert all(msame), '끝 상태가 다른 실행이 있다'
margin = '\n'.join(mlines) + ('\n\n  묶음마다 끝 상태 요약이 모두 같다. 여유 사용률의 최대는 처음 원반이 퍼지는 첫 8스텝의 값이다(8스텝에 6~7셀. 이 구간은 두 규칙이 같고 모델이 보장한다).'
                                   ' 새 규칙이 "스텝당 한 칸"보다 덜 허용한 구간만 보면 사용률이 훨씬 낮다.')
out = (tmpl.replace('{{JUDGE}}', judge).replace('{{BENCH}}', btab).replace('{{GLCALLS}}', '\n'.join(gl_lines)).replace('{{GLBYNAME}}', gl_byname).replace('{{GLTEXPCT}}', str(gl_texpct)).replace('{{GLMIN}}', gl_min).replace('{{GLMAX}}', gl_max).replace('{{N_A1}}', str(n_a1)).replace('{{D384_V3}}', num['D384'][3])
       .replace('{{SW_384_V0}}', f"{sw[(384, '기준형')]['msPerStep']:.0f}").replace('{{SW_384_V2}}', f"{sw[(384, '합친 패스 + 몸 주변만')]['msPerStep']:.0f}").replace('{{SW_TINY}}', f"{bench['usPerTinyDraw']:.0f}").replace('{{MARGIN}}', margin))
assert '{{' not in out, [x for x in out.split('{{')[1:]][:3]
open(os.path.join(ROOT, 'RESULT-A.md'), 'w').write(out)
print(num)
