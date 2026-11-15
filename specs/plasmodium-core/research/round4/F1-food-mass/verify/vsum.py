#!/usr/bin/env python3
"""[verify] vmet.summarise 를 여러 실행에 돌려 표로 찍고 summ/<run>.json 에 저장. usage: vsum.py food|mig [--exp] RUN ...   (--exp: 실험자 폴더 ../runs)"""
import json, os, sys, numpy as np, vmet
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(os.path.join(HERE, 'summ'), exist_ok=True)
kind = sys.argv[1]; args = sys.argv[2:]; exp = '--exp' in args; args = [a for a in args if a != '--exp']
base = os.path.join(HERE, '..', 'runs') if exp else os.path.join(HERE, 'runs')
for r in args:
    cache = os.path.join(HERE, 'summ', ('exp_' if exp else '') + r + '.json')
    if os.path.exists(cache): o = json.load(open(cache))
    else:
        if not os.path.exists(os.path.join(base, r, 'metrics.json')): print(r, '(아직 없음)'); continue
        o = vmet.summarise(os.path.join(base, r), kind); o.pop('rows', None); json.dump(o, open(cache, 'w'), ensure_ascii=False)
    if kind == 'food':
        f = lambda d: '/'.join(f'{v:g}' for v in d.values()) if d else '-'
        pc = '; '.join(f"{k}:{v['corr']:+.2f}({v['dphi_mean_deg']:+.0f}°)" for k, v in (o.get('pulse') or {}).items())
        print(f"{o['run']:18s} n={o['n_states']:2d} 창 {o['window'][0]:.0f}-{min(o['window'][1],9999):.0f}({o['window'][2]}) | 같은성분 C>4 {f(o.get('same4'))} C>10 {f(o.get('same10'))} C>30 {f(o.get('same30'))} | 경로최소C {f(o.get('pathminC_med'))} | 병목 중앙 {f(o.get('bottleneck_med'))} 최소 {f(o.get('bottleneck_min'))} | 정맥중앙C {o.get('vein_medC_med')} | "
              f"정맥최대 C>4 {o.get('vein4_largest_med')} C>10 {o.get('vein10_largest_med')} C>30 {o.get('vein30_largest_med')} | 몸최대부피 최소(창) {o.get('body_largest_vol_min')} (전체 {o.get('body_largest_vol_min_all')}, 끝 {o.get('body_largest_vol_end')}) | 닿음 {o['t_touch']} | 이동(추적) {o.get('disp_track')} | hmin {o.get('m_h_min_seen'):.4f} 끝음수 {o.get('m_neg_end_cellsteps')} | 부피오차 {o.get('m_mass_err_max'):.1e} | mg {[round(x,3) for x in o['m_mg_err']] if o.get('m_mg_err') else None} | 맥동상관 {pc}")
    else:
        print(f"{o['run']:18s} n={o['n_states']:2d} | 정맥최대(중앙/최소) C>4 {o['vein4_largest_med']}/{o['vein4_largest_min']} C>10 {o['vein10_largest_med']}/{o['vein10_largest_min']} C>30 {o['vein30_largest_med']}/{o['vein30_largest_min']} | 간선 C>4 {o['vein4_E_med']:.0f} C>30 {o['vein30_E_med']:.0f} | 순환 {o['cycles4_med']:.0f} | 이동 {o.get('disp_track')}@{o.get('disp_dir_deg')}° (실험자 계산 {o.get('m_disp')}, 폭 {o.get('span_xy')}) | 몸최대부피 최소 {o['body_largest_vol_min']} 조각 {o['body_ncomp_end']} | 시트진폭 {o.get('m_sheet_amp')} | hmin {o.get('m_h_min_seen'):.4f} | 부피오차 {o.get('m_mass_err_max'):.1e} | mg {[round(x,3) for x in o['m_mg_err']] if o.get('m_mg_err') else None} | 면적 {o.get('area_end')}")
