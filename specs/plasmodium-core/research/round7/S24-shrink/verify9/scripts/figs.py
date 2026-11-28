#!/usr/bin/env python3
"""verify9 그림 (판정 아님). out/run_*.json 과 실행 폴더의 vs 상태를 읽어 fig/*.png 를 만든다."""
import json, os, sys, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
import matplotlib.font_manager as _fm
for _f in glob.glob('/usr/share/fonts/truetype/nanum/*.ttf'): _fm.fontManager.addfont(_f)
plt.rcParams['axes.unicode_minus'] = False
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import meas as M
V9 = os.path.normpath(os.path.join(HERE, '..')); OUT = os.path.join(V9, 'out'); FIG = os.path.join(V9, 'fig')
RUNS = os.path.normpath(os.path.join(V9, '..', 'model', 'runs'))
C_CTRL = '#257de0'; C_CAND = '#f47230'; INK = '#191919'; INK2 = '#666666'; GRID = '#e6e6e6'
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.grid': True, 'grid.color': GRID,
                     'grid.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False, 'lines.linewidth': 2, 'legend.frameon': False, 'font.family': ['NanumGothic', 'DejaVu Sans']})


def load():
    return {r['name']: r for r in (json.load(open(f)) for f in sorted(glob.glob(os.path.join(OUT, 'run_*.json'))))}


def vs(name, t):
    Z = np.load(os.path.join(RUNS, name, f'vs_t{int(round(t)):04d}.npz')); return Z['wet'].astype(bool), Z['h'].astype(float), Z['age'].astype(float)


def crop(m, pad=6):
    """토러스 상태를 몸 무게중심 가운데로 돌리고 몸 둘레만 자른다"""
    N0, N1 = m.shape; cx, cy = M.circ_centroid(m); sx = int(round(N1 / 2 - cx)); sy = int(round(N0 / 2 - cy))
    mm = np.roll(np.roll(m, sy, 0), sx, 1); ys, xs = np.nonzero(mm)
    return (sy, sx), (max(ys.min() - pad, 0), min(ys.max() + pad + 1, N0), max(xs.min() - pad, 0), min(xs.max() + pad + 1, N1))


def show(ax, w, h, sh, box, vmax, mark=None, title=''):
    a = np.roll(np.roll(np.where(w, h, np.nan), sh[0], 0), sh[1], 1)[box[0]:box[1], box[2]:box[3]]
    ax.imshow(a, origin='lower', cmap='YlOrBr', vmin=0, vmax=vmax, interpolation='nearest')
    if mark is not None:
        mk = np.roll(np.roll(mark, sh[0], 0), sh[1], 1)[box[0]:box[1], box[2]:box[3]]
        ys, xs = np.nonzero(mk); ax.plot(xs, ys, 's', ms=2.2, mfc='none', mec='#6a4ce2', mew=0.7)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False); ax.set_title(title, fontsize=8, color=INK)
    for s in ax.spines.values(): s.set_visible(False)


