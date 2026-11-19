#!/usr/bin/env python3
"""관문 B 의 지표. 실행 폴더 하나를 채점해 JSON 으로 낸다.

usage: bmet.py RUN_DIR [RUN_DIR ...] [--out DIR]
  RUN_DIR  numpy 기준 실행(ref/runs/b_<시나리오>_s<시드>[_이름]) 또는 gpu2run.py 가 바꾼 GPU 실행(runs_gpu/b_…)
  --out    요약을 DIR/<출처>_<실행>.json 으로도 쓴다 (출처 = numpy | gpu)

GPU 와 numpy 를 똑같이 채점한다: 두 쪽 모두 같은 꼴의 파일(vs_t*.npz, params.json, metrics.json, hfood.npy, series.npz)을 읽는다.
정맥·먹이 연결의 지표는 5차 검증자의 vmet.py(사본)와 3~5차의 graphm.py 를 그대로 쓴다. 새로 만든 것은 아래 넷이다.

지표의 정의 (실행하기 전에 정했다. spec 의 B1~B7)
  B1 질량   mass_err   max |Σh − 처음 부피 − 먹은 양| / 처음 부피                              (metrics.json)
            neg_end    스텝 끝에 음수 두께인 젖은 셀이 있던 스텝 수                             (metrics.json)
            out_frac   1 − (가장 큰 몸 성분의 부피 비율)의 최소. 저장 시각마다                  (vmet.body_stats)
  B2 전진면 disp300    무게중심의 이동 t=0~300 (셀)과 그 방향이 유인원 방향과 이루는 각(도)
                       "한 방향 이주" = 이동 ≥ 20셀 이고 각 ≤ 30°
            chord      정맥 현(길이 ≥ 5)의 방향이 격자 방향(45° 의 배수 ±7.5°)인 길이 비율. t ≥ 200 의 중앙  (graphm.chord_orient)
            t_touch    유인원에 처음 닿은 시각 (방향별 실행을 judge_b.py 가 모아 최대/최소를 낸다)
  B3 정맥   모두 "시간 평균 전도도"(직전 다섯 주기의 평균 Cmean)로 잰다. 정맥 = Cmean > 4 이고 양 끝이 젖은 간선. t ≥ 200 의 중앙
            veinT      정맥 간선 가운데 가장 큰 연결 성분에 든 비율                              [새로 만든 것]
            strahler   가장 큰 성분의 최대 전도도 신장 나무에서 Strahler 차수의 최대            (graphm.strahler)
            rad_ratio  반지름 C^(1/4) 의 p90/p10                                               [새로 만든 것]
            rear       전진면에서 먼 절반의 정맥 전도도 중앙 ÷ 가까운 절반의 중앙, 그리고 거리와 log C 의 Spearman 상관   [새로 만든 것]
                       (192² 는 몸이 격자 절반을 넘기 전인 t ≤ 300 만. "멀수록 굵음" = 비 > 1 이고 상관 > 0)
            vein4      견줄 값: 그 순간의 전도도로 잰 최대 성분 (4~5차의 방법)
  B4 맥동   gross_net  정맥(그 순간 C > 4)의 Σ(총유량) ÷ Σ|순유량| (직전 다섯 주기). t ≥ 200 의 중앙   (graphm 의 vein_gross_over_net)
            lag        뒤 → 앞 위상 지연(바퀴): 가장 큰 젖은 성분을 진행 축을 따라 여섯 띠로 나눠 (맨 뒤 띠 − 맨 앞 띠)의 평균 위상. t ≥ 100 의 저장 시각마다
                       2차 E10 의 phasestat.py 와 같은 꼴. 위상은 맨 앞 셀에서 젖은 이웃을 따라 풀어서 쓴다(GPU 의 θ 는 0~2π 로 감겨 있다)   [새로 만든 것]
                       "몸 길이가 2배가 돼도 유지" = t = 300 의 값이 기본 몸(192²)과 2배 몸(mig2x: 384², 처음 원반 반지름 2배)에서 모두 0.5~2
                       (한 실행 안에서는 몸이 자라면서 지연도 커진다. numpy 시드 1: 길이 63셀에 0.13바퀴 → 100셀에 1.42바퀴)
            sheet_amp  시트(평균 두께 > 0.5·h0) 셀의 두께 진폭/평균 두께의 평균. t ≥ 200 의 중앙
  B5 먹이   vmet.summarise(kind='food') 그대로: 닿은 시각, 먹는 동안 같은 정맥 성분인 시간 비율(C > 4), 경로 최소 전도도의 중앙, 정맥 중앙, 몸 최대 성분
            굵은 쌍 = 경로 최소 전도도(중앙) ≥ 5 × 정맥 중앙.  시드의 통과 = 모든 먹이에 닿음 & 모든 쌍이 굵음 & 같은 성분 ≥ 0.9 & 몸 최대 성분 ≥ 0.9
  B6 점액   frac_empty 새로 젖은 셀 가운데 흔적이 없는 쪽(가운데의 오른쪽)의 비율. 처음 원반이 퍼지는 t < 20 은 뺀다   [새로 만든 것]
            late_new   사방이 흔적일 때 뒤쪽 절반(t ≥ T/2)에 새로 젖은 셀 수 ("멈추지 않음" = 100개 이상)
  B7 지속   구간(200~400, 400~800, …, 1600~2000)마다 B3 의 값. turnover = 이웃한 저장 시각 사이에 젖음이 바뀐 셀 ÷ 넓이의 중앙 (끝 400 시간)
            "얼어붙지 않음" = turnover > 0.02 이고 sheet_amp ≥ 0.03, "사라지지 않음" = 끝의 넓이 > 0
"""
import glob, json, os, re, sys
import numpy as np
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'ref'))
import vmet, graphm

