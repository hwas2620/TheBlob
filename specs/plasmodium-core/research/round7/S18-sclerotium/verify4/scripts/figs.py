#!/usr/bin/env python3
"""verify4 그림 (판정에는 쓰지 않는다). usage: figs.py          -> fig/*.png
   figs.py case NAME T1,T2,... OUT [제목]   -> 한 실행의 두께 지도 띠"""
import json, glob, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

V4 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(os.path.dirname(V4), 'model', 'runs')
FIG = os.path.join(V4, 'fig')
C_CTRL = '#2a78d6'; C_CAND = '#eb6834'; INK = '#0b0b0b'; INK2 = '#52514e'; GRID = '#e4e3df'
for f in sorted(font_manager.findSystemFonts(), key=lambda p: (os.path.basename(p) != 'NanumGothic.ttf', p)):
    if any(k in os.path.basename(f) for k in ('NanumGothic', 'NotoSansCJK', 'NotoSansKR', 'UnDotum')):
        font_manager.fontManager.addfont(f); plt.rcParams['font.family'] = font_manager.FontProperties(fname=f).get_name(); break
plt.rcParams.update({'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.grid': True, 'grid.color': GRID,
                     'grid.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 9, 'axes.unicode_minus': False})


def load():
    R = {}
    for f in sorted(glob.glob(os.path.join(V4, 'data', 'runs', '*.json'))):
        r = json.load(open(f)); R[(r['scn'], r['seed'], r['cfg'])] = r
    return R


def paired(ax, c, w, title, ylab):
    c = np.asarray(c, float); w = np.asarray(w, float)
    for a, b in zip(c, w): ax.plot([0, 1], [a, b], color=GRID, lw=1.2, zorder=1)
    ax.scatter(np.zeros_like(c), c, s=36, color=C_CTRL, edgecolor='white', lw=1.5, zorder=2, label='대조 v4c')
    ax.scatter(np.ones_like(w), w, s=36, color=C_CAND, edgecolor='white', lw=1.5, zorder=2, label='후보 v4w')
    ax.plot([-0.15, 0.15], [np.median(c)] * 2, color=C_CTRL, lw=2); ax.plot([0.85, 1.15], [np.median(w)] * 2, color=C_CAND, lw=2)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['대조', '후보']); ax.set_xlim(-0.5, 1.5); ax.set_title(title, color=INK, fontsize=9.5); ax.set_ylabel(ylab)
    ax.grid(axis='x', visible=False)


def summary_figs(R, S):
    os.makedirs(FIG, exist_ok=True)
    # 1. 부스러기
    rows = S['claim1']['rows']; scns = ['long', 'food4', 'food3', 'asym3', 'mig']
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    x = np.arange(len(scns)); wd = 0.36
    for j, (cfg, col, lab) in enumerate((('v4c', C_CTRL, '대조 v4c'), ('v4w', C_CAND, '후보 v4w'))):
        v = []; nlab = []
        for s in scns:
            rr = [r for r in rows if r['scn'] == s and r['cfg'] == cfg]
            v.append(sum(r['debris_snaps'] for r in rr) / max(sum(r['snaps'] for r in rr), 1)); nlab.append(f"{sum(r['debris_snaps'] > 0 for r in rr)}/{len(rr)}")
        b = ax.bar(x + (j - 0.5) * wd, v, wd - 0.03, color=col, label=lab)
        for xi, vi, nl in zip(x + (j - 0.5) * wd, v, nlab): ax.text(xi, vi + 0.01, nl, ha='center', va='bottom', fontsize=7.5, color=INK2)
    ax.set_xticks(x); ax.set_xticklabels(scns); ax.set_ylabel('부스러기가 있는 스냅숏 비율 (t ≥ 100)')
    ax.set_title('주장 1: 부스러기 (막대 위 = 부스러기 낸 실행 / 실행 수)', color=INK); ax.legend(frameon=False); ax.grid(axis='x', visible=False)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'claim1_debris.png'), dpi=150); plt.close(fig)
    # 2·3. long 이주 창
    t2 = S['claim2']['tests']; t3 = S['claim3']['tests']
    fig, axs = plt.subplots(1, 5, figsize=(12, 3.0))
    paired(axs[0], t2['multi']['c'], t2['multi']['w'], '여러 덩이 몸 비율', '스냅숏 비율')
    paired(axs[1], t2['dumb']['c'], t2['dumb']['w'], '아령 비율', '스냅숏 비율')
    paired(axs[2], t3['film_cells']['c'], t3['film_cells']['w'], '얇은 막 (칸)', '창 평균 칸 수')
    paired(axs[3], t3['dead_thread']['c'], t3['dead_thread']['w'], '흐름 없는 죽은 실 (칸)', '창 평균 칸 수')
    paired(axs[4], t3['dead_tips']['c'], t3['dead_tips']['w'], '흐름 없는 가지 끝 (개)', '창 평균 개수')
    axs[0].legend(frameon=False, fontsize=7.5, loc='upper right')
    fig.suptitle(f"주장 2·3: long 옮겨 다니는 창 (짝 {len(S['claim2']['pairs'])}, 선 = 같은 시드)", color=INK, fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'claim23_migration.png'), dpi=150); plt.close(fig)
    # 4. long 시간에 따른 모양
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.2), sharex=True)
    for cfg, col in (('v4c', C_CTRL), ('v4w', C_CAND)):
        for key, ax, lab in (('n_mass', axs[0], '덩이 수 n_mass'), ('K', axs[1], '큰 몸 둥글기·촘촘함 K'), ('fresh', axs[2], '가장자리 새 땅 비율')):
            M = []
            for k, r in R.items():
                if k[0] != 'long' or k[2] != cfg: continue
                t = [s['t'] for s in r['snaps']]; y = [s[key] if s.get(key) is not None else np.nan for s in r['snaps']]
                ax.plot(t, y, color=col, lw=0.6, alpha=0.35); M.append(y)
            if M:
                L = min(len(m) for m in M); ax.plot(t[:L], np.nanmedian(np.array([m[:L] for m in M], float), 0), color=col, lw=2.2, label=('대조' if cfg == 'v4c' else '후보') + ' 중앙값')
            ax.set_title(lab, color=INK); ax.set_xlabel('t')
    axs[2].axhline(0.05, color=INK2, lw=0.8, ls='--'); axs[0].legend(frameon=False, fontsize=8)
    for ax in axs: ax.axvline(1600, color=INK2, lw=0.8, ls=':')
    fig.suptitle('주장 4: long 실행별 시간 변화 (가는 선 = 실행, 점선 t = 1600, 오른쪽 파선 = 갇힘 문턱 0.05)', color=INK, fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'claim4_long_time.png'), dpi=150); plt.close(fig)
    t4 = S['claim4']['tests']
    if S['claim4']['pairs']:
        fig, axs = plt.subplots(1, 4, figsize=(10, 3.0))
        paired(axs[0], t4['n_mass']['c'], t4['n_mass']['w'], '덩이 수', '갇힌 뒤 평균'); paired(axs[1], t4['K']['c'], t4['K']['w'], 'K (원반 = 1)', '갇힌 뒤 평균')
        paired(axs[2], t4['lam']['c'], t4['lam']['w'], 'lam (원반 = 1)', '갇힌 뒤 평균'); paired(axs[3], t4['main_narrow_share']['c'], t4['main_narrow_share']['w'], '가는 칸 비율', '갇힌 뒤 평균')
        fig.suptitle(f"주장 4: 갇힌 뒤 [T_trap+100, 2000] (짝 {len(S['claim4']['pairs'])})", color=INK, fontsize=10)
        fig.tight_layout(); fig.savefig(os.path.join(FIG, 'claim4_trapped.png'), dpi=150); plt.close(fig)
    # 5. 먹이·이주
    t5 = S['claim5']['tests']; fig, axs = plt.subplots(1, 6, figsize=(14, 3.0)); i = 0
    for scn in ('food4', 'food3', 'asym3'):
        if scn in t5: paired(axs[i], t5[scn]['tau']['c'], t5[scn]['tau']['w'], f'{scn}: 닿는 시각 평균', '시간 (못 닿으면 T)'); i += 1
    if 'mig' in t5:
        paired(axs[i], t5['mig']['t_touch']['c'], t5['mig']['t_touch']['w'], 'mig: 유인원 닿는 시각', '시간 (400 에서 자름)'); i += 1
        paired(axs[i], t5['mig']['P200']['c'], t5['mig']['P200']['w'], 'mig: t=200 유인원 쪽 거리', '칸'); i += 1
        paired(axs[i], t5['mig']['heading']['c'], t5['mig']['heading']['w'], 'mig: 방향 오차', '도'); i += 1
    fig.suptitle('주장 5: 먹이 찾기와 이주 (낮을수록 좋음, 이동 거리만 높을수록 좋음)', color=INK, fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'claim5_food_mig.png'), dpi=150); plt.close(fig)