def fig_scl(R):
    S = sorted([r for r in R.values() if r['tag'] == 'v9b' and r['scn'] == 'slimeall' and r.get('scl', {}).get('trapped')], key=lambda r: (r['R_init'], r['seed']))
    if not S: return
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
    for r in S:
        t0 = r['scl']['t_scl']; a = np.array(r['area_series'], float); t = np.arange(a.size) * r['dt'] - t0; d = r['scl']['d']
        lw = 1.2; col = C_CAND if r['R_init'] == 12.0 else '#6a4ce2'
        ax[0].plot(t, a, color=col, lw=lw, alpha=0.75)
        ax[1].plot(np.array(d['times']) - t0, d['removed'], color=col, lw=lw, alpha=0.75)
        if 'fill_frac' in d: ax[2].plot(np.array(d['times']) - t0, d['fill_frac'], color=col, lw=lw, alpha=0.75)
    ax[0].set_xlim(-120, 400); ax[0].set_xlabel('갇힌 뒤 시간'); ax[0].set_ylabel('젖은 칸 수'); ax[0].set_title('넓이 (스텝마다)', color=INK)
    ax[1].set_xlim(-5, 250); ax[1].set_xlabel('갇힌 뒤 시간'); ax[1].set_ylabel('걷힌 몫'); ax[1].set_title('덩이 밖 칸이 걷힌 몫 r(t)', color=INK)
    ax[2].set_xlim(-5, 250); ax[2].set_xlabel('갇힌 뒤 시간'); ax[2].set_ylabel('메운 몫'); ax[2].set_title('덩이 자리 구멍을 메운 몫 (10칸 이상인 실행)', color=INK)
    ax[0].text(0.98, 0.95, '주황: 같은 부피 8 실행\n보라: R_init 15 두 실행', transform=ax[0].transAxes, ha='right', va='top', color=INK2, fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'scl_area.png'), dpi=130); plt.close(fig)
    # 지도: 두 시드
    pick = [S[0], S[min(3, len(S) - 1)]]
    fig, axs = plt.subplots(len(pick), 7, figsize=(14, 2.3 * len(pick) + 0.4))
    for i, r in enumerate(pick):
        t0 = r['scl']['t_trap_snap']; ts = [t0, t0 + 20, t0 + 40, t0 + 60, t0 + 90, t0 + 130, r['T']]
        w0, _, _ = vs(r['name'], t0); sh, box = crop(w0)
        for j, t in enumerate(ts):
            w, h, _ = vs(r['name'], t); show(axs[i, j], w, h, sh, box, 3.5, title=f"s{r['seed']} t={t:.0f} ({t - r['scl']['t_scl']:+.0f})")
    fig.suptitle('균핵이 맺히는 모습: 두께 h (색 0→3.5), 괄호는 갇힌 뒤 시간', color=INK, fontsize=10); fig.tight_layout(); fig.savefig(os.path.join(FIG, 'scl_maps.png'), dpi=130); plt.close(fig)
    # 두께 고리, 윤곽
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    for r in S:
        f = r['scl']['f']; col = C_CAND if r['R_init'] == 12.0 else '#6a4ce2'
        ax[0].plot(f['rings'], f['means'], 'o-', color=col, ms=3, lw=1.2, alpha=0.8)
        dx, dy = r['scl']['c']['coords']; dx = np.array(dx); dy = np.array(dy)
        m = np.zeros((90, 90), bool); ix = np.clip(np.round(dx).astype(int) + 45, 0, 89); iy = np.clip(np.round(dy).astype(int) + 45, 0, 89); m[iy, ix] = True
        ax[1].contour(m.astype(float), levels=[0.5], colors=[col], linewidths=1.0, alpha=0.8)
    ax[0].set_xlabel('가장자리에서의 거리 ⌊EDT⌋'); ax[0].set_ylabel('주기 평균 두께'); ax[0].set_title('균핵 두께 고리 평균 (t 800)', color=INK)
    ax[1].set_aspect('equal'); ax[1].set_xlim(15, 75); ax[1].set_ylim(15, 75); ax[1].set_title('끝 덩이 윤곽 (무게중심 맞춤)', color=INK); ax[1].set_xticks([]); ax[1].set_yticks([])
    r = S[0]; w, h, _ = vs(r['name'], r['T']); sh, box = crop(w); show(ax[2], w, h, sh, box, None, title=f"s{r['seed']} t 800 두께")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'scl_profile.png'), dpi=130); plt.close(fig)


