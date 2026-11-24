#!/usr/bin/env python3
"""verify6 그림 (판정 뒤). usage: figs.py"""
import glob, json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
V6 = os.path.normpath(os.path.join(HERE, '..')); RUNS = os.path.normpath(os.path.join(V6, '..', 'model', 'runs')); FIG = os.path.join(V6, 'fig'); DATA = os.path.join(V6, 'data')
CTRL_C = '#2a78d6'; CAND_C = '#eb6834'; INK = '#0b0b0b'; INK2 = '#52514e'; SURF = '#fcfcfb'
CM = LinearSegmentedColormap.from_list('h', ['#cfe0f5', '#7fb0ea', '#2a78d6', '#0d2f5c']); CM.set_bad(SURF)
plt.rcParams.update({'font.size': 8, 'axes.edgecolor': '#c9c8c2', 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.titlecolor': INK,
                     'figure.facecolor': SURF, 'axes.facecolor': SURF, 'savefig.facecolor': SURF})
from matplotlib import font_manager as fm_
for fp in ('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'):
    if os.path.exists(fp):
        fm_.fontManager.addfont(fp); plt.rcParams['font.family'] = fm_.FontProperties(fname=fp).get_name(); break
plt.rcParams['axes.unicode_minus'] = False


def frame(scn, sd, tg, t):
    f = os.path.join(RUNS, f'b_{scn}_s{sd}_{tg}', f'vs_t{int(t):04d}.npz')
    return np.load(f) if os.path.exists(f) else None


def crop(Z, W=110, cen=None):
    wet = Z['wet'].astype(bool); h = np.where(wet, Z['h'], 0.0); N = wet.shape[0]
    if cen is None:
        cen = M.circ_center(wet, h) if wet.any() else (N / 2, N / 2)
    sx = int(round(N / 2 - cen[0])); sy = int(round(N / 2 - cen[1])); hr = np.roll(h, (sy, sx), (0, 1)); W = min(W, N)
    a = N // 2 - W // 2
    return hr[a:a + W, a:a + W], cen


def show(ax, Z, title, cen=None, W=110):
    if Z is None:
        ax.axis('off'); ax.set_title(title + ' (없음)', fontsize=7); return None
    im, cen = crop(Z, W, cen)
    ax.imshow(np.ma.masked_where(im <= 0, im), cmap=CM, vmin=0, vmax=2.5, origin='lower', interpolation='nearest'); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=7)
    return cen


def runs_json():
    R = {}
    for f in glob.glob(os.path.join(DATA, 'b_*.json')):
        d = json.load(open(f)); R[(d['scn'], d['seed'], d['tag'])] = d
    return R


def fig_trap(R):
    seeds = sorted({k[1] for k in R if k[0] == 'slimeall'})[:3]
    ts = [100, 200, 300, 400, 600, 800]
    fig, axs = plt.subplots(2 * len(seeds), len(ts), figsize=(1.6 * len(ts), 1.7 * 2 * len(seeds)))
    for i, sd in enumerate(seeds):
        c = R.get(('slimeall', sd, 'v6g'), {}); ton = c.get('met', {}).get('t_scl')
        for j, t in enumerate(ts):
            for r, tg in enumerate(('v6g', 'v6c')):
                show(axs[2 * i + r, j], frame('slimeall', sd, tg, t), f"{'후보' if tg == 'v6g' else '대조'} s{sd} t={t}" + (f' (갇힘 {ton:.0f})' if (tg == 'v6g' and j == 0 and ton) else ''))
    fig.suptitle('갇힘 시험 slimeall: 두께 h (0~2.5), 무게중심을 가운데로', fontsize=9); fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(FIG, 'fig1_trap_slimeall.png'), dpi=110); plt.close(fig)


