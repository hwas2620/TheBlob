#!/usr/bin/env python3
"""[검증] 작성자가 재지 않은 것을 저장된 상태에서 직접 잰다. 기준 모델·채점기는 고치지 않고 읽기만 한다.

usage: extra_metrics.py RUN_DIR [RUN_DIR ...] --out DIR      → DIR/extra_<실행>.json

실행마다
  시각별(vs_t*.npz, 20 시간마다)
    area        젖은 셀 수
    thin        "얇은 셀" = 젖었고 h < h_min 이고 age > grace 인 셀 수 (마름 문턱 아래인데 남아 있는 셀)
    memonly     thin 가운데 닿은 간선의 최대 전도도 Cn < bridge_break(1.0) 인 셀 수 (지금 규칙이면 붙잡지 않을 셀)
    vthin       thin 셀이 가진 부피 ÷ 총 부피
    neg         음수 두께인 젖은 셀 수, hmin 최소 두께
    out         1 − 가장 큰 8연결 젖은 덩어리의 부피 비율 (채점기의 out_frac 과 같은 정의)
    ncomp       젖은 덩어리 수, comp2 둘째 덩어리의 부피 비율
    out_strip   memonly 셀을 지우고 다시 잰 것 (남은 부피 기준)
    두 덩어리가 memonly 가닥으로만 이어져 있을 때(out < 0.10 이고 out_strip >= 0.10):
      cutQ      지운 뒤의 가장 큰 두 덩어리 사이 최소 절단, 간선 용량 = Qgross (직전 다섯 주기의 평균 |유량|)
      cutW      같은 절단을 전도도 G·(C+r)/L 로
      bnC, bnQ  가장 넓은 길의 병목(최대-최소 경로): 전도도 C, 총유량 Qgross
      carry     cutQ × 주기 ÷ 작은 덩어리의 부피 (한 주기에 오가는 부피의 비율)
    medC_thin, medQ_thin   thin 셀에 닿은 간선의 C·Qgross 중앙.   medC_vein, medQ_vein  정맥 간선(C > 4)의 중앙
    disc_wet    먹이(유인원) 원반마다 젖은 셀 수
  실행 전체
    부피 장부(V0, Vinj, V_end, V_crumb), 끝 상태 h.npy 로 다시 더한 값, 버린 부피의 누적(기록 시각마다)의 단조성
    series.npz 에서: 새로 젖은 셀 수(구간별), 넓이
    twet.npy 에서: 한 번이라도 젖은 셀 수
"""
import glob, json, os, sys
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE0 = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..', '..', 'stage0'))
sys.path.insert(0, os.path.join(STAGE0, 'metrics')); sys.path.insert(0, os.path.join(STAGE0, 'ref'))
import vmet     # 채점기가 쓰는 것과 같은 간선 목록·성분 함수 (읽기만)

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
LS = np.array([1.0, 1.0, 2 ** 0.5, 2 ** 0.5])


def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))


def node_C(C):
    Cn = np.zeros(C.shape[1:])
    for k, d in enumerate(DIRS): Cn = np.maximum(Cn, np.maximum(C[k], rev(C[k], d)))
    return Cn


def comp_vol(src, dst, wet, h):
    """8연결 성분의 라벨과 성분별 부피(큰 순서의 번호)"""
    N = wet.shape[0]; n = N * N
    nc, lab = vmet.comps(src, dst, n)
    w = wet.ravel(); vol = np.bincount(lab[w], weights=h.ravel()[w].astype(float), minlength=nc); area = np.bincount(lab[w], minlength=nc)
    order = np.argsort(-vol)
    order = [int(c) for c in order if area[c] > 0]
    return lab, vol, area, order


def min_cut(src, dst, cap, n, a_nodes, b_nodes):
    """a_nodes 와 b_nodes 사이의 최소 절단 (무방향 간선 용량 cap). 정수 최대 유량으로 푼다. 돌려줌: 절단 값 (cap 의 단위)"""
    if a_nodes.size == 0 or b_nodes.size == 0 or cap.size == 0: return 0.0
    cmax = float(cap.max())
    if cmax <= 0: return 0.0
    # 가는 가닥의 용량이 0 으로 뭉개지지 않게: 가닥을 지나는 최대 용량의 척도로 잡는다. 큰 용량은 잘라도 절단(가는 쪽)에는 영향이 없다
    pos = cap[cap > 0]; ref = float(np.percentile(pos, 10)) if pos.size else cmax
    scale = 1e4 / max(ref, 1e-300); ceil = 2_000_000
    ci = np.minimum(np.round(cap * scale), ceil).astype(np.int64)
    s, t = n, n + 1; big = 30_000_000
    rows = np.concatenate([src, dst, np.full(a_nodes.size, s), b_nodes]); cols = np.concatenate([dst, src, a_nodes, np.full(b_nodes.size, t)])
    vals = np.concatenate([ci, ci, np.full(a_nodes.size, big), np.full(b_nodes.size, big)]).astype(np.int32)
    g = csr_matrix((vals, (rows, cols)), shape=(n + 2, n + 2))
    f = maximum_flow(g, s, t).flow_value
    return float(f) / scale


