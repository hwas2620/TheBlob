#!/usr/bin/env python3
"""그림 (판정 뒤에 만든 것, 판정에는 쓰지 않는다).

usage: figs.py series            long 의 스텝별 숫자 (시드마다 대조/후보)
       figs.py states RUN [t ...]  한 실행의 저장 상태 그림 (h, 마른 곳은 검정)
       figs.py pair SCN SEED [t ...]  대조와 후보의 같은 시각 상태를 나란히
       figs.py perseed           주장 1c, 2 의 시드별 값
"""
import glob, json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.normpath(os.path.join(HERE, '..', '..', 'model'))
FIG = os.path.join(HERE, '..', 'fig'); DATA = os.path.join(HERE, '..', 'data')
sys.path.insert(0, HERE)
import monitor

CM = LinearSegmentedColormap.from_list('body', ['#3a3410', '#d7b928', '#fff4b0'])
COL = dict(v15c='#4c72b0', v15k='#dd8452')


def load_state(run, t):
    rd = os.path.join(MODEL, 'runs', run)
    for pat in ('lv_t%04d.npz', 'vs_t%04d.npz'):
        f = os.path.join(rd, pat % t)
        if os.path.exists(f):
            Z = np.load(f); return Z['wet'].astype(bool), Z['h'].astype(float)
    if t < 0:
        return np.load(os.path.join(rd, 'wet.npy')), np.load(os.path.join(rd, 'h.npy')).astype(float)
    raise FileNotFoundError(run, t)


def draw(ax, wet, h, title, mark_lines=True):
    img = np.where(wet, np.clip(h, 0, 1.5), np.nan)
    ax.imshow(np.zeros_like(h), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    ax.imshow(img, cmap=CM, vmin=0, vmax=1.3, interpolation='nearest')
    if mark_lines:
        rg = monitor.ring_groups(wet); ys, xs = np.nonzero(rg >= 2); ax.scatter(xs, ys, s=0.3, c='#e0457b', linewidths=0)
        th = wet & (h < 0.3); ys, xs = np.nonzero(th & (rg < 2)); ax.scatter(xs, ys, s=0.3, c='#5fb7e5', linewidths=0)
    lab, n = monitor.tlabel(wet)
    ax.set_title(f'{title}\n조각 {n}, 넓이 {int(wet.sum())}', fontsize=8); ax.set_xticks([]); ax.set_yticks([])


def series():
    fs = sorted(glob.glob(os.path.join(DATA, 'mon', 'b_long_s2[01]*_v15[ck].npz')))
    seeds = sorted({int(os.path.basename(f).split('_s')[1].split('_')[0]) for f in fs if not '_s220_' in f})
    rows = [('ncomp', '젖은 조각 수'), ('vol_out', '가장 큰 조각 밖 부피 비율'), ('big_0.6_0.1', '큰 굵은 조각 수 (h≥0.6, ≥10%)'), ('thin', '얇은 셀 (h<0.3)'), ('line', '줄 셀')]
    fig, axs = plt.subplots(len(rows), len(seeds), figsize=(2.2 * len(seeds), 1.7 * len(rows)), sharex=True, squeeze=False)
    for j, s in enumerate(seeds):
        for tag in ('v15c', 'v15k'):
            f = os.path.join(DATA, 'mon', f'b_long_s{s}_{tag}.npz')
            if not os.path.exists(f): continue
            Z = np.load(f); A = Z['stats']; keys = list(Z['keys']); t = Z['t']
            for i, (k, lab) in enumerate(rows):
                y = A[:, keys.index(k)]; st = max(1, y.size // 2000)
                axs[i, j].plot(t[::st], y[::st], lw=0.6, color=COL[tag], label='대조' if tag == 'v15c' else '후보')
        axs[0, j].set_title(f'시드 {s}', fontsize=9)
    for i, (k, lab) in enumerate(rows): axs[i, 0].set_ylabel(lab, fontsize=7)
    axs[0, 0].legend(fontsize=6)
    for ax in axs.ravel(): ax.tick_params(labelsize=6)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'long_series.png'), dpi=110); plt.close(fig)


def states(run, ts):
    fig, axs = plt.subplots(1, len(ts), figsize=(3.2 * len(ts), 3.6), squeeze=False)
    for j, t in enumerate(ts):
        w, h = load_state(run, t); draw(axs[0, j], w, h, f'{run} t={t}')
    fig.tight_layout(); fig.savefig(os.path.join(FIG, f'states_{run}.png'), dpi=120); plt.close(fig)


