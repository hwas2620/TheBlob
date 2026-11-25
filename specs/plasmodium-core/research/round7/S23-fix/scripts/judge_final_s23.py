#!/usr/bin/env python3
"""[7차 S23] 결승 판정. 기준은 ../CRITERIA.md (실행 전에 커밋, sha256은 ../criteria_sha256.txt).
첫 거르기 screen_s23.py에서 시드를 바꾸고(761~), 조건마다 확인/반박 문턱을 두었다(S22 결승 judge_final_s22.py와 같은 꼴; 새 조건 S6·S7·L6·H3과 조인 S3의 반박 문턱은 ../CRITERIA.md).
첫 거르기 설명: [7차 S23] 거르기 판정. 기준은 ../SCREEN.md (실행 전에 커밋, sha256은 ../screen_sha256.txt).
S22 둘째 거르기 screen2_s22.py에서 시드·꼬리표를 바꾸고, 일곱째 검증에서 틀린 것을 조건으로 더했다:
  S6 구멍 없음, S7 촘촘함(볼록 껍질 대비 넓이), S3을 실행마다로 조이기, L6 먹은 몸의 자유 꼬리, H3 풀이 최댓값.
시험용: 환경 변수 S23_TEST=1 이면 시드·꼬리표를 S23_* 변수에서 읽는다.
S22 둘째 거르기 설명: 기준은 ../SCREEN2.md.
첫 거르기 screen_s22.py에서 시드를 바꾸고(621~), S5를 '갇힐 때 부피 5% 이상인 몸마다 끝에 한 덩어리'로 고쳤다(까닭: ../RESULT.md).
첫 거르기 설명: [7차 S22] 거르기 판정.
S21 screen_s21.py에서 시드·꼬리표를 바꾸고, slimeall 시나리오와 균핵 조건 S1~S5, 풀이 조건 H2를 더하고, L3을 '끝 덩이 자리에 부피가 모인 시각'으로 바꿨다(균핵 측정은 sclform.py).
시험용: 환경 변수 S22_TEST=1 이면 시드·꼬리표를 S22_* 변수에서 읽는다.
S21 설명: [7차 S21] 거르기 판정. S20 screen_s20.py에서 시드·꼬리표를 바꾸고 L5(100칸 넘는 긴 실이 나온 시각)를 더했다.
S20 설명: [7차 S20] 거르기 판정. S19 screen_s19.py에서 시드·꼬리표를 바꾸고 겉모습 조건(L1~L4)을 더했다.
원래 설명: [7차 S19] 거르기 판정. S18 둘째 거르기 screen2_s18.py에서 시드, 꼬리표를 바꾸고 균핵 끝 상태 조건(T3, T4)을 더하고 food3·asym3를 늘렸다.
원래 설명: 기준은 ../SCREEN.md. S17 screen_s17.py에서 시드·꼬리표, 조각 문턱 5%, 갇힌 뒤 조건(T1·T2)을 바꾸고 더했다.
두 독립 검증자의 측정 코드를 그대로 쓴다:
  첫 검증자 ../../S16-dumbbell/verify/scripts/vlib.py (실 아령 dumbbell D2)
  둘째 검증자 ../../S16-dumbbell/verify2/scripts/measure.py (frame: 덩이 둘 이상, 죽은 실, 가지 끝, 막)
usage: judge_final_s23.py [후보=s23w]   (대조 s23c = 지금 모델, 같은 모델 복사본)"""
import json, os, sys, glob, re
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, '..', 'model', 'runs')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify', 'scripts'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify2', 'scripts'))
import vlib
import measure as M2
sys.path.insert(0, os.path.join(HERE, '..', 'model')); from ref_model import rev, DIRS, _torus_label, nb, RING
from scipy import ndimage as ndi
sys.path.insert(0, HERE); import sclform
def dead_tips(Z, w, h):     # 가지 끝 줄(길이 3 이상, 둘째 검증자의 tip_lines) 칸 가운데 흐름 없는 칸(주변 간선 Cmean 최대 ≤ 4) 수
    N = w.shape[0]; lab8, n8 = M2.torus_label(w, 8); vol = np.bincount(lab8.ravel(), weights=np.where(w, h, 0.0).ravel(), minlength=n8 + 1); vol[0] = -1; body = lab8 == int(np.argmax(vol))
    cells = set()
    for _, c in M2.tip_lines(w, body):
        if len(c) >= 3: cells |= c
    if not cells: return 0
    ys, xs = np.divmod(np.array(sorted(cells)), N); Cm = Z['Cmean']; CM = np.zeros(w.shape)
    for k, d in enumerate(DIRS): CM = np.maximum(CM, np.maximum(Cm[k], rev(Cm[k], d)))
    return int((CM[ys, xs] <= 4.0).sum())
