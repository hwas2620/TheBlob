#!/usr/bin/env python3
"""verify2 측정: 실행 폴더의 vs_t*.npz 프레임마다 CRITERIA.md 의 지표를 잰다. 모델 코드(ref_model, graphm)는 import 하지 않는다.

usage: measure.py RUN_DIR [RUN_DIR ...]     -> data/frames/<run>.json
"""
import glob, json, os, re, sys
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'frames')
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]
ALL8 = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]   # cyclic ring order
NECK_S = sorted({np.sqrt(a * a + b * b) for a in range(0, 6) for b in range(0, 6) if 1 <= a * a + b * b <= 25}, reverse=True)


def nb(a, d): return np.roll(a, (-d[1], -d[0]), (0, 1))      # value at the neighbour (x+dx, y+dy)
def rev(a, d): return np.roll(a, (d[1], d[0]), (0, 1))


def torus_label(mask, conn=8):
    """components on the torus; returns (labels 0..n, n)"""
    st = np.ones((3, 3), bool) if conn == 8 else ndi.generate_binary_structure(2, 1)
    lab, n = ndi.label(mask, structure=st)
    if n == 0: return lab, 0
    N0, N1 = mask.shape; A = []; B = []
    offs = (-1, 0, 1) if conn == 8 else (0,)
    for d in offs:
        a = lab[:, 0]; b = np.roll(lab[:, N1 - 1], -d); m = (a > 0) & (b > 0); A.append(a[m]); B.append(b[m])
        a = lab[0, :]; b = np.roll(lab[N0 - 1, :], -d); m = (a > 0) & (b > 0); A.append(a[m]); B.append(b[m])
    A = np.concatenate(A); B = np.concatenate(B)
    g = coo_matrix((np.ones(A.size + n), (np.concatenate([A, np.arange(1, n + 1)]), np.concatenate([B, np.arange(1, n + 1)]))), shape=(n + 1, n + 1))
    nc, cl = connected_components(g, directed=False)
    # map: label 0 stays 0; others -> 1..k
    used = np.unique(cl[1:]); remap = np.zeros(nc, np.int64); remap[used] = np.arange(1, used.size + 1)
    newl = np.zeros(n + 1, np.int64); newl[1:] = remap[cl[1:]]
    return newl[lab], int(used.size)


def edt_torus(mask):
    """Euclidean distance from each True cell to the nearest False cell, on the torus (0 on False cells)"""
    N0, N1 = mask.shape
    if not mask.any(): return np.zeros(mask.shape)
    if mask.all(): return np.full(mask.shape, np.inf)
    t = np.tile(mask, (3, 3))
    return ndi.distance_transform_edt(t)[N0:2 * N0, N1:2 * N1]


def in_full_block(m, size):
    """cells of m that lie in some size x size block (size 2 or 3) whose cells are all in m"""
    if size == 2:
        c = m & nb(m, (1, 0)) & nb(m, (0, 1)) & nb(m, (1, 1))       # top-left corner of a full 2x2
        return c | nb(c, (-1, 0)) | nb(c, (0, -1)) | nb(c, (-1, -1))
    c = m.copy()
    for d in ALL8: c &= nb(m, d)                                    # centre of a full 3x3
    o = c.copy()
    for d in ALL8: o |= nb(c, d)
    return o


def ring_groups(wet):
    x = [nb(wet, d) for d in ALL8]
    g = np.zeros(wet.shape, np.int8); n = np.zeros(wet.shape, np.int8)
    for q in range(8):
        g += (x[q] & ~x[q - 1]).astype(np.int8); n += x[q].astype(np.int8)
    return g, n