def pair(scn, seed, ts, crop=None):
    fig, axs = plt.subplots(2, len(ts), figsize=(3.2 * len(ts), 7.8), squeeze=False)
    for i, tag in enumerate(('v15c', 'v15k')):
        run = f'b_{scn}_s{seed}_{tag}'
        for j, t in enumerate(ts):
            w, h = load_state(run, t); draw(axs[i, j], w, h, f"{'대조' if tag == 'v15c' else '후보'} s{seed} t={t}")
            P = json.load(open(os.path.join(MODEL, 'runs', run, 'params.json')))
            if P.get('eat', 0) > 0:
                c0 = P['N'] / 2 - 0.5
                for q, (a_, d_) in enumerate(P['foods']):
                    fx = c0 + d_ * np.cos(np.radians(a_)); fy = c0 + d_ * np.sin(np.radians(a_))
                    axs[i, j].add_patch(plt.Circle((fx, fy), P['food_r'] + 1.5, fill=False, ec='#38d6ff', lw=0.8)); axs[i, j].text(fx + 7, fy, str(q + 1), color='#38d6ff', fontsize=7)
    fig.suptitle('색: 두께 h (검정 = 마름). 분홍 점 = 줄 셀, 하늘 점 = 얇은 셀(h<0.3, 줄 아님)', fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.97), h_pad=2.5); fig.savefig(os.path.join(FIG, f'pair_{scn}_s{seed}.png'), dpi=120); plt.close(fig)


def perseed():
    V = json.load(open(os.path.join(DATA, 'verdict.json')))
    items = [('claim1', 'a_split', '갈라진 시간 비율'), ('claim1', 'b_volout', '바깥 부피 (시간 평균)'), ('claim1', 'c_big2', '큰 굵은 조각 ≥2 시간 비율'),
             ('claim2', 'late_thin', '늦은 때 얇은 셀 수'), ('claim2', 'late_line', '늦은 때 줄 셀 수')]
    fig, axs = plt.subplots(1, len(items), figsize=(3.3 * len(items), 3.2))
    for ax, (c, k, lab) in zip(axs, items):
        o = V[c][k]; xc = o['control_per_seed']; xk = o['candidate_per_seed']
        for a, b in zip(xc, xk): ax.plot([0, 1], [a, b], color='#999', lw=0.7)
        ax.scatter(np.zeros(len(xc)), xc, color=COL['v15c'], s=14); ax.scatter(np.ones(len(xk)), xk, color=COL['v15k'], s=14)
        ax.set_xticks([0, 1]); ax.set_xticklabels(['대조', '후보']); ax.set_title(f"{lab}\n판정: {o['verdict']}", fontsize=8); ax.tick_params(labelsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'perseed_claims12.png'), dpi=120); plt.close(fig)


def sens():
    """주장 1c 의 문턱 민감도 (판정 0.6/10% 외의 값은 판정에 쓰지 않는다)와 시간 창별 값"""
    V = json.load(open(os.path.join(DATA, 'verdict.json')))['claim1']['c_big2']; Pp = json.load(open(os.path.join(DATA, 'post.json')))['big2']
    keys = [f'big2_{a}_{b}' for a in (0.3, 0.45, 0.6) for b in (0.05, 0.1, 0.2)]
    vals = {k: (V['control_mean'], V['candidate_mean']) if k == V['key'] else (V['sensitivity'][k]['control_mean'], V['sensitivity'][k]['candidate_mean']) for k in keys}
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.4))
    x = np.arange(len(keys)); axs[0].bar(x - 0.2, [vals[k][0] for k in keys], 0.4, color=COL['v15c'], label='대조'); axs[0].bar(x + 0.2, [vals[k][1] for k in keys], 0.4, color=COL['v15k'], label='후보')
    axs[0].set_xticks(x); axs[0].set_xticklabels([k.replace('big2_', 'h≥').replace('_', '\n≥') for k in keys], fontsize=7); axs[0].legend(fontsize=7)
    axs[0].set_title('큰 굵은 조각 ≥2 인 스텝 비율 (long 12 시드 평균)\n굵음 문턱 h 와 큰 조각 문턱(몸 부피의 비율). 판정은 h≥0.6, ≥0.1', fontsize=8)
    ws = ['0-500', '500-1000', '1000-1500', '1500-2001']
    for key, ls in (('big_0.6_0.1', '-'), ('big_0.3_0.1', '--')):
        for tag, i in (('v15c', 'control'), ('v15k', 'candidate')):
            axs[1].plot(range(4), [Pp[key][w][i] for w in ws], ls, color=COL[tag], marker='o', label=f"{'대조' if tag == 'v15c' else '후보'} {key.replace('big_', 'h≥').replace('_0.1', '')}")
    axs[1].set_xticks(range(4)); axs[1].set_xticklabels(['t 0~500', '500~1000', '1000~1500', '1500~2000'], fontsize=7); axs[1].legend(fontsize=7); axs[1].set_title('시간 창별 (10% 문턱)', fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'claim1c_threshold.png'), dpi=120); plt.close(fig)


if __name__ == '__main__':
    plt.rcParams['font.family'] = ['WenQuanYi Zen Hei', 'DejaVu Sans']; plt.rcParams['axes.unicode_minus'] = False
    cmd = sys.argv[1]
    if cmd == 'series': series()
    elif cmd == 'states': states(sys.argv[2], [int(x) for x in sys.argv[3:]])
    elif cmd == 'pair': pair(sys.argv[2], int(sys.argv[3]), [int(x) for x in sys.argv[4:]])
    elif cmd == 'perseed': perseed()
    elif cmd == 'sens': sens()
