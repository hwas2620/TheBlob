#!/usr/bin/env python3
"""verify7 그림: fig/*.png (판정에는 쓰지 않는다)"""
import json, os, sys, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import judge as JG
V = os.path.normpath(os.path.join(HERE, '..')); FIG = os.path.join(V, 'fig'); RUNS = os.path.normpath(os.path.join(V, '..', 'model', 'runs'))
os.makedirs(FIG, exist_ok=True)
CC, CY = '#2a78d6', '#eb6834'          # 대조(파랑), 후보(주황) — 검사기 통과
INK, MUTED, GRID = '#2b2b29', '#6b6a63', '#e6e5e0'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': MUTED, 'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.grid': True, 'grid.color': GRID,
                     'grid.linewidth': 0.6, 'axes.unicode_minus': False, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 110})
for fp in ('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'):
    if os.path.exists(fp):
        from matplotlib import font_manager
        font_manager.fontManager.addfont(fp); plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name(); break
HMAP = LinearSegmentedColormap.from_list('h', ['#f7f6f2', '#9ec5f4', '#3987e5', '#1c5cab', '#0d366b'])
D = JG.load()
LBL = {'v7c': '대조 v7c', 'v7y': '후보 v7y'}


def mig(tag):
    return sorted([r for r in D.values() if r['tag'] == tag and r['scn'] in JG.MIG_SEEDS and r['seed'] in JG.MIG_SEEDS[r['scn']]], key=lambda r: r['seed'])


def vs(name, t):
    f = os.path.join(RUNS, name, f'vs_t{int(t):04d}.npz')
    if not os.path.exists(f): return None
    Z = np.load(f); return Z['wet'].astype(bool), Z['h'].astype(float)


def fig_traj():
    fig, ax = plt.subplots(1, 3, figsize=(12, 4))
    for j, tag in enumerate(('v7c', 'v7y')):
        a = ax[j]
        for r in mig(tag):
            tr = np.array([[x[0], x[1], x[2]] for x in r['traj'] if x[0] <= 400]); a.plot(tr[:, 1] - tr[0, 1], tr[:, 2] - tr[0, 2], color=(CC, CY)[j], lw=1.2, alpha=0.75)
        fx, fy = r['foods'][0][0] - r['c0'], r['foods'][0][1] - r['c0']
        a.plot([fx], [fy], 'o', ms=10, mfc='none', mec=INK, mew=1.5); a.annotate('유인원', (fx, fy), xytext=(6, 6), textcoords='offset points', color=INK)
        a.plot([0, fx], [0, fy], ls=':', color=MUTED, lw=1)
        a.set_aspect('equal'); a.set_title(f'{LBL[tag]}: 무게중심 경로 (t ≤ 400, 18 시드)', color=INK); a.set_xlabel('x 변위 (셀)'); a.set_ylabel('y 변위 (셀)')
        a.set_xlim(-40, 110); a.set_ylim(-60, 90)
    a = ax[2]
    for j, tag in enumerate(('v7c', 'v7y')):
        e = [JG.mig_measures(r)['err35'] for r in mig(tag)]; e = [x for x in e if x is not None]
        a.scatter(np.full(len(e), j) + np.linspace(-0.15, 0.15, len(e)), e, s=36, color=(CC, CY)[j], edgecolor='white', linewidth=1, zorder=3, label=LBL[tag])
        a.plot([j - 0.25, j + 0.25], [np.mean(e)] * 2, color=INK, lw=2)
    a.axhline(0, color=MUTED, lw=1); a.set_xticks([0, 1]); a.set_xticklabels([LBL['v7c'], LBL['v7y']]); a.set_ylabel('방향 오차 (°, + = 반시계)')
    a.set_title('변위 35 셀 때의 방향 오차 (막대 = 평균)', color=INK)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig1_migration.png')); plt.close(fig)


