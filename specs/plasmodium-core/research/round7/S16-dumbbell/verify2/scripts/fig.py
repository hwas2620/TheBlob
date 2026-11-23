#!/usr/bin/env python3
"""verify2 그림: data/verdict.json, data/frames, data/runs_summary.json 과 실행 상태에서 fig/*.png 를 만든다."""
import glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import measure as Ms
D = os.path.join(HERE, '..', 'data'); FIG = os.path.join(HERE, '..', 'fig'); RUNS = os.path.normpath(os.path.join(HERE, '..', '..', 'model', 'runs'))
for f in ('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',):
    if os.path.exists(f): font_manager.fontManager.addfont(f); plt.rcParams['font.family'] = font_manager.FontProperties(fname=f).get_name()
plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#c3c2b7', 'axes.grid': True, 'grid.color': '#e1e0d9', 'grid.linewidth': 0.6,
                     'axes.axisbelow': True, 'font.size': 9, 'axes.titlesize': 10, 'lines.linewidth': 2, 'savefig.dpi': 130})
CC, CG = '#2a78d6', '#eb6834'      # 대조, 후보 (categorical slot 1, 2)
OV = dict(blob='#2a78d6', film='#1baf7a', tip='#eda100', dead='#e87ba4')
V = json.load(open(os.path.join(D, 'verdict.json')))
F = {json.load(open(f))['run']: json.load(open(f))['frames'] for f in glob.glob(os.path.join(D, 'frames', '*.json'))}
name = lambda scn, s, arm: f'b_{scn}_s{s}_' + dict(ctrl='w16c', cand='w16gm')[arm]
seeds = V['seeds_long']


def pairs(ax, c, g, title, ylab):
    c = np.asarray(c, float); g = np.asarray(g, float)
    for a, b in zip(c, g): ax.plot([0, 1], [a, b], color='#c3c2b7', lw=1, zorder=1)
    ax.scatter(np.zeros_like(c), c, s=28, color=CC, zorder=3, edgecolor='white', linewidth=1, label='대조 w16c')
    ax.scatter(np.ones_like(g), g, s=28, color=CG, zorder=3, edgecolor='white', linewidth=1, label='후보 w16gm')
    ax.plot([-0.15, 0.15], [c.mean()] * 2, color=CC, lw=3); ax.plot([0.85, 1.15], [g.mean()] * 2, color=CG, lw=3)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['대조', '후보']); ax.set_xlim(-0.4, 1.4); ax.set_title(title); ax.set_ylabel(ylab)


# ---- 1. claim 2 / 3 paired ----
fig, axs = plt.subplots(1, 5, figsize=(14, 3.4))
c2 = V['claim2']
pairs(axs[0], c2['early']['primary']['ctrl'], c2['early']['primary']['cand'], f'아령 이른 창 (p={c2["early"]["primary"]["p"]})', '아령 프레임 비율 D')
pairs(axs[1], c2['late']['primary']['ctrl'], c2['late']['primary']['cand'], f'아령 늦은 창 (p={c2["late"]["primary"]["p"]})', '아령 프레임 비율 D')
c3 = V['claim3']
for ax, k, lab in zip(axs[2:], ('film', 'dead', 'tip'), ('얇은 막 칸', '죽은 실 칸', '가지 끝 줄 칸')):
    pairs(ax, c3[k]['primary']['ctrl'], c3[k]['primary']['cand'], f'{lab} 늦은 창 (p={c3[k]["primary"]["p"]})', '프레임 평균 칸 수')
axs[0].legend(loc='upper right', frameon=False, fontsize=8)
fig.suptitle('long, 시드 짝 16개 (회색 선 = 같은 시드, 굵은 가로선 = 평균)', fontsize=10); fig.tight_layout(); fig.savefig(os.path.join(FIG, 'c2c3_pairs.png')); plt.close(fig)

# ---- 2. time series ----
PK = 'M=wet|r=3|f=0.10|neck=any'
get = dict(dumbbell=lambda x: float(x['db'][PK]), film=lambda x: x['film']['h=0.3|a=40|b=3'], dead=lambda x: x['dead']['line=3|F0.1|smin=4'], tip=lambda x: x['tip']['L=3|cells'],
           comps=lambda x: x['n8'], veins=lambda x: x['veins'])
labs = dict(dumbbell='아령 프레임 몫 (시드 평균)', film='얇은 막 칸', dead='죽은 실 칸', tip='가지 끝 줄 칸', comps='젖은 성분 수 (8-연결)', veins='정맥 간선 수 (Cmean>4)')
fig, axs = plt.subplots(2, 3, figsize=(13, 6.2)); axs = axs.ravel()
for ax, (k, fn) in zip(axs, get.items()):
    for arm, col, lb in (('ctrl', CC, '대조'), ('cand', CG, '후보')):
        M = np.array([[fn(x) for x in F[name('long', s, arm)]] for s in seeds], float); t = [x['t'] for x in F[name('long', seeds[0], arm)]]
        ax.plot(t, M.mean(0), color=col, label=lb)
    ax.axvspan(100, 1000, color='#f3f2ee', zorder=0); ax.set_title(labs[k]); ax.set_xlabel('t')
