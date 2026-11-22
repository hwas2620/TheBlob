#!/usr/bin/env python3
"""그림. data/summary.json, data/long_rows/, data/verdict.json 과 실행 폴더를 읽어 fig/ 에 PNG 를 쓴다. 만든 파일 이름을 찍는다."""
import json, os, sys, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vlib as V

for f in font_manager.findSystemFonts():
    if 'wqy-zenhei' in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'WenQuanYi Zen Hei', 'axes.unicode_minus': False, 'font.size': 9,
                     'axes.edgecolor': '#52514e', 'axes.labelcolor': '#0b0b0b', 'xtick.color': '#52514e', 'ytick.color': '#52514e',
                     'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb', 'axes.grid': True, 'grid.color': '#e4e3df', 'grid.linewidth': 0.6})
CC, CG = '#2a78d6', '#eb6834'          # 대조(slot 1 blue), 후보(slot 2 orange)
AQUA, VIOLET, RED = '#1baf7a', '#6250d6', '#e34948'
VER = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FIG = os.path.join(VER, 'fig'); os.makedirs(FIG, exist_ok=True)
R = json.load(open(os.path.join(VER, 'data', 'summary.json'))); BY = {(r['scn'], r['seed'], r['tag']): r for r in R}
VD = json.load(open(os.path.join(VER, 'data', 'verdict.json')))
made = []


def save(fig, name):
    if fig._suptitle is not None and fig._suptitle.get_position()[1] < 1.0: fig._suptitle.set_y(1.03)    # 칸 제목과 겹치지 않게
    p = os.path.join(FIG, name); fig.savefig(p, dpi=130, bbox_inches='tight'); plt.close(fig); made.append(name)


def paired(ax, scn, key, title, ylabel):
    seeds = sorted({r['seed'] for r in R if r['scn'] == scn and r['tag'] == 'v16c'})
    c = []; g = []
    for s in seeds:
        a = BY.get((scn, s, 'v16c'), {}).get(key); b = BY.get((scn, s, 'v16gh'), {}).get(key)
        if a is None or b is None: continue
        c.append(a); g.append(b); ax.plot([0, 1], [a, b], color='#b8b7b0', lw=1, zorder=1)
    ax.scatter(np.zeros(len(c)), c, s=36, color=CC, edgecolor='#fcfcfb', lw=1.5, zorder=3, label='대조 v16c')
    ax.scatter(np.ones(len(g)), g, s=36, color=CG, edgecolor='#fcfcfb', lw=1.5, zorder=3, label='후보 v16gh')
    for x, v, col in ((0, c, CC), (1, g, CG)):
        if v: ax.plot([x - 0.18, x + 0.18], [np.mean(v)] * 2, color='#0b0b0b', lw=2, zorder=4)
    ax.set_xticks([0, 1], ['대조', '후보']); ax.set_xlim(-0.5, 1.5); ax.set_title(title, fontsize=9); ax.set_ylabel(ylabel)


# ---- 주장 2: 시드별 아령 비율
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.2))
paired(axs[0], 'long', 'f_D2_main', f"실 아령 D2 (주 지표) — {VD['claim2']['verdict']}", 't 200~2000 저장 상태 중 비율')
paired(axs[1], 'long', 'f_D1_main', '굵은 덩이 둘 이상 D1 (보조)', '비율')
axs[0].legend(loc='upper right', fontsize=8, frameon=False); fig.suptitle('주장 2 · long, 시드 짝 (검은 막대 = 평균)', fontsize=10)
save(fig, 'c2_dumbbell_paired.png')

# ---- 주장 2: 시각별, D2 인 시드 비율
fig, ax = plt.subplots(figsize=(7.2, 2.8))
for tag, col, lab in (('v16c', CC, '대조'), ('v16gh', CG, '후보')):
    rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(VER, 'data', 'long_rows', f'b_long_s*_{tag}.json')))]
    if not rows: continue
    ts = [r['t'] for r in rows[0]]; frac = [np.mean([rr[i]['D2_main'] for rr in rows if i < len(rr)]) for i in range(len(ts))]
    ax.plot(ts, frac, color=col, lw=2, label=f'{lab} ({len(rows)} 시드)')
ax.set_xlabel('t'); ax.set_ylabel('실 아령인 시드 비율'); ax.legend(frameon=False, fontsize=8); ax.set_title('주장 2 · 시각마다 D2 인 시드의 비율', fontsize=10)
save(fig, 'c2_dumbbell_time.png')