def crop(w, h, cen, R):
    N = w.shape[0]; cx, cy = int(round(cen[0])) % N, int(round(cen[1])) % N
    sl = np.roll(np.roll(np.where(w, h, np.nan), N // 2 - cy, 0), N // 2 - cx, 1)
    return sl[N // 2 - R:N // 2 + R, N // 2 - R:N // 2 + R]


def fig_snaps(names, times, fn, title, R=70, vmax=2.5):
    fig, ax = plt.subplots(2, len(names) * len(times), figsize=(2.2 * len(names) * len(times), 4.8), squeeze=False)
    for j, tag in enumerate(('v7c', 'v7y')):
        k = 0
        for n in names:
            for t in times:
                a = ax[j, k]; k += 1; nm = n + '_' + tag; S = vs(nm, t)
                a.set_xticks([]); a.set_yticks([]); a.grid(False)
                if S is None: a.set_title(f'{nm}\nt={t} 없음', fontsize=7); continue
                w, h = S; ys, xs = np.nonzero(w)
                N = w.shape[0]; ang = 2 * np.pi / N
                cen = ((np.angle(np.exp(1j * xs * ang).mean()) / ang) % N, (np.angle(np.exp(1j * ys * ang).mean()) / ang) % N)
                im = a.imshow(crop(w, h, cen, R), cmap=HMAP, vmin=0, vmax=vmax, interpolation='nearest')
                a.set_title(f"{LBL[tag]}  {n.replace('b_', '')}  t={t}", fontsize=7, color=INK)
    fig.suptitle(title, color=INK); fig.colorbar(im, ax=ax, shrink=0.6, label='두께 h')
    fig.savefig(os.path.join(FIG, fn)); plt.close(fig)


def fig_scl():
    rs = sorted([r for r in D.values() if r['tag'] == 'v7y' and r.get('scl') and r['scn'] == 'slimeall'], key=lambda r: r['seed'])
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    for r in rs:
        f = np.array(r['scl']['f_curve']); ax[0].plot(f[:, 0], f[:, 1], color=CY, lw=1.2, alpha=0.8)
        ts = [x['t'] for x in r['frames']]; ar = [x['bodies'][0]['area'] if x.get('bodies') else np.nan for x in r['frames']]
        ax[1].plot(ts, ar, color=CY, lw=1.2, alpha=0.8); ax[1].axvline(r['t_scl'], color=MUTED, lw=0.6, ls=':')
    for r in sorted([r for r in D.values() if r['tag'] == 'v7c' and r['scn'] == 'slimeall'], key=lambda r: r['seed']):
        ts = [x['t'] for x in r['frames']]; ar = [x['bodies'][0]['area'] if x.get('bodies') else np.nan for x in r['frames']]
        ax[1].plot(ts, ar, color=CC, lw=1.2, alpha=0.8)
    ax[0].set_title('후보 slimeall: 끝 덩이 자리 안의 부피 몫 f(t)', color=INK); ax[0].set_xlabel('t'); ax[0].set_ylabel('f')
    ax[1].set_title('가장 큰 몸의 넓이 (파랑 대조, 주황 후보; 점선 t_scl)', color=INK); ax[1].set_xlabel('t'); ax[1].set_ylabel('넓이 (셀)')
    J = json.load(open(os.path.join(V, 'judge_out.json')))
    p = J['claim7']['f']['pairs']
    for x in p:
        ax[2].plot([0, 1], [x['ctrl']['solidity'], x['cand']['solidity']], color=MUTED, lw=0.8)
        ax[2].scatter([0], [x['ctrl']['solidity']], color=CC, s=30, zorder=3); ax[2].scatter([1], [x['cand']['solidity']], color=CY, s=30, zorder=3)
    ax[2].set_xticks([0, 1]); ax[2].set_xticklabels([LBL['v7c'], LBL['v7y']]); ax[2].set_ylabel('solidity (넓이/볼록 껍질)'); ax[2].set_title('slimeall 마지막 장면의 가장 큰 몸 (짝)', color=INK)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig4_sclerotium.png')); plt.close(fig)


def fig_metrics():
    J = json.load(open(os.path.join(V, 'judge_out.json')))
    items = [('부스러기 있는 장면 몫\n(주장 1, t≥60)', J['claim1']['v7c']['frac_frames_with_crumb'], J['claim1']['v7y']['frac_frames_with_crumb']),
             ('아령 몸 있는 장면 몫\n(주장 2, 이주)', J['claim2']['v7c']['frac_dumbbell'], J['claim2']['v7y']['frac_dumbbell']),
             ('흐름 없는 실 몫\n(주장 3, 이주)', J['claim3']['mig']['v7c']['dead_thread_frac'], J['claim3']['mig']['v7y']['dead_thread_frac']),
             ('얇은 막 몫\n(주장 3, 이주)', J['claim3']['mig']['v7c']['film_frac'], J['claim3']['mig']['v7y']['film_frac']),
             ('흐름 없는 끝 수/장면\n(주장 3, 이주)', J['claim3']['mig']['v7c']['dead_tips'], J['claim3']['mig']['v7y']['dead_tips']),
             ('긴 꼬리(L≥30) 장면 몫\n(주장 6)', J['claim6']['v7c']['frac_tail30'], J['claim6']['v7y']['frac_tail30'])]
    fig, ax = plt.subplots(1, len(items), figsize=(13, 3.0))
    for a, (t, c, y) in zip(ax, items):
        a.bar([0, 1], [c, y], color=[CC, CY], width=0.6, edgecolor='white', linewidth=2)
        for x, v in ((0, c), (1, y)): a.annotate(f'{v:.3g}', (x, v), xytext=(0, 3), textcoords='offset points', ha='center', color=INK, fontsize=8)
        a.set_xticks([0, 1]); a.set_xticklabels(['대조', '후보']); a.set_title(t, fontsize=8, color=INK); a.grid(axis='x', visible=False)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig5_structure_metrics.png')); plt.close(fig)


def fig_flux():
    J = json.load(open(os.path.join(V, 'judge_out.json')))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    pos = 0; ticks = []
    for s in JG.MAIN_SCN:
        for j, tag in enumerate(('v7c', 'v7y')):
            e = np.array([x[1] for r in D.values() if r['tag'] == tag and r['scn'] == s for x in r['mg_err_series']])
            if e.size == 0: continue
            bp = ax[0].boxplot([e], positions=[pos + 0.35 * j], widths=0.3, whis=(1, 99), showfliers=False, patch_artist=True)
            for b in bp['boxes']: b.set(facecolor=(CC, CY)[j], edgecolor='white')
            for m in bp['medians']: m.set(color=INK)
            ax[0].scatter([pos + 0.35 * j], [e.max()], marker='x', color=INK, s=14)
        ticks.append((pos + 0.17, s)); pos += 1
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: f'{v:g}')
    ax[0].set_yscale('log'); ax[0].yaxis.set_major_formatter(fmt); ax[0].set_xticks([p for p, _ in ticks]); ax[0].set_xticklabels([s for _, s in ticks]); ax[0].set_ylabel('유량 상대 오차 (실행 중 기록)')
    ax[0].set_title('실행 기록: 파랑 대조(MG) / 주황 후보(PCG), 수염 1–99%, x 최댓값', fontsize=8, color=INK)
    rp = os.path.join(V, 'data', 'replay.json')
    if os.path.exists(rp):
        R = json.load(open(rp)); em = np.array([x['mg']['e_flux'] for x in R]); ep = np.array([x['pcg']['e_flux'] for x in R])
        sc = np.array([x['scl'] for x in R])
        ax[1].scatter(em[~sc], ep[~sc], s=22, color=MUTED, edgecolor='white', label='균핵 상태 아님'); ax[1].scatter(em[sc], ep[sc], s=26, marker='s', color=INK, edgecolor='white', label='균핵 상태(후보)')
        lo = min(em.min(), ep.min()) * 0.7; hi = max(em.max(), ep.max()) * 1.4
        ax[1].plot([lo, hi], [lo, hi], color=MUTED, lw=1, ls=':'); ax[1].set_xscale('log'); ax[1].set_yscale('log'); ax[1].xaxis.set_major_formatter(fmt); ax[1].yaxis.set_major_formatter(fmt)
        ax[1].set_xlabel('대조 풀이 MG 오차'); ax[1].set_ylabel('후보 풀이 PCG 오차'); ax[1].legend(frameon=False, fontsize=8)
        ax[1].set_title('짝 비교: 같은 문제·같은 웜스타트 (점선 아래 = PCG 가 더 정확)', fontsize=8, color=INK)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig6_solver.png')); plt.close(fig)


def fig_threads():
    cases = [('b_long_s661_v7y', 1420, '후보 long 661 t=1420: 그물 끝에서 뻗은 실 끝의 덩이'), ('b_food4_s701_v7y', 600, '후보 food4 701 t=600: 끝이 자유로운 긴 꼬리(~120)'),
             ('b_food4_s703_v7y', 700, '후보 food4 703 t=700: 긴 꼬리(~134)'), ('b_mig_s672_v7y', 380, '후보 mig 672 t=380: 몸 뒤 관 그물(바깥 줄기 > 100)'),
             ('b_long_s661_v7c', 1020, '대조 long 661 t=1020: 관 그물과 부스러기')]
    fig, ax = plt.subplots(1, len(cases), figsize=(4.2 * len(cases), 4.6))
    for a, (nm, t, ti) in zip(ax, cases):
        S = vs(nm, t); a.set_xticks([]); a.set_yticks([]); a.grid(False)
        if S is None: continue
        w, h = S; im = a.imshow(np.where(w, h, np.nan), cmap=HMAP, vmin=0, vmax=2.0, interpolation='nearest'); a.set_title(ti, fontsize=8, color=INK)
    fig.colorbar(im, ax=ax, shrink=0.7, label='두께 h'); fig.savefig(os.path.join(FIG, 'fig7_threads.png')); plt.close(fig)


if __name__ == '__main__':
    fig_traj()
    fig_snaps(['b_mig_s667', 'b_mig_s668', 'b_long_s661'], [200, 400], 'fig2_migration_snapshots.png', '이주 중 몸 (두께, 몸 중심으로 자름)')
    fig_snaps(['b_long_s662', 'b_long_s663'], [1000, 2000], 'fig3_long_snapshots.png', 'long: 오래 굶은 뒤 (두께)')
    fig_snaps([f'b_slimeall_s{s}' for s in (681, 682, 685, 688)], [800], 'fig3b_slimeall_end.png', 'slimeall t=800 (사방 점액, 갇힌 뒤)', R=45, vmax=4.0)
    fig_snaps(['b_slimeall_s686'], [120, 160, 200, 260, 800], 'fig3c_slimeall_686_time.png', 'slimeall 686: 갇힌 뒤 시간에 따라 (t_scl = 130)', R=45, vmax=4.0)
    fig_threads()
    fig_scl(); fig_metrics(); fig_flux()
    print('figs done')