axs[0].legend(frameon=False); fig.suptitle('long 시간 따라 (시드 16개 평균, 옅은 띠 = 이른 창, 그 뒤 = 늦은 창)', fontsize=10); fig.tight_layout(); fig.savefig(os.path.join(FIG, 'long_timeseries.png')); plt.close(fig)


# ---- 3. frame maps ----
def masks(Z):
    wet = Z['wet'].astype(bool); h = Z['h'].astype(float); age = Z['age'].astype(float); N = wet.shape[0]
    lab, n = Ms.torus_label(wet, 8); vol = np.bincount(lab.ravel(), weights=np.where(wet, h, 0).ravel()); vol[0] = -1; body = lab == int(np.argmax(vol)); Vb = vol.max()
    F_ = np.zeros((N, N))
    for k, d in enumerate(Ms.DIRS):
        act = wet & Ms.nb(wet, d); q = np.where(act, Z['Qgross'][k], 0.0); F_ = np.maximum(F_, np.maximum(q, Ms.rev(q, d)))
    Fref = np.median(F_[body & (age >= 20)])
    thin = wet & (h < 0.3); film = body & thin & (age >= 40) & Ms.in_full_block(thin, 3)
    line = body & ~Ms.in_full_block(wet, 3); ll, nl = Ms.torus_label(line, 8); sz = np.bincount(ll.ravel()); sz[0] = 0
    dead = line & (sz[ll] >= 4) & (age >= 20) & (F_ < 0.1 * Fref)
    tip = np.zeros(N * N, bool)
    for _, s in Ms.tip_lines(wet, body):
        if len(s) >= 3: tip[list(s)] = True
    e = Ms.edt_torus(wet); core = wet & (e > 3); blob = np.zeros((N, N), int)
    if core.any():
        reg = wet & (Ms.edt_torus(~core) <= 3) & body; lb, nb_ = Ms.torus_label(reg, 8); bv = np.bincount(lb.ravel(), weights=np.where(reg, h, 0).ravel())[1:]
        for j, i in enumerate([i for i in np.argsort(bv)[::-1] if bv[i] >= 0.1 * Vb]): blob[lb == i + 1] = j + 1
    return wet, h, body, film, dead, tip.reshape(N, N), blob


def center_on(a, c):
    N = a.shape[0]; return np.roll(a, (N // 2 - int(round(c[1])) % N, N // 2 - int(round(c[0])) % N), (0, 1))


def show(ax, run, t, title):
    Z = np.load(os.path.join(RUNS, run, f'vs_t{int(t):04d}.npz')); wet, h, body, film, dead, tip, blob = masks(Z)
    c = np.asarray(Z['cen']).ravel()[:2] % wet.shape[0]
    img = np.ones(wet.shape + (3,)) * np.array([0.11, 0.11, 0.10])
    g = np.clip(h / 1.2, 0, 1)[..., None]; img = np.where(wet[..., None], np.array([0.35, 0.33, 0.25]) * (1 - g) + np.array([0.98, 0.93, 0.70]) * g, img)
    img = np.where((wet & ~body)[..., None], np.array([0.9, 0.2, 0.2]), img)
    for m, k in ((film, 'film'), (tip, 'tip'), (dead, 'dead')):
        col = np.array([int(OV[k][i:i + 2], 16) / 255 for i in (1, 3, 5)]); img = np.where(m[..., None], col, img)
    img = center_on(img, c); bl = center_on(blob, c)
    ax.imshow(img, origin='lower', interpolation='nearest')
    if bl.max() >= 1:
        for j in range(1, bl.max() + 1): ax.contour(bl == j, levels=[0.5], colors=[OV['blob']], linewidths=1.2, origin='lower')
    ax.set_title(title, fontsize=9); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    return int(film.sum()), int(dead.sum()), int(tip.sum()), int(blob.max())


W = V['worst']; cases = [(k, W[k]) for k in ('dumbbell_late', 'film_late', 'dead_late', 'tip_late', 'dumbbell_early') if W.get(k) and W[k]['value'] is not None and W[k]['value'] >= 0]
for k, w in cases:
    fig, axs = plt.subplots(1, 2, figsize=(10, 5.3))
    for ax, arm in zip(axs, ('ctrl', 'cand')):
        r = show(ax, name('long', w['seed'], arm), w['t'], '')
        ax.set_title(f'{"대조" if arm == "ctrl" else "후보"} s{w["seed"]} t={w["t"]:.0f}  막 {r[0]}, 죽은 실 {r[1]}, 끝 줄 {r[2]}, 큰 덩이 {r[3]}', fontsize=9)
    fig.suptitle(f'후보의 가장 나쁜 프레임: {k}\n(노랑 바탕 = 두께, 청록 = 얇은 막, 분홍 = 죽은 실, 노랑 = 가지 끝 줄, 파란 선 = 큰 덩이, 빨강 = 몸 밖 조각)', fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93]); fig.savefig(os.path.join(FIG, f'worst_{k}_s{w["seed"]}_t{int(w["t"]):04d}.png')); plt.close(fig)

# galleries: t = 1000, 1500, 2000 of the first 6 seeds
for tg in (1000, 1500, 2000):
    fig, axs = plt.subplots(2, 6, figsize=(18, 7.2))
    for j, s in enumerate(seeds[:6]):
        for i, arm in enumerate(('ctrl', 'cand')):
            r = show(axs[i, j], name('long', s, arm), tg, '')
            axs[i, j].set_title(f'{"대조" if arm == "ctrl" else "후보"} s{s}  막{r[0]} 죽은실{r[1]} 끝줄{r[2]} 덩이{r[3]}', fontsize=8)
    fig.suptitle(f'long t={tg} (위: 대조, 아래: 후보. 청록 = 얇은 막, 분홍 = 죽은 실, 노랑 = 가지 끝 줄, 파란 선 = 큰 덩이, 빨강 = 몸 밖 조각)', fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95], h_pad=2.0); fig.savefig(os.path.join(FIG, f'gallery_t{tg:04d}.png')); plt.close(fig)