cand = sys.argv[1] if len(sys.argv) > 1 else 's23w'; C = 's23c'
LONG = range(761, 771); FOOD4 = range(761, 771); FOOD3 = range(761, 765); ASYM3 = range(761, 765); MIG = range(761, 769); SLIME = range(771, 777)
OUT = os.path.join(HERE, '..', 'judge_final.json')
RUNS_C = os.environ.get('S23_RUNS_C', RUNS)
if os.environ.get('S23_TEST'):
    sl_ = lambda k: [int(x) for x in os.environ[k].split(',')] if os.environ.get(k) else []
    C = os.environ.get('S23_C', C); LONG = sl_('S23_LONG'); FOOD4 = sl_('S23_FOOD4'); FOOD3 = sl_('S23_FOOD3'); ASYM3 = sl_('S23_ASYM3'); MIG = sl_('S23_MIG'); SLIME = sl_('S23_SLIME')
    OUT = os.environ.get('S23_OUT', '/dev/null')
TINY = 0.05
PK = 'M=wet|r=3|f=0.10|neck=any'

def rd(scn, s, tag):
    d = os.path.join(RUNS, f'b_{scn}_s{s}_{tag}')
    return d if os.path.exists(d) else os.path.join(RUNS_C, f'b_{scn}_s{s}_{tag}')      # 시험용: 다른 폴더의 실행