def analyse(S, G, P, do_cut=True):
    C = S['C'].astype(float); wet = S['wet'].astype(bool); h = S['h'].astype(float); age = S['age'].astype(float); N = wet.shape[0]; n = N * N
    Qg = S['Qgross'].astype(float); Qm = S['Qmean'].astype(float)
    o = dict(t=float(S['t']), area=int(wet.sum()))
    if not wet.any(): return o
    Cn = node_C(C)
    thin = wet & (h < P['h_min']) & (age > P['grace']); mem = thin & (Cn < P['bridge_break'])
    tot = float(h.sum())
    o.update(thin=int(thin.sum()), memonly=int(mem.sum()), vthin=float(h[thin].sum() / tot) if tot > 0 else 0.0, neg=int((wet & (h < 0)).sum()), hmin=float(h[wet].min()),
             hmean=float(h[wet].mean()), vol=tot)
    src, dst, cc, kk = vmet.edge_list(C, wet)
    lab, vol, area, order = comp_vol(src, dst, wet, h)
    o['out'] = float(1.0 - vol[order[0]] / tot) if tot > 0 else 1.0; o['ncomp'] = len(order)
    o['comp2'] = float(vol[order[1]] / tot) if len(order) > 1 and tot > 0 else 0.0
    # 외톨이(젖은 이웃이 없는) 셀
    nw = np.zeros((N, N))
    for d in ((1, 0), (0, 1), (1, 1), (1, -1), (-1, 0), (0, -1), (-1, -1), (-1, 1)): nw += np.roll(wet, (-d[1], -d[0]), (0, 1))
    o['lone'] = int((wet & (nw == 0)).sum()); o['lone_neg'] = int((wet & (nw == 0) & (h < 0)).sum())
    # 간선 값의 견줌
    ys, xs = np.divmod(src, N); qg = Qg[kk, ys, xs]; qm = Qm[kk, ys, xs]
    tf = thin.ravel(); et = tf[src] | tf[dst]; ev = cc > 4.0
    med = lambda v: float(np.median(v)) if v.size else None
    o.update(medC_thin=med(cc[et]), medQ_thin=med(qg[et]), medC_vein=med(cc[ev]), medQ_vein=med(qg[ev]), medC_all=med(cc), medQ_all=med(qg), n_edge_thin=int(et.sum()), n_edge_vein=int(ev.sum()))
    # memonly 셀을 지운 몸
    wet2 = wet & ~mem
    if wet2.any():
        s2, d2, c2, k2 = vmet.edge_list(C, wet2); lab2, vol2, area2, ord2 = comp_vol(s2, d2, wet2, h); tot2 = float(vol2[[c for c in ord2]].sum())
        o['out_strip'] = float(1.0 - vol2[ord2[0]] / tot2) if tot2 > 0 else 1.0; o['ncomp_strip'] = len(ord2)
        o['comp2_strip'] = float(vol2[ord2[1]] / tot2) if len(ord2) > 1 and tot2 > 0 else 0.0
        if do_cut and len(ord2) > 1 and o['comp2_strip'] >= 0.02:
            w2 = wet2.ravel(); ids = np.arange(n)
            a = ids[w2 & (lab2 == ord2[0])]; b = ids[w2 & (lab2 == ord2[1])]
            # 전체 젖은 그래프에서 두 덩어리가 이어져 있는가
            joined = bool(lab[a[0]] == lab[b[0]])
            o['lobes_joined'] = joined; o['lobeB_vol'] = float(vol2[ord2[1]]); o['lobeB_area'] = int(area2[ord2[1]])
            if joined:
                wgt = G[kk, ys, xs].astype(float) * (cc + P['r']) / LS[kk]
                o['cutQ'] = min_cut(src, dst, qg, n, a, b); o['cutW'] = min_cut(src, dst, wgt, n, a, b); o['cutQnet'] = min_cut(src, dst, np.abs(qm), n, a, b)
                o['bnC'] = vmet.bottleneck(src, dst, cc, n, a, b); o['bnQ'] = vmet.bottleneck(src, dst, qg, n, a, b)
                o['carry'] = float(o['cutQ'] * P['period'] / max(o['lobeB_vol'], 1e-12))
    # 먹이(유인원) 원반
    if P.get('foods'):
        big = wet & (lab.reshape(N, N) == order[0])
        discs = [vmet.disc_mask(N, fx, fy, P['food_r']) for fx, fy in vmet.food_positions(P)]
        o['disc_wet'] = [int((m & wet).sum()) for m in discs]
        o['disc_in_big'] = [int((m & big).sum()) for m in discs]      # 그 가운데 가장 큰 덩어리(본체)에 든 셀 수: 0 이면 그 먹이는 본체에서 떨어진 조각이 덮고 있다
    return o


