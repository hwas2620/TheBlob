#!/usr/bin/env python3
"""verify3 그림. judge.py all 뒤에 돌린다.

fig/trap_F.png        시드마다 새 땅 비율 F(t) 와 갇힌 시각
fig/mb_raster.png     long 의 판마다 상태 (한 덩이 / 여러 덩이 / 아령), 시드 × 팔
fig/claim3_pairs.png  주장 3 의 세 지표, 시드마다 대조 → 후보
fig/case_*.png        가장 나쁜 사례의 두께 지도 (judge 가 고른 판)
"""
import sys, os, json, gzip, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge as J
from vlib import tlabel, topen

V3 = J.V3; FIG = os.path.join(V3, 'fig'); RUNS = os.path.normpath(os.path.join(V3, '..', 'model', 'runs'))
C_CTRL = '#2a78d6'; C_CAND = '#eb6834'; SURF = '#fcfcfb'; INK = '#0b0b0b'; INK2 = '#52514e'; GRID = '#e4e3df'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2,
                     'text.color': INK, 'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                     'lines.linewidth': 2, 'font.family': ['WenQuanYi Zen Hei', 'DejaVu Sans'], 'axes.unicode_minus': False})
os.makedirs(FIG, exist_ok=True)


def trap_fig(trap):
    seeds = list(J.SEEDS['long']); fig, axs = plt.subplots(2, 7, figsize=(16, 5), sharex=True, sharey=True)
    for ax, s in zip(axs.ravel(), seeds):
        for a, col, lb in (('x17c', C_CTRL, '대조 x17c'), ('x17fs', C_CAND, '후보 x17fs')):
            R = J.load('long', s, a)
            if R is None: continue
            t = np.array([f['t'] for f in R['frames']]); F = np.array([f['F'] for f in R['frames']])
            Fb = np.array([F[max(0, i - 4):i + 1].mean() for i in range(len(F))])
            ax.plot(t, Fb, color=col, label=lb)
            tp = trap[f'{s}_{a}']['F0.3']; Fe = trap[f'{s}_{a}']['F_early']
            ax.axhline(0.3 * Fe, color=col, lw=0.8, ls=':')
            if tp is not None: ax.axvline(tp, color=col, lw=1, ls='--')
        ax.set_title(f'seed {s}', fontsize=9)
    axs[0, 0].legend(frameon=False, fontsize=8)
    for ax in axs[1]: ax.set_xlabel('t')
    for ax in axs[:, 0]: ax.set_ylabel('F (5판 이동 평균)')
    fig.suptitle('long: 가장 큰 몸 둘레의 새 땅 비율 F(t). 점선 = 0.3 × 이른 수준, 세로 파선 = 갇힌 시각', fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'trap_F.png'), dpi=110); plt.close(fig)


def raster_fig(trap):
    seeds = list(J.SEEDS['long']); rows = []; labels = []; marks = []
    for s in seeds:
        for a in J.ARMS:
            R = J.load('long', s, a)
            if R is None: continue
            row = []
            for f in R['frames']:
                v = 2 if J.db_frame(f, 0.5, 0.10, 2) else (1 if J.mb_frame(f, 0.5, 0.10) else 0)
                row.append(v)
            rows.append(row); labels.append(f'{s} {"대조" if a == "x17c" else "후보"}'); marks.append(trap[f'{s}_{a}']['F0.3'])
    L = max(len(r) for r in rows); A = np.full((len(rows), L), np.nan)
    for i, r in enumerate(rows): A[i, :len(r)] = r
    cmap = ListedColormap(['#eeede9', '#f4a582', '#b2182b'])
    fig, ax = plt.subplots(figsize=(13, 0.28 * len(rows) + 1.5))
    ax.imshow(A, aspect='auto', cmap=cmap, vmin=0, vmax=2, extent=(10, 20 * L + 10, len(rows) - 0.5, -0.5), interpolation='nearest')
    for i, tp in enumerate(marks):
        if tp is not None: ax.plot([tp, tp], [i - 0.45, i + 0.45], color=INK, lw=2)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(labels, fontsize=7); ax.grid(False); ax.set_xlabel('t')
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color='#eeede9', label='큰 덩이 하나 이하'), Patch(color='#f4a582', label='한 몸에 큰 덩이 둘 이상 (MB)'), Patch(color='#b2182b', label='그중 가는 실로 이어짐 (아령, DB)'),
                       Patch(color=INK, label='검은 막대 = 갇힌 시각')], loc='upper center', bbox_to_anchor=(0.5, -0.06), ncol=4, frameon=False)
    ax.set_title('long: 판마다 상태 (h ≥ 0.5, 큰 덩이 ≥ 몸 부피의 10%, 아령 = 가장 좁은 곳 w ≤ 2)', fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'mb_raster.png'), dpi=110); plt.close(fig)