def case(name, times, out, title=''):
    from matplotlib.colors import LinearSegmentedColormap
    cm = LinearSegmentedColormap.from_list('h', ['#fff4d6', '#f2c14e', '#c46b00', '#5a2a00'])
    fig, axs = plt.subplots(1, len(times), figsize=(2.6 * len(times), 2.9))
    axs = np.atleast_1d(axs)
    for ax, t in zip(axs, times):
        Z = np.load(os.path.join(RUNS, name, f'vs_t{int(t):04d}.npz')); wet = Z['wet']; h = Z['h']; N = wet.shape[0]
        cx, cy = [float(v) % N for v in Z['cen']]; sx = int(round(N / 2 - cx)); sy = int(round(N / 2 - cy))
        hw = np.roll(np.where(wet, h, np.nan), (sy, sx), (0, 1))
        im = ax.imshow(hw, cmap=cm, vmin=0, vmax=2.0, interpolation='nearest', origin='lower')
        ax.set_facecolor('#e8e8e6'); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False); ax.set_title(f't = {int(t)}', color=INK, fontsize=9)
        for sp in ax.spines.values(): sp.set_visible(False)
    cb = fig.colorbar(im, ax=list(axs), fraction=0.02, pad=0.01); cb.set_label('두께 h (회색 = 마른 땅)')
    fig.suptitle(title or name, color=INK, fontsize=10)
    fig.savefig(os.path.join(FIG, out), dpi=130, bbox_inches='tight'); plt.close(fig)