def run_level(rd, P, rows):
    met = json.load(open(os.path.join(rd, 'metrics.json')))
    o = dict(run=os.path.basename(rd.rstrip('/')), N=P['N'], seed=P['seed'], T=P['T'],
             opts={k: P.get(k) for k in ('bridge_mem', 'bridge_mem_tau', 'sat_k', 'sat_scent', 'crumb_dry', 'neg_fill', 'bridge_break')})
    V0 = met['V0']; Vinj = met['Vinj']; Vend = met['V_end']; Vc = met.get('V_crumb', 0.0)
    hend = float(np.load(os.path.join(rd, 'h.npy')).astype(np.float64).sum())
    o['vol'] = dict(V0=V0, Vinj=Vinj, V_end=Vend, V_end_from_h=hend, V_crumb=Vc, crumb_cells=met.get('crumb_cells', 0),
                    books=abs(Vend - V0 - Vinj + Vc) / V0, true_change=(Vend - V0 - Vinj) / V0, crumb_over_Vend=Vc / Vend if Vend else None, crumb_over_V0=Vc / V0,
                    mass_err_max=met.get('mass_err_max'))
    # 버린 부피의 누적: 기록 시각마다 D(t) = V0 + Vinj(t) − V(t)
    log = met.get('log') or []
    if log:
        D = np.array([V0 + e['Vinj'] - e['V'] for e in log]); dD = np.diff(D)
        o['vol'].update(drop_max=float(D.max()), drop_end=float(D[-1]), drop_abs_sum_logres=float(np.abs(dD).sum()), drop_neg_incr=int((dD < -1e-9).sum()), drop_neg_sum=float(dD[dD < -1e-9].sum()) if (dD < -1e-9).any() else 0.0)
    sr = np.load(os.path.join(rd, 'series.npz')); dt = float(sr['dt']); vol = sr['vol'].astype(float); new = sr['newm' if 'newm' in sr.files else 'new'].astype(float); areaS = sr['area'].astype(float); dry = sr['dry'].astype(float)
    if Vinj == 0.0:       # 굶은 실행: 스텝마다의 부피 변화가 곧 버린 양이다
        dv = np.diff(vol); tol = 1e-9
        o['vol'].update(step_drops=int((dv < -tol).sum()), step_drop_sum=float(-dv[dv < -tol].sum()), step_gains=int((dv > tol).sum()), step_gain_sum=float(dv[dv > tol].sum()), step_abs_sum=float(np.abs(dv[np.abs(dv) > tol]).sum()))
    tt = np.arange(vol.size) * dt
    win = lambda a, b: float(new[(tt >= a) & (tt < b)].sum())
    T = P['T']; edges = [0, 100, 200, 300, 400] if T <= 480 else ([0, 100, 200, 300, 400, 500, 600, 700] if T <= 700 else [0, 200, 400, 800, 1200, 1600, 2000] + ([2400, 2800, 3200, 3600, 4000] if T > 2000 else []))
    edges = [e for e in edges if e <= T + 1e-6]
    if edges[-1] < T: edges.append(T)
    o['new_by_window'] = [[edges[i], edges[i + 1], win(edges[i], edges[i + 1] + (1e-6 if i == len(edges) - 2 else 0))] for i in range(len(edges) - 1)]
    o['dry_total'] = float(dry.sum()); o['new_total'] = float(new.sum())
    # 멈춤: 마지막으로 새 셀이 젖은 시각, 마지막으로 셀이 마른 시각. 그 뒤로 끝까지 젖음도 마름도 없으면 몸이 멈춘 것이다
    o['last_new_t'] = float(tt[np.nonzero(new > 0)[0][-1]]) if (new > 0).any() else None; o['last_dry_t'] = float(tt[np.nonzero(dry > 0)[0][-1]]) if (dry > 0).any() else None
    o['still_for'] = float(T - max(o['last_new_t'] or 0.0, o['last_dry_t'] or 0.0))
    at = lambda t: int(areaS[min(int(round(t / dt)), areaS.size - 1)])
    o['area_at'] = {str(int(e)): at(e) for e in edges[1:]}
    tw = np.load(os.path.join(rd, 'twet.npy')); o['ever_wet'] = int((tw >= 0).sum()); o['ever_wet_frac'] = float((tw >= 0).mean())
    o['t_touch'] = met.get('t_touch'); o['t_cover'] = met.get('t_cover'); o['t_exh'] = met.get('t_exh'); o['fM_end'] = met.get('fM_end')
    o['neg'] = dict(neg_end_steps=met.get('neg_end_steps'), neg_end_cellsteps=met.get('neg_end_cellsteps'), h_min_end=met.get('h_min_end_of_step'), h_min_in=met.get('h_min_seen'), neg_cellsteps=met.get('neg_cellsteps'),
                    bridge_kept_cellsteps=met.get('bridge_kept_cellsteps'), steps=met.get('steps_done'))
    o['runtime'] = met.get('runtime'); o['area_end'] = met.get('area_end'); o['disp'] = met.get('disp'); o['path_len'] = met.get('path_len')
    # 시각별 값의 요약
    key = lambda k: [r.get(k) for r in rows]
    o['series'] = {k: key(k) for k in ('t', 'area', 'thin', 'memonly', 'vthin', 'neg', 'hmin', 'out', 'ncomp', 'comp2', 'out_strip', 'comp2_strip', 'lone', 'lone_neg', 'medC_thin', 'medQ_thin', 'medC_vein', 'medQ_vein', 'hmean')}
    if P.get('foods'):
        o['series']['disc_wet'] = key('disc_wet'); o['series']['disc_in_big'] = key('disc_in_big')
        # 먹이마다: 덮여 있는 저장 시각 가운데 본체가 덮고 있는 비율, 끝 시각에 본체가 덮고 있는가
        dw = np.array([r.get('disc_wet') for r in rows], float); db = np.array([r.get('disc_in_big') for r in rows], float)
        cov = dw > 0
        o['food_body'] = dict(frac_covered_by_body=[float(((db[:, k] > 0) & cov[:, k]).sum() / max(int(cov[:, k].sum()), 1)) if cov[:, k].any() else None for k in range(dw.shape[1])],
                              end_covered=[bool(dw[-1, k] > 0) for k in range(dw.shape[1])], end_by_body=[bool(db[-1, k] > 0) for k in range(dw.shape[1])],
                              first_covered_t=[float(rows[int(np.argmax(cov[:, k]))]['t']) if cov[:, k].any() else None for k in range(dw.shape[1])],
                              first_by_body_t=[float(rows[int(np.argmax(db[:, k] > 0))]['t']) if (db[:, k] > 0).any() else None for k in range(dw.shape[1])])
    cuts = [dict(t=r['t'], out=r['out'], out_strip=r['out_strip'], comp2_strip=r.get('comp2_strip'), joined=r.get('lobes_joined'), cutQ=r.get('cutQ'), cutQnet=r.get('cutQnet'), cutW=r.get('cutW'), bnC=r.get('bnC'), bnQ=r.get('bnQ'),
                 carry=r.get('carry'), lobeB_vol=r.get('lobeB_vol'), lobeB_area=r.get('lobeB_area')) for r in rows if r.get('lobes_joined') is not None]
    o['cuts'] = cuts
    return o


def main():
    args = sys.argv[1:]; out_dir = None
    if '--out' in args:
        i = args.index('--out'); out_dir = args[i + 1]; args = args[:i] + args[i + 2:]
    for rd in args:
        if not os.path.exists(os.path.join(rd, 'metrics.json')): print('건너뜀(끝나지 않음):', rd); continue
        states, G, P = vmet.load_states(rd)
        rows = [analyse(S, G, P) for S in states]
        o = run_level(rd, P, rows)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            json.dump(o, open(os.path.join(out_dir, f"extra_{o['run']}.json"), 'w'), ensure_ascii=False)
        s = o['series']
        print(o['run'], 'area_end', s['area'][-1], 'thin_end', s['thin'][-1], 'memonly_end', s['memonly'][-1], 'out_max %.3f' % max(s['out']), 'out_strip_max %.3f' % max(v for v in s['out_strip'] if v is not None),
              'cuts', len(o['cuts']), 'crumb/Vend %.2e' % (o['vol']['crumb_over_Vend'] or 0), 'true_change %.2e' % o['vol']['true_change'], flush=True)


if __name__ == '__main__':
    main()
