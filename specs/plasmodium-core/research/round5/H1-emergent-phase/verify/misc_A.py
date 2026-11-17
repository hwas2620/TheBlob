#!/usr/bin/env python3
"""[verify5] 작성자 저장 자료에서 M1, M3, (c) 다른 배치, 먹이 넷(256²)을 다시 잰 표. 출력: out_A_misc.txt"""
import json, os, numpy as np, vmet
A = '..'; V4 = os.path.join('..', '..', '..', 'research4', 'F1-food-mass', 'verify')
f3 = lambda d: '/'.join('%g' % v for v in d.values()) if d else '-'
L = lambda p: json.load(open(p)) if os.path.exists(p) else None
def S(r): return L(f'{A}/summ/{r}.json') or L(f'A/summ/{r}.json')
def row(tag, o):
    if o is None: print(f'{tag:30s} (없음)'); return
    pc = o.get('pathminC_med') or {}; thick = sum(x >= 5 * o['vein_medC_med'] for x in pc.values())
    print(f"{tag:30s} 같은 성분 C>4 {f3(o.get('same4')):14s} C>10 {f3(o.get('same10')):14s} | 경로 최소 C {f3(pc):18s} | 정맥 중앙 C {o.get('vein_medC_med')} | 굵은 쌍 {thick}/{len(pc)} | 몸(창 최소) {o.get('body_largest_vol_min')} | 닿음 {[round(t) if t else None for t in o['t_touch']]} | 스텝 안 최소 두께 {o['m_h_min_seen']:.3f} | 스텝 끝 음수 {o['m_neg_end_cellsteps']} | 유량 오차 최대 {o['m_mg_err'][2]:.2f}")
print('--- M1: 시드 11, Y3 (압력 되먹임 mech_rel, 먹이 진동수 om_food)')
for r in ['Y3_base_s11', 'Y3_wave_s11', 'Y3_m1_s11', 'Y3_m2_s11', 'Y3_m4_s11', 'Y3_m8_s11', 'Y3_f20_s11', 'Y3_f20m2_s11']: row(r, S(r))
print('    Ym 정맥 최대(C>4): ' + ', '.join(f"{r} {S(r)['vein4_largest_med']:.3f}" for r in ['Ym_base_s11', 'Ym_wave_s11', 'Ym_m1_s11', 'Ym_m2_s11', 'Ym_m4_s11', 'Ym_m8_s11']))
print('--- M3: 정적 진동수 잡음 (om_noise=0.02, om_noise_T=0)')
print('    Ym 정맥 최대(C>4): ' + ', '.join(f"{r} {S(r)['vein4_largest_med']:.3f}" for r in ['Ym_n02_s11', 'Ym_n02_s12', 'Ym_n02_s13', 'Ym_n02x_s11']))
for r in ['Y3_n02_s11', 'Y3_n02_s12', 'Y3_n02_s13', 'Y3_n02x_s11']: row(r, S(r))
print('--- M3: 삼각 격자 변형 가운데 작성자 summ 에 없던 것 (정지 격자 P=48, 정지 격자 T=320)')
for r in ['Y3_tri48T80_s21', 'Y3_tri48T80_s22', 'Y3_tri48T80_s23', 'Y3_tri96T320_s21', 'Y3_tri96T320_s22', 'Y3_tri96T320_s23']: row(r, S(r))
print('--- (c) 다른 배치: 4차 검증의 base/wave(시드 11, 12)와 작성자의 tri96d, n03T320')
for test, seeds in (('A3', (11, 12)), ('S3', (11,)), ('Y2', (11, 12))):
    for s in seeds:
        row(f'{test} base s{s} (4차 검증)', L(f'{V4}/summ/{test}_base_s{s}.json')); row(f'{test} wave s{s} (4차 검증)', L(f'{V4}/summ/{test}_wave_s{s}.json'))
        row(f'{test} tri96d s{s} (작성자)', S(f'{test}_tri96d_s{s}')); row(f'{test} n03T320 s{s} (작성자)', S(f'{test}_n03T320_s{s}'))
print('--- 먹이 넷 (256², T=700, 시드 11)')
for tag, rd in (('base (V4b, 작성자)', f'{A}/runs/V4b_s11'), ('noise (V4n, 작성자)', f'{A}/runs/V4n_s11'), ('tri P=128 (V4t, 작성자)', f'{A}/runs/V4t_s11'), ('wave+gate (4차 검증 V4_gate_s11)', f'{V4}/runs/V4_gate_s11')):
    if not os.path.exists(rd + '/metrics.json'): print(tag, '(없음)'); continue
    o = vmet.summarise(rd, 'mig', verbose=True); m = json.load(open(rd + '/metrics.json')); rows = o['rows']
    b = lambda t: next(x['body_largest_vol'] for x in rows if abs(x['t'] - t) < 1); late = [x['body_largest_vol'] for x in rows if x['t'] >= 500]
    print(f"{tag:34s} 닿은 시각 {m['t_touch']} | 몸 최대 성분 부피 t=300/500/600/700: {b(300):.3f}/{b(500):.3f}/{b(600):.3f}/{b(700):.3f} (t>=500 최소 {min(late):.3f}) | 스텝 안 최소 두께 {m['h_min_seen']:.3f}")