def grid(rows, out, title):
    """rows: [(실행 이름, [시각...], 줄 이름)]. 줄마다 그 실행의 두께 지도 (몸 중심을 가운데로 옮김, 먹이 원은 파란 테두리)"""
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Circle
    cm = LinearSegmentedColormap.from_list('h', ['#fff4d6', '#f2c14e', '#c46b00', '#5a2a00'])
    nc = max(len(r[1]) for r in rows)
    fig, axs = plt.subplots(len(rows), nc, figsize=(2.3 * nc, 2.45 * len(rows)), squeeze=False)
    for i, (name, times, lab) in enumerate(rows):
        J = json.load(open(os.path.join(V4, 'data', 'runs', name + '.json')))
        for j in range(nc):
            ax = axs[i, j]; ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            for sp in ax.spines.values(): sp.set_visible(False)
            if j >= len(times): ax.axis('off'); continue
            t = times[j]; Z = np.load(os.path.join(RUNS, name, f'vs_t{int(t):04d}.npz')); wet = Z['wet']; h = Z['h']; N = wet.shape[0]
            cx, cy = [float(v) % N for v in Z['cen']]; sx = int(round(N / 2 - cx)); sy = int(round(N / 2 - cy))
            im = ax.imshow(np.roll(np.where(wet, h, np.nan), (sy, sx), (0, 1)), cmap=cm, vmin=0, vmax=2.0, interpolation='nearest', origin='lower')
            ax.set_facecolor('#e8e8e6')
            for a_, d_ in (J.get('foods') or []):
                fx = (J['c0'] + d_ * np.cos(np.radians(a_)) + sx) % N; fy = (J['c0'] + d_ * np.sin(np.radians(a_)) + sy) % N
                ax.add_patch(Circle((fx, fy), J['food_r'], fill=False, ec='#2a78d6', lw=1.0))
            ax.set_title(f't = {int(t)}', color=INK, fontsize=8.5)
            if j == 0: ax.set_ylabel(lab, color=INK, fontsize=8.5)
    cb = fig.colorbar(im, ax=axs.ravel().tolist(), fraction=0.015, pad=0.01); cb.set_label('두께 h (2 이상은 같은 색, 회색 = 마른 땅)')
    fig.suptitle(title, color=INK, fontsize=10)
    fig.savefig(os.path.join(FIG, out), dpi=120, bbox_inches='tight'); plt.close(fig)


