"""measure17.py RUN [RUN ...] — [S17] 갈라짐 허용을 재는 지표 (저장 상태, t >= 200).
몸 수: 몸 부피 5% 이상 젖은 조각 수 (평균, 끝). 부스러기: 5% 미만 조각의 수와 부피 몫 (평균).
실 아령 f_D2: S16 첫 검증자 vlib.dumbbell (같은 몸 안, h>0.5, 5%, 이음 ≤ 3), t 200~2000 / 1000~2000.
가장 큰 몸 안 막·죽은 실·끝 줄: vlib.late_cells, t 1500~2000."""
import sys, os, glob, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify', 'scripts'))
import vlib
R = os.path.join(HERE, '..', 'model', 'runs')
def stats(name):
    rd = os.path.join(R, name); nb_ = []; deb_n = []; deb_v = []; d2 = []; d2l = []; cell = {'film': [], 'dead': [], 'endline': []}
    for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
        Z = np.load(f); S = {k: Z[k] for k in Z.files}; t = float(S['t'])
        if t < 200: continue
        w = S['wet'].astype(bool); h = np.where(w, S['h'].astype(float), 0.0)
        lab, n = vlib.torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]; V = vol.sum()
        big = vol >= 0.05 * V; nb_.append(int(big.sum())); deb_n.append(int((~big).sum())); deb_v.append(float(vol[~big].sum() / V))
        x = vlib.dumbbell(w, h, lab_w=lab)['D2']; d2.append(x)
        if t >= 1000: d2l.append(x)
        if t >= 1500:
            main = lab == np.argmax(vol) + 1; S2 = dict(S); S2['wet'] = main; S2['h'] = np.where(main, h, 0.0); c = vlib.late_cells(S2)
            for k in cell: cell[k].append(c[k])
    m = json.load(open(os.path.join(rd, 'metrics.json')))
    return dict(bodies=round(float(np.mean(nb_)), 2), bodies_end=nb_[-1], debris_n=round(float(np.mean(deb_n)), 1), debris_v=round(float(np.mean(deb_v)), 4),
                fD2=round(float(np.mean(d2)), 3), fD2_late=round(float(np.mean(d2l)), 3), **{k: int(np.mean(v)) for k, v in cell.items()},
                fission=m.get('fission_runs'), neg_end=m.get('neg_end_cellsteps'), V_crumb=round(float(m.get('V_crumb', 0)), 4), t_touch=m.get('t_touch'))
if __name__ == '__main__':
    for a in sys.argv[1:]: print(a, json.dumps(stats(a), ensure_ascii=False))
