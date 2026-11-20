#!/usr/bin/env python3
"""[검증] 덧붙인 실행(탐색)의 표: 더 오래(T=4000), 규칙 가르기(vbm, vsat), 굶은 이주 256², 세기 바꾸기.

usage: extra_tables.py [--json OUT]
읽는 것: verify/summaries/numpy_<실행>.json, extra_<실행>.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); V = os.path.normpath(os.path.join(HERE, '..'))
OUT = {}


def S(scn, seed, tag, kind='numpy'):
    p = os.path.join(V, 'summaries', f'{kind}_b_{scn}_s{seed}_{tag}.json')
    return json.load(open(p)) if os.path.exists(p) else None


def f(x, fmt='%.3f'):
    if x is None: return '없음'
    if isinstance(x, bool): return '예' if x else '아니오'
    return fmt % x


def long_row(seed, tag, label=None):
    a, e = S('long', seed, tag), S('long', seed, tag, 'extra')
    if a is None or e is None: return None
    sr = e['series']; t = np.array(sr['t']); o = np.array(sr['out'], float); os_ = np.array([v if v is not None else 0.0 for v in sr['out_strip']], float)
    dw = np.array([d[0] for d in sr['disc_wet']]); late = t >= 400
    cuts = [q for q in e['cuts'] if q.get('joined') and q['out'] < 0.10 and q['out_strip'] >= 0.10]
    r = dict(seed=seed, tag=tag, label=label or tag, T=e['T'], out=a['out_frac'], strip_max=float(os_.max()), frac_out=float((o >= 0.10).mean()), frac_strip=float((os_ >= 0.10).mean()),
             area_end=sr['area'][-1], thin_end=sr['thin'][-1], mem_end=sr['memonly'][-1], vthin_end=sr['vthin'][-1], disc_wet_frac=float((dw[late] > 0).mean()), neg_end=a['neg_end'], turnover=a.get('turnover'),
             ever_wet=e['ever_wet'], new=[x[2] for x in e['new_by_window']], new_edges=[x[0] for x in e['new_by_window']] + [e['new_by_window'][-1][1]],
             carry_med=float(np.median([q['carry'] for q in cuts])) if cuts else None, bnC_med=float(np.median([q['bnC'] for q in cuts])) if cuts else None, n_nominal=len(cuts),
             V_crumb=e['vol']['V_crumb'], crumb_cells=e['vol']['crumb_cells'], veinT=a.get('veinT'), sheet_amp=a.get('sheet_amp'), segs=a.get('segments'),
             last_new=e.get('last_new_t'), last_dry=e.get('last_dry_t'), still_for=e.get('still_for'))
    return r


def long_table(title, items, key):
    print('\n## ' + title)
    print('| 시드 | 규칙 | out_frac (채점기) | 기억 셀을 지운 뒤의 최대 | 갈라져 있던 시각의 비율 (채점기 정의 / 지운 뒤) | 끝 넓이 | 끝의 얇은 셀 (그 가운데 기억으로만) | 얇은 셀의 부피 비율 | 유인원 원반이 젖어 있던 비율 (t≥400) | 새로 젖은 셀 (구간별) | 한 번이라도 젖은 셀 | 음수 스텝 | 가닥으로만 이어진 시각 수 (병목 C 중앙, 한 주기 오가는 비율 중앙) | 마지막으로 젖은 시각 (끝까지 변화 없던 시간) |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    rows = []
    for seed, tag, label in items:
        r = long_row(seed, tag, label)
        if r is None: print(f'| {seed} | {label} | 없음 |' + ' |' * 10); continue
        rows.append(r)
        print(f"| {seed} | {label} | {r['out']:.3f} | {r['strip_max']:.3f} | {r['frac_out']:.2f} / {r['frac_strip']:.2f} | {r['area_end']} | {r['thin_end']} ({r['mem_end']}) | {r['vthin_end']:.3f} | {r['disc_wet_frac']:.2f} | {' / '.join('%.0f' % v for v in r['new'])} | {r['ever_wet']} | {r['neg_end']} | {r['n_nominal']} ({f(r['bnC_med'], '%.2g')}, {f(r['carry_med'], '%.1e')}) | {f(r['last_new'], '%.0f')} ({f(r['still_for'], '%.0f')}) |")
    OUT[key] = rows
    return rows


def t4000():
    print('\n## 더 오래 (T=4000): 구간별 값')
    for seed, tag in ((21, 'v0T4'), (21, 'v0T4st'), (21, 'vpkT4st'), (22, 'v0T4st'), (22, 'vpkT4st')):
        e = S('long', seed, tag, 'extra'); a = S('long', seed, tag)
        if e is None: print(f'  시드 {seed} {tag}: 없음'); continue
        sr = e['series']; t = np.array(sr['t']); segs = [(0, 400), (400, 800), (800, 1200), (1200, 1600), (1600, 2000), (2000, 2400), (2400, 2800), (2800, 3200), (3200, 3600), (3600, 4000.5)]
        m = lambda k: [float(np.mean([v for v, tt in zip(sr[k], t) if lo < tt <= hi])) for lo, hi in segs]
        mx = lambda k: [float(np.max([(v if v is not None else 0.0) for v, tt in zip(sr[k], t) if lo < tt <= hi])) for lo, hi in segs]
        body = [a_ - th for a_, th in zip(m('area'), m('thin'))]
        print(f'  시드 {seed} {tag}: out_frac(채점기) {a["out_frac"]:.3f}, 음수 스텝 {a["neg_end"]}, V_crumb {e["vol"]["V_crumb"]:.4f} ({e["vol"]["crumb_cells"]}셀), 마지막으로 젖은 시각 {f(e.get("last_new_t"), "%.1f")}, 마지막으로 마른 시각 {f(e.get("last_dry_t"), "%.1f")}')
        print('    구간 끝        : ' + ' / '.join('%d' % hi for lo, hi in segs))
        print('    넓이           : ' + ' / '.join('%.0f' % v for v in m('area')))
        print('    얇은 셀        : ' + ' / '.join('%.0f' % v for v in m('thin')))
        print('    넓이 − 얇은 셀 : ' + ' / '.join('%.0f' % v for v in body))
        print('    얇은 셀의 부피 : ' + ' / '.join('%.3f' % v for v in m('vthin')))
        print('    몸 밖(채점기)  : ' + ' / '.join('%.3f' % v for v in mx('out')))
        print('    몸 밖(지운 뒤) : ' + ' / '.join('%.3f' % v for v in mx('out_strip')))
        print('    새로 젖은 셀   : ' + ' / '.join('%.0f' % x[2] for x in e['new_by_window']) + '   (구간: ' + ' '.join('%d~%d' % (x[0], x[1]) for x in e['new_by_window']) + ')')
        OUT[f'T4000_s{seed}_{tag}'] = dict(area=m('area'), thin=m('thin'), vthin=m('vthin'), out=mx('out'), out_strip=mx('out_strip'), new=[x[2] for x in e['new_by_window']], out_frac=a['out_frac'])


def mig256():
    print('\n## 굶은 이주 256² (포만 항이 유인원에 닿은 뒤 판의 75.6% 에 걸린다)')
    print('| 시드 | 규칙 | disp300 | 각 | veinT | vein4 | gross_net | out_frac | 닿은 시각 | 넓이 t=400 | 새로 젖은 셀 0~100 / 100~200 / 200~300 / 300~400 | 얇은 셀(끝) | 음수 스텝 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    rows = []
    for seed in (21, 22, 23):
        for tag in ('v0', 'vpk'):
            a, e = S('mig256', seed, tag), S('mig256', seed, tag, 'extra')
            if a is None or e is None: print(f'| {seed} | {tag} | 없음 |' + ' |' * 10); continue
            nw = [x[2] for x in e['new_by_window']]
            print(f"| {seed} | {tag} | {f(a.get('disp300'), '%.2f')} | {f(a.get('disp_angle'), '%.1f')} | {f(a['veinT'])} | {f(a['vein4'])} | {f(a['gross_net'])} | {a['out_frac']:.4f} | {f(a['t_touch'][0], '%.1f')} | {a['area_end']} | {' / '.join('%.0f' % v for v in nw)} | {e['series']['thin'][-1]} | {a['neg_end']} |")
            rows.append(dict(seed=seed, tag=tag, disp300=a.get('disp300'), veinT=a['veinT'], vein4=a['vein4'], gross_net=a['gross_net'], out=a['out_frac'], area=a['area_end'], new=nw, t_touch=a['t_touch'][0]))
    OUT['mig256'] = rows


def food4_sens():
    print('\n## 먼 먹이 넷: 포만의 세기를 바꾸면 (sat_k 0.3 / 0.4 = 후보 / 0.5)')
    print('| 시드 | 규칙 | 닿은 시각 | 모두 닿음 | out_frac | 굵은 쌍 | 같은 성분 ≥ 0.9 인 쌍 | 통과 | 끝에 본체가 덮고 있는 먹이 | 먹은 양 | 음수 스텝 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    rows = []
    for seed in (21, 22, 23):
        for tag, label in (('v0', '지금 규칙'), ('vsk03', 'sat_k=0.3'), ('vpk', 'sat_k=0.4 (후보)'), ('vsk05', 'sat_k=0.5')):
            a, e = S('food4', seed, tag), S('food4', seed, tag, 'extra')
            if a is None or e is None: print(f'| {seed} | {label} | 없음 |' + ' |' * 8); continue
            q = e.get('food_body') or {}
            print(f"| {seed} | {label} | {'/'.join(f(v, '%.0f') for v in a['t_touch'])} | {f(a['reached'])} | {a['out_frac']:.3f} | {a['thick']}/{a['pairs']} | {a['same_ok']} | {f(a['pass'])} | {''.join('O' if x else 'x' for x in q.get('end_by_body', []))} | {e['vol']['Vinj']:.0f} | {a['neg_end']} |")
            rows.append(dict(seed=seed, tag=tag, reached=a['reached'], out=a['out_frac'], thick=a['thick'], passed=a['pass'], end_by_body=q.get('end_by_body'), vinj=e['vol']['Vinj'], neg_end=a['neg_end']))
    OUT['food4_sens'] = rows


def main():
    long_table('오래 굶긴 실행: 어느 규칙이 일을 하는가 (v0 = 지금 규칙, vpk = 묶음, vbm = 기억만 [bridge_mem=50 crumb_dry=1], vsat = 포만만 [sat_k=0.4 sat_scent=0.5 crumb_dry=1])',
               [(s, t, t) for s in (21, 22, 23) for t in ('v0', 'vpk', 'vbm', 'vsat')], 'long_decomp')
    long_table('오래 굶긴 실행: 기억의 문턱을 바꾸면 (bridge_mem 25 / 50 = 후보 / 100)',
               [(s, t, lab) for s in (21, 22) for t, lab in (('vbm25', 'bridge_mem=25'), ('vpk', 'bridge_mem=50 (후보)'), ('vbm100', 'bridge_mem=100'))], 'long_sens')
    long_table('더 오래 (T=4000). st = 흔적이 옅어지는 설정(slime_tau=300)', [(21, 'v0T4', '지금 규칙 T=4000'), (21, 'v0T4st', '지금 규칙 T=4000 st'), (21, 'vpkT4st', '후보 T=4000 st'),
                (22, 'v0T4st', '지금 규칙 T=4000 st'), (22, 'vpkT4st', '후보 T=4000 st')], 'long_T4000')
    t4000(); mig256(); food4_sens()
    if '--json' in sys.argv: json.dump(OUT, open(sys.argv[sys.argv.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