def fig_long(R):
    seeds = sorted({k[1] for k in R if k[0] == 'long'})
    ts = [400, 1000, 1500, 2000]
    fig, axs = plt.subplots(2 * len(seeds), len(ts), figsize=(1.6 * len(ts), 1.7 * 2 * len(seeds)))
    for i, sd in enumerate(seeds):
        ton = R.get(('long', sd, 'v6g'), {}).get('met', {}).get('t_scl')
        for j, t in enumerate(ts):
            for r, tg in enumerate(('v6g', 'v6c')):
                show(axs[2 * i + r, j], frame('long', sd, tg, t), f"{'후보' if tg == 'v6g' else '대조'} s{sd} t={t}" + (f' (갇힘 {ton:.0f})' if (tg == 'v6g' and j == 0 and ton) else ''), W=192)
    fig.suptitle('long (T=2000): 두께 h', fontsize=9); fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(FIG, 'fig2_long.png'), dpi=100); plt.close(fig)


def fig_mig(R):
    seeds = sorted({k[1] for k in R if k[0] == 'mig'})[:4]
    ts = [100, 200, 300, 400]
    fig, axs = plt.subplots(2 * len(seeds), len(ts), figsize=(1.6 * len(ts), 1.7 * 2 * len(seeds)))
    for i, sd in enumerate(seeds):
        for j, t in enumerate(ts):
            for r, tg in enumerate(('v6g', 'v6c')):
                show(axs[2 * i + r, j], frame('mig', sd, tg, t), f"{'후보' if tg == 'v6g' else '대조'} s{sd} t={t}", W=192)
    fig.suptitle('이주 mig: 두께 h', fontsize=9); fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(FIG, 'fig3_mig.png'), dpi=110); plt.close(fig)


def fig_food(R):
    rows = [(s, sd) for s in ('food3', 'asym3', 'food4') for sd in sorted({k[1] for k in R if k[0] == s})[:1]]
    fig, axs = plt.subplots(len(rows), 4, figsize=(6.6, 1.7 * len(rows)))
    for i, (s, sd) in enumerate(rows):
        T = 700 if s == 'food4' else 480; ts = [T // 2, T]
        for j, t in enumerate(ts):
            for r, tg in enumerate(('v6g', 'v6c')):
                Z = frame(s, sd, tg, t)
                if Z is not None:
                    N = Z['wet'].shape[0]; show(axs[i, 2 * j + r], Z, f"{'후보' if tg == 'v6g' else '대조'} {s} s{sd} t={t}", cen=(N / 2, N / 2), W=N)
    fig.suptitle('먹이 시나리오 (판 전체)', fontsize=9); fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(FIG, 'fig4_food.png'), dpi=110); plt.close(fig)


def fig_dir(J):
    c5 = J['c5']; fig, ax = plt.subplots(figsize=(5.0, 2.0))
    for y, tg, col, nm in ((1, 'v6g', CAND_C, '후보'), (0, 'v6c', CTRL_C, '대조')):
        v = c5[tg]['d25'].get('values', [])
        ax.scatter(v, np.full(len(v), y) + np.random.default_rng(0).uniform(-0.12, 0.12, len(v)), s=22, color=col, edgecolor=SURF, linewidth=1.0, zorder=3)
        ax.text(-58, y, nm, va='center', ha='left', color=INK, fontsize=8)
    ax.axvline(0, color='#c9c8c2', lw=1, zorder=1); ax.set_yticks([]); ax.set_xlim(-60, 60); ax.set_ylim(-0.6, 1.6)
    ax.set_xlabel('25칸 옮겨 간 때의 방향 - 유인원 방향 (도, +는 반시계)'); ax.set_title('이주 방향 오차 (mig 10 + long 6 시드)')
    for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
    fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(FIG, 'fig5_direction.png'), dpi=130); plt.close(fig)


