"""유인원 방향별 이주 방향 오차 (진단 6·7, mig 1011~1042, s25d 설정)"""
import json, glob, os, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf'); plt.rcParams['font.family'] = 'NanumSquareRound'; plt.rcParams['axes.unicode_minus'] = False
def wrap(a): return (a + 180) % 360 - 180
R = '../model/runs/'; groups = [('27°', 's25d'), ('45°', 'y20'), ('63°', 'y19')]; data = []
for lab, tg in groups:
    e = []
    for f in sorted(glob.glob(R + f'b_mig_s*_{tg}/metrics.json')):
        d = os.path.dirname(f); P = json.load(open(d + '/params.json')); m = json.load(open(f)); tr = np.array(m['traj'], float); c0 = P['N'] / 2 - 0.5
        dd = np.hypot(tr[:, 1] - c0, tr[:, 2] - c0); i = int(np.argmax(dd >= 25)); e.append(wrap(np.degrees(np.arctan2(tr[i, 2] - c0, tr[i, 1] - c0)) - float(P['foods'][0][0])))
    data.append(np.array(e))
INK, INK2, GRID, BLUE = '#191919', '#666666', '#e6e6e6', '#257de0'
fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=160)
for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
for sp in ('left', 'bottom'): ax.spines[sp].set_color('#bbbbbb')
ax.axhline(0, color='#999999', lw=1, ls='--', zorder=1)
rng = np.random.default_rng(0)
for k, e in enumerate(data):
    x = k + rng.uniform(-0.18, 0.18, e.size)
    ax.scatter(x, e, s=26, color=BLUE, alpha=0.55, edgecolor='white', linewidth=0.8, zorder=2)
    mu = e.mean(); se = e.std(ddof=1) / np.sqrt(e.size)
    ax.plot([k - 0.3, k + 0.3], [mu, mu], color=INK, lw=2.2, zorder=3, solid_capstyle='round')
    ax.errorbar(k, mu, yerr=1.96 * se, color=INK, lw=1.2, capsize=4, zorder=3)
    ax.annotate(f'평균 {mu:+.1f}°\n+{int((e > 0).sum())} / -{int((e < 0).sum())}', (k + 0.33, mu), va='center', fontsize=10, color=INK)
ax.set_xticks(range(3)); ax.set_xticklabels([f'유인원 {g[0]}\n({d.size}판)' for g, d in zip(groups, data)], fontsize=10, color=INK)
ax.set_xlim(-0.6, 2.9); ax.set_ylabel('이주 방향 오차 (°, + = 반시계)', fontsize=10, color=INK2); ax.tick_params(colors=INK2, labelsize=9)
ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
from scipy.stats import ttest_ind
pv = ttest_ind(data[0], data[2], equal_var=False).pvalue
ax.set_title('이주 방향이 격자 대각선(45°) 쪽으로 조금 끌린다', fontsize=12, color=INK, loc='left', pad=12)
ax.text(0, -0.2, f'점 하나 = 이주 한 판(S24 후보 모델). 굵은 선 = 평균, 세로 막대 = 평균의 95% 구간.\n27°에서는 +, 63°에서는 -로 부호가 뒤집히고, 45°에서는 0에 가깝다. 한 각도만 보면 구간이 0에 걸치지만,\n27°와 63°의 평균 차이 {data[0].mean() - data[2].mean():.1f}°는 우연으로 보기 어렵다(웰치 t 검정 p = {pv:.3f}).', transform=ax.transAxes, fontsize=8.5, color=INK2, va='top')
fig.tight_layout(); fig.savefig('../fig/direction_by_angle.png', facecolor='white'); print([round(float(d.mean()), 2) for d in data])