def cases():
    T5 = [400, 800, 1200, 1600, 2000]
    grid([('b_long_s401_v4c', T5, '대조 s401'), ('b_long_s401_v4w', T5, '후보 s401')], 'case1_long_s401.png',
         '사례 1 (long s401): 대조는 몸이 둘로 갈리고 부스러기 점이 흩어진다. 후보는 한 몸의 부채꼴 앞자락으로 옮겨 다닌다 (뒤로 긴 실을 끈다)')
    T2 = [720, 760, 800, 840, 880]
    grid([('b_long_s405_v4c', T2, '대조 s405'), ('b_long_s405_v4w', T2, '후보 s405')], 'case2_dumbbell_s405.png',
         '사례 2 (long s405): 대조의 아령 (굵은 덩이 둘이 한 칸 폭 실로 이어짐) 과 같은 때의 후보')
    grid([('b_long_s404_v4w', [1500, 1560, 1600, 1620, 1700, 2000], '후보 s404')], 'case3_sclerotium_good_s404.png',
         '사례 3 (좋은 것, long s404 후보): 갇힌 뒤 몸 전체가 둥근 균핵 하나로 모인다 (두께 3 의 원반)')
    grid([('b_long_s402_v4w', [1820, 1860, 1900, 2000], '후보 s402: 꼬리'), ('b_long_s408_v4w', [1500, 1700, 1800, 2000], '후보 s408: 나뉨'),
          ('b_long_s409_v4w', [1700, 1860, 1880, 1960], '후보 s409: 깜빡임'), ('b_long_s403_v4w', [1820, 1900, 1940, 2000], '후보 s403: 풀림')],
         'case4_sclerotium_bad.png', '사례 4 (나쁜 것, long 후보): 균핵에 죽은 실 꼬리가 붙어 남음 / 앞서 나뉜 두 몸이 균핵 둘 / 균핵이 풀렸다 다시 맺힘 / 균핵이 풀려 판으로 퍼짐')
    T6 = [80, 160, 240, 320, 480]
    grid([('b_food3_s422_v4c', T6, '대조 food3 s422'), ('b_food3_s422_v4w', T6, '후보 food3 s422')], 'case5_food3_s422.png',
         '사례 5 (나쁜 것, food3 s422): 대조는 먹이 셋에 85 안에 닿는데, 후보는 한 먹이에 311 에야 닿는다 (파란 원 = 먹이)')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'cases':
        cases()
    elif len(sys.argv) > 1 and sys.argv[1] == 'case':
        case(sys.argv[2], [float(x) for x in sys.argv[3].split(',')], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else '')
    else:
        summary_figs(load(), json.load(open(os.path.join(V4, 'data', 'summary.json'))))
