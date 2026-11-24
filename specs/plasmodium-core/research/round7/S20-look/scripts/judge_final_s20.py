#!/usr/bin/env python3
"""[7차 S20] 결승 판정. 기준은 ../CRITERIA.md (실행 전에 커밋, sha256은 ../criteria_sha256.txt). 거르기 screen_s20.py에서 시드와 확인/반박 판정만 바꿨다.
원래 설명: [7차 S19] 결승 판정. 거르기 screen_s19.py에서 시드와 확인/반박 판정만 바꿨다.
원래 설명: S18 둘째 거르기 screen2_s18.py에서 시드, 꼬리표를 바꾸고 균핵 끝 상태 조건(T3, T4)을 더하고 food3·asym3를 늘렸다.
원래 설명: 기준은 ../SCREEN.md. S17 screen_s17.py에서 시드·꼬리표, 조각 문턱 5%, 갇힌 뒤 조건(T1·T2)을 바꾸고 더했다.
두 독립 검증자의 측정 코드를 그대로 쓴다:
  첫 검증자 ../../S16-dumbbell/verify/scripts/vlib.py (실 아령 dumbbell D2)
  둘째 검증자 ../../S16-dumbbell/verify2/scripts/measure.py (frame: 덩이 둘 이상, 죽은 실, 가지 끝, 막)
usage: judge_final_s20.py [후보=s20z]   (대조 s20c = 지금 모델, 같은 모델 복사본)"""
import json, os, sys, glob, re
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify', 'scripts'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify2', 'scripts'))
import vlib
import measure as M2
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import rev, DIRS, _torus_label, nb, RING
def dead_tips(Z, w, h):     # 가지 끝 줄(길이 3 이상, 둘째 검증자의 tip_lines) 칸 가운데 흐름 없는 칸(주변 간선 Cmean 최대 ≤ 4) 수
    N = w.shape[0]; lab8, n8 = M2.torus_label(w, 8); vol = np.bincount(lab8.ravel(), weights=np.where(w, h, 0.0).ravel(), minlength=n8 + 1); vol[0] = -1; body = lab8 == int(np.argmax(vol))
    cells = set()
    for _, c in M2.tip_lines(w, body):
        if len(c) >= 3: cells |= c
    if not cells: return 0
    ys, xs = np.divmod(np.array(sorted(cells)), N); Cm = Z['Cmean']; CM = np.zeros(w.shape)
    for k, d in enumerate(DIRS): CM = np.maximum(CM, np.maximum(Cm[k], rev(Cm[k], d)))
    return int((CM[ys, xs] <= 4.0).sum())
cand = sys.argv[1] if len(sys.argv) > 1 else 's20z'; C = 's20c'
LONG = range(491, 501); FOOD4 = range(491, 501); FOOD3 = range(491, 495); ASYM3 = range(491, 495); MIG = range(491, 499)
TINY = 0.05
PK = 'M=wet|r=3|f=0.10|neck=any'

def rd(scn, s, tag): return os.path.join(RUNS, f'b_{scn}_s{s}_{tag}')
def met(scn, s, tag): return json.load(open(os.path.join(rd(scn, s, tag), 'metrics.json')))

