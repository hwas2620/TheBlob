#!/usr/bin/env python3
"""verify8 그림 (판정에는 쓰지 않음). usage: make_figs.py   -> verify8/fig/*.png"""
import numpy as np, json, os, glob, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.ticker
import matplotlib.pyplot as plt, matplotlib.font_manager as fm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure as Mz

V = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); MD = os.path.join(V, '..', 'model', 'runs'); DD = os.path.join(V, 'data'); FD = os.path.join(V, 'fig')
for f in ('/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf', '/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf'):
    if os.path.exists(f): fm.fontManager.addfont(f)
plt.rcParams.update({'font.family': 'NanumBarunGothic', 'axes.unicode_minus': False, 'font.size': 9, 'axes.edgecolor': '#999999', 'axes.labelcolor': '#191919',
                     'xtick.color': '#666666', 'ytick.color': '#666666', 'axes.grid': True, 'grid.color': '#e6e6e6', 'grid.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False})
C_CTRL, C_CAND, TXT2 = '#257de0', '#f47230', '#666666'
R = {}
for f in glob.glob(os.path.join(DD, '*.json')):
    r = json.load(open(f)); R[(r['scn'], r['seed'], r['arm'])] = r
pairs = lambda scns: [(R[k], R[(k[0], k[1], 'v8v')]) for k in sorted(R) if k[2] == 'v8c' and k[0] in scns and (k[0], k[1], 'v8v') in R]
ALL = ('mig', 'long', 'food3', 'asym3', 'food4', 'slimeall'); MIG = ('mig', 'long'); FOOD = ('food3', 'asym3', 'food4')


def per_run(r, key, tmin=60.0, tmax=np.inf):
    v = [s[key] for s in r['snaps'] if tmin <= s['t'] < tmax and s.get(key) is not None]
    return float(np.mean(v)) if v else np.nan


def paired(ax, P, f, title):
    c = np.array([f(a) for a, b in P]); v = np.array([f(b) for a, b in P])
    for i in range(len(P)): ax.plot([0, 1], [c[i], v[i]], color='#cccccc', lw=0.8, zorder=1)
    ax.scatter(np.zeros(len(c)), c, s=18, color=C_CTRL, zorder=2, edgecolor='white', linewidth=0.8)
    ax.scatter(np.ones(len(v)), v, s=18, color=C_CAND, zorder=2, edgecolor='white', linewidth=0.8)
    for x, y, col in ((0, np.nanmean(c), C_CTRL), (1, np.nanmean(v), C_CAND)): ax.plot([x - 0.18, x + 0.18], [y, y], color=col, lw=2.5, solid_capstyle='round', zorder=3)
    ax.set_xticks([0, 1]); ax.set_xticklabels([f'대조\n평균 {np.nanmean(c):.3g}', f'후보\n평균 {np.nanmean(v):.3g}']); ax.set_xlim(-0.5, 1.5); ax.set_title(title, fontsize=9, loc='left')
    ax.grid(axis='x', visible=False)


def fig1():
    fig, axs = plt.subplots(2, 3, figsize=(11, 6.6))
    tscl = lambda r: r['metrics'].get('t_scl') or np.inf
    first = lambda r: min([x for x in r['metrics']['t_touch'] if x is not None] or [np.inf]) + 20
    paired(axs[0, 0], pairs(ALL), lambda r: per_run(r, 'crumbs'), '1. 스냅숏당 부스러기 (전체 짝, t≥60)')
    paired(axs[0, 1], pairs(MIG), lambda r: float(np.mean([s['nbig_sq3'] >= 2 for s in r['snaps'] if 60 <= s['t'] < tscl(r)])), '2. 아령 스냅숏 몫 (mig·long)')
    paired(axs[0, 2], pairs(ALL), lambda r: per_run(r, 'nf_thread_0.05'), '3. 흐름 없는 실 칸 / 스냅숏')
    paired(axs[1, 0], pairs(ALL), lambda r: per_run(r, 'nf_tipr_0.05'), '3. 흐름 없는 가지 끝 / 스냅숏')
    paired(axs[1, 1], pairs(FOOD), lambda r: per_run(r, 'tail_cells', first(r)), '6. 막다른 꼬리 칸 (먹이 판, 닿은 뒤)')
    paired(axs[1, 2], pairs(FOOD), lambda r: per_run(r, 'th_tail_old_cells', first(r)), '6(보조). 굳센 정의 매달린 실 칸')
    fig.suptitle('같은 시드 짝: 대조(지금 모델) 대 후보 — 점 하나가 실행 하나, 회색 선이 짝', fontsize=10, x=0.01, ha='left')
    fig.tight_layout(); fig.savefig(os.path.join(FD, 'fig1_paired.png'), dpi=130); plt.close(fig)


def crop(a, sy, sx, w):
    a = np.roll(a, (sy, sx), (0, 1)); N = a.shape[0]; c = N // 2; return a[c - w:c + w, c - w:c + w]


def show_state(ax, rd, t, title, w=None):
    f = os.path.join(MD, rd, f'vs_t{int(t):04d}.npz')
    if not os.path.exists(f): ax.set_axis_off(); ax.set_title(title + ' (파일 없음)', fontsize=8); return
    S = Mz.load_vs(f); wet = S['wet'].astype(bool); h = np.where(wet, S['h'], np.nan); N = wet.shape[0]
    lab, n = Mz.label8(wet); vol = np.bincount(lab.ravel(), weights=np.where(wet, np.maximum(S['h'], 0), 0).ravel()); vol[0] = 0; main = lab == int(np.argmax(vol))
    sy, sx = Mz.centered_shift(main, N); w = int(0.42 * N) if w is None else min(w, N // 2)
    rem, cur = Mz.prune_claim(wet); q = Mz.cell_flux(S['Qgross'].astype(float)); ok = wet & (S['age'] >= 20); qm = np.median(q[ok]) if ok.sum() > 10 else 0
    cls, core, thin = Mz.thin_classes(wet, np.where(wet, np.maximum(S['h'], 0), 0), lab, vol)
    thr = np.zeros_like(wet)
    for c in cls:
        if c['cls'] != 'fringe': thr |= c['mask']
    nf = thr & ok & (q < 0.05 * qm)
    ax.imshow(crop(h, sy, sx, w), cmap='YlOrBr', vmin=0, vmax=2.0, interpolation='nearest')
    for m, col, lbl in ((crop(nf, sy, sx, w), '#6a4ce2', '흐름 없는 실'), (crop(rem & dilate1(cur), sy, sx, w), '#191919', '꼬리(주장 정의)')):
        yy, xx = np.nonzero(m); ax.scatter(xx, yy, s=2, color=col, marker='s', linewidths=0, label=lbl)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False); ax.set_title(title, fontsize=8, loc='left')


def dilate1(m): return Mz.dilate(m, Mz.SQ3)


def fig2():
    ex = [('mig', 801, 300), ('long', 821, 400), ('food3', 831, 400), ('asym3', 841, 400), ('food4', 851, 600)]
    ex = [e for e in ex if (e[0], e[1], 'v8c') in R]
    if not ex: return
    fig, axs = plt.subplots(2, len(ex), figsize=(2.6 * len(ex), 5.6))
    axs = np.array(axs).reshape(2, -1)
    for j, (s, sd, t) in enumerate(ex):
        for i, (tag, nm) in enumerate((('v8c', '대조'), ('v8v', '후보'))):
            show_state(axs[i, j], f'b_{s}_s{sd}_{tag}', t, f'{nm} {s} s{sd} t={t}')
    h, l = axs[0, 0].get_legend_handles_labels()
    if h: fig.legend(h, l, loc='lower center', ncol=2, markerscale=4, frameon=False)
    fig.suptitle('두께 h (밝음 0 → 짙음 2) 와 흐름 없는 실(보라)·막다른 꼬리(검정)', fontsize=10, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0.04, 1, 0.96)); fig.savefig(os.path.join(FD, 'fig2_snapshots.png'), dpi=130); plt.close(fig)


def fig3():
    rs = [r for k, r in sorted(R.items()) if k[2] == 'v8v' and 'scl' in r]
    if not rs: return
    n = len(rs); nc = 6; nr = (n + nc - 1) // nc; fig = plt.figure(figsize=(13, 4.3 * nr + 3.2)); gs = fig.add_gridspec(2 * nr + 1, nc, height_ratios=[1] * (2 * nr) + [1.3])
    for j, r in enumerate(rs):
        f = os.path.join(DD, r['run'] + '_lump.npz')
        Z = np.load(f); N = Z['mask_abs'].shape[0]; Mf = Z['mask_abs']; sy, sx = Mz.centered_shift(Mf, N); w = 30
        jr, jc = 2 * (j // nc), j % nc
        ax = fig.add_subplot(gs[jr, jc]); tw = crop(Z['trap_G'], sy, sx, w); ax.imshow(tw, cmap='Greys', interpolation='nearest'); ax.contour(crop(Mf, sy, sx, w).astype(float), [0.5], colors=[C_CAND], linewidths=1.0)
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False); ax.set_title(f"{r['scn']} s{r['seed']}\n갇힐 때 흐린 두께 + 끝 덩이 윤곽", fontsize=7, loc='left')
        ax = fig.add_subplot(gs[jr + 1, jc])
        fl = os.path.join(MD, r['run'], f"vs_t{int(r['scl']['t_final']):04d}.npz")
        if os.path.exists(fl):
            S = Mz.load_vs(fl); hc = crop(np.where(S['wet'], S['h'], np.nan), sy, sx, w); im = ax.imshow(hc, cmap='YlOrBr', vmin=0, vmax=np.nanmax(hc), interpolation='nearest')
            L = r['scl']['lump_final']; ax.set_title(f"끝 h (최대 {np.nanmax(hc):.1f})\n넓이 {L['area']}, 볼록비 {L['solidity']:.2f}, 원판IoU {L['disc_iou']:.2f}", fontsize=7, loc='left')
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    ax = fig.add_subplot(gs[2 * nr, :]); first = True
    for r in rs:
        ser = np.load(os.path.join(MD, r['run'], 'series.npz')); a = ser['area'].astype(float); dt = float(ser['dt']); ts = r['scl']['t_scl']; i0 = int(round(ts / dt))
        t = np.arange(a.size - i0) * dt; fa = (a[i0] - a[i0:]) / max(a[i0] - a[-1], 1)
        c = np.array(r['scl']['conc']); fc = (c[:, 1] - c[0, 1]) / max(c[-1, 1] - c[0, 1], 1e-9)
        ax.plot(t, fa, lw=1.0, color=C_CAND, alpha=0.75, label='넓이 변화 몫 (스텝별)' if first else None)
        ax.plot(c[:, 0] - ts, fc, lw=1.0, color=C_CTRL, alpha=0.75, marker='o', ms=3, label='끝 덩이 칸에 모인 부피 몫 (20 시간 간격)' if first else None); first = False
    ax.set_xlim(-20, 250); ax.set_xlabel('균핵 상태 시작부터 시각'); ax.set_ylabel('변화의 몫 (0 → 1)')
    ax.legend(frameon=False, loc='lower right'); ax.set_title('7(d) 맺힘의 빠르기: 부피는 80~100 시간에 걸쳐 모이고, 넓이는 50~60 시간 그대로이다가 10~20 시간 사이에 줄어든다', fontsize=8, loc='left')
    fig.tight_layout(); fig.savefig(os.path.join(FD, 'fig3_sclerotium.png'), dpi=130); plt.close(fig)


def fig4():
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.4))
    for k, (tag, col, nm) in enumerate((('v8c', C_CTRL, '대조'), ('v8v', C_CAND, '후보'))):
        e = [(r['seed'], (r.get('heading') or {}).get('35') or (r.get('heading') or {}).get('20')) for kk, r in sorted(R.items()) if kk[2] == tag and kk[0] in MIG]
        e = [(s, x['err']) for s, x in e if x]
        if e: axs[0].scatter([s for s, _ in e], [x for _, x in e], s=22, color=col, label=nm, edgecolor='white', linewidth=0.8)
    axs[0].axhline(0, color='#999999', lw=0.8); axs[0].set_xlabel('시드'); axs[0].set_ylabel('방향 오차 (도, +는 반시계)'); axs[0].legend(frameon=False); axs[0].set_title('5. 35칸 갔을 때 방향 오차', fontsize=9, loc='left')
    for tag, col, nm in (('v8c', C_CTRL, '대조'), ('v8v', C_CAND, '후보')):
        e = np.sort([x for kk, r in R.items() if kk[2] == tag for x in r['mg_err_list']])
        if e.size: axs[1].plot(e, np.arange(1, e.size + 1) / e.size, color=col, lw=2, label=f'{nm} (n={e.size})')
    axs[1].set_xscale('log'); axs[1].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:g}')); axs[1].set_xlabel('상대 유량 오차'); axs[1].set_ylabel('누적 몫'); axs[1].legend(frameon=False); axs[1].set_title('9. 압력 풀이 유량 오차의 누적 분포', fontsize=9, loc='left')
    P = pairs(FOOD); c = [a['metrics']['t_touch'] for a, b in P]; v = [b['metrics']['t_touch'] for a, b in P]
    for (a, b) in P:
        for x, y in zip(a['metrics']['t_touch'], b['metrics']['t_touch']):
            axs[2].scatter(x if x is not None else a['T'] * 1.05, y if y is not None else b['T'] * 1.05, s=14, color='#191919' if (x and y) else '#ec4647', alpha=0.7, edgecolor='white', linewidth=0.5)
    m = max([a['T'] for a, b in P] or [500]) * 1.08; axs[2].plot([0, m], [0, m], color='#999999', lw=0.8); axs[2].plot([0, m], [0, 1.4 * m], color='#cccccc', lw=0.8, ls='--')
    axs[2].set_xlim(0, m); axs[2].set_ylim(0, m); axs[2].set_xlabel('대조 닿은 시각'); axs[2].set_ylabel('후보 닿은 시각'); axs[2].set_title('4. 먹이별 닿은 시각 (빨강 = 한쪽이 못 닿음, T 너머에 둠)', fontsize=9, loc='left')
    fig.tight_layout(); fig.savefig(os.path.join(FD, 'fig4_heading_flux_food.png'), dpi=130); plt.close(fig)