def pairs_fig(trap):
    specs = [('3a 얇은 막 (몸 넓이 비율)', J.run_val_c3('film', '0.3_60')), ('3b 죽은 실 (셀 수)', J.run_val_c3('thr', 'med_0.1')), ('3c 죽은 가지 끝 (개수)', J.run_val_c3('tip', 'med_0.1')),
             ('2 여러 덩이 판 비율 (MB)', lambda R, w: J.frac(J.win_frames(R, w), lambda f: J.mb_frame(f, 0.5, 0.10)))]
    fig, axs = plt.subplots(1, 4, figsize=(14, 3.8))
    for ax, (tt, fn) in zip(axs, specs):
        c, x, seeds = J.paired(trap, fn)
        for ci, xi in zip(c, x):
            ax.plot([0, 1], [ci, xi], color='#b9b8b2', lw=1, zorder=1)
        ax.scatter(np.zeros_like(c), c, s=40, color=C_CTRL, zorder=3, edgecolor=SURF, linewidth=1.5, label='대조')
        ax.scatter(np.ones_like(x), x, s=40, color=C_CAND, zorder=3, edgecolor=SURF, linewidth=1.5, label='후보')
        ax.set_xticks([0, 1]); ax.set_xticklabels(['대조 x17c', '후보 x17fs']); ax.set_xlim(-0.4, 1.4)
        ax.set_title(f'{tt}\n평균 {np.nanmean(c):.3g} → {np.nanmean(x):.3g}', fontsize=9)
    fig.suptitle('long, 옮겨 다니는 때 (t = 100 ~ 갇힌 시각): 시드마다 대조 → 후보', fontsize=10, y=1.02)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'claim3_pairs.png'), dpi=110, bbox_inches='tight'); plt.close(fig)


def case_fig(run, t, title, fname, zoom=True, dead=False):
    d = np.load(os.path.join(RUNS, run, f'vs_t{int(round(t)):04d}.npz'))
    wet = d['wet'].astype(bool); h = d['h'].astype(float); N = wet.shape[0]
    lab, n = tlabel(wet); hw = np.where(wet, h, 0); vol = np.bincount(lab.ravel(), weights=hw.ravel()); big = int(np.argmax(vol[1:]) + 1)
    # 가장 큰 몸의 무게 중심을 가운데로 옮긴다
    ys, xs = np.nonzero(lab == big)
    cy = int(np.angle(np.exp(2j * np.pi * ys / N).mean()) / (2 * np.pi) * N) % N; cx = int(np.angle(np.exp(2j * np.pi * xs / N).mean()) / (2 * np.pi) * N) % N
    sh = (N // 2 - cy, N // 2 - cx)
    W = np.roll(wet, sh, (0, 1)); H = np.roll(h, sh, (0, 1))
    op = np.roll(topen(wet & (h >= 0.5), 3), sh, (0, 1))
    img = np.where(W, np.clip(H, 0, 1.2), np.nan)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_facecolor('#f1f0ec')
    im = ax.imshow(img, cmap='YlOrBr', vmin=0, vmax=1.2, interpolation='nearest')
    ax.contour(op.astype(float), levels=[0.5], colors=[INK], linewidths=0.8)
    if dead:      # 흐름 없는 실 셀 (q < 0.03 × 중앙값, 실 셀, age >= 20): 파란 점
        from vlib import cell_flow
        age = d['age'].astype(float); q = cell_flow(d['Qgross'].astype(float)); body = lab == big
        qref = np.median(q[body & (age >= 20)]); plate = topen(body, 3); thread = body & ~plate
        tl, nt = tlabel(thread); tsz = np.bincount(tl.ravel()); tsz[0] = 0
        dm = np.roll(thread & (tsz[tl] >= 3) & (q < 0.03 * qref) & (age >= 20), sh, (0, 1))
        yy, xx = np.nonzero(dm); ax.scatter(xx, yy, s=6, color=C_CTRL, marker='s', linewidths=0, label=f'흐름 없는 실 셀 ({int(dm.sum())})')
        ax.legend(loc='lower left', fontsize=8, frameon=False)
    small = [(k, vol[k] / vol[1:].sum()) for k in range(1, n + 1) if vol[k] / vol[1:].sum() < 0.05]
    L2 = np.roll(lab, sh, (0, 1))
    for k, fv in small:
        yy, xx = np.nonzero(L2 == k); ax.scatter(xx.mean(), yy.mean(), s=120, facecolors='none', edgecolors='#b2182b', linewidths=1.5)
    if zoom:
        yy, xx = np.nonzero(W); pad = 12
        ax.set_xlim(max(0, xx.min() - pad), min(N, xx.max() + pad)); ax.set_ylim(min(N, yy.max() + pad), max(0, yy.min() - pad))
    ax.grid(False); ax.set_xticks([]); ax.set_yticks([])
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02); cb.set_label('두께 h')
    ax.set_title(title, fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=110); plt.close(fig)


if __name__ == '__main__':
    trap = json.load(open(os.path.join(V3, 'data', 'trap.json')))
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('all', 'trap'): trap_fig(trap)
    if what == 'all':
        raster_fig(trap); pairs_fig(trap)
    if what == 'case':
        case_fig(sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5], dead=(len(sys.argv) > 6 and sys.argv[6] == 'dead'))