# ---- 주장 3
fig, axs = plt.subplots(1, 3, figsize=(9, 3.1))
for ax, k, nm in zip(axs, ('late_film', 'late_dead', 'late_endline'), ('얇은 막 칸', '죽은 실 칸', '끝 줄 칸')):
    paired(ax, 'long', k, f"{nm} — {VD['claim3']['parts'][k[5:]]['verdict']}", '칸 수 (t 1500~2000 평균)')
axs[0].legend(fontsize=8, frameon=False); fig.suptitle('주장 3 · long 늦은 때, 시드 짝', fontsize=10)
save(fig, 'c3_late_paired.png')

# ---- 주장 4
fig, axs = plt.subplots(1, 5, figsize=(12, 3.1))
for ax, (scn, k) in zip(axs, (('food3', 't_all'), ('asym3', 't_all'), ('food4', 't_all'), ('mig', 't_mig'), ('mig', 'disp'))):
    vv = VD['claim4']['metrics'][scn if k in ('t_all', 't_mig') else f'{scn}:{k}']['verdict']
    paired(ax, scn, k, f'{scn} {k} — {vv}', '시각' if k != 'disp' else '이동 (칸)')
axs[0].legend(fontsize=8, frameon=False); fig.suptitle('주장 4 · 먹이에 모두 닿은 시각 / 유인원에 닿은 시각 / 이동 (낮을수록 좋음, disp 만 높을수록 좋음)', fontsize=10)
save(fig, 'c4_food_paired.png')


# ---- 지도
def recentre(h, wet):
    N = h.shape[0]; ang = 2 * np.pi * np.arange(N) / N; w = np.where(wet, h, 0)
    cx = np.angle((w.sum(0) * np.exp(1j * ang)).sum()) / (2 * np.pi) * N; cy = np.angle((w.sum(1) * np.exp(1j * ang)).sum()) / (2 * np.pi) * N
    return int(round(N / 2 - cx)), int(round(N / 2 - cy))


def load_snap(scn, seed, tag, t):
    d = V.run_dir(scn, seed, tag); f = os.path.join(d, f'vs_t{int(round(t)):04d}.npz')
    if not os.path.exists(f):
        fs = sorted(glob.glob(os.path.join(d, 'vs_t*.npz'))); ts = np.array([int(os.path.basename(x)[4:8]) for x in fs]); f = fs[int(np.argmin(np.abs(ts - t)))]
    Z = np.load(f); return {k: Z[k] for k in Z.files}


CM = ListedColormap(plt.get_cmap('Greys')(np.linspace(0.12, 0.95, 256)))


def draw(ax, S, title, over=(), shift=None):
    wet = S['wet'].astype(bool); h = S['h'].astype(float)
    sx, sy = shift if shift is not None else recentre(h, wet)
    r = lambda a: np.roll(a, (sy, sx), (0, 1))
    img = np.ma.masked_where(~r(wet), r(h))
    ax.set_facecolor('#fcfcfb'); im = ax.imshow(img, cmap=CM, vmin=0, vmax=1.5, origin='lower', interpolation='nearest')
    for m, col, lab in over:
        ys, xs = np.nonzero(r(m)); ax.scatter(xs, ys, s=3, marker='s', color=col, lw=0, label=f'{lab} ({int(m.sum())})')
    thick = wet & (h > 0.5); lt, nt = V.torus_label(thick); Vb = float(h[wet].sum())
    if nt:
        vol = np.bincount(lt.ravel(), weights=np.where(thick, h, 0).ravel()); vol[0] = 0
        for j, k in enumerate([k for k in np.argsort(vol)[::-1] if vol[k] >= 0.05 * Vb]):
            ax.contour(r(lt == k).astype(float), levels=[0.5], colors=[(CG, AQUA, VIOLET, RED)[j % 4]], linewidths=1.0)
    ax.set_title(title, fontsize=9); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    if over: ax.legend(loc='lower left', fontsize=7, markerscale=3, frameon=True, framealpha=0.85)
    return im, (sx, sy)


def masks3(S):
    wet = S['wet'].astype(bool); h = S['h'].astype(float)
    film = V.block_cover(wet & (h < 0.3)); one = wet & ~V.block_cover(wet); act = V.active(wet)
    Qg = S['Qgross'].astype(float); Cm = S['Cmean'].astype(float)
    qv = np.concatenate([Qg[k][act[k] & (Cm[k] > 4)] for k in range(4)])
    if qv.size < 10: qv = np.concatenate([Qg[k][act[k]] for k in range(4)])
    dead = one & (V.incident_max(Qg, act) < 0.01 * np.percentile(qv, 90)); ends, _ = V.prune_ends(wet)
    return [(film, AQUA, '얇은 막'), (dead, RED, '죽은 실'), (ends & ~dead, VIOLET, '끝 줄 (죽은 실 제외)')]


