#!/usr/bin/env python3
"""verify5 그림 (사람이 보는 것만). usage: figs.py
읽는 것: verify5/data/runs/*.json, model/runs/b_*_v5[cy]/vs_t*.npz (내 실행만)
쓰는 것: verify5/fig/*.png
"""
import os, sys, json, glob, re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

HERE = os.path.dirname(os.path.abspath(__file__)); V5 = os.path.dirname(HERE); S19 = os.path.dirname(V5)
RUNS = os.path.join(S19, 'model', 'runs'); DATA = os.path.join(V5, 'data', 'runs'); FIG = os.path.join(V5, 'fig')
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({'font.size': 9})
from matplotlib import font_manager as fm
for fp in ('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'):
    if os.path.exists(fp):
        fm.fontManager.addfont(fp); plt.rcParams['font.family'] = fm.FontProperties(fname=fp).get_name(); break
plt.rcParams['axes.unicode_minus'] = False
CM = LinearSegmentedColormap.from_list('slime', [(0, '#0b120b'), (0.05, '#3a3008'), (0.35, '#a08a1c'), (0.7, '#e8c63a'), (1, '#fff6c8')])


def J(name):
    return json.load(open(os.path.join(DATA, name + '.json')))


def vs(name, t):
    return np.load(os.path.join(RUNS, name, f'vs_t{int(t):04d}.npz'))


def centre_on(a, cx, cy):
    N = a.shape[0]
    return np.roll(a, (int(round(N / 2 - cy)), int(round(N / 2 - cx))), (0, 1))


def show_h(ax, name, t, title='', centre=None, vmax=3.0):
    Z = vs(name, t); h = np.where(Z['wet'], Z['h'], 0.0)
    if centre is not None: h = centre_on(h, *centre)
    ax.imshow(np.clip(h, 0, vmax) / vmax, cmap=CM, vmin=0, vmax=1, interpolation='nearest', origin='lower')
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=8)


def series_fig(seed):
    """long 한 시드: 대조/후보의 h 지도를 여러 시각에"""
    ts = [200, 600, 1000, 1400, 1600, 1800, 2000]
    fig, axs = plt.subplots(2, len(ts), figsize=(2.0 * len(ts), 4.8))
    for r, (arm, nm) in enumerate((('c', '대조'), ('y', '후보'))):
        name = f'b_long_s{seed}_v5{arm}'; d = J(name)
        sn = {s['t']: s for s in d['snaps']}
        for k, t in enumerate(ts):
            s = sn.get(float(t))
            info = '' if s is None else f"덩이{max([b['n_lumps'] for b in s['bodies']] or [0])} 부스{s['n_debris']}" + (' 아령' if s['any_dumb'] else '') + (' 균핵' if s['all_scl'] else '')
            show_h(axs[r, k], name, t, f'{nm} t={t}\n{info}')
        axs[r, 0].set_ylabel(f'{nm}\n갇힘(바뀐 기준) {d.get("T_trap2")}\n갇힘(원래 기준) {d["T_trap"]}' + (f'\nt_scl {d["metrics"]["t_scl"]:.0f}' if d['metrics'].get('t_scl') else ''), fontsize=8)
    fig.suptitle(f'long s{seed}: 두께 h (밝을수록 두꺼움, 0~3)', fontsize=10)
    fig.tight_layout(h_pad=1.5); fig.savefig(os.path.join(FIG, f'long_s{seed}_series.png'), dpi=110); plt.close(fig)


def end_gallery(seeds):
    fig, axs = plt.subplots(2, len(seeds), figsize=(1.75 * len(seeds), 4.4))
    for k, s in enumerate(seeds):
        for r, arm in enumerate('cy'):
            name = f'b_long_s{s}_v5{arm}'; d = J(name); b = d['final']['bodies']
            lab = ' '.join(('균' if x['scl'] else '×') for x in b)
            show_h(axs[r, k], name, 2000, f's{s} {"대조" if arm == "c" else "후보"} {lab}')
    fig.suptitle('long 끝 상태 t=2000 (균 = 내 기준의 균핵, × = 아님)', fontsize=10)
    fig.tight_layout(h_pad=1.8); fig.savefig(os.path.join(FIG, 'long_end_gallery.png'), dpi=110); plt.close(fig)


