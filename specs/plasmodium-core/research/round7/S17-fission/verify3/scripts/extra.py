#!/usr/bin/env python3
"""verify3 덧붙임 (판정 밖): 이어지는 시간(사건 길이), 가장 나쁜 사례, 갈라짐 수. data/summary_extra.json 에 쓴다."""
import os, json
import numpy as np
import judge as J

V3 = J.V3


def episodes(flags, ts):
    out = []; start = None; n = 0
    for fl, t in zip(flags, ts):
        if fl:
            if start is None: start = t; n = 0
            n += 1
        elif start is not None:
            out.append((start, n)); start = None
    if start is not None: out.append((start, n))
    return out


def main():
    trap = json.load(open(os.path.join(V3, 'data', 'trap.json')))
    res = {}
    for a in J.ARMS:
        ep_db = []; ep_mb = []; worst_thr = (0, None); worst_tip = (0, None); worst_film = (0, None); split_big = []
        for s in J.SEEDS['long']:
            R = J.load('long', s, a)
            if R is None: continue
            w = J.wins(trap, s, a)['primary']; fs = J.win_frames(R, w); ts = [f['t'] for f in fs]
            for st, n in episodes([J.db_frame(f, 0.5, 0.10, 2) for f in fs], ts): ep_db.append((n, s, st))
            for st, n in episodes([J.mb_frame(f, 0.5, 0.10) for f in fs], ts): ep_mb.append((n, s, st))
            for f in fs:
                c = f.get('c3')
                if c is None: continue
                if c['dead_thr']['med_0.1'] > worst_thr[0]: worst_thr = (c['dead_thr']['med_0.1'], f'{s} t{f["t"]}')
                if c['dead_tip']['med_0.1'] > worst_tip[0]: worst_tip = (c['dead_tip']['med_0.1'], f'{s} t{f["t"]}')
                if c['film']['0.3_60'] > worst_film[0]: worst_film = (c['film']['0.3_60'], f'{s} t{f["t"]}')
                nbig = sum(1 for x in f['fb'] if x >= 0.10)
                if nbig >= 2: split_big.append((s, f['t']))
        # 굵은 덩이가 줄어든 것이 몸 전체가 얇아져서인지 보려고: 가장 큰 몸의 가장 큰 덩이 비율, 덩이 합 비율 (h 0.5, 옮겨 다니는 때 평균)
        b1 = []; bsum = []; thin_seed = []
        for s in J.SEEDS['long']:
            R = J.load('long', s, a)
            if R is None: continue
            fs = J.win_frames(R, J.wins(trap, s, a)['primary'])
            v1 = []; vs = []
            for f in fs:
                bb = [b for b in f.get('bodies', []) if b['big']]
                if bb:
                    fr = bb[0]['b0.5']; v1.append(fr[0] if fr else 0.0); vs.append(sum(fr))
            b1.append(float(np.mean(v1))); bsum.append(float(np.mean(vs)))
        ep_db.sort(reverse=True); ep_mb.sort(reverse=True)
        res[a] = dict(DB_episodes=len(ep_db), DB_longest=ep_db[:5], DB_len_mean=float(np.mean([e[0] for e in ep_db])) if ep_db else 0.0,
                      MB_episodes=len(ep_mb), MB_longest=ep_mb[:5], MB_len_mean=float(np.mean([e[0] for e in ep_mb])) if ep_mb else 0.0,
                      worst_dead_thread=worst_thr, worst_dead_tip=worst_tip, worst_film=worst_film,
                      frames_with_2plus_big_bodies=len(split_big), seeds_with_big_split=sorted(set(x[0] for x in split_big)),
                      largest_blob_frac_mean=float(np.mean(b1)), blob_sum_frac_mean=float(np.mean(bsum)))
        fis = {}
        for scn, ss in J.SEEDS.items():
            v = []
            for s in ss:
                R = J.load(scn, s, a)
                if R is not None: v.append(R['metrics']['fission_runs'] or 0)
            fis[scn] = dict(total=int(sum(v)), runs_with=int(sum(1 for x in v if x > 0)))
        res[a]['fission_runs'] = fis
    # 아주 엄한 죽은 실 (q < 0.03 × 중앙값): 시드마다 가장 큰 셀 수와 20 셀 이상인 판 수
    for a in J.ARMS:
        st = []
        for s in J.SEEDS['long']:
            fs = J.win_frames(J.load('long', s, a), J.wins(trap, s, a)['primary'])
            v = [f['c3']['dead_thr']['med_0.03'] for f in fs]; st.append((s, int(max(v)), int(sum(1 for x in v if x >= 20))))
        res[a]['strict_dead_thread_max_frames20'] = st
    # 조각 사건 (후보, 5% 아래): 실행, 시작 t, 판 수, 가장 작은 비율, long 이면 옮겨 다님/갇힘
    ev = []
    for scn, ss in J.SEEDS.items():
        for s in ss:
            _, evs, _ = J.crumb_scan(J.load(scn, s, 'x17fs'), 0.05)
            for e in evs:
                ph = ('migrating' if e[0] < (trap[f'{s}_x17fs']['F0.3'] or 1e9) else 'trapped') if scn == 'long' else 'food' if scn != 'mig' else 'mig'
                ev.append(dict(run=f'{scn}_{s}', t0=e[0], frames=e[1], fmin=round(e[2], 4), phase=ph))
    res['x17fs']['piece_events_lt5pct'] = ev
    # 주장 5 를 문턱 3% / 2% 로 다시 본 것 (끝 상태 조각)
    for c in (0.02, 0.03, 0.05):
        bad = [f'{scn}_{s}' for scn, ss in J.SEEDS.items() for s in ss if any(p['f'] < c for p in J.load(scn, s, 'x17fs')['end']['small'])]
        res['x17fs'][f'end_piece_runs_lt{c}'] = bad
    # 떨어진 몸 사이 부피 이동 (먹지 않는 long, mig; 몸 수가 그대로인 판만)
    for a in J.ARMS:
        rs = []
        for scn in ('long', 'mig'):
            for s in J.SEEDS[scn]:
                fr = J.load(scn, s, a)['frames']
                for i in range(1, len(fr)):
                    if fr[i]['nb'] != fr[i - 1]['nb']: continue
                    rs += [abs(vn - vp) / vp for vn, vp in fr[i]['dvol'] if vp > 0.01 * fr[i]['V']]
        res[a]['body_volume_change_max_nofeed'] = float(max(rs)) if rs else 0.0
    json.dump(res, open(os.path.join(V3, 'data', 'summary_extra.json'), 'w'), indent=1, default=str)
    vp = os.path.join(V3, 'data', 'verdict.json'); vd = json.load(open(vp))
    vd['extra_notes'] = dict(strict_dead_thread=res['x17fs']['strict_dead_thread_max_frames20'], strict_dead_thread_ctrl=res['x17c']['strict_dead_thread_max_frames20'],
                             piece_events_lt5pct=ev, end_piece_runs_lt3pct=res['x17fs']['end_piece_runs_lt0.03'], end_piece_runs_lt2pct=res['x17fs']['end_piece_runs_lt0.02'],
                             body_volume_change_max_nofeed=dict(x17c=res['x17c']['body_volume_change_max_nofeed'], x17fs=res['x17fs']['body_volume_change_max_nofeed']))
    json.dump(vd, open(vp, 'w'), indent=1, ensure_ascii=False)
    print('\n[덧붙임: 사건 길이 (판 수, 시드, 시작 t), 가장 나쁜 사례 (옮겨 다니는 때)]')
    for a in J.ARMS:
        r = res[a]
        print(f' {a}: DB 사건 {r["DB_episodes"]} (평균 {r["DB_len_mean"]:.1f} 판) 가장 긴 것 {r["DB_longest"][:3]}; MB 사건 {r["MB_episodes"]} (평균 {r["MB_len_mean"]:.1f} 판) 가장 긴 것 {r["MB_longest"][:3]}')
        print(f'      죽은 실 최대 {r["worst_dead_thread"]}, 죽은 가지 끝 최대 {r["worst_dead_tip"]}, 막 최대 {r["worst_film"]}')
        print(f'      큰 몸(≥10%) 둘 이상 판 {r["frames_with_2plus_big_bodies"]} (시드 {r["seeds_with_big_split"]}); 갈라짐(fission_runs) {r["fission_runs"]}')
        print(f'      가장 큰 몸: 가장 큰 덩이 비율 평균 {r["largest_blob_frac_mean"]:.3f}, 덩이(h≥0.5, 열기 뒤) 합 비율 평균 {r["blob_sum_frac_mean"]:.3f}')
        print(f'      아주 엄한 죽은 실 (q<0.03×중앙값) (시드, 최대 셀, 20셀 이상 판 수): {r["strict_dead_thread_max_frames20"]}')
        print(f'      떨어진 몸 사이 부피 변화 최대 (long, mig, 몸 수 그대로인 판): {r["body_volume_change_max_nofeed"]:.2e}')
    print(' 후보의 5% 아래 조각 사건:')
    for e in res['x17fs']['piece_events_lt5pct']: print('   ', e)
    for c in (0.02, 0.03, 0.05): print(f' 후보 끝 상태에 {c*100:.0f}% 아래 조각이 있는 실행: {res["x17fs"][f"end_piece_runs_lt{c}"]}')


if __name__ == '__main__':
    main()