def pair_map(scn, seed, t, name, sup, over_fn=None, tags=('v16c', 'v16gh')):
    Sc = load_snap(scn, seed, tags[0], t); Sg = load_snap(scn, seed, tags[1], t)
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.6))
    oc = over_fn(Sc) if over_fn else (); og = over_fn(Sg) if over_fn else ()
    im, _ = draw(axs[0], Sc, f"대조 {tags[0]}  t={float(Sc['t']):.0f}  넓이 {int(Sc['wet'].sum())}", oc)
    draw(axs[1], Sg, f"후보 {tags[1]}  t={float(Sg['t']):.0f}  넓이 {int(Sg['wet'].sum())}", og)
    cb = fig.colorbar(im, ax=axs, shrink=0.7, pad=0.02); cb.set_label('두께 h (마른 칸은 흰색). 색 선 = 큰 덩이(h>0.5, 부피 ≥ 5%)의 테두리')
    fig.suptitle(sup, fontsize=10); save(fig, name)


# 주장 2 의 가장 나쁜 사례: 후보에서 f_D2 가 가장 큰 시드, 그 가운데 가장 늦은 D2 시각
cand = [r for r in R if r['scn'] == 'long' and r['tag'] == 'v16gh' and r.get('f_D2_main') is not None]
if cand:
    w = max(cand, key=lambda r: (r['f_D2_main'], r['seed']))
    rows = json.load(open(os.path.join(VER, 'data', 'long_rows', w['run'] + '.json')))
    d2 = [r for r in rows if r['D2_main'] and r['t'] >= 200]
    if d2:
        rr = max(d2, key=lambda r: max([min(p[0], p[1]) for p in r['pairs'] if p[2] is not None and p[2] <= 3] or [0]))   # 가장 고른 실 아령 짝
        t = rr['t']
        pair_map('long', w['seed'], t, f"worst_c2_long_s{w['seed']}_t{int(t):04d}.png",
                 f"주장 2 가장 나쁜 사례: 후보 시드 {w['seed']} (f_D2 = {w['f_D2_main']:.2f}), t={t:.0f} 의 실 아령. 덩이 짝 [부피비, 부피비, 가장 좁은 곳, 길이] = {rr['pairs']}")
        WORST2 = dict(seed=w['seed'], t=t, f=w['f_D2_main'], pairs=rr['pairs'])
    else: WORST2 = dict(seed=w['seed'], t=None, f=w['f_D2_main'])
# 주장 3 의 가장 나쁜 사례: 후보 − 대조 가 가장 큰 (지표, 시드). 지표는 대조 대비 비율이 가장 나쁜 것
best = None
for k in ('late_film', 'late_dead', 'late_endline'):
    for s in sorted({r['seed'] for r in cand}):
        a = BY.get(('long', s, 'v16c'), {}).get(k); b = BY.get(('long', s, 'v16gh'), {}).get(k)
        if a is None or b is None: continue
        sc = (b - a) / max(a, 1.0)
        if best is None or sc > best[0]: best = (sc, k, s, a, b)
if best:
    sc, k, s, a, b = best
    rows = json.load(open(os.path.join(VER, 'data', 'long_rows', f'b_long_s{s}_v16gh.json')))
    win = [r for r in rows if 1500 <= r['t'] <= 2000 and k[5:] in r]; rr = max(win, key=lambda r: r[k[5:]])
    pair_map('long', s, rr['t'], f"worst_c3_long_s{s}_t{int(rr['t']):04d}.png",
             f"주장 3 가장 나쁜 사례: {k} 시드 {s} (창 평균 대조 {a:.1f} → 후보 {b:.1f}), 후보에서 그 수가 가장 큰 시각 t={rr['t']:.0f}", masks3)
    WORST3 = dict(metric=k, seed=s, ctrl=a, cand=b, t=rr['t'])
# 주장 4 의 가장 나쁜 사례: 주 지표의 나빠짐이 가장 큰 (시나리오, 시드)
b4 = None
for scn, k in (('food3', 't_all'), ('asym3', 't_all'), ('food4', 't_all'), ('mig', 't_mig')):
    for s in sorted({r['seed'] for r in R if r['scn'] == scn}):
        a = BY.get((scn, s, 'v16c'), {}).get(k); b = BY.get((scn, s, 'v16gh'), {}).get(k)
        if a is None or b is None: continue
        if b4 is None or (b - a) > b4[0]: b4 = (b - a, scn, s, a, b)
