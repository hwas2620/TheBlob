#!/usr/bin/env python3
"""verify4 사후 분석 (미리 정한 판정에는 쓰지 않는다; 판정이 왜 그렇게 나왔는지 보는 것). usage: extra.py -> logs/extra.txt, data/extra.json
   1) long 후보의 끝 상태: 가장 큰 덩이의 부피 몫, 큰 몸 수, 가는 칸을 뺀 몸통의 K, 꼬리(가는 칸) 수
   2) long 후보의 균핵 깜빡임: 스냅숏마다 두께 최대 > 2 (균핵 원반의 두께 3 h0) 인지, 처음 균핵 뒤 켜짐/꺼짐 바뀐 수
   3) 갇힘 시각을 후보의 t_scl 로 두 실행에 같이 쓴 비교 ([t_scl + 100, 2000])
   4) 먹이 시나리오 후보의 나뉨(fission)과 부스러기 사례"""
import json, glob, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure as M
import judge as J

V4 = J.V4; RUNS = os.path.join(os.path.dirname(V4), 'model', 'runs'); L = []


def say(*a):
    s = ' '.join(str(x) for x in a); L.append(s); print(s)


def main():
    R = J.load(); OUT = {}
    say('# verify4 사후 분석 (판정에 쓰지 않음)')
    say('\n## 1·2. long 후보: 끝 상태와 균핵 깜빡임')
    rows = []
    for s in sorted({k[1] for k in R if k[0] == 'long'}):
        if ('long', s, 'v4w') not in R: continue
        r = R[('long', s, 'v4w')]; m = r['metrics']; d = os.path.join(RUNS, r['name'])
        files = sorted(glob.glob(os.path.join(d, 'vs_t*.npz'))); ind = []; ts = []
        for f in files:
            Z = np.load(f); ts.append(float(Z['t'])); ind.append(bool(Z['h'][Z['wet']].max() > 2.0))
        first = next((i for i, v in enumerate(ind) if v), None)
        flips = int(sum(ind[i] != ind[i - 1] for i in range(first + 1, len(ind)))) if first is not None else 0
        Z = np.load(files[-1]); wet = Z['wet']; h = Z['h'].astype(float)
        lab, nb = M.label8(wet); bv = np.bincount(lab.ravel(), weights=np.where(wet, h, 0).ravel()); V = h[wet].sum()
        kb = int(np.argmax(np.where(np.arange(nb + 1) > 0, bv, -1))); mb = lab == kb
        narrow = wet & ~M.opening(wet, M.SQ3); Kb, lb = M.shape_of(mb & ~narrow)
        e = r['snaps'][-1]
        row = dict(seed=s, t_scl=m['t_scl'], fission=m['fission_runs'], first_disc=ts[first] if first is not None else None, flips=flips, disc_at_end=ind[-1],
                   n_big=e['n_big'], top_lump=e['lump_shares'][0] if e['lump_shares'] else 0.0, K=e['K'], K_bulk=Kb, lam_bulk=lb, tail_cells=int((narrow & mb).sum()), area=e['area'])
        rows.append(row)
        say(f"   s{s}: t_scl {m['t_scl']}, 나뉨 {m['fission_runs']}, 처음 원반 {row['first_disc']}, 원반 켜짐/꺼짐 바뀜 {flips}, 끝에 원반 {ind[-1]}, 큰 몸 {e['n_big']}, "
            f"가장 큰 덩이 몫 {row['top_lump']:.3f}, K {e['K']:.3f}, 몸통 K {Kb:.3f}, 꼬리 칸 {row['tail_cells']}")
    good = [x for x in rows if x['n_big'] == 1 and x['disc_at_end'] and (x['K_bulk'] or 0) >= 0.75]
    say(f"   끝에 원반 하나(몸통 K >= 0.75, 큰 몸 1): {len(good)}/{len(rows)}; 끝에 원반 둘(나뉜 몸마다): {sum(x['n_big'] >= 2 for x in rows)}; 끝에 원반 아님: {sum(not x['disc_at_end'] for x in rows)}; 깜빡임(바뀜 >= 2): {sum(x['flips'] >= 2 for x in rows)}")
    OUT['long_cand_end'] = rows
    say('\n## 3. 갇힘 시각 = 후보 t_scl (두 실행 같이), 창 [t_scl + 100, 2000]')
    M3 = {k: ([], []) for k in ('n_mass', 'K', 'lam', 'main_narrow_share', 'top_lump')}; used = []
    for s in sorted({k[1] for k in R if k[0] == 'long'}):
        if ('long', s, 'v4c') not in R or ('long', s, 'v4w') not in R: continue
        ts_ = R[('long', s, 'v4w')]['metrics']['t_scl']
        if ts_ is None: continue
        Sc = J.win(R[('long', s, 'v4c')], ts_ + 100, 1e9); Sw = J.win(R[('long', s, 'v4w')], ts_ + 100, 1e9)
        if len(Sc) < 3: continue
        used.append(s)
        tl = lambda x: x['lump_shares'][0] if x['lump_shares'] else 0.0
        for k in M3: M3[k][0].append(np.mean([(tl(x) if k == 'top_lump' else x[k]) for x in Sc])); M3[k][1].append(np.mean([(tl(x) if k == 'top_lump' else x[k]) for x in Sw]))
    res = {}
    for k in M3:
        res[k] = J.stat(*M3[k]); say(f"   {k:18s}", J.fmt(res[k], ('n', 'mean_c', 'mean_w', 'med_d', 'p_less', 'p_greater')))
    OUT['tscl_window'] = dict(pairs=used, tests=res)
    say('\n## 4. 후보의 나뉨과 부스러기 (시나리오별)')
    for scn in ('long', 'food4', 'food3', 'asym3', 'mig'):
        rr = [R[k] for k in sorted(R) if k[0] == scn and k[2] == 'v4w']
        if not rr: continue
        fis = [r['metrics']['fission_runs'] for r in rr]; nb2 = [max(s['n_big'] for s in r['snaps']) for r in rr]
        say(f"   {scn}: 나뉨이 있던 후보 실행 {sum(f > 0 for f in fis)}/{len(rr)} (나뉨 수 {fis}), 큰 몸 최대 수 {nb2}")
        for r in rr:
            ds = [(s['t'], s['debris_n'], s['debris_max_share'], s['body_shares']) for s in r['snaps'] if s['debris_n'] > 0 and s['t'] >= 100]
            if ds: say(f"      {r['name']}: 부스러기 스냅숏 {len(ds)}, 처음 {ds[0]}, 마지막 {ds[-1]}")
    say('\n## 5. 이주 방향: 유인원 방향에서 벗어난 각 (부호 있음, + = y 가 커지는 쪽으로 돎), min(닿는 시각, 200) 의 중심 이동')
    sg = {'v4c': [], 'v4w': []}; spd = {'v4c': [], 'v4w': []}
    for scn in ('mig', 'long'):
        for s in sorted({k[1] for k in R if k[0] == scn}):
            for cfg in ('v4c', 'v4w'):
                if (scn, s, cfg) not in R: continue
                r = R[(scn, s, cfg)]; c0 = r['c0']; a_, d_ = r['foods'][0]; u = np.array([np.cos(np.radians(a_)), np.sin(np.radians(a_))])
                tt = r['metrics']['t_touch'][0]; tt = tt if (tt is not None and tt <= 400) else 400.0; te = min(tt, 200.0)
                v = J.cen_at(r, te) - c0; ang = float(np.degrees(np.arctan2(u[0] * v[1] - u[1] * v[0], u @ v)))
                sg[cfg].append(ang); spd[cfg].append(float(np.linalg.norm(J.cen_at(r, 200.0) - c0)))
    for cfg in sg:
        a = np.array(sg[cfg]); say(f"   {cfg}: n {a.size}, 부호 각 평균 {a.mean():.1f}°, 중앙값 {np.median(a):.1f}°, + 쪽 {int((a > 0).sum())}, - 쪽 {int((a < 0).sum())}; t=200 이동 거리 중앙값 {np.median(spd[cfg]):.1f}")
    OUT['heading_signed'] = sg
    open(os.path.join(V4, 'logs', 'extra.txt'), 'w').write('\n'.join(L) + '\n')
    json.dump(OUT, open(os.path.join(V4, 'data', 'extra.json'), 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))


if __name__ == '__main__':
    main()