def zoom_end(seeds, fname, title):
    """끝 상태의 몸을 확대"""
    fig, axs = plt.subplots(2, len(seeds), figsize=(2.2 * len(seeds), 4.6))
    axs = np.atleast_2d(axs)
    if axs.shape[0] != 2: axs = axs.T
    for k, s in enumerate(seeds):
        for r, arm in enumerate('cy'):
            name = f'b_long_s{s}_v5{arm}'; d = J(name); b = d['final']['bodies']
            Z = vs(name, 2000); h = np.where(Z['wet'], Z['h'], 0.0); N = h.shape[0]
            if b:
                big = max(b, key=lambda x: x['share']); h = centre_on(h, big['cx'], big['cy'])
            h = h[N // 2 - 40:N // 2 + 40, N // 2 - 40:N // 2 + 40]
            ax = axs[r, k]; ax.imshow(np.clip(h, 0, 3) / 3, cmap=CM, vmin=0, vmax=1, interpolation='nearest', origin='lower'); ax.set_xticks([]); ax.set_yticks([])
            if b:
                x = max(b, key=lambda x: x['share'])
                ax.set_title(f"s{s} {'대조' if arm == 'c' else '후보'}\n덩이{x['n_lumps']} 축비{x['ar']:.2f} κ{x['kappa_area']:.2f}\n꼬리{x['tail']:.2f} {'균핵' if x['scl'] else '균핵 아님'}", fontsize=7)
    fig.suptitle(title, fontsize=10); fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=120); plt.close(fig)


def snapshot_pair(seed, t, fname, title, half=48):
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 3.4))
    for k, arm in enumerate('cy'):
        name = f'b_long_s{seed}_v5{arm}'; d = J(name); s = next(x for x in d['snaps'] if x['t'] == float(t))
        Z = vs(name, t); h = np.where(Z['wet'], Z['h'], 0.0); N = h.shape[0]
        big = max(s['bodies'], key=lambda x: x['share']) if s['bodies'] else None
        if big: h = centre_on(h, big['cx'], big['cy'])
        h = h[N // 2 - half:N // 2 + half, N // 2 - half:N // 2 + half]
        axs[k].imshow(np.clip(h, 0, 2) / 2, cmap=CM, vmin=0, vmax=1, interpolation='nearest', origin='lower'); axs[k].set_xticks([]); axs[k].set_yticks([])
        dd = s['dead']
        axs[k].set_title(f"{'대조' if arm == 'c' else '후보'} t={t}: 덩이 {[b['n_lumps'] for b in s['bodies']]}{' 아령' if s['any_dumb'] else ''}\n막 {dd['film']} 죽은실 {dd['deadthread']} 죽은끝 {dd['deadtips']} 부스러기 {s['n_debris']}", fontsize=8)
    fig.suptitle(title, fontsize=9); fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=120); plt.close(fig)


def timeline(seeds):
    fig, axs = plt.subplots(4, 1, figsize=(8, 8.4), sharex=True)
    for arm, col in (('c', '#888888'), ('y', '#c0392b')):
        for s in seeds:
            d = J(f'b_long_s{s}_v5{arm}'); t = [x['t'] for x in d['snaps']]
            axs[0].plot(t, [max([b['n_lumps'] for b in x['bodies']] or [0]) + (0.06 if arm == 'y' else 0) for x in d['snaps']], color=col, alpha=0.35, lw=0.8)
            axs[1].plot(t, [x['n_debris'] for x in d['snaps']], color=col, alpha=0.35, lw=0.8)
            axs[2].plot(t, [x['rimfresh'] for x in d['snaps']], color=col, alpha=0.35, lw=0.8)
            axs[3].plot(t, [x['board_fresh'] for x in d['snaps']], color=col, alpha=0.35, lw=0.8)
    axs[0].set_ylabel('한 몸의 덩이 수 (최대)'); axs[1].set_ylabel('부스러기 수'); axs[2].set_ylabel('둘레 새 땅 몫 r(t)\n(원래 갇힘 기준)')
    axs[2].axhline(0.05, color='k', lw=0.6, ls=':'); axs[3].set_ylabel('판의 새 땅 몫 F(t)\n(바뀐 기준 0.02)'); axs[3].axhline(0.02, color='k', lw=0.6, ls=':'); axs[3].set_yscale('log'); axs[3].set_xlabel('t')
    for ax in axs: ax.axvline(1600, color='k', lw=0.6, ls='--')
    axs[0].plot([], [], color='#888888', label='대조'); axs[0].plot([], [], color='#c0392b', label='후보'); axs[0].legend(loc='upper right')
    fig.suptitle('long 모든 시드: 시간에 따른 덩이 수, 부스러기 수, 새 땅 몫 (점선 t=1600)', fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'long_timeline.png'), dpi=110); plt.close(fig)


