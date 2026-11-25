"""S23 풀이 진단 2: 웜스타트(p0) 대 0 출발 대 '잔차가 작은 쪽' 출발, 켤레기울기 2·3·4 번의 유량 오차.
python3 pcgz.py out.json dump...  (pcgk.py 와 같은 덤프)"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from pcgk import pcg_trace, load, exact, ferr
if __name__ == '__main__':
    out = sys.argv[1]; res = []
    for f in sys.argv[2:]:
        W, wet, M, S, p0, t = load(f); pe = exact(W, M, S, wet); Z = np.zeros_like(p0)
        pw, rw, _, rel0 = pcg_trace(W, M, S, p0, kmax=4); pz, rz_, _, _ = pcg_trace(W, M, S, Z, kmax=4)
        pick = 'z' if rel0 > 1.0 else 'w'; pb = pz if pick == 'z' else pw
        row = dict(f=f, t=t, rel0=rel0, warm=[ferr(W, p_, pe) for p_ in pw], zero=[ferr(W, p_, pe) for p_ in pz], best=[ferr(W, p_, pe) for p_ in pb], pick=pick, relw=rw, relz=rz_)
        res.append(row)
        print(os.path.basename(os.path.dirname(os.path.dirname(f))), os.path.basename(f), f"rel0 {rel0:.2f}", 'warm', ' '.join(f"{e:.3f}" for e in row['warm'][1:]), 'zero', ' '.join(f"{e:.3f}" for e in row['zero'][1:]), pick, flush=True)
    json.dump(res, open(out, 'w'))
