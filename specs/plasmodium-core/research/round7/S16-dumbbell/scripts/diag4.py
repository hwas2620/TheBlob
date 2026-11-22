"""diag4.py — [S16 진단 4] 고리 풀기(keep_conn=3). 이미 쓴 시드. 판정 아님."""
import json, os, sys, glob, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from shape import nbig, tlab
R = os.path.join(HERE, '..', 'model', 'runs')
RING = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]
def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))
def linemask(w):
    xr = [~nb(w, d) for d in RING]; Nc = np.zeros(w.shape, int)
    for q in (0, 2, 4, 6): Nc += xr[q].astype(int) - (xr[q] & xr[q + 1] & xr[(q + 2) % 8]).astype(int)
    return w & (Nc > 1)
def main():
    print('== long (시드 231, 233, 239): big2_06, 늦은 얇은 칸, 끝 줄 칸, 끝 줄 칸 부피 몫, 끝 넓이, 끝 조각, 풀린 칸, 걸린 시간')
    for tag in ('s15c', 's15dc', 's16h', 's16kr', 's16hr'):
        rows = []
        for s in (231, 233, 239):
            rd = os.path.join(R, f'b_long_s{s}_{tag}')
            if not os.path.exists(os.path.join(rd, 'metrics.json')): continue
            b6 = []; thin = []
            for f in sorted(glob.glob(os.path.join(rd, 'vs_t*.npz'))):
                Z = np.load(f); t = float(Z['t']); w = Z['wet'].astype(bool); h = Z['h']
                if t >= 100: b6.append(nbig(h, w, 0.6) >= 2)
                if t >= 1600: thin.append(int((w & (h < 0.3)).sum()))
            w = np.load(os.path.join(rd, 'wet.npy')).astype(bool); h = np.load(os.path.join(rd, 'h.npy'))
            L = linemask(w); m = json.load(open(os.path.join(rd, 'metrics.json')))
            rows.append((s, round(np.mean(b6), 3), int(np.mean(thin)), int(L.sum()), round(float(h[L].sum() / h[w].sum()), 3), int(w.sum()), tlab(w)[1], m.get('conn_released_cells'), int(m['runtime'])))
        print(tag); [print('   ', r) for r in rows]
    print('== food4 (시드 231~234): 먹이 닿은 시각, 늦음(대조보다 50 넘게 늦거나 못 닿음)')
    def tt(s, tag):
        f = os.path.join(R, f'b_food4_s{s}_{tag}', 'metrics.json')
        return json.load(open(f))['t_touch'] if os.path.exists(f) else None
    for s in (231, 232, 233, 234):
        print(s, {tag: tt(s, tag) for tag in ('s15c', 's15dc', 's16k0', 's16k0r', 's16kr')})
    for tag in ('s15dc', 's16k0', 's16k0r', 's16kr', 's16h'):
        late = 0
        for s in (231, 232, 233, 234):
            c = tt(s, 's15c'); k = tt(s, tag)
            late += sum(1 for i in range(4) if c[i] is not None and (k[i] is None or k[i] > c[i] + 50))
        print(f'{tag}: 늦음 {late} / 16쌍')

if __name__ == '__main__': main()
