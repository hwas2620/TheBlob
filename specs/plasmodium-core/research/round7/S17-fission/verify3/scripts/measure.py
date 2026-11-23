#!/usr/bin/env python3
"""verify3: 실행 하나의 판(vs_t*.npz)과 끝 상태를 재어 data/frames/<run>.json.gz 로 쓴다.

usage: measure.py RUN_NAME [RUN_NAME ...]     (RUN_NAME 예: b_long_s351_x17c)
정의는 CRITERIA.md 를 따른다. 판정은 하지 않는다 (judge.py 가 한다).
"""
import sys, os, json, gzip, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vlib import tlabel, topen, tdt, tskel, nsum8, nmax8, dilate_cheb, cell_flow, wconn

V3 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RUNS = os.path.normpath(os.path.join(V3, '..', 'model', 'runs'))
OUT = os.path.join(V3, 'data', 'frames')
HTS = (0.4, 0.5, 0.6, 0.7)
FS = (0.03, 0.1, 0.3)
HF = (0.2, 0.3, 0.4)
AMIN = (40, 60, 100)
BIG = 0.10          # 큰 몸
MSMALL = 0.05       # 덩이 목록에 남길 가장 작은 비율 (민감도의 가장 작은 m)


def bodies(wet, hw):
    lab, n = tlabel(wet)
    vol = np.bincount(lab.ravel(), weights=hw.ravel(), minlength=n + 1)
    area = np.bincount(lab.ravel(), minlength=n + 1)
    return lab, n, vol, area


def small_pieces(lab, n, vol, area, V):
    big = int(np.argmax(vol[1:]) + 1) if n else 0
    out = []
    for k in range(1, n + 1):
        if vol[k] / V < BIG:
            idx = np.flatnonzero(lab.ravel() == k)
            out.append(dict(f=float(vol[k] / V), frel=float(vol[k] / vol[big]), area=int(area[k]), idx=idx.tolist()))
    return out


def blob_stats(body, hw, wet, h, lab, dt, ht):
    thick = wet & (h >= ht) & body
    op = topen(thick, 3)
    bl, nbl = tlabel(op)
    if nbl == 0: return [], None
    bv = np.bincount(bl.ravel(), weights=hw.ravel(), minlength=nbl + 1)[1:]
    Vb = float(hw[body].sum())
    order = np.argsort(bv)[::-1]
    fr = [float(bv[i] / Vb) for i in order[:6]]
    wc = None
    if len(order) >= 2 and fr[1] >= MSMALL:
        wc = int(wconn(body, dt, bl == order[0] + 1, bl == order[1] + 1))
    return fr, wc


def geo_stats(body, dt):
    op = topen(body, 7)
    gl, ng = tlabel(op)
    if ng == 0: return [], None
    ga = np.bincount(gl.ravel(), minlength=ng + 1)[1:].astype(float)
    Ab = float(body.sum()); order = np.argsort(ga)[::-1]
    fr = [float(ga[i] / Ab) for i in order[:6]]
    wc = None
    if len(order) >= 2 and fr[1] >= MSMALL:
        wc = int(wconn(body, dt, gl == order[0] + 1, gl == order[1] + 1))
    return fr, wc


def largest_body_c3(body, h, age, Qg):
    q = cell_flow(Qg.astype(np.float64))
    old = body & (age >= 20)
    if old.sum() < 10: return None
    qr = dict(med=float(np.median(q[old])), p90=float(np.percentile(q[old], 90)))
    plate = topen(body, 3)
    thread = body & ~plate
    tl, ntl = tlabel(thread)
    tsz = np.bincount(tl.ravel(), minlength=ntl + 1); tsz[0] = 0
    thread3 = thread & (tsz[tl] >= 3)
    A = float(body.sum())
    film = {f'{hf}_{am}': float((plate & (h < hf) & (age >= am)).sum() / A) for hf in HF for am in AMIN}
    sk = tskel(body)
    ep = sk & (nsum8(sk) == 1)
    tips = ep & thread
    qn = nmax8(np.where(body, q, 0.0))
    dead_thr = {}; dead_tip = {}
    for rn, rv in qr.items():
        for f in FS:
            dead_thr[f'{rn}_{f}'] = int((thread3 & (q < f * rv) & (age >= 20)).sum())
            dead_tip[f'{rn}_{f}'] = int((tips & (qn < f * rv) & (age >= 20)).sum())
    return dict(area=int(A), qref=qr, film=film, thread=int(thread.sum()), thread3=int(thread3.sum()), tips=int(tips.sum()),
                dead_thr=dead_thr, dead_tip=dead_tip, plate=int(plate.sum()))


