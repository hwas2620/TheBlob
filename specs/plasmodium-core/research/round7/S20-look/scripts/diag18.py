"""diag18.py — [S18 진단] 조각 크기, 갇힌 뒤 모양(둘째 검증자 frame), 죽은 실(엄한 정의 포함). 이미 쓴 시드, 판정 아님."""
import sys, os, glob, re, json, numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify2', 'scripts')); import measure as M2
sys.path.insert(0, os.path.join(HERE, '..', '..', 'S16-dumbbell', 'verify', 'scripts')); import vlib
R = os.path.join(HERE, '..', 'model', 'runs'); PK = 'M=wet|r=3|f=0.10|neck=any'
def one(name):
    fs = sorted(glob.glob(os.path.join(R, name, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    mid = {'mc': [], 'dead': [], 'dead3': []}; end = {'mc': [], 'area': [], 'peri': [], 'lumps': []}; pieces_mid = 0; pieces_frames = 0; maxsmall = 0.0
    for f in fs:
        Z = np.load(f); t = float(Z['t'])
        if t < 100: continue
        w = Z['wet'].astype(bool); h = np.where(w, Z['h'], 0.0); lab, n = vlib.torus_label(w); vol = np.bincount(lab.ravel(), weights=h.ravel())[1:]; fr = vol / vol.sum()
        small = fr[(fr < 0.10)]
        if small.size: maxsmall = max(maxsmall, float(small.max())); pieces_frames += 1
        F = M2.frame(Z)
        if t <= 1600:
            mid['mc'].append(F['db'][PK])
            if t >= 1000: mid['dead'].append(F['dead']['line=3|F0.1|smin=4']); mid['dead3'].append(F['dead']['line=3|F0.03|smin=4'])
        else:
            end['mc'].append(F['db'][PK]); end['area'].append(int(w.sum()))
            big = lab == np.argmax(vol) + 1; edge = big & ~(np.roll(big, 1, 0) & np.roll(big, -1, 0) & np.roll(big, 1, 1) & np.roll(big, -1, 1))
            end['peri'].append(float(edge.sum()) / np.sqrt(big.sum()))
            core = F['blob'].get('nblob', 0); end['lumps'].append(core)
    m = json.load(open(os.path.join(R, name, 'metrics.json')))
    return name, dict(mc_mid=round(float(np.mean(mid['mc'])), 3), dead_mid=round(float(np.mean(mid['dead'])), 1), dead3_mid=round(float(np.mean(mid['dead3'])), 1),
                      mc_end=round(float(np.mean(end['mc'])), 3), area_end=int(np.mean(end['area'])), peri_end=round(float(np.mean(end['peri'])), 1), blobs_end=round(float(np.mean(end['lumps'])), 2),
                      frames_with_piece_lt10=pieces_frames, max_piece_lt10=round(maxsmall, 4), t_scl=m.get('t_scl'), fission=m.get('fission_runs'))
if __name__ == '__main__':
    with Pool(4) as p:
        for n, r in p.imap(one, sys.argv[1:]): print(n, json.dumps(r), flush=True)