def recentre(m):      # 토러스에서 덩이를 가운데로 옮긴다 (감김 없이 재려고)
    N_ = m.shape[0]; ys, xs = np.nonzero(m)
    cy = int(np.angle(np.exp(2j * np.pi * ys / N_).mean()) * N_ / (2 * np.pi)) % N_; cx = int(np.angle(np.exp(2j * np.pi * xs / N_).mean()) * N_ / (2 * np.pi)) % N_
    return np.roll(m, (N_ // 2 - cy, N_ // 2 - cx), (0, 1))

def lump_shape(w, h):      # [S23] 끝 가장 큰(부피) 조각의 구멍 칸 수, 볼록 껍질 대비 넓이
    lab = _torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel()); vol[0] = -1; big = recentre(lab == int(np.argmax(vol)))
    holes = int((ndi.binary_fill_holes(big) & ~big).sum())
    from scipy.spatial import ConvexHull
    ys, xs = np.nonzero(big); pts = np.concatenate([np.c_[xs + dx, ys + dy] for dx in (-0.5, 0.5) for dy in (-0.5, 0.5)])
    return holes, float(big.sum() / ConvexHull(pts).volume)

def free_tails(w, h):      # [S23] 자유 끝(젖은 이웃 ≤ 1)을 하나씩 깎아 들어가(400번까지) 깎인 칸 = 몸·고리에 매달린 실 나무. 자유 끝 수, 깎인 칸 합, 가장 큰 나무(8-이웃 덩이) 칸 수
    w = w.copy(); pr = np.zeros_like(w); nend = None
    for _ in range(400):
        nw = np.zeros(w.shape, int)
        for dd in RING: nw += nb(w, dd)
        e = w & (nw <= 1)
        if nend is None: nend = int(e.sum())
        if not e.any(): break
        pr |= e; w &= ~e
    lab = _torus_label(pr); sz = np.bincount(lab.ravel()); sz[0] = 0
    return nend, int(pr.sum()), (int(sz.max()) if sz.size > 1 else 0)
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
    sl2 = []        # [S21] t 600~1600 매 200 가장 긴 외가닥 실
    for s in LONG:
        for t in range(600, 1601, 200):
            Z = np.load(os.path.join(rd('long', s, cand), f'vs_t{t:04d}.npz')); w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); sl2.append(strands(w, h)[0])
    lines.append(f'  (L) 후보 가장 긴 외가닥 실(t 1000·1200·1400): {sl}, 자유 끝: {tips}, 균핵 축비: {ars}, 맺힘 시각(부피 90%가 h ≥ 1.5): {t90s}')
    cond('L1', f'꼬리: 후보 long의 가장 긴 외가닥 실 평균 ≤ 50칸, 자유 끝 평균 ≤ 10: {float(np.mean(sl)):.1f}, {float(np.mean(tips)):.1f}', float(np.mean(sl)) <= 50 and float(np.mean(tips)) <= 10, float(np.mean(sl)) > 80 or float(np.mean(tips)) > 20)
    cond('L5', f'긴 다리: 후보 long의 t 600~1600 매 200 시각({len(sl2)}개) 가운데 가장 긴 외가닥 실이 100칸 넘는 시각 ≤ 3: {sum(x >= 100 for x in sl2)} {sl2}', len(sl2) == 6 * len(LONG) and sum(x >= 100 for x in sl2) <= 3, sum(x >= 100 for x in sl2) >= 8)
    cond('L2', f'균핵이 원판이 아니다: 균핵 150 시간 넘은 실행({len(ars)}개)의 70% 이상이 끝 가장 큰 몸 축비 ≤ 0.9: {sum(a_ <= 0.9 for a_ in ars)}/{len(ars)}', len(ars) >= 1 and sum(a_ <= 0.9 for a_ in ars) >= 0.7 * len(ars), len(ars) >= 1 and sum(a_ <= 0.9 for a_ in ars) < 0.4 * len(ars))
    # [S22] 균핵 조건: long·slimeall 후보 실행 가운데 균핵이 된 지 150 시간 넘은 것 (sclform.py)
    SR = []
    for scn_, ss in (('long', LONG), ('slimeall', SLIME)):
        for s in ss:
            m = met(scn_, s, cand); ts = m.get('t_scl')
            if ts is None or float(m['t_end']) - ts < 150: continue
            r = sclform.run(rd(scn_, s, cand)); r['scn'] = scn_; r['seed'] = s
            w = np.load(os.path.join(rd(scn_, s, cand), 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(rd(scn_, s, cand), 'h.npy')), 0.0)
            lab, n = vlib.torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]; r['big_pieces'] = int((vol >= TINY * vol.sum()).sum())
            fs_ = sorted(glob.glob(os.path.join(rd(scn_, s, cand), 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))      # [S22 둘째] 갇힐 때(그 앞 마지막 장면) 부피 5% 이상인 몸 수
            f0_ = [f for f in fs_ if int(re.findall(r'vs_t(\d+)', f)[0]) <= ts][-1]; Z0_ = np.load(f0_); w0_ = Z0_['wet'].astype(bool); h0_ = np.where(w0_, Z0_['h'].astype(float), 0.0)
            lab0_, _ = vlib.torus_label(w0_); v0_ = np.bincount(lab0_.ravel(), weights=h0_.ravel())[1:]; r['big_bodies_trap'] = int((v0_ >= TINY * v0_.sum()).sum()); SR.append(r)
            lines.append(f"  균핵 {scn_} s{s}: 넓이 {r.get('area')} 조각(5% 이상) {r['big_pieces']} (갇힐 때 몸 {r['big_bodies_trap']}) 원판 IoU {r.get('disc_iou', 0):.2f} 짙던 자리 IoU {r.get('iou_mass', 0):.2f} 두께 CV {r.get('h_cv', 0):.2f} ±10% {r.get('h_in10', 0):.2f} 한 장면 최대 몫 {r.get('max_share')} 오름 90% {r.get('t90')}")
    t90m = [r['t90'] for r in SR if r.get('t90') is not None]
    cond('L3', f'맺힘이 너무 빠르지 않다: 균핵이 된 뒤 끝 덩이 자리(+1칸) 안 부피 몫이 오름의 90%에 닿은 시각, 중앙값 60~300 ({len(t90m)}/{len(SR)} 실행): {float(np.median(t90m)) if t90m else None}', len(SR) >= 1 and len(t90m) >= 0.7 * len(SR) and 60 <= float(np.median(t90m)) <= 300, bool(t90m) and (float(np.median(t90m)) < 40 or float(np.median(t90m)) > 400))
    nS = len(SR); im = [r.get('iou_mass', 0.0) for r in SR]; fm = lambda x: 'None' if x is None else f'{x:.3f}'
    cond('S1', f'균핵이 짙던 곳에서 맺힌다: 끝 덩이와 갇힐 때(그 앞 마지막 장면) σ 3으로 흐린 두께 위쪽 칸(끝 덩이 넓이만큼)의 IoU 평균 ≥ 0.4 ({nS} 실행): {float(np.mean(im)) if im else None}', nS >= 1 and float(np.mean(im)) >= 0.4, nS >= 1 and float(np.mean(im)) < 0.3)
    msh = [r.get('max_share') for r in SR]; ok_sh = sum(1 for x in msh if x is not None and x <= 0.5)
    cond('S2', f'천천히 모인다: 한 장면(20 시간) 사이 모인 몫 ≤ 전체 오름의 절반인 실행 ≥ 90%: {ok_sh}/{nS} {[None if x is None else round(x, 2) for x in msh]}', nS >= 1 and ok_sh >= 0.9 * nS, nS >= 1 and ok_sh < 0.7 * nS)
    hc = [r.get('h_cv', 0.0) for r in SR]; hi = [r.get('h_in10', 1.0) for r in SR]
    cond('S3', f'두께가 고르지 않다: 끝 덩이 두께 CV 중앙값 ≥ 0.15 그리고 모든 실행 ≥ 0.12, 중앙값 ±10% 안 칸 몫의 중앙값 ≤ 0.6: {fm(float(np.median(hc)) if hc else None)} (가장 작은 것 {fm(min(hc) if hc else None)}), {fm(float(np.median(hi)) if hi else None)}', nS >= 1 and float(np.median(hc)) >= 0.15 and min(hc) >= 0.12 and float(np.median(hi)) <= 0.6, nS >= 1 and (float(np.median(hc)) < 0.10 or min(hc) < 0.06 or float(np.median(hi)) > 0.8))
    ar_ = np.array([r.get('area', 0) for r in SR], float)
    cond('S4', f'넓이가 정해진 값이 아니다: 끝 덩이 넓이의 실행 사이 변동계수 ≥ 0.15: {fm(float(ar_.std() / max(ar_.mean(), 1e-9)) if nS else None)} {ar_.astype(int).tolist()}', nS >= 2 and float(ar_.std() / max(ar_.mean(), 1e-9)) >= 0.15, nS >= 2 and float(ar_.std() / max(ar_.mean(), 1e-9)) < 0.08)
    one = sum(1 for r in SR if r['big_pieces'] == r['big_bodies_trap'] >= 1)
    cond('S5', f'몸마다 한 덩어리: 끝에 부피 5% 이상 조각 수가 갇힐 때 부피 5% 이상인 몸 수와 같은 실행 모두: {one}/{nS} (끝 조각 하나인 실행 {sum(1 for r in SR if r["big_pieces"] == 1)}/{nS})', nS >= 1 and one == nS, nS - one >= 2)
    hol = []; sol = []      # [S23] 끝 상태(h.npy, wet.npy)의 가장 큰 조각
    for r in SR:
        w_ = np.load(os.path.join(rd(r['scn'], r['seed'], cand), 'wet.npy')).astype(bool); h_ = np.where(w_, np.load(os.path.join(rd(r['scn'], r['seed'], cand), 'h.npy')), 0.0)
        a_, b_ = lump_shape(w_, h_); hol.append(a_); sol.append(b_); r['holes'] = a_; r['convex'] = b_
    cond('S6', f'균핵에 구멍이 없다: 끝 덩이가 둘러싼 마른 칸 ≤ 3인 실행 모두: {sum(1 for x in hol if x <= 3)}/{nS} {hol}', nS >= 1 and all(x <= 3 for x in hol), sum(1 for x in hol if x > 3) >= 2)
    cond('S7', f'균핵이 촘촘하다: 끝 덩이 넓이 / 볼록 껍질 넓이 중앙값 ≥ 0.85 그리고 모든 실행 ≥ 0.70: {fm(float(np.median(sol)) if sol else None)} {[round(x, 2) for x in sol]}', nS >= 1 and float(np.median(sol)) >= 0.85 and min(sol) >= 0.70, nS >= 1 and (float(np.median(sol)) < 0.80 or sum(1 for x in sol if x < 0.70) >= 2))
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
    cond('F2', f'food3·asym3 늦음 ≤ 1 (24쌍): {late3}', late3 <= 1, late3 >= 3)
    fe = {C: [], cand: []}; dg = {C: [], cand: []}; tl = {C: [], cand: []}      # [S23] 먹이 판(먹은 몸)의 매달린 실 나무: t 200부터 50마다
    for scn_, ss in (('food4', FOOD4), ('food3', FOOD3), ('asym3', ASYM3)):
        for s in ss:
            for tg in (C, cand):
                T_ = int(met(scn_, s, tg)['t_end'])
                for t_ in range(200, T_ + 1, 50):
                    f_ = os.path.join(rd(scn_, s, tg), f'vs_t{t_:04d}.npz')
                    if not os.path.exists(f_): continue
                    Z_ = np.load(f_); w_ = Z_['wet'].astype(bool); a_, b_, c_ = free_tails(w_, None); fe[tg].append(a_); dg[tg].append(b_); tl[tg].append(c_)
    mn = lambda v: float(np.mean(v)) if v else float('nan')
    cond('L6', f'먹은 몸이 실 꼬리를 매달고 다니지 않는다 (food4·food3·asym3, t ≥ 200 매 50, 자유 끝을 깎아 들어간 칸): 후보 장면당 합 평균 ≤ 15칸 그리고 ≤ 0.2배 대조, 모든 장면 가장 큰 나무 ≤ 40칸: {mn(dg[cand]):.1f} / {mn(dg[C]):.1f}, 가장 큰 나무 {max(tl[cand]) if tl[cand] else None} (대조 {max(tl[C]) if tl[C] else None}), 자유 끝 평균 {mn(fe[cand]):.2f} / {mn(fe[C]):.2f} (장면 {len(dg[cand])})',
         bool(dg[cand]) and mn(dg[cand]) <= 15 and mn(dg[cand]) <= 0.2 * mn(dg[C]) and max(tl[cand]) <= 40, bool(dg[cand]) and (mn(dg[cand]) > 30 or mn(dg[cand]) > 0.5 * mn(dg[C]) or max(tl[cand]) > 80))
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
    cond('M1', f'mig 이동 ≥ 0.8배·넓이 ≤ 1.2배인 쌍 ≥ 6/8: {good}/8', good >= 6, good <= 3)
    me = float(np.mean(np.abs(errs[cand]))); mc = float(np.mean(np.abs(errs[C])))
    cond('M2', f'mig 후보가 모두 유인원에 닿고({reach}/8), 방향 오차 평균 ≤ 25°: {me:.1f}° (대조 {mc:.1f}°)', reach == len(MIG) and me <= 25.0, reach <= len(MIG) - 2 or me > 35.0)
    cond('L4', f'이주 방향 치우침이 작다: 후보 방향 오차 |평균| ≤ 12°: {me:.1f}° (대조 {mc:.1f}°)', me <= 12.0, me > 18.0)
    bad = []; nr = 0
    for scn, ss in (('long', LONG), ('food4', FOOD4), ('food3', FOOD3), ('asym3', ASYM3), ('mig', MIG), ('slimeall', SLIME)):
        for s in ss:
            b = met(scn, s, cand); nr += 1
            w = np.load(os.path.join(rd(scn, s, cand), 'wet.npy')).astype(bool); h = np.where(w, np.load(os.path.join(rd(scn, s, cand), 'h.npy')), 0.0)
            lab, n = vlib.torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]
            tiny = int((vol < TINY * vol.sum()).sum())
            if not (b['neg_end_cellsteps'] == 0 and b['mass_err_max'] < 1e-10 and abs(b['V_crumb']) / b['V0'] < 0.001 and tiny == 0 and b.get('stop', '') in ('', None)):
                bad.append(f'{scn}{s}: 음수 {b["neg_end_cellsteps"]} 오차 {b["mass_err_max"]:.1e} 버린 {b["V_crumb"]:.3f} 끝 부스러기 {tiny}')
    cond('H1', f'건강 (후보 {nr} 실행: 스텝 끝 음수 0, 부피 오차 < 1e-10, |버린 부피| < 0.1%, 끝에 5% 미만 조각 0, 끝까지 돎) 어긴 것 {bad}', not bad, bool(bad))
    ge1 = 0; fr = {C: [0, 0], cand: [0, 0]}      # [S22] 풀이: 20 스텝마다 직접 풀이와 견준 유량 오차
    for tg in (C, cand):
        for scn, ss in (('long', LONG), ('food4', FOOD4), ('food3', FOOD3), ('asym3', ASYM3), ('mig', MIG), ('slimeall', SLIME)):
            for s in ss:
                e = np.array(json.load(open(os.path.join(rd(scn, s, tg), 'mg_err_series.json'))), float)
                e = e[:, 1] if e.size else np.zeros(0); fr[tg][0] += int((e > 0.5).sum()); fr[tg][1] += int(e.size)
                if tg == cand: ge1 += int((e > 1.0).sum())
    f_ = lambda tg: fr[tg][0] / max(fr[tg][1], 1)
    cond('H2', f'풀이: 후보 유량 오차 > 1 인 검사 0, > 0.5 인 몫 ≤ 대조: {ge1}, {f_(cand):.5f} / {f_(C):.5f} (검사 {fr[cand][1]} / {fr[C][1]})', ge1 == 0 and f_(cand) <= f_(C), ge1 > 0 or f_(cand) > 2 * f_(C))
    emax = {C: 0.0, cand: 0.0}
    for tg in (C, cand):
        for scn, ss in (('long', LONG), ('food4', FOOD4), ('food3', FOOD3), ('asym3', ASYM3), ('mig', MIG), ('slimeall', SLIME)):
            for s in ss:
                e = np.array(json.load(open(os.path.join(rd(scn, s, tg), 'mg_err_series.json'))), float)
                if e.size: emax[tg] = max(emax[tg], float(e[:, 1].max()))
    cond('H3', f'풀이가 크게 틀리지 않는다: 후보 모든 검사의 유량 오차 최댓값 ≤ 0.6: {emax[cand]:.3f} (대조 {emax[C]:.3f})', emax[cand] <= 0.6, emax[cand] > 1.0)
    GO = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'T1', 'T2', 'T3', 'T4', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'H1', 'H2', 'H3')
    go = all(ok[k] == '확인' for k in GO) and all(ok[k] != '반박' for k in ('F1', 'F2', 'M1', 'M2'))
    print('\n'.join(lines)); print(f'\n후보 {cand}: ' + ('독립 검증으로 간다' if go else '가지 않는다 (' + ', '.join(f'{k} {v}' for k, v in ok.items() if (k in GO and v != '확인') or v == '반박') + ')'))
    json.dump(dict(cand=cand, ok=ok, go=go, long={f'{k[0]}_{k[1]}': v for k, v in L.items()}, food4=dict(late=late, early=early, dall=dall, allr=allr), food3_asym3_late=late3, mig_good=good, health_bad=bad, scl=SR, solver=dict(ge1=ge1, frac=fr, emax=emax), tails=dict(fe={k: mn(v) for k, v in fe.items()}, dangling={k: mn(v) for k, v in dg.items()}, tree_max={k: (max(v) if v else None) for k, v in tl.items()})),
              open(OUT, 'w'), indent=1, default=float)
