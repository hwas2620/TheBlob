#!/usr/bin/env python3
"""vextract.py RUN_DIR [RUN_DIR ...]  — 독립 검증의 채점(실행 하나씩).

쓰는 것 (verify/data/):
  bmet_<run>.json  stage0/metrics/bmet.py 의 score() 그대로 (고치지 않고 import 해서 부른다)
  x_<run>.json     이 검증에서 따로 재는 값:
                   - metrics.json 의 음수·부피·이음 횟수·먹이 시각
                   - params.json 확인 (neck_keep, ncyc, solver, crumb_dry, thin_h)
                   - 저장 상태(vs_t*.npz)마다: 바깥 몫 out (bmet.body_out 과 같은 계산), 넓이, h<0.3 넓이, 부피
                   - 저장 상태마다 이음 다시 찾기 (ref_model.py 의 neck 찾기를 그대로 옮김) 와 이음 간선의 흐름 (CRITERIA.md 2절)
ref_model.py 는 import 하지 않는다(numba 컴파일을 피하려고 _torus_label 과 이음 찾기만 옮겨 적었다).
"""
import sys, os, json, glob, re
import numpy as np

V = '/home/user/TheBlob/specs/plasmodium-core/research/round7/S6-neck-mg3/verify'
MET = '/home/user/TheBlob/specs/plasmodium-core/stage0/metrics'
sys.path.insert(0, MET); sys.path.insert(0, os.path.join(MET, '..', 'ref'))
import vmet, bmet

TH = json.load(open(os.path.join(V, 'thresholds.json')))
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL = DIRS + [(-d[0], -d[1]) for d in DIRS]


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))     # ref_model.nb 와 같다