if b4:
    dd, scn, s, a, b = b4
    pair_map(scn, s, a, f"worst_c4_{scn}_s{s}_t{int(round(a / 20) * 20):04d}.png",
             f"주장 4 가장 나쁜 사례: {scn} 시드 {s}, 모든 먹이에 닿은 시각 대조 {a:.0f} → 후보 {b:.0f}. 대조가 다 닿은 무렵의 두 몸")
    WORST4 = dict(scn=scn, seed=s, ctrl=a, cand=b)
json.dump(dict(worst2=globals().get('WORST2'), worst3=globals().get('WORST3'), worst4=globals().get('WORST4'), figs=made), open(os.path.join(VER, 'data', 'worst.json'), 'w'), indent=1, ensure_ascii=False)
print('\n'.join(made))

# ---- 판정 밖 덧붙임 (CRITERIA_CHANGES 1·3): data/extra.json
WF = None
if os.path.exists(os.path.join(VER, 'data', 'extra.json')):
    EX = json.load(open(os.path.join(VER, 'data', 'extra.json')))
    fig, axs = plt.subplots(1, 4, figsize=(11, 3.1))
    def pp(ax, d, title, ylabel):
        ks = sorted(d['per_seed'], key=int); c = [d['per_seed'][k][0] for k in ks]; g = [d['per_seed'][k][1] for k in ks]
        for a, b in zip(c, g): ax.plot([0, 1], [a, b], color='#b8b7b0', lw=1, zorder=1)
        ax.scatter(np.zeros(len(c)), c, s=36, color=CC, edgecolor='#fcfcfb', lw=1.5, zorder=3, label='대조'); ax.scatter(np.ones(len(g)), g, s=36, color=CG, edgecolor='#fcfcfb', lw=1.5, zorder=3, label='후보')
        for x, v in ((0, c), (1, g)): ax.plot([x - 0.18, x + 0.18], [np.mean(v)] * 2, color='#0b0b0b', lw=2, zorder=4)
        ax.set_xticks([0, 1], ['대조', '후보']); ax.set_xlim(-0.5, 1.5); ax.set_title(title, fontsize=9); ax.set_ylabel(ylabel)
    pp(axs[0], EX['main_dead'], f"큰 몸의 죽은 실 칸\np(적음)={EX['main_dead']['p_less']:.3f}", '칸 수 (t 1500~2000)')
    pp(axs[1], EX['main_endline'], f"큰 몸의 끝 줄 칸\np(많음)={EX['main_endline']['p_greater']:.3f}", '칸 수 (t 1500~2000)')
    pp(axs[2], EX['f_D2_hmean_late'], f"실 아령 (hmean>0.5), t 1000~2000\np(많음)={EX['f_D2_hmean_late']['p_greater']:.3f}", '저장 상태 중 비율')
    if 'far' in EX: pp(axs[3], EX['far']['t_all'], f"먼 먹이 food3(거리 75) t_all\n{EX['far']['t_all']['verdict']}", '모든 먹이에 닿은 시각 (480 = 못 닿음)')
    axs[0].legend(fontsize=8, frameon=False); fig.suptitle('판정 밖 튼튼함 검사 (대조의 부스러기 빼기, 맥동 빼기, 굶은 채 먼 먹이 찾기)', fontsize=10, y=1.06)
    save(fig, 'extra_robustness.png')
    if 'far' in EX:
        ps = EX['far']['t_all']['per_seed']; s_ = max(ps, key=lambda k: ps[k][1] - ps[k][0]); a, b = ps[s_]
        pair_map('food3', int(s_), a, f"worst_far_food3_s{s_}_t{int(round(a / 20) * 20):04d}.png",
                 f"먼 먹이 시험의 가장 나쁜 사례: 시드 {s_}, 모든 먹이에 닿은 시각 대조 {a:.0f} → 후보 {b:.0f}. 대조가 다 닿은 무렵", tags=('v16c_far', 'v16gh_far'))
        WF = dict(seed=int(s_), ctrl=a, cand=b)
W = json.load(open(os.path.join(VER, 'data', 'worst.json'))); W['worst_far'] = WF; W['figs'] = made
json.dump(W, open(os.path.join(VER, 'data', 'worst.json'), 'w'), indent=1, ensure_ascii=False)
print('\n'.join(made[-3:]))