def fig_ts(R):
    keys = [('dumbbell', '아령 장면 몫', None), ('dead_thread_cells', '흐름 없는 실 칸 / 넓이', 'area'), ('film_cells', '얇은 막 칸 / 넓이', 'area'),
            ('n_dead_tips', '흐름 없는 가지 끝 수', None), ('thread_maxlen', '가장 긴 실 (칸)', None), ('n_debris', '부스러기 수', None)]
    fig, axs = plt.subplots(2, 3, figsize=(8.0, 4.4))
    tgrid = np.arange(20, 2001, 20)
    for ax, (k, nm, norm) in zip(axs.ravel(), keys):
        for tg, col, lab in (('v6c', CTRL_C, '대조'), ('v6g', CAND_C, '후보')):
            acc = {t: [] for t in tgrid}
            for (s, sd, t_), d in R.items():
                if t_ != tg or s not in ('mig', 'long'): continue
                for f in d['frames']:
                    if f.get('empty') or f['t'] not in acc: continue
                    acc[f['t']].append(float(f[k]) / (max(f[norm], 1) if norm else 1.0))
            xs = [t for t in tgrid if acc[t]]; ys = [np.mean(acc[t]) for t in xs]
            ax.plot(xs, ys, color=col, lw=2, label=lab)
        ax.set_title(nm, fontsize=8); ax.set_xlabel('t'); ax.grid(color='#ecebe6', lw=0.6)
        for s in ('top', 'right'): ax.spines[s].set_visible(False)
    axs[0, 0].legend(frameon=False, fontsize=7)
    fig.suptitle('mig + long 실행 평균 (t ≤ 400 은 16 실행, 그 뒤는 long 6 실행)', fontsize=9); fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(FIG, 'fig6_timeseries.png'), dpi=120); plt.close(fig)


def fig_form(R):
    SM = json.load(open(os.path.join(DATA, 'scl_mass.json'))) if os.path.exists(os.path.join(DATA, 'scl_mass.json')) else {}
    cases = [('slimeall', 571, [120, 140, 160, 180, 200, 240, 280]), ('long', 521, [1780, 1800, 1820, 1840, 1880, 1920, 1960])]
    fig, axs = plt.subplots(len(cases), 8, figsize=(13.5, 2.0 * len(cases)), gridspec_kw=dict(width_ratios=[1] * 7 + [1.6]))
    for i, (s, sd, ts) in enumerate(cases):
        c = R.get((s, sd, 'v6g'), {}); ton = c.get('met', {}).get('t_scl'); cen = None
        Zl = frame(s, sd, 'v6g', ts[-1]); cen = crop(Zl, 90)[1] if Zl is not None else None
        for j, t in enumerate(ts):
            Z = frame(s, sd, 'v6g', t); show(axs[i, j], Z, f'{s} s{sd} t={t}' + (f'\nh 최대 {float(Z["h"].max()):.1f}' if Z is not None else ''), cen=cen, W=90)
        ms = SM.get(f'b_{s}_s{sd}_v6g', []); ax = axs[i, 7]
        if ms:
            tt = [a for a, b in ms]; vv = [b for a, b in ms]; ax.plot(tt, vv, color=CAND_C, lw=2, marker='o', ms=3)
            if ton: ax.axvline(ton, color=INK2, lw=1, ls='--'); ax.text(ton, 0.05, ' 갇힘', color=INK2, fontsize=7)
            ax.set_xlim(ton - 100, ton + 250); ax.set_ylim(0, 1.05); ax.set_title('마지막 덩이 자리 안 부피 몫', fontsize=7); ax.set_xlabel('t')
            for q in ('top', 'right'): ax.spines[q].set_visible(False)
    fig.suptitle('후보 균핵 형성 과정 (20 시간 간격)', fontsize=9); fig.tight_layout(rect=(0, 0, 1, 0.95)); fig.savefig(os.path.join(FIG, 'fig7_formation.png'), dpi=110); plt.close(fig)


if __name__ == '__main__':
    os.makedirs(FIG, exist_ok=True)
    R = runs_json(); J = json.load(open(os.path.join(V6, 'judge.json')))
    for f in (fig_trap, fig_long, fig_mig, fig_food, fig_ts, fig_form):
        try: f(R); print('ok', f.__name__)
        except Exception as e: print('fail', f.__name__, e)
    try: fig_dir(J); print('ok fig_dir')
    except Exception as e: print('fail fig_dir', e)