def fig_err(R):
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    for tag, col, lab in (('v9c', C_CTRL, '대조'), ('v9b', C_CAND, '후보')):
        e = np.sort(np.concatenate([r['mg_err_series'] for r in R.values() if r['tag'] == tag]))
        ax.plot(e, np.arange(1, e.size + 1) / e.size, color=col, label=lab)
        ax.text(e[int(0.5 * e.size)], 0.5, f' {lab}', color=INK, fontsize=8, va='bottom')
    ax.set_xscale('log'); ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:g}')); ax.set_xlabel('상대 유량 오차 (20 스텝마다, 모든 실행)'); ax.set_ylabel('누적 몫'); ax.axvline(0.6, color=INK2, lw=1, ls='--'); ax.text(0.6, 0.05, ' 0.6', color=INK2, fontsize=8)
    ax.legend(loc='upper left'); ax.set_title('압력 풀이 유량 오차의 누적 분포', color=INK)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'flux_err.png'), dpi=130); plt.close(fig)


def fig_dir(J):
    if '5' not in J: return
    fig, ax = plt.subplots(figsize=(5.5, 2.8))
    for i, (key, col, lab) in enumerate((('ctrl', C_CTRL, '대조'), ('cand', C_CAND, '후보'))):
        e = [x[2] for x in J['5'][key]]; ax.plot(e, np.full(len(e), i) + np.linspace(-0.12, 0.12, len(e)), 'o', ms=7, color=col, mec='white', mew=1.5)
        ax.text(-58, i, lab, color=INK, va='center', ha='left')
    ax.axvline(0, color=INK2, lw=1); ax.set_yticks([]); ax.set_xlim(-60, 60); ax.set_xlabel('이주 방향 - 유인원 방향 (도, 반시계 +)')
    ax.set_title('무게중심이 25칸 옮겨 간 때의 방향 오차 (시드마다 점 하나)', color=INK); fig.tight_layout(); fig.savefig(os.path.join(FIG, 'direction.png'), dpi=130); plt.close(fig)


def fig_examples(R):
    """long 의 아령 예와 먹이 판의 꼬리 예 (대조와 후보를 같은 시각에)"""
    for scn, key, fname, ttl in (('long', 'db', 'example_long.png', 'long: 같은 시드·같은 시각'), ('food4', 'tail', 'example_food4.png', 'food4: 보라 네모 = 막다른 실 꼬리(엄격)')):
        cs = sorted([r for r in R.values() if r['tag'] == 'v9c' and r['scn'] == scn], key=lambda r: r['seed'])
        if not cs: continue
        best = None
        for c in cs:
            b = R.get(c['name'].replace('_v9c', '_v9b'))
            if b is None: continue
            for s in c['snaps']:
                if s['t'] < 200 or (key == 'db' and not (600 <= s['t'] <= 1500)): continue
                sc = (len(s['db_detail']) + s['db_detail'][0].get('nbig', 0) if s['db'] else 0) if key == 'db' else s['tail']['cells']
                if best is None or sc > best[0]: best = (sc, c, b, s['t'])
        if best is None: continue
        _, c, b, t = best; fig, ax = plt.subplots(1, 2, figsize=(9, 4.4))
        for a_, r, lab in ((ax[0], c, '대조'), (ax[1], b, '후보')):
            w, h, age = vs(r['name'], t); sh, box = crop(w, pad=4)
            mark = None
            if key == 'tail':
                lab_, n_, vol_, _, V_ = M.components(w, h); main = np.isin(lab_, [k for k in range(1, n_ + 1) if vol_[k] >= M.MAIN_FRAC * V_])
                mark, _ = M.prune_strict(main)
            show(a_, w, h, sh, box, 2.5, mark=mark, title=f"{lab} {r['name']} t={t:.0f}")
        fig.suptitle(ttl, color=INK, fontsize=10); fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=130); plt.close(fig)


if __name__ == '__main__':
    os.makedirs(FIG, exist_ok=True); R = load()
    J = json.load(open(os.path.join(V9, 'judge.json'))) if os.path.exists(os.path.join(V9, 'judge.json')) else {}
    fig_scl(R); fig_err(R); fig_dir(J); fig_examples(R)
    print('figs:', sorted(os.listdir(FIG)))