def tip_lines(wet, body, cap=500):
    """list of (tip index, collected cell set) per tip of the largest body"""
    N = wet.shape[0]
    oneW = wet & ~in_full_block(wet, 2)
    grp, nn = ring_groups(wet)
    tip = oneW & body & (nn >= 1) & (nn <= 3) & (grp == 1)
    junc = grp >= 3
    thick = wet & ~oneW; att = np.zeros_like(wet)
    for d in ALL8: att |= nb(thick, d)
    stopm = junc | att
    oneWf = oneW.ravel(); stopf = stopm.ravel()
    out = []
    for t0 in np.flatnonzero(tip.ravel()):
        seen = {int(t0)}; q = [int(t0)]; i = 0
        while i < len(q) and len(seen) < cap:
            u = q[i]; i += 1
            if u != t0 and stopf[u]: continue
            y, x = divmod(u, N)
            for dx, dy in ALL8:
                v = ((y + dy) % N) * N + (x + dx) % N
                if oneWf[v] and v not in seen: seen.add(v); q.append(v)
        out.append((int(t0), seen))
    return out


def frame(Z):
    wet = Z['wet'].astype(bool); h = Z['h'].astype(np.float64); age = Z['age'].astype(np.float64); N = wet.shape[0]
    Qg = Z['Qgross'].astype(np.float64); Cm = Z['Cmean'].astype(np.float64)
    r = dict(t=float(Z['t']))
    lab8, n8 = torus_label(wet, 8); _, n4 = torus_label(wet, 4)
    vol = np.bincount(lab8.ravel(), weights=np.where(wet, h, 0.0).ravel(), minlength=n8 + 1); vol[0] = -np.inf
    big = int(np.argmax(vol)); body = lab8 == big; Vb = float(vol[big]); Vt = float(h[wet].sum())
    r.update(n8=n8, n4=n4, vout=float((Vt - Vb) / max(Vt, 1e-12)), area=int(wet.sum()), body_area=int(body.sum()), Vbody=Vb)
    F = np.zeros((N, N)); CM = np.zeros((N, N)); veins = 0
    for k, d in enumerate(DIRS):
        act = wet & nb(wet, d); q = np.where(act, Qg[k], 0.0); c = np.where(act, Cm[k], 0.0)
        F = np.maximum(F, np.maximum(q, rev(q, d))); CM = np.maximum(CM, np.maximum(c, rev(c, d)))
        veins += int((act & body & nb(body, d) & (Cm[k] > 4.0)).sum())
    r.update(veins=veins, front=int((body & (age < 10)).sum()), cen=[float(v) for v in np.asarray(Z['cen']).ravel()[:2]])
    old20 = body & (age >= 20); Fref = float(np.median(F[old20])) if old20.any() else float('nan'); r['Fref'] = Fref
    e = edt_torus(wet)
    # ---- claim 2: blobs ----
    db = {}; info = {}
    for Mn, M in (('wet', wet), ('h03', wet & (h >= 0.3))):
        eM = edt_torus(M)
        for rr in (2, 3, 4):
            core = M & (eM > rr)
            if core.any():
                region = M & (edt_torus(~core) <= rr) & body
                lb, nb_ = torus_label(region, 8)
                bv = np.bincount(lb.ravel(), weights=np.where(region, h, 0.0).ravel(), minlength=nb_ + 1)[1:]
            else:
                lb = None; bv = np.zeros(0)
            order = np.argsort(bv)[::-1]
            for f in (0.05, 0.10, 0.20):
                bigs = [int(i) + 1 for i in order if bv[i] >= f * Vb]
                key = f'M={Mn}|r={rr}|f={f:.2f}'
                isdb = len(bigs) >= 2; narrow = False; bmin = None; rel = False
                if isdb:
                    rel = bv[bigs[1] - 1] >= 0.25 * bv[bigs[0] - 1]
                    bun = np.isin(lb, bigs); bX = {X: None for X in bigs}
                    for s in NECK_S:
                        if all(v is not None for v in bX.values()): break
                        ll, _ = torus_label((wet & (e >= s - 1e-9)) | bun, 8)
                        LX = {X: int(ll[lb == X].flat[0]) for X in bigs}
                        for X in bigs:
                            if bX[X] is None and any(LX[X] == LX[Y] for Y in bigs if Y != X): bX[X] = float(s)
                    bmin = min(v if v is not None else 1.0 for v in bX.values()); narrow = bmin <= 2.0 + 1e-9
                db[key + '|neck=any'] = bool(isdb); db[key + '|neck=b2'] = bool(narrow)
                if key == 'M=wet|r=3|f=0.10':
                    info = dict(nblob=len(bigs), blob_vol=[round(float(bv[X - 1] / Vb), 4) for X in bigs[:4]], neck=bmin, rel=bool(rel))
    # [CRITERIA_CHANGES 1] report only: big blobs counted over ALL wet pieces (a torn-off lump counts), volume relative to the total volume
    core = wet & (e > 3)
    if core.any():
        reg = wet & (edt_torus(~core) <= 3); lb, nb_ = torus_label(reg, 8)
        bv = np.bincount(lb.ravel(), weights=np.where(reg, h, 0.0).ravel(), minlength=nb_ + 1)[1:]
        nbig = int((bv >= 0.10 * Vt).sum())
    else: nbig = 0
    db['allpieces_r3_f10'] = bool(nbig >= 2)
    pv = np.sort(vol[1:])[::-1] if n8 > 0 else np.zeros(0)
    db['torn10'] = bool(pv.size >= 2 and pv[1] >= 0.10 * Vt)                       # a detached piece holding >= 10% of the volume
    db['bad_db_or_torn10'] = bool(db['M=wet|r=3|f=0.10|neck=any'] or db['torn10'])
    thick = body & (h >= 0.6); lt, nt = torus_label(thick, 8)
    tv = np.bincount(lt.ravel(), weights=np.where(thick, h, 0.0).ravel(), minlength=nt + 1)[1:]
    db['native_h06_f05'] = bool((tv >= 0.05 * Vb).sum() >= 2)
    r['db'] = db; r['blob'] = info
    # ---- claim 3: films ----
    film = {}
    for hf in (0.2, 0.3, 0.4):
        thin = wet & (h < hf)
        for bs in (3, 2):
            ib = in_full_block(thin, bs)
            for a in (20, 40, 80):
                m = body & thin & (age >= a) & ib
                film[f'h={hf}|a={a}|b={bs}'] = int(m.sum())
                if hf == 0.3 and a == 40 and bs == 3: film['primary_novein'] = int((m & (CM <= 4.0)).sum())
    r['film'] = film
    # ---- dead threads ----
    dead = {}
    for ls in (3, 2):
        line = body & ~in_full_block(wet, ls)
        ll, nl = torus_label(line, 8); sz = np.bincount(ll.ravel(), minlength=nl + 1); sz[0] = 0
        csz = sz[ll]
        for crit, m0 in (('F0.03', F < 0.03 * Fref), ('F0.1', F < 0.1 * Fref), ('F0.3', F < 0.3 * Fref), ('C0.5', CM < 0.5), ('C1', CM < 1.0), ('C2', CM < 2.0)):
            for smin in (2, 4, 8):
                dead[f'line={ls}|{crit}|smin={smin}'] = int((line & (csz >= smin) & (age >= 20) & m0).sum())
    r['dead'] = dead
    # ---- tip lines ----
    tl = tip_lines(wet, body); tip = {}
    for L in (1, 3, 6):
        sel = [s for _, s in tl if len(s) >= L]
        tip[f'L={L}|cells'] = len(set().union(*sel)) if sel else 0
        tip[f'L={L}|lines'] = len(sel)
    tip['maxlen'] = max((len(s) for _, s in tl), default=0)
    r['tip'] = tip
    return r


def run_dir(rd):
    name = os.path.basename(rd.rstrip('/'))
    fs = sorted(glob.glob(os.path.join(rd, 'vs_t*.npz')), key=lambda f: int(re.findall(r'vs_t(\d+)', f)[0]))
    res = []
    for f in fs:
        Z = np.load(f); res.append(frame(Z))
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(run=name, frames=res), open(os.path.join(OUT, name + '.json'), 'w'))
    return name, len(res)


if __name__ == '__main__':
    for rd in sys.argv[1:]:
        print(*run_dir(rd), flush=True)