def mig_paths():
    fig, axs = plt.subplots(1, 2, figsize=(9, 4.4), sharex=True, sharey=True)
    files = sorted(glob.glob(os.path.join(DATA, 'b_mig_s*_v5?.json'))) + sorted(glob.glob(os.path.join(DATA, 'b_long_s*_v5?.json')))
    for f in files:
        d = json.load(open(f)); arm = f[-6]; ax = axs[0 if arm == 'c' else 1]
        tr = np.asarray(d['metrics']['traj'], float); tr = tr[tr[:, 0] <= 400]; P0 = d['N'] / 2 - 0.5
        ax.plot(tr[:, 1] - P0, tr[:, 2] - P0, color='#c0392b' if arm == 'y' else '#555555', alpha=0.5, lw=0.9)
    for ax, nm in zip(axs, ('대조', '후보')):
        a = np.radians(27); ax.plot([0, 70 * np.cos(a)], [0, 70 * np.sin(a)], 'b--', lw=0.8); ax.add_patch(plt.Circle((70 * np.cos(a), 70 * np.sin(a)), 4, fill=False, color='b'))
        ax.set_aspect('equal'); ax.set_title(f'{nm}: 몸 중심의 길 (t ≤ 400), 파란 점선 = 유인원 방향'); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'mig_paths.png'), dpi=110); plt.close(fig)


def food_scatter():
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, scn in zip(axs, ('food4', 'food3', 'asym3')):
        mx = 0
        for f in sorted(glob.glob(os.path.join(DATA, f'b_{scn}_s*_v5c.json'))):
            g = f.replace('_v5c', '_v5y')
            if not os.path.exists(g): continue
            a = json.load(open(f)); b = json.load(open(g)); T = a['T']
            for i, (x, y) in enumerate(zip(a['metrics']['t_touch'], b['metrics']['t_touch'])):
                x = T if x is None else x; y = T if y is None else y; mx = max(mx, T)
                ax.scatter(x, y, s=14, color=plt.cm.tab10(i), alpha=0.8)
        ax.plot([0, mx], [0, mx], 'k:', lw=0.8); ax.set_xlabel('대조 닿은 시각'); ax.set_ylabel('후보 닿은 시각'); ax.set_title(f'{scn} (색 = 먹이 번호, 못 닿으면 T)')
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'food_touch.png'), dpi=110); plt.close(fig)


def strip(seed, arm, ts, fname, half=60):
    """한 실행의 여러 시각, 끝 상태의 가장 큰 몸 중심으로 확대"""
    name = f'b_long_s{seed}_v5{arm}'; d = J(name); sn = {x['t']: x for x in d['snaps']}
    big = max(d['final']['bodies'], key=lambda x: x['share'])
    fig, axs = plt.subplots(1, len(ts), figsize=(2.3 * len(ts), 2.9))
    for ax, t in zip(axs, ts):
        Z = vs(name, t); h = np.where(Z['wet'], Z['h'], 0.0); N = h.shape[0]; h = centre_on(h, big['cx'], big['cy'])[N // 2 - half:N // 2 + half, N // 2 - half:N // 2 + half]
        ax.imshow(np.clip(h, 0, 3) / 3, cmap=CM, vmin=0, vmax=1, interpolation='nearest', origin='lower'); ax.set_xticks([]); ax.set_yticks([])
        x = sn[float(t)]; b = max(x['bodies'], key=lambda q: q['share'])
        ax.set_title(f"t={t} 넓이 {x['area']}\nκ{b['kappa_area']:.2f} 꼬리{b['tail']:.2f}{' 균핵' if x['all_scl'] else ''}", fontsize=8)
    fig.suptitle(f"long s{seed} {'후보' if arm == 'y' else '대조'}: {fname}", fontsize=9); fig.tight_layout(); fig.savefig(os.path.join(FIG, fname + '.png'), dpi=110); plt.close(fig)


if __name__ == '__main__':
    what = sys.argv[1:] or ['all']
    seeds = sorted({int(re.findall(r's(\d+)_', os.path.basename(f))[0]) for f in glob.glob(os.path.join(DATA, 'b_long_s*_v5y.json')) if os.path.exists(f.replace('_v5y', '_v5c'))})
    if 'all' in what or 'gallery' in what: end_gallery(seeds); timeline(seeds)
    if 'all' in what or 'mig' in what: mig_paths(); food_scatter()
    for w in what:
        if w.startswith('series:'): series_fig(int(w.split(':')[1]))
        if w.startswith('pair:'):
            _, s, t, fn = w.split(':', 3); snapshot_pair(int(s), int(t), fn + '.png', f'long s{s} t={t}')
        if w.startswith('strip:'):
            _, sd, arm, tt, fn = w.split(':', 4); strip(int(sd), arm, [int(x) for x in tt.split(',')], fn)
        if w.startswith('zoom:'):
            _, ss, fn = w.split(':', 2); zoom_end([int(x) for x in ss.split(',')], fn + '.png', '끝 상태 확대 (가장 큰 몸 중심, 80x80)')
