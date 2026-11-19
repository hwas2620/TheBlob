#!/usr/bin/env python3
"""RESULT-B.tmpl.md 의 자리표시({{…}})를 판정 출력(judge_b.py)으로 채워 RESULT-B.md 를 쓴다.

usage: python3 make_result_b.py      (이 폴더의 RESULT-B.tmpl.md → RESULT-B.md, results/b_judge.txt, results/b_judge.json)
글을 고칠 때는 RESULT-B.md 가 아니라 RESULT-B.tmpl.md 를 고치고 이 스크립트를 다시 돌린다.

자리표시
  {{B1}} … {{B7}}   기준별 표 (줄마다 GPU·numpy 의 시드별 값, 문턱을 넘은 수, 판정 둘)
  {{SUMMARY}}       기준별 요약 (같은가 몇 줄, 기준 몇 줄)
  {{EXTRA}}         판정에 쓰지 않은 추가 시드로 본 GPU − numpy 의 짝 차이
  {{F32}}, {{F32S}}, {{GPU_F32S}}   float32 대조 실험의 짝 차이 (float32 로 돌린 numpy − numpy 두 가지, GPU − float32 로 돌린 numpy)
  {{LONG5}}         지속 실행의 시드를 늘려 본 표 (판정 출력에서 그대로)
"""
import json, math, os, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
jpath = os.path.join(ROOT, 'results', 'b_judge.json')
text = subprocess.run([sys.executable, os.path.join(ROOT, 'judge_b.py'), '--json', jpath], capture_output=True, text=True)
if text.returncode != 0: raise SystemExit(text.stderr)
open(os.path.join(ROOT, 'results', 'b_judge.txt'), 'w', encoding='utf-8').write(text.stdout)
rows = json.load(open(jpath, encoding='utf-8'))


def fv(x, fmt):
    if x is None: return '없음'
    if isinstance(x, list): return '%.1f셀 %.0f°' % (x[0], x[1])
    if isinstance(x, float) and math.isinf(x): return '∞'
    return fmt % x


def mark(v, yes, no): return '판정 불가' if v is None else (yes if v else no)


def table(crit):
    out = ['| 무엇을 | 문턱 | GPU (시드 순) | numpy (시드 순) | 넘은 수 GPU / numpy | 같은가 | 기준 |', '|---|---|---|---|---|---|---|']
    for r in rows:
        if r['crit'] != crit: continue
        if 'gpu' in r:
            fmt = r.get('fmt', '%.3g'); g = ' / '.join(fv(v, fmt) for v in r['gpu']) or '-'; n = ' / '.join(fv(v, fmt) for v in r['numpy']) or '-'
        else:      # B5: 시드별 가장 가는 쌍의 배율
            g = '배율 ' + ' / '.join(fv(v, '%.1f') for v in r['minratio_gpu']) + f" · 굵은 쌍 {r['thick_gpu'][0]}/{r['thick_gpu'][1]}"
            n = '배율 ' + ' / '.join(fv(v, '%.1f') for v in r['minratio_numpy']) + f" · 굵은 쌍 {r['thick_numpy'][0]}/{r['thick_numpy'][1]}"
        out.append(f"| {r['what']} | {r['thr']} | {g} | {n} | {r['gpu_pass']}/{r['n_gpu']} · {r['numpy_pass']}/{r['n_numpy']} | {mark(r['same'], '같음', '**다름**')} | {mark(r['ok'], '통과', '**불통과**')} |")
    return '\n'.join(out)


def summary():
    out = ['| 기준 | GPU 가 numpy 와 같은가 | 모델이 기준을 넘는가 | 넘지 못한 줄 / 다르게 나온 줄 |', '|---|---|---|---|']
    names = dict(B1='B1 질량', B2='B2 전진면', B3='B3 정맥', B4='B4 맥동', B5='B5 먹이', B6='B6 점액', B7='B7 지속')
    for c in ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'):
        rs = [r for r in rows if r['crit'] == c and '(견줌)' not in r['what'] and not r['what'].startswith('이동 거리')]
        same = [r['same'] for r in rs]; ok = [r['ok'] for r in rs]
        notes = []
        if any(v is False for v in ok): notes.append('못 넘음: ' + ', '.join(r['what'] for r in rs if r['ok'] is False))
        if any(v is False for v in same): notes.append('다름: ' + ', '.join(r['what'] for r in rs if r['same'] is False))
        if any(v is None for v in same): notes.append('판정 불가: ' + ', '.join(r['what'] for r in rs if r['same'] is None))
        out.append(f"| {names[c]} | {sum(1 for v in same if v)}/{len(same)} 줄 | {sum(1 for v in ok if v)}/{len(ok)} 줄 | {' · '.join(notes) or '-'} |")
    return '\n'.join(out)


def paired_table(crit):
    """덧붙임의 짝 차이 표 (judge_b.py 의 paired)"""
    rs = [r for r in rows if r['crit'] == crit]
    if not rs: return '(실행이 없다)'
    a, b = rs[0]['a'], rs[0]['b']
    out = [f"| 지표 (시드 {rs[0]['n']}개) | {a} 평균 | {b} 평균 | 차이의 평균 | 차이의 표준편차 | t | {a} 가 큰 시드 | {a} 중앙이 {b} 범위 안인가 |", '|---|---|---|---|---|---|---|---|']
    for r in rs:
        out.append(f"| {r['what']} | {r['a_mean']:.3f} | {r['b_mean']:.3f} | {r['diff_mean']:+.3f} | {r['diff_sd']:.3f} | {r['t']:.2f} | {r['a_higher']}/{r['n']} | {'안' if r['inside'] else '**밖**'} ({r['b_min']:.3g}~{r['b_max']:.3g}, 중앙 {r['a_median']:.3g}) |")
    return '\n'.join(out)


def block(title):
    """판정 출력에서 '덧붙임 N' 덩어리를 그대로 가져온다"""
    lines = text.stdout.split('\n'); out = []; on = False
    for ln in lines:
        if ln.startswith(title): on = True
        elif on and (ln.startswith('덧붙임') or ln.startswith('요약')): break
        if on: out.append(ln)
    return '```\n' + '\n'.join(out).rstrip() + '\n```' if out else '(실행이 없다)'


tmpl = open(os.path.join(ROOT, 'RESULT-B.tmpl.md'), encoding='utf-8').read()
out = (tmpl.replace('{{SUMMARY}}', summary()).replace('{{EXTRA}}', paired_table('extra')).replace('{{F32}}', paired_table('extra_f32')).replace('{{F32S}}', paired_table('extra_f32s'))
       .replace('{{GPU_F32S}}', paired_table('extra_gpu_f32s')).replace('{{LONG5}}', block('덧붙임 3')))
for c in ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7'): out = out.replace('{{%s}}' % c, table(c))
assert '{{' not in out, [x[:40] for x in out.split('{{')[1:]][:3]
open(os.path.join(ROOT, 'RESULT-B.md'), 'w', encoding='utf-8').write(out)
print(text.stdout.split('요약 —')[-1])
