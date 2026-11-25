#!/usr/bin/env python3
"""verify8 보조 분석 (등록 기준 밖, 실행을 본 뒤 더함 — CRITERIA_CHANGES.md 참고). 판정은 등록 기준(judge.py)으로 하고, 이것은 해석을 돕는 데만 쓴다.

usage: extra.py RUN_DIR OUT_DIR -> OUT_DIR/<run>.json
  - 주장 3 을 주 몸에 붙은 실·끝으로만: 떨어진 부스러기(free)는 빼고 잰다 (대조의 '흐름 없는 실' 대부분이 부스러기였다)
  - 주장 6 의 굳센 꼬리: 굳센 가지 끝(measure.tips_robust)을 없을 때까지 깎아 들어가 없어지는, 남은 몸에 붙은 칸 (계단꼴·2칸 폭 실도 잡고, 고리·관의 칸은 깎이지 않는다)
"""
import numpy as np, json, os, sys, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure as M


def prune_robust(wet):
    cur = wet.copy(); rem = np.zeros_like(wet)
    for _ in range(5000):
        e = M.tips_robust(cur)
        if not e.any(): break
        cur &= ~e; rem |= e
    return rem, cur


def trees(rem, cur, keep):
    lr, nr = M.label8(rem & keep); att = M.dilate(cur, M.SQ3); s = []
    for j in range(1, nr + 1):
        m = lr == j
        if (m & att).any(): s.append(int(m.sum()))
    return s


def snap(S):
    wet = S['wet'].astype(bool); h = S['h'].astype(float); hp = np.where(wet, np.maximum(h, 0), 0); age = S['age'].astype(float)
    lab, n = M.label8(wet)
    if n == 0: return None
    vol = np.bincount(lab.ravel(), weights=hp.ravel(), minlength=n + 1); vol[0] = 0; main = int(np.argmax(vol)); mm = lab == main
    q = M.cell_flux(S['Qgross'].astype(float)); ok = wet & (age >= M.AGE_OK); qmed = float(np.median(q[ok])) if ok.sum() >= 10 else None
    cls, core, thin = M.thin_classes(wet, hp, lab, vol)
    thr = np.zeros_like(wet)
    for c in cls:
        if c['cls'] not in ('fringe', 'free') and c['body'] == main: thr |= c['mask']
    o = dict(t=round(float(S['t']), 2), thread_main=int(thr.sum()))
    tr = M.tips_robust(wet) & mm
    if qmed:
        nf = ok & (q < 0.05 * qmed); o['nf_thread_main'] = int((thr & nf).sum()); o['nf_tipr_main'] = M.label8(tr & nf)[1]
        o['nf_thread_main_01'] = int((thr & ok & (q < 0.01 * qmed)).sum())
    rc, cc = M.prune_claim(wet); s1 = trees(rc, cc, mm); o['tail_main'] = int(sum(s1)); o['tail_main_max'] = int(max(s1 or [0]))
    rr, cr = prune_robust(wet); s2 = trees(rr, cr, mm); o['rtail_cells'] = int(sum(s2)); o['rtail_max'] = int(max(s2 or [0])); o['rtail_n5'] = int(sum(x >= 5 for x in s2))
    old = rr & mm & (age >= M.AGE_OK); o['rtail_old_cells'] = int(old.sum())
    return o


def main(rd, od):
    name = os.path.basename(rd.rstrip('/')); out = []
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0])):
        S = M.load_vs(f)
        if float(S['t']) < 60: continue
        o = snap(S)
        if o: out.append(o)
    os.makedirs(od, exist_ok=True); json.dump(dict(run=name, snaps=out), open(os.path.join(od, name + '.json'), 'w')); print(name, len(out))


if __name__ == '__main__':
    for rd in sys.argv[2:]: main(rd, sys.argv[1])