CTHR = 4.0


def med(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return float(np.median(v)) if v else None


def rnd(x, n=3):
    return None if x is None else round(float(x), n)


def track(states, N):
    """저장 시각마다의 무게중심 (직전 무게중심 기준 최소 상으로 따라간다. vmet.summarise 와 같은 방법)"""
    c0 = N / 2 - 0.5; yy, xx = np.indices((N, N)); cx = cy = c0; out = []
    for S in states:
        h = S['h'].astype(float); m = h.sum()
        if m > 0:
            for _ in range(4):
                cx += float((h * vmet.wrapd(xx - cx, N)).sum() / m); cy += float((h * vmet.wrapd(yy - cy, N)).sum() / m)
        out.append((float(S['t']), cx, cy))
    return out


def vein_time_avg(S, N):
    """시간 평균 전도도로 잰 정맥: 최대 성분 비율, Strahler 최대, 반지름 p90/p10"""
    C = S['Cmean'].astype(float); wet = S['wet'].astype(bool); n = N * N
    src, dst, cc, kk = vmet.edge_list(C, wet)
    vs, _ = vmet.vein_stats(src, dst, cc, n, CTHR)
    out = dict(veinT=vs['largest'], veinT_E=vs['E'], strahler=None, rad_ratio=None)
    v = cc[cc > CTHR]
    if v.size >= 10:
        r = v ** 0.25; out['rad_ratio'] = float(np.percentile(r, 90) / np.percentile(r, 10))
    bs, gi = graphm.basic(C, wet, CTHR)
    if gi is not None: out['strahler'] = int(graphm.strahler(gi, C)['strahler_max'])
    return out


def axis_of(cen, i, back=5):
    """i 번째 저장 시각의 진행 방향: back 시각 전(100 시간 전)의 무게중심에서 지금 무게중심으로"""
    j = max(0, i - back); dx = cen[i][1] - cen[j][1]; dy = cen[i][2] - cen[j][2]; d = np.hypot(dx, dy)
    return (dx / d, dy / d) if d > 1.0 else None


def rear_front(S, N, cx, cy, ax):
    """전진면에서의 거리와 정맥 전도도(시간 평균): 먼 절반의 중앙 ÷ 가까운 절반의 중앙, Spearman(거리, log C)"""
    C = S['Cmean'].astype(float); wet = S['wet'].astype(bool); yy, xx = np.indices((N, N))
    proj = vmet.wrapd(xx - cx, N) * ax[0] + vmet.wrapd(yy - cy, N) * ax[1]
    front = float(proj[wet].max())
    d = []; c = []
    for k in range(4):
        m = (C[k] > CTHR) & wet
        d.append(front - proj[m]); c.append(C[k][m])
    d = np.concatenate(d); c = np.concatenate(c)
    if d.size < 20: return None, None
    far = d > np.median(d)
    return float(np.median(c[far]) / np.median(c[~far])), float(spearmanr(d, np.log(c))[0])


def phase_lag(S, N, cx, cy, ax, nband=6):
    """뒤 → 앞 위상 지연(바퀴)과 몸 길이(셀). 뒤가 앞서면 양수. 2차 E10 의 phasestat.py 와 같은 꼴이다:
    가장 큰 젖은 성분을 진행 축을 따라 여섯 띠로 나누고 (맨 뒤 띠의 평균 위상 − 맨 앞 띠의 평균 위상).
    E10 은 풀어진(누적) θ 를 그대로 썼다. GPU 의 θ 는 0~2π 로 감겨 있으므로, 맨 앞 셀에서 출발해 젖은 8이웃을 따라
    이웃 사이의 차이를 (−π, π] 로 접어 더해 가며 위상을 푼다(너비 우선). 돌려줌: (푼 위상으로 잰 지연, 몸 길이, 누적 θ 로 잰 지연 또는 None)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components, breadth_first_order
    wet = S['wet'].astype(bool); th = S['theta'].astype(float); yy, xx = np.indices((N, N)); n = N * N
    if wet.sum() < 50: return None, None, None
    idx = np.arange(n).reshape(N, N); src = []; dst = []
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        m = wet & np.roll(wet, (-dy, -dx), (0, 1)); src.append(idx[m]); dst.append(np.roll(idx, (-dy, -dx), (0, 1))[m])
    src = np.concatenate(src); dst = np.concatenate(dst)
    g = coo_matrix((np.ones(src.size, np.int8), (src, dst)), shape=(n, n)).tocsr(); g = g + g.T
    nc, lab = connected_components(g, directed=False)
    cnt = np.bincount(lab[wet.ravel()], minlength=nc); big = (lab == int(np.argmax(cnt))).reshape(N, N) & wet
    proj = vmet.wrapd(xx - cx, N) * ax[0] + vmet.wrapd(yy - cy, N) * ax[1]
    p = proj[big]; lo, hi = float(p.min()), float(p.max())
    if hi - lo < 12: return None, hi - lo, None
    start = int(idx[big][np.argmax(p)])
    order, pred = breadth_first_order(g, start, directed=False, return_predecessors=True)
    tw = th.ravel(); un = np.zeros(n); un[start] = tw[start]
    for v in order[1:]:
        u = pred[v]; d = (tw[v] - tw[u] + np.pi) % (2 * np.pi) - np.pi; un[v] = un[u] + d
    band = np.minimum(((p - lo) / (hi - lo + 1e-9) * nband).astype(int), nband - 1); u_ = un.reshape(N, N)[big]; t_ = th[big]
    if (band == 0).sum() < 5 or (band == nband - 1).sum() < 5: return None, hi - lo, None
    lag = float((u_[band == 0].mean() - u_[band == nband - 1].mean()) / (2 * np.pi))
    cum = float((t_[band == 0].mean() - t_[band == nband - 1].mean()) / (2 * np.pi)) if th[wet].max() > 2 * np.pi + 1e-3 else None      # 누적 θ 는 numpy 실행에만 있다 (한 주기만 지나도 2π 를 넘는다)
    return lag, hi - lo, cum


def gross_net(S):
    C = S['C'].astype(float); wet = S['wet'].astype(bool)
    bs, gi = graphm.basic(C, wet, CTHR)
    if gi is None: return None
    k, ys, xs = gi['k'], gi['ys'], gi['xs']; qn = np.abs(S['Qmean'].astype(float)[k, ys, xs]); qg = S['Qgross'].astype(float)[k, ys, xs]; ok = qg > 0
    if ok.sum() < 10: return None
    return float(qg[ok].sum() / max(qn[ok].sum(), 1e-12))


def chord_frac(S, N):
    bs, gi = graphm.basic(S['C'].astype(float), S['wet'].astype(bool), CTHR)
    if gi is None: return None
    return (graphm.chord_orient(gi, N).get('L>=5') or {}).get('frac_within7p5')


def sheet_amp(S, h0):
    hm = S['hmean'].astype(float); ha = S['hamp'].astype(float); m = hm > 0.5 * h0
    return float((ha[m] / hm[m]).mean()) if m.sum() >= 20 else None


def body_out(states):
    out = []
    for S in states:
        wet = S['wet'].astype(bool)
        if not wet.any(): out.append(1.0); continue
        src, dst, cc, kk = vmet.edge_list(S['C'].astype(float), wet)
        out.append(1.0 - vmet.body_stats(src, dst, wet, S['h'].astype(float))['body_largest_vol'])
    return out


def common(run_dir, states, P):
    """B1 과 실행의 기본 정보"""
    met = json.load(open(os.path.join(run_dir, 'metrics.json')))
    steps = met.get('steps_done') or int(round(met.get('t_end', 0) / P['dt'])) + 1
    out = dict(run=os.path.basename(run_dir.rstrip('/')), origin=met.get('origin', 'numpy'), N=P['N'], seed=P['seed'], steps=int(steps), n_states=len(states), stop=met.get('stop', ''),
               mass_err=met.get('mass_err_max'), neg_end=met.get('neg_end_steps'), neg_end_cellsteps=met.get('neg_end_cellsteps'), h_min_end=met.get('h_min_end_of_step'), h_min_in=met.get('h_min_seen'),
               flux_err=met.get('mg_err'), t_touch=met.get('t_touch'), t_exh=met.get('t_exh'), area_end=int(states[-1]['wet'].sum()) if states else None)
    bo = body_out(states)
    out['out_frac'] = rnd(max(bo), 4) if bo else None
    return out


def mig(run_dir, long=False):
    states, G, P = vmet.load_states(run_dir); N = P['N']; c0 = N / 2 - 0.5
    out = common(run_dir, states, P); cen = track(states, N)
    tmax_axis = 300 if N <= 192 else 400          # 그 뒤로는 몸이 격자의 절반을 넘어 무게중심과 진행 축이 흐려진다
    # B2: 이동
    c300 = next((c for c in cen if abs(c[0] - 300) < 1e-6), None)
    if c300 and P.get('foods'):
        dx, dy = c300[1] - c0, c300[2] - c0; fa = np.radians(P['foods'][0][0])
        out['disp300'] = rnd(np.hypot(dx, dy), 2)
        out['disp_angle'] = rnd(np.degrees(np.arccos(np.clip((dx * np.cos(fa) + dy * np.sin(fa)) / max(np.hypot(dx, dy), 1e-9), -1, 1))), 1)
    rows = []
    for i, S in enumerate(states):
        t = float(S['t']); r = dict(t=t)
        if t >= 200:
            r.update(vein_time_avg(S, N))
            src, dst, cc, kk = vmet.edge_list(S['C'].astype(float), S['wet'].astype(bool)); r['vein4'] = vmet.vein_stats(src, dst, cc, N * N, CTHR)[0]['largest']
            r['chord'] = chord_frac(S, N); r['gross_net'] = gross_net(S); r['sheet_amp'] = sheet_amp(S, P.get('h0', 1.0))
        ax = axis_of(cen, i)
        if ax and 100 <= t <= tmax_axis:
            r['lag'], r['length'], r['lag_cum'] = phase_lag(S, N, cen[i][1], cen[i][2], ax)
            if t >= 200: r['rear_ratio'], r['rear_rho'] = rear_front(S, N, cen[i][1], cen[i][2], ax)
        rows.append(r)
    W = [r for r in rows if r['t'] >= 200]
    for k in ('veinT', 'vein4', 'strahler', 'rad_ratio', 'chord', 'gross_net', 'sheet_amp', 'rear_ratio', 'rear_rho'):
        out[k] = rnd(med([r.get(k) for r in W]))
    out['veinT_min'] = rnd(min([r['veinT'] for r in W], default=None)); out['strahler_min'] = min([r['strahler'] for r in W if r.get('strahler') is not None], default=None)
    lags = [(r['t'], r['lag'], r['length'], r.get('lag_cum')) for r in rows if r.get('lag') is not None]
    out['lag'] = [[t, rnd(l), rnd(L, 1), rnd(c)] for t, l, L, c in lags]      # 시각, 푼 위상으로 잰 지연(바퀴), 몸 길이, 누적 θ 로 잰 지연(numpy 실행에만 있다)
    out['lag_min'] = rnd(min([l for _, l, _, _ in lags], default=None)); out['lag_max'] = rnd(max([l for _, l, _, _ in lags], default=None))
    if long:
        segs = [(200, 400), (400, 800), (800, 1200), (1200, 1600), (1600, 2000.5)]; out['segments'] = []
        for a, b in segs:
            Wseg = [r for r in rows if a <= r['t'] < b]
            if not Wseg: continue
            ss = [S for S in states if a <= float(S['t']) < b]
            out['segments'].append(dict(t=[a, int(b)], veinT=rnd(med([r.get('veinT') for r in Wseg])), strahler=med([r.get('strahler') for r in Wseg]), rad_ratio=rnd(med([r.get('rad_ratio') for r in Wseg])),
                                        sheet_amp=rnd(med([r.get('sheet_amp') for r in Wseg])), gross_net=rnd(med([r.get('gross_net') for r in Wseg])), out_frac=rnd(max(body_out(ss)), 4), area=int(np.median([S['wet'].sum() for S in ss]))))
        last = [S for S in states if float(S['t']) >= float(states[-1]['t']) - 400]
        to = [float((last[i]['wet'].astype(bool) ^ last[i - 1]['wet'].astype(bool)).sum() / max(int(last[i]['wet'].sum()), 1)) for i in range(1, len(last))]
        out['turnover'] = rnd(med(to)); out['t_last'] = float(states[-1]['t'])
    return out


def food(run_dir):
    o = vmet.summarise(run_dir, 'food'); o.pop('rows', None)
    states, G, P = vmet.load_states(run_dir)
    out = common(run_dir, states, P)
    pm = o.get('pathminC_med') or {}; vm = o.get('vein_medC_med'); same = o.get('same4') or {}
    out.update(t_touch_v=o.get('t_touch'), window=o.get('window'), pathminC=pm, vein_medC=vm, same4=same, body_min=o.get('body_largest_vol_min'), body_min_all=o.get('body_largest_vol_min_all'),
               vein4=o.get('vein4_largest_med'), note=o.get('note'))
    npair = len(P['foods']) * (len(P['foods']) - 1) // 2
    reached = all(v is not None for v in (o.get('t_touch') or [None]))
    out['reached'] = reached; out['pairs'] = npair
    out['thick'] = sum(1 for v in pm.values() if vm and v >= 5 * vm)
    out['ratio'] = {k: rnd(v / vm, 1) for k, v in pm.items()} if vm else {}
    out['same_ok'] = sum(1 for v in same.values() if v >= 0.9)
    out['pass'] = bool(reached and len(pm) == npair and out['thick'] == npair and out['same_ok'] == npair and (o.get('body_largest_vol_min') or 0) >= 0.9)
    return out


def slime(run_dir):
    states, G, P = vmet.load_states(run_dir); out = common(run_dir, states, P)
    s = np.load(os.path.join(run_dir, 'series.npz')); new = s['new'].astype(float); newl = s['newl'].astype(float); dt = P['dt']
    k0 = int(round(20 / dt)); half = new.size // 2
    out['new_total'] = int(new.sum()); out['new_after20'] = int(new[k0:].sum())
    out['frac_empty_all'] = rnd(1 - newl.sum() / max(new.sum(), 1)); out['frac_empty'] = rnd(1 - newl[k0:].sum() / max(new[k0:].sum(), 1))
    out['late_new'] = int(new[half:].sum()); out['slime0'] = P.get('slime0', '')
    return out


def touch(run_dir):
    P = json.load(open(os.path.join(run_dir, 'params.json'))); met = json.load(open(os.path.join(run_dir, 'metrics.json')))
    return dict(run=os.path.basename(run_dir.rstrip('/')), origin=met.get('origin', 'numpy'), N=P['N'], seed=P['seed'], angle=P['foods'][0][0], t_touch=met.get('t_touch'), stop=met.get('stop', ''),
                mass_err=met.get('mass_err_max'), neg_end=met.get('neg_end_steps'), h_min_in=met.get('h_min_seen'))


def score(run_dir):
    name = os.path.basename(run_dir.rstrip('/')); m = re.match(r'b_(.+?)_s\d+', name)
    scn = m.group(1) if m else name
    if scn.startswith('dir'): o = touch(run_dir)
    elif scn.startswith('slime'): o = slime(run_dir)
    elif scn.startswith(('food', 'asym')): o = food(run_dir)
    elif scn == 'long': o = mig(run_dir, long=True)
    else: o = mig(run_dir)
    o['scn'] = scn
    return o


if __name__ == '__main__':
    args = sys.argv[1:]; out_dir = None
    if '--out' in args:
        i = args.index('--out'); out_dir = args[i + 1]; args = args[:i] + args[i + 2:]
    if not args: raise SystemExit(__doc__)
    for rd in args:
        o = score(rd)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            json.dump(o, open(os.path.join(out_dir, f"{o['origin']}_{o['run']}.json"), 'w'), ensure_ascii=False, indent=1)
        print(json.dumps(o, ensure_ascii=False))