# ---- 4. claim 4 ----
c4 = V['claim4']; fig, axs = plt.subplots(1, 4, figsize=(12, 3.3))
for ax, scn in zip(axs, ('food3', 'asym3', 'food4', 'mig')):
    d = c4.get(scn)
    if not d: continue
    st = d['disp'] if scn == 'mig' else d['score']
    pairs(ax, st['ctrl'], st['cand'], f'{scn} (닿은 수 {d["touched"][0]}→{d["touched"][1]})', '끝 변위 (셀)' if scn == 'mig' else '평균 닿은 시각 S')
axs[0].legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(FIG, 'c4_food_mig.png')); plt.close(fig)
print('figs', sorted(os.listdir(FIG)))

# ---- 5. health failure: persistent negative cells (asym3 s316 candidate) ----
fails = [f for f in V['claim5']['fails'] if 'neg' in f['failed']]
for fl in fails:
    rn = fl['name']; ctl = rn.replace('_w16gm', '_w16c'); rd = os.path.join(RUNS, rn)
    fr = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))); first = None
    for f in fr:
        Z = np.load(f)
        if (Z['wet'] & (Z['h'] < 0)).any(): first = float(Z['t']); break
    if first is None: continue
    ys, xs = np.nonzero(np.load(os.path.join(rd, f'vs_t{int(first):04d}.npz'))['wet'] & (np.load(os.path.join(rd, f'vs_t{int(first):04d}.npz'))['h'] < 0)); cy, cx = int(np.median(ys)), int(np.median(xs))
    ts = [first - 20, first, min(first + 160, 480)]
    fig, axs = plt.subplots(2, 3, figsize=(12, 8.2))
    for i, run in enumerate((ctl, rn)):
        for j, t in enumerate(ts):
            Z = np.load(os.path.join(RUNS, run, f'vs_t{int(t):04d}.npz')); w = Z['wet']; h = Z['h'].astype(float); N = w.shape[0]
            sh = (N // 2 - cy, N // 2 - cx); w2 = np.roll(w, sh, (0, 1)); h2 = np.roll(h, sh, (0, 1)); win_ = slice(N // 2 - 30, N // 2 + 30)
            img = np.ones(w.shape + (3,)) * np.array([0.11, 0.11, 0.10]); g = np.clip(h2 / 3.0, 0, 1)[..., None]
            img = np.where(w2[..., None], np.array([0.35, 0.33, 0.25]) * (1 - g) + np.array([0.98, 0.93, 0.70]) * g, img)
            img = np.where((w2 & (h2 < 0))[..., None], np.array([0.89, 0.29, 0.28]), img)
            ax = axs[i, j]; ax.imshow(img[win_, win_], origin='lower', interpolation='nearest'); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            neg = w & (h < 0)
            ax.set_title(f'{"대조" if run == ctl else "후보"} t={t:.0f}: 음수 칸 {int(neg.sum())}, 합 {h[neg].sum():.2f}, 최소 {h[neg].min() if neg.any() else 0:.2f}', fontsize=9)
    fig.suptitle(f'{rn}: 스텝 끝 음수 두께가 남은 칸 (빨강). 60×60 칸 확대, 밝을수록 두꺼움(0~3)', fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95]); fig.savefig(os.path.join(FIG, f'health_neg_{rn}.png')); plt.close(fig)
print('figs', sorted(os.listdir(FIG)))