def long_stats(arg):
    s, tag = arg
    fs = sorted(glob.glob(os.path.join(rd('long', s, tag), 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    out = dict(mc_act=[], mc_end=[], d2_act=[], dead_act=[], tip_act=[], dtip_act=[], film_act=[], dead_end=[], tip_end=[], debris=[], bodies=[], mc_t18=[], peri_t18=[])
    for f in fs:
        Z = np.load(f); t = float(Z['t'])
        if t < 100: continue
        w = Z['wet'].astype(bool); h = np.where(w, Z['h'].astype(float), 0.0)
        lab, n = vlib.torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]
        out['debris'].append(int((vol < TINY * vol.sum()).sum())); out['bodies'].append(int((vol >= TINY * vol.sum()).sum()))
        fr = M2.frame(Z)
        if t <= 1600:
            out['mc_act'].append(fr['db'][PK])
            if t >= 200: out['d2_act'].append(vlib.dumbbell(w, h, lab_w=lab)['D2'])
            if t >= 1000:
                out['dead_act'].append(fr['dead']['line=3|F0.1|smin=4']); out['tip_act'].append(fr['tip']['L=3|cells']); out['film_act'].append(fr['film']['h=0.3|a=40|b=3']); out['dtip_act'].append(dead_tips(Z, w, h))
        else:
            out['mc_end'].append(fr['db'][PK]); out['dead_end'].append(fr['dead']['line=3|F0.1|smin=4']); out['tip_end'].append(fr['tip']['L=3|cells'])
            if t >= 1800:      # 갇힌 뒤: 한 몸 안 덩이 둘 이상, 가장 큰 몸의 둘레/√넓이 (4-이웃 가운데 마른 칸이 있는 칸 = 둘레)
                out['mc_t18'].append(fr['db'][PK]); big = lab == np.argmax(vol) + 1
                edge = big & ~(np.roll(big, 1, 0) & np.roll(big, -1, 0) & np.roll(big, 1, 1) & np.roll(big, -1, 1)); out['peri_t18'].append(float(edge.sum()) / np.sqrt(big.sum()))
    m = met('long', s, tag)
    return (s, tag), dict({k: float(np.mean(v)) for k, v in out.items()}, bodies_end=out['bodies'][-1], fission=m.get('fission_runs') or 0, t_scl=m.get('t_scl') or 0.0)

if __name__ == '__main__':
    with Pool(4) as p: L = dict(p.map(long_stats, [(s, t) for t in (C, cand) for s in LONG]))
    def col(tag, k): return [L[(s, tag)][k] for s in LONG]
    def mean(tag, k): return float(np.mean(col(tag, k)))
    lines = []; ok = {}
    def cond(key, text, conf, refu):
        v = '확인' if conf and not refu else ('반박' if refu else '판정 못 함'); ok[key] = v; lines.append(f'{key} {text} → {v}')
    for k in ('mc_act', 'd2_act', 'dead_act', 'dtip_act', 'tip_act', 'film_act', 'debris', 'bodies', 'mc_end', 'dead_end', 'tip_end', 'mc_t18', 'peri_t18', 'bodies_end', 'fission', 't_scl'):
        lines.append(f'  long {k}: 대조 {mean(C, k):.3f}  후보 {mean(cand, k):.3f}   후보 시드별 {[round(x, 3) for x in col(cand, k)]}')
    low = sum(1 for a, b in zip(col(C, 'mc_act'), col(cand, 'mc_act')) if b < a)
    cond('A1', f'옮겨 다니는 구간(t 100~1600) 한 몸 안 덩이 둘 이상 비율 ≤ 0.5배, 후보가 낮은 시드 ≥ 7/10: {mean(cand, "mc_act"):.3f} / {mean(C, "mc_act"):.3f}, {low}/10',
         mean(cand, 'mc_act') <= 0.5 * mean(C, 'mc_act') and low >= 7, mean(cand, 'mc_act') >= mean(C, 'mc_act'))
    cond('A2', f'실 아령 비율(t 200~1600) ≤ 0.5배: {mean(cand, "d2_act"):.3f} / {mean(C, "d2_act"):.3f}', mean(cand, 'd2_act') <= 0.5 * mean(C, 'd2_act'), mean(cand, 'd2_act') >= mean(C, 'd2_act'))
    cond('A3', f'죽은 실(t 1000~1600) ≤ 1배: {mean(cand, "dead_act"):.1f} / {mean(C, "dead_act"):.1f}', mean(cand, 'dead_act') <= mean(C, 'dead_act'), mean(cand, 'dead_act') > 1.3 * mean(C, 'dead_act'))
    cond('A4', f'흐름 없는 가지 끝 줄(t 1000~1600, Cmean ≤ 4) ≤ 1배: {mean(cand, "dtip_act"):.1f} / {mean(C, "dtip_act"):.1f}', mean(cand, 'dtip_act') <= mean(C, 'dtip_act'), mean(cand, 'dtip_act') > 1.3 * mean(C, 'dtip_act'))
    lines.append(f'  (관문 아님) 가지 끝 줄 전체(t 1000~1600): {mean(cand, "tip_act"):.1f} / {mean(C, "tip_act"):.1f} ({mean(cand, "tip_act") / max(mean(C, "tip_act"), 1e-9):.2f}배)')
    cond('A5', f'얇은 막(t 1000~1600) ≤ 1배: {mean(cand, "film_act"):.1f} / {mean(C, "film_act"):.1f}', mean(cand, 'film_act') <= mean(C, 'film_act'), mean(cand, 'film_act') > 1.3 * mean(C, 'film_act'))
    cond('A6', f'부스러기(몸 부피 5% 미만 조각 수, t ≥ 100 평균) ≤ 0.1배 그리고 후보 ≤ 0.05: {mean(cand, "debris"):.3f} / {mean(C, "debris"):.2f}', mean(cand, 'debris') <= 0.1 * mean(C, 'debris') and mean(cand, 'debris') <= 0.05, mean(cand, 'debris') >= 0.5 * mean(C, 'debris'))
    cond('T1', f'갇힌 뒤(t ≥ 1800) 한 몸 안 덩이 둘 이상 비율 ≤ 대조: {mean(cand, "mc_t18"):.3f} / {mean(C, "mc_t18"):.3f}', mean(cand, 'mc_t18') <= mean(C, 'mc_t18'), mean(cand, 'mc_t18') > 1.5 * mean(C, 'mc_t18') + 0.02)
    cond('T2', f'갇힌 뒤(t ≥ 1800) 가장 큰 몸의 둘레/√넓이 ≤ 대조: {mean(cand, "peri_t18"):.2f} / {mean(C, "peri_t18"):.2f}', mean(cand, 'peri_t18') <= mean(C, 'peri_t18'), mean(cand, 'peri_t18') > 1.15 * mean(C, 'peri_t18'))
    wake = []; tails = []; nform = 0
    for s in LONG:      # [S19] 균핵 끝 상태: 다시 깨어남 없음(T3), 균핵이 된 지 150 시간 넘은 실행의 끝 얇은 칸(h < 0.5) 몫 ≤ 5%(T4)
        m = met('long', s, cand); ts = m.get('t_scl')
        if ts is None: continue
        out = (float(m['t_end']) - ts) - m['scl_steps'] * 0.1
        if out > 1.0: wake.append((s, round(ts, 1), round(out, 1)))
        if float(m['t_end']) - ts >= 150:
            nform += 1
            w = np.load(os.path.join(rd('long', s, cand), 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(rd('long', s, cand), 'h.npy')), 0.0)
            th = float((w & (h < 0.5)).sum()) / max(int(w.sum()), 1)
            lines.append(f'  long s{s} 후보 균핵: 처음 {ts:.1f}, 끝 젖은 칸 {int(w.sum())}, 얇은 칸 몫 {th:.3f}')
            if th > 0.05: tails.append((s, round(th, 3)))
    cond('T3', f'균핵이 다시 깨어나지 않는다 (균핵 모드에서 빠진 시간 > 1인 실행 0): {wake}', not wake, len(wake) >= 2)
    cond('T4', f'균핵이 된 지 150 시간 넘은 실행({nform}개) 모두 끝 얇은 칸(h < 0.5) 몫 ≤ 5%: 어긴 것 {tails}', nform >= 1 and not tails, len(tails) >= 2)

    # [S20] 겉모습 조건
    def strands(w, h):      # 외가닥 실: 젖은 8-이웃 ≤ 2이고 h < 0.6인 칸의 8-이웃 덩이. 가장 긴 것의 칸 수와 자유 끝(젖은 이웃 ≤ 1) 수
        nw = np.zeros(w.shape, int)
        for dd in RING: nw += nb(w, dd)
        lab = _torus_label(w & (nw <= 2) & (h < 0.6)); sz = np.bincount(lab.ravel())[1:]
        return (int(sz.max()) if sz.size else 0), int((w & (nw <= 1)).sum())
    def shape_ar(m):        # 축비: 공분산 고유값의 제곱근 비(작은/큰), 토러스 감김 고려
        ys, xs = np.nonzero(m); N_ = m.shape[0]
        cy = np.angle(np.exp(2j * np.pi * ys / N_).mean()) * N_ / (2 * np.pi); cx = np.angle(np.exp(2j * np.pi * xs / N_).mean()) * N_ / (2 * np.pi)
        dy = ((ys - cy + N_ / 2) % N_) - N_ / 2; dx = ((xs - cx + N_ / 2) % N_) - N_ / 2
        ev = np.linalg.eigvalsh(np.cov(np.vstack([dx, dy])) + 1e-9 * np.eye(2)); return float(np.sqrt(ev[0] / ev[1]))
    sl = []; tips = []; ars = []; t90s = []
    for s in LONG:
        d = rd('long', s, cand)
        for t in (1000, 1200, 1400):
            Z = np.load(os.path.join(d, f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); a_, b_ = strands(w, h); sl.append(a_); tips.append(b_)
        m = met('long', s, cand); ts = m.get('t_scl')
        if ts is None: continue
        fs = sorted(glob.glob(os.path.join(d, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0])); t90 = None
        for f in fs:
            t = int(re.findall(r'vs_t(\d+)', f)[0])
            if t < ts: continue
            Z = np.load(f); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0)
            if h[w & (h >= 1.5)].sum() >= 0.9 * h.sum(): t90 = t - ts; break
        if t90 is not None: t90s.append(round(t90, 1))
        if float(m['t_end']) - ts >= 150:
            w = np.load(os.path.join(d, 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(d, 'h.npy')), 0.0)
            lab = _torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]; ars.append(round(shape_ar(lab == int(np.argmax(vol)) + 1), 2))
    lines.append(f'  (L) 후보 가장 긴 외가닥 실(t 1000·1200·1400): {sl}, 자유 끝: {tips}, 균핵 축비: {ars}, 맺힘 시각(부피 90%가 h ≥ 1.5): {t90s}')
    msl = float(np.mean(sl)); mtp = float(np.mean(tips)); nar = sum(a_ <= 0.9 for a_ in ars); mt90 = float(np.median(t90s)) if t90s else None
    cond('L1', f'꼬리: 후보 long의 가장 긴 외가닥 실 평균 ≤ 50칸, 자유 끝 평균 ≤ 10: {msl:.1f}, {mtp:.1f}', msl <= 50 and mtp <= 10, msl > 80 or mtp > 20)
    cond('L2', f'균핵이 원판이 아니다: 균핵 150 시간 넘은 실행({len(ars)}개)의 70% 이상이 끝 가장 큰 몸 축비 ≤ 0.9: {nar}/{len(ars)}', len(ars) >= 1 and nar >= 0.7 * len(ars), len(ars) >= 1 and nar < 0.4 * len(ars))
    cond('L3', f'맺힘이 너무 빠르지 않다: 맺힘 시각 중앙값 60~300: {mt90}', mt90 is not None and 60 <= mt90 <= 300, mt90 is not None and (mt90 < 40 or mt90 > 400))

    allr = {C: 0, cand: 0}; late = []; early = []; dall = []
    for s in FOOD4:
        a, b = met('food4', s, C)['t_touch'], met('food4', s, cand)['t_touch']
        allr[C] += all(x is not None for x in a); allr[cand] += all(x is not None for x in b)
        for i in range(4):
            if a[i] is not None and (b[i] is None or b[i] > a[i] + 50): late.append((s, i + 1, a[i], b[i]))
            if b[i] is not None and (a[i] is None or a[i] > b[i] + 50): early.append((s, i + 1, a[i], b[i]))
        dall.append(round(max(x if x is not None else 700.0 for x in b) - max(x if x is not None else 700.0 for x in a), 1))
        lines.append(f'  food4 s{s}: 대조 {a}  후보 {b}')
    cond('F1', f'food4 모두 닿음 ≥ 대조 − 1, 늦음 ≤ 이름 + 2, 마지막 먹이 차이 중앙 ≤ +20: {allr[cand]} / {allr[C]}, 늦음 {len(late)} {late}, 이름 {len(early)}, 중앙 {float(np.median(dall)):+.1f} {dall}',
         allr[cand] >= allr[C] - 1 and len(late) <= len(early) + 2 and float(np.median(dall)) <= 20.0, allr[cand] <= allr[C] - 3 or len(late) >= len(early) + 5)
    late3 = 0
    for scn_, s in [('food3', x) for x in FOOD3] + [('asym3', x) for x in ASYM3]:
        a, b = met(scn_, s, C)['t_touch'], met(scn_, s, cand)['t_touch']
        late3 += sum(1 for i in range(3) if a[i] is not None and (b[i] is None or b[i] > a[i] + 50))
    cond('F2', f'food3·asym3 늦음 (24쌍): {late3}', late3 <= 1, late3 >= 3)
    def direction_err(tag, s):      # 처음 → t 200 무게중심 이동 방향이 유인원 방향(27°)에서 벗어난 각도
        fs = sorted(glob.glob(os.path.join(rd('mig', s, tag), 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
        c0 = np.load(fs[0])['cen']; c1 = None
        for f in fs:
            Z = np.load(f)
            if float(Z['t']) <= 200: c1 = Z['cen']
        N = np.load(fs[0])['wet'].shape[0]; d = ((c1 - c0 + N / 2) % N) - N / 2; a = np.arctan2(d[1], d[0])
        return float(np.degrees((a - np.radians(27) + np.pi) % (2 * np.pi) - np.pi))
    good = 0; reach = 0; errs = {C: [], cand: []}
    for s in MIG:
        a, b = met('mig', s, C), met('mig', s, cand); r = b['disp'] / a['disp']; q = b['area_end'] / a['area_end']; good += (r >= 0.8 and q <= 1.2)
        reach += b['t_touch'][0] is not None
        for tg in (C, cand): errs[tg].append(direction_err(tg, s))
        lines.append(f'  mig s{s}: 이동 {r:.2f}배, 끝 넓이 {q:.2f}배, 닿은 시각 {a["t_touch"][0]} → {b["t_touch"][0]}, 방향 오차 {errs[C][-1]:+.1f}° → {errs[cand][-1]:+.1f}°')
    cond('M1', f'mig 이동 ≥ 0.8배·넓이 ≤ 1.2배인 쌍: {good}/8', good >= 6, good <= 3)
    me = float(np.mean(np.abs(errs[cand]))); mc = float(np.mean(np.abs(errs[C])))
    cond('M2', f'mig 후보가 모두 유인원에 닿고({reach}/8), 방향 오차 평균 ≤ 25°: {me:.1f}° (대조 {mc:.1f}°)', reach == len(MIG) and me <= 25.0, reach <= len(MIG) - 2 or me > 35.0)
    cond('L4', f'이주 방향 치우침이 작다: 후보 방향 오차 절댓값 평균 ≤ 12°: {me:.1f}° (대조 {mc:.1f}°), 부호 붙은 평균 {float(np.mean(errs[cand])):+.1f}°', me <= 12.0, me > 18.0)
    bad = []; nr = 0
    for scn, ss in (('long', LONG), ('food4', FOOD4), ('food3', FOOD3), ('asym3', ASYM3), ('mig', MIG)):
        for s in ss:
            b = met(scn, s, cand); nr += 1
            w = np.load(os.path.join(rd(scn, s, cand), 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(rd(scn, s, cand), 'h.npy')), 0.0)
            lab, n = vlib.torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]
            tiny = int((vol < TINY * vol.sum()).sum())
            if not (b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and abs(b['V_crumb']) / b['V0'] < 0.001 and tiny == 0 and b.get('stop', '') in ('', None)):
                bad.append(f'{scn}{s}: 음수 {b["neg_end_cellsteps"]} 오차 {b["mass_err_max"]:.1e} 버린 {b["V_crumb"]:.3f} 끝 부스러기 {tiny}')
    cond('H1', f'건강 (후보 {nr} 실행: 스텝 끝 음수 0, 부피 오차 < 1e-10, |버린 부피| < 0.1%, 끝에 5% 미만 조각 0, 끝까지 돎) 어긴 것 {bad}', not bad, bool(bad))
    go = all(ok[k] == '확인' for k in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'T1', 'T2', 'T3', 'T4', 'H1', 'L1', 'L2', 'L3', 'L4')) and all(ok[k] != '반박' for k in ('F1', 'F2', 'M1', 'M2'))
    print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('독립 검증으로 간다' if go else '독립 검증으로 가지 않는다') + f'  {ok}')
    json.dump(dict(cand=cand, ok=ok, go=go, long={f'{k[0]}_{k[1]}': v for k, v in L.items()}, food4=dict(late=late, early=early, dall=dall, allr=allr), food3_asym3_late=late3, mig_good=good, health_bad=bad, look=dict(strand=sl, tips=tips, ar=ars, t90=t90s, mig_err=errs)),
              open(os.path.join(HERE, '..', 'judge_final.json'), 'w'), indent=1, default=float)