def measure(name):
    rd = os.path.join(RUNS, name)
    P = json.load(open(os.path.join(rd, 'params.json')))
    met = json.load(open(os.path.join(rd, 'metrics.json')))
    N = int(P['N']); c0 = N / 2 - 0.5
    jj, ii = np.mgrid[0:N, 0:N]
    vis = np.hypot(ii - c0, jj - c0) < P['R_init']
    is_long = '_long_' in name
    files = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')))
    frames = []
    prev_lab = None; prev_vol = None
    for fpath in files:
        d = np.load(fpath)
        wet = d['wet'].astype(bool); h = d['h'].astype(np.float64); age = d['age'].astype(np.float64); t = float(d['t'])
        hw = np.where(wet, h, 0.0); V = float(hw.sum())
        lab, n, vol, area = bodies(wet, hw)
        rec = dict(t=round(t, 2), V=V, nb=n, fb=sorted([float(v / V) for v in vol[1:]], reverse=True)[:12], area=int(wet.sum()))
        rec['small'] = small_pieces(lab, n, vol, area, V)
        big = int(np.argmax(vol[1:]) + 1)
        lb = lab == big
        # 2절: 새 땅 비율 (가장 큰 몸 둘레)
        ring = dilate_cheb(lb, 2) & ~wet
        rec['F'] = float((ring & ~vis).sum() / max(int(ring.sum()), 1))
        rec['U'] = float(1.0 - (vis | wet).sum() / (N * N))
        # 몸마다 부피 보존 (떨어진 몸 사이로 부피가 옮겨지는지): 앞 판과 겹침으로 1:1 맞는 몸의 부피 변화
        dvs = []
        if prev_lab is not None and (n >= 2 or int(prev_lab.max()) >= 2):
            for k in range(1, n + 1):
                m = lab == k
                pk = np.unique(prev_lab[m]); pk = pk[pk > 0]
                if pk.size == 1:
                    back = np.unique(lab[prev_lab == pk[0]]); back = back[back > 0]
                    if back.size == 1:
                        dvs.append([float(vol[k]), float(prev_vol[pk[0]])])
        rec['dvol'] = dvs
        prev_lab = lab; prev_vol = vol
        if is_long:
            bl_rec = []
            for k in range(1, n + 1):
                if vol[k] / V < BIG: continue
                body = lab == k
                dt = tdt(body)
                br = dict(f=float(vol[k] / V), area=int(area[k]), big=(k == big))
                for ht in HTS:
                    fr, wc = blob_stats(body, hw, wet, h, lab, dt, ht)
                    br[f'b{ht}'] = fr; br[f'w{ht}'] = wc
                fr, wc = geo_stats(body, dt)
                br['geo'] = fr; br['wgeo'] = wc
                bl_rec.append(br)
            rec['bodies'] = bl_rec
            # 판 전체 굵은 덩이 (몸 구분 없이), h_t = 0.5
            op = topen(wet & (h >= 0.5), 3); bl, nbl = tlabel(op)
            bv = np.bincount(bl.ravel(), weights=hw.ravel(), minlength=nbl + 1)[1:] if nbl else np.zeros(0)
            rec['allblobs'] = sorted([float(v / V) for v in bv], reverse=True)[:6]
            rec['c3'] = largest_body_c3(lb, h, age, d['Qgross'])
        frames.append(rec)
        vis |= wet
    # 끝 상태
    wet = np.load(os.path.join(rd, 'wet.npy')).astype(bool); h = np.load(os.path.join(rd, 'h.npy')).astype(np.float64)
    hw = np.where(wet, h, 0.0); V = float(hw.sum()); lab, n, vol, area = bodies(wet, hw)
    end = dict(V=V, nb=n, fb=sorted([float(v / V) for v in vol[1:]], reverse=True)[:12], small=small_pieces(lab, n, vol, area, V))
    keys = ('name', 'stop', 't_end', 'runtime', 'V0', 'Vinj', 'V_end', 'mass_err_max', 'h_min_seen', 'disp', 'path_len', 'area_end', 'foods', 't_touch', 't_cover', 't_exh',
            'fM_end', 'V_crumb', 'crumb_cells', 'ret_cellsteps', 'conn_kept_cellsteps', 'conn_released_cells', 'sup_fed_skips', 'hang_cellsteps', 'fission_runs',
            'h_min_end_of_step', 'neg_end_cellsteps', 'neg_end_steps', 'steps_done', 'neg_cellsteps', 'neg_fill_cellsteps', 'sup_updates')
    out = dict(name=name, N=N, T=P['T'], food_M=P.get('food_M'), metrics={k: met.get(k) for k in keys}, frames=frames, end=end)
    os.makedirs(OUT, exist_ok=True)
    with gzip.open(os.path.join(OUT, name + '.json.gz'), 'wt') as fo:
        json.dump(out, fo)
    return out


if __name__ == '__main__':
    for nm in sys.argv[1:]:
        o = measure(nm)
        print(nm, 'frames', len(o['frames']), 'end_nb', o['end']['nb'], flush=True)