def _torus_label(mask):
    """ref_model._torus_label 을 그대로 옮김: 8연결 라벨, 토러스 가장자리를 건너 붙은 성분은 합친다"""
    from scipy import ndimage as _ndi
    N_ = mask.shape[0]
    lab, n = _ndi.label(mask, structure=np.ones((3, 3)))
    if n == 0: return lab
    parent = np.arange(n + 1)
    def f(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for i in range(N_):
        for d in (-1, 0, 1):
            for a, b in ((lab[i, 0], lab[(i + d) % N_, N_ - 1]), (lab[0, i], lab[N_ - 1, (i + d) % N_])):
                if a and b:
                    a, b = f(a), f(b)
                    if a != b: parent[b] = a
    root = np.array([f(k) for k in range(n + 1)])
    _, comp = np.unique(root, return_inverse=True)
    return comp[lab]


def find_neck(h, wet, neck_h, neck_min):
    """ref_model.py 의 [S5] 이음 찾기를 그대로 옮김. 돌려줌: neck(얇은 이음 셀), neckp(끝을 포함한 길), 정보"""
    N = h.shape[0]
    neck = np.zeros((N, N), bool); neckp = np.zeros((N, N), bool); info = dict(n_thick_parts=0, n_big=0, link_len=None, n_links=0)
    thick_ = wet & (h >= neck_h); lt_ = _torus_label(thick_); nt_ = int(lt_.max()); info['n_thick_parts'] = nt_
    if nt_ >= 2:
        vt_ = np.bincount(lt_.ravel(), weights=np.where(thick_, h, 0.0).ravel(), minlength=nt_ + 1); vt_[0] = 0.0
        big_ = [k_ for k_ in np.argsort(vt_)[::-1] if vt_[k_] >= neck_min * float(h[wet].sum())]
        info['n_big'] = len(big_)
        if len(big_) >= 2:
            def _geo(src_):
                dist_ = np.where(src_, 0.0, np.inf); fr_ = src_.copy(); seen_ = src_.copy(); it_ = 0
                while fr_.any() and it_ < N:
                    it_ += 1; nbm_ = np.zeros((N, N), bool)
                    for d_ in ALL: nbm_ |= nb(fr_, d_)
                    fr_ = nbm_ & wet & ~seen_; dist_[fr_] = it_; seen_ |= fr_
                return dist_
            dA_ = _geo(lt_ == big_[0]); lens = []
            for kb_ in big_[1:]:
                dB_ = _geo(lt_ == kb_); sm_ = dA_ + dB_
                if not np.isfinite(sm_[wet]).any(): continue
                m_ = float(np.min(sm_[wet])); path_ = wet & (sm_ <= m_ + 1)
                neckp |= path_; neck |= path_ & ~thick_; lens.append(m_)
            if lens: info['link_len'] = min(lens); info['n_links'] = len(lens)
    return neck, neckp, info


def med(a):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    return float(np.median(a)) if a.size else None


def link_flow(S, neck, neckp, W):
    """이음 간선과 비교 간선의 흐름 (CRITERIA 2절)"""
    wet = S['wet'].astype(bool); C = S['C'].astype(float); Cm = S['Cmean'].astype(float); Qg = S['Qgross'].astype(float); Qm = np.abs(S['Qmean'].astype(float))
    Lc = []; Lcm = []; Lqg = []; Lqm = []; Omask = []
    for k, d in enumerate(DIRS):
        act = wet & nb(wet, d); inl = act & neckp & nb(neckp, d)
        L = inl & (neck | nb(neck, d))
        Lc.append(C[k][L]); Lcm.append(Cm[k][L]); Lqg.append(Qg[k][L]); Lqm.append(Qm[k][L]); Omask.append(act & ~inl)
    Lc = np.concatenate(Lc); Lcm = np.concatenate(Lcm); Lqg = np.concatenate(Lqg); Lqm = np.concatenate(Lqm)
    out = dict(n_link_edges=int(Lc.size))
    if Lc.size == 0: return out
    mc = float(np.median(Lcm))
    comp = np.concatenate([Qg[k][Omask[k] & (Cm[k] >= W['comp_lo'] * mc) & (Cm[k] <= W['comp_hi'] * mc)] for k in range(4)])
    vein = np.concatenate([Qg[k][Omask[k] & (Cm[k] > W['vein_C'])] for k in range(4)])
    vein_qm = np.concatenate([Qm[k][Omask[k] & (Cm[k] > W['vein_C'])] for k in range(4)])
    out.update(pin=float(np.mean(Lc <= W['neck_C'] + W['pin_eps'])), C_link_med=float(np.median(Lc)), C_link_min=float(Lc.min()), Cmean_link_med=mc,
               Qg_link_med=float(np.median(Lqg)), Qg_link_min=float(Lqg.min()), Qm_link_med=float(np.median(Lqm)),
               n_comp=int(comp.size), Qg_comp_med=med(comp) if comp.size else None, n_vein=int(vein.size), Qg_vein_med=med(vein) if vein.size else None,
               Qm_vein_med=med(vein_qm) if vein_qm.size else None)
    out['R_same'] = (out['Qg_link_med'] / out['Qg_comp_med']) if (comp.size >= W['comp_min_n'] and out['Qg_comp_med']) else None
    out['R_vein'] = (out['Qg_link_med'] / out['Qg_vein_med']) if (vein.size >= W['comp_min_n'] and out['Qg_vein_med']) else None
    return out


def extract(run_dir):
    run = os.path.basename(run_dir.rstrip('/'))
    P = json.load(open(os.path.join(run_dir, 'params.json'))); M = json.load(open(os.path.join(run_dir, 'metrics.json')))
    W = TH['W3']; thin_h = TH['C7']['thin_h']
    o = dict(run=run, scn=re.match(r'b_(.+?)_s\d+', run).group(1), seed=P['seed'], tag=run.rsplit('_', 1)[-1], N=P['N'], T=P['T'])
    o['params_check'] = {k: P.get(k) for k in ('neck_keep', 'ncyc', 'solver', 'crumb_dry', 'thin_h', 'neck_h', 'neck_min', 'neck_C', 'neck_every', 'gm_every', 'vsave', 'curv_gain', 'eat', 'foods')}
    for k in ('stop', 't_end', 'steps_done', 'runtime', 'mass_err_max', 'h_min_seen', 'h_min_end_of_step', 'neg_end_steps', 'neg_end_cellsteps', 'neg_cellsteps',
              'neck_updates', 'neck_cells', 'V_crumb', 'crumb_cells', 't_touch', 't_cover', 't_exh', 'area_end', 'V0', 'Vinj', 'V_end', 'disp'):
        o['m_' + k] = M.get(k)
    o['expected_steps'] = int(round(P['T'] / P['dt'])) + 1
    o['complete'] = bool(M.get('stop', '') == '' and M.get('steps_done') == o['expected_steps'])
    o['neck_update_total'] = int(round(P['T'] / P.get('neck_every', 1.0)))
    rows = []
    for f in sorted(glob.glob(os.path.join(run_dir, 'vs_t*.npz'))):
        Z = np.load(f); S = {k: Z[k] for k in Z.files}
        wet = S['wet'].astype(bool); h = S['h'].astype(float); r = dict(t=float(S['t']), area=int(wet.sum()), vol=float(h.sum()), thin=int((wet & (h < thin_h)).sum()))
        if wet.any():
            src, dst, cc, kk = vmet.edge_list(S['C'].astype(float), wet); bs = vmet.body_stats(src, dst, wet, h)
            r['out'] = 1.0 - bs['body_largest_vol']; r['ncomp'] = bs['body_ncomp']
            neck, neckp, info = find_neck(h, wet, W['neck_h'], W['neck_min']); r.update(info)
            r['n_neck'] = int(neck.sum()); r['n_neckp'] = int(neckp.sum())
            if neck.any():
                r['h_neck_med'] = float(np.median(h[neck])); r.update(link_flow(S, neck, neckp, W))
        else:
            r['out'] = 1.0; r['ncomp'] = 0
        rows.append(r)
    o['rows'] = rows; o['n_states'] = len(rows)
    return o


def main():
    os.makedirs(os.path.join(V, 'data'), exist_ok=True)
    for rd in sys.argv[1:]:
        run = os.path.basename(rd.rstrip('/'))
        b = bmet.score(rd); json.dump(b, open(os.path.join(V, 'data', f'bmet_{run}.json'), 'w'), ensure_ascii=False, indent=1)
        x = extract(rd); json.dump(x, open(os.path.join(V, 'data', f'x_{run}.json'), 'w'), ensure_ascii=False, indent=0)
        print(run, 'ok', x['n_states'], 'states', flush=True)


if __name__ == '__main__':
    main()