def fig5():
    X = {}
    for f in glob.glob(os.path.join(V, 'data_extra', '*.json')):
        x = json.load(open(f)); X[x['run']] = x
    if not X: return
    def pe(r, key, tmin=60.0):
        x = X.get(r['run']); v = [o[key] for o in (x['snaps'] if x else []) if o['t'] >= tmin and o.get(key) is not None]
        return float(np.mean(v)) if v else np.nan
    first = lambda r: min([x for x in r['metrics']['t_touch'] if x is not None] or [np.inf]) + 20
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.8))
    paired(axs[0], pairs(ALL), lambda r: pe(r, 'nf_thread_main'), '3(보조). 주 몸에 붙은 흐름 없는 실 칸')
    paired(axs[1], pairs(ALL), lambda r: pe(r, 'nf_tipr_main'), '3(보조). 주 몸의 흐름 없는 가지 끝')
    paired(axs[2], pairs(FOOD), lambda r: pe(r, 'rtail_cells', first(r)), '6(보조). 굳센 끝 깎기 꼬리 칸 (먹이 판)')
    paired(axs[3], pairs(MIG), lambda r: pe(r, 'rtail_cells'), '6(보조). 굳센 끝 깎기 꼬리 칸 (이주 판)')
    fig.suptitle('보조 분석 (등록 기준 밖): 떨어진 부스러기를 뺀 실·끝, 계단꼴·2칸 폭도 잡는 꼬리', fontsize=10, x=0.01, ha='left')
    fig.tight_layout(); fig.savefig(os.path.join(FD, 'fig5_supplement.png'), dpi=130); plt.close(fig)


if __name__ == '__main__':
    os.makedirs(FD, exist_ok=True)
    for f in (fig1, fig2, fig3, fig4, fig5):
        try: f(); print(f.__name__, 'ok')
        except Exception as e: print(f.__name__, 'FAILED', repr(e))
