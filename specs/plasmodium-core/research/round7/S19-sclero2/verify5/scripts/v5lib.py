"""verify5 측정 도구 (독립 검증자가 직접 쓴 것). 모델 코드는 import 하지 않는다.

격자는 토러스(주기 경계)이고, 이어짐은 모두 8-이웃으로 본다(모델의 몸 이어짐과 같은 뜻).
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import ConvexHull

S8 = np.ones((3, 3), bool)                                   # 8-이웃 / 3x3 정사각
_yy, _xx = np.mgrid[-2:3, -2:3]
D2 = (_xx ** 2 + _yy ** 2) <= 5                              # 반지름 약 2 의 원판 (21셀, 폭 5)
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]                     # 모델의 간선 채널 k: 셀 (y,x) 에서 (y+dy, x+dx) 로
ALL8 = [(1, 0), (0, 1), (1, 1), (1, -1), (-1, 0), (0, -1), (-1, -1), (-1, 1)]

# ---- 미리 정한 문턱 (CRITERIA.md 와 같다) ----
DEBRIS_FRAC = 0.05      # 주장 1: 몸 전체 부피의 5% 미만인 떨어진 조각 = 부스러기
BODY_FRAC = 0.05        # 몸으로 셈하는 조각의 최소 부피 몫
THICK_REL = 0.5         # 굵은 셀: h >= THICK_REL * (그 몸의 부피 가중 평균 두께)
LUMP_FRAC = 0.10        # 덩이: 굵은 셀을 원판 D2 로 열기(opening)한 뒤 남은 8-이음 조각 중 몸 부피의 10% 이상
FILM_H = 0.35           # 주장 3: 얇은 막 = 폭 3 이상(3x3 열기에 남음), 나이 >= 20, h < 0.35
OLD_AGE = 20.0          # 죽은 구조로 셀 셀의 최소 나이 (흐름 창 20 과 같다)
DEAD_REL = 0.05         # 흐름 없음: 셀의 최대 간선 총흐름(Qgross) < 0.05 x (나이 >= 20 인 젖은 셀의 Qgross 90백분위)
SCL = dict(lump1=1, lumpfrac=0.80, ar=0.60, solidity=0.85, kappa=0.85, tail=0.05)   # 균핵 판정 문턱


def roll_nb(a, d):
    """a 를 (x+dx, y+dy) 에서 읽은 값"""
    return np.roll(a, (-d[1], -d[0]), (0, 1))


def roll_back(a, d):
    """간선 배열에서, -d 쪽 이웃이 이 셀로 보내는 간선"""
    return np.roll(a, (d[1], d[0]), (0, 1))


def mimg(v, N):
    return (v + N / 2.0) % N - N / 2.0


def tlabel(mask):
    """토러스 위 8-이음 라벨. (lab, n), 라벨은 1..n"""
    mask = np.asarray(mask, bool)
    N0, N1 = mask.shape
    lab, n = ndi.label(mask, structure=S8)
    if n == 0:
        return lab, 0
    parent = np.arange(n + 1)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    pairs = []
    for d in (-1, 0, 1):
        a = lab[:, N1 - 1]; b = lab[(np.arange(N0) + d) % N0, 0]; m = (a > 0) & (b > 0); pairs.append(np.stack([a[m], b[m]], 1))
        a = lab[N0 - 1, :]; b = lab[0, (np.arange(N1) + d) % N1]; m = (a > 0) & (b > 0); pairs.append(np.stack([a[m], b[m]], 1))
    for a, b in np.concatenate(pairs, 0):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[rb] = ra
    root = np.array([find(k) for k in range(n + 1)])
    u, comp = np.unique(root, return_inverse=True)          # root 0 -> 0 (배경은 자기 자신이 뿌리이고 가장 작다)
    return comp[lab].astype(np.int32), int(u.size - 1)


def topen(mask, se):
    """토러스 위 이진 열기(침식 뒤 팽창)"""
    p = se.shape[0] + 1
    m = np.pad(np.asarray(mask, bool), p, mode='wrap')
    o = ndi.binary_opening(m, structure=se)
    return o[p:-p, p:-p]


def dilate8(mask):
    out = mask.copy()
    for d in ALL8:
        out |= roll_nb(mask, d)
    return out


def n8(mask):
    c = np.zeros(mask.shape, np.int16)
    for d in ALL8:
        c += roll_nb(mask, d)
    return c


def node_flux(Qg):
    """셀에 닿은 8 간선의 총흐름(창 평균 |Q|) 중 최댓값"""
    F = np.zeros(Qg.shape[1:], np.float64)
    for k, d in enumerate(DIRS):
        F = np.maximum(F, Qg[k]); F = np.maximum(F, roll_back(Qg[k], d))
    return F


def skeleton_endpoints(mask):
    from skimage.morphology import skeletonize
    p = 12
    m = np.pad(np.asarray(mask, bool), p, mode='wrap')
    sk = skeletonize(m)[p:-p, p:-p]
    return sk & (n8(sk) == 1), sk


def geom(B, h, N):
    """몸 하나(마스크 B)의 모양 수치. 토러스는 원형 평균 중심에서 최소 이미지로 편다."""
    ys, xs = np.nonzero(B)
    A = int(ys.size)
    if A < 3:
        return dict(area=A, ar=None, solidity=None, kappa_area=None, kappa_vol=None, cx=None, cy=None)
    ang = 2 * np.pi / N
    cx = (np.arctan2(np.sin(xs * ang).mean(), np.cos(xs * ang).mean()) / ang) % N
    cy = (np.arctan2(np.sin(ys * ang).mean(), np.cos(ys * ang).mean()) / ang) % N
    dx = mimg(xs - cx, N); dy = mimg(ys - cy, N)
    mx, my = dx.mean(), dy.mean(); dx = dx - mx; dy = dy - my
    cx = (cx + mx) % N; cy = (cy + my) % N
    Req = np.sqrt(A / np.pi); rg_disc = Req / np.sqrt(2.0)
    rg_a = np.sqrt((dx ** 2 + dy ** 2).mean() + 1.0 / 6.0)
    w = np.maximum(h[ys, xs].astype(np.float64), 0.0)
    if w.sum() > 0:
        wx = (w * dx).sum() / w.sum(); wy = (w * dy).sum() / w.sum()
        rg_v = np.sqrt((w * ((dx - wx) ** 2 + (dy - wy) ** 2)).sum() / w.sum() + 1.0 / 6.0)
    else:
        rg_v = np.nan
    cxx = (dx * dx).mean() + 1 / 12.0; cyy = (dy * dy).mean() + 1 / 12.0; cxy = (dx * dy).mean()
    ev = np.linalg.eigvalsh(np.array([[cxx, cxy], [cxy, cyy]]))
    ar = float(np.sqrt(max(ev[0], 0) / max(ev[1], 1e-12)))
    pts = np.unique(np.concatenate([np.stack([dx + sx, dy + sy], 1) for sx in (-0.5, 0.5) for sy in (-0.5, 0.5)]).round(3), axis=0)
    try:
        hull = ConvexHull(pts).volume
        sol = float(A / hull)
    except Exception:
        sol = None
    return dict(area=A, ar=round(ar, 4), solidity=None if sol is None else round(sol, 4), kappa_area=round(float(rg_disc / rg_a), 4),
                kappa_vol=None if not np.isfinite(rg_v) else round(float(rg_disc / rg_v), 4), cx=round(float(cx), 2), cy=round(float(cy), 2))


def is_scl(b):
    """균핵 판정: 한 덩어리 + 둥근 + 촘촘 + 꼬리 없음 (문턱은 SCL)"""
    if b.get('ar') is None or b.get('solidity') is None:
        return False
    return (b['n_lumps'] == SCL['lump1'] and b['lump_frac'] >= SCL['lumpfrac'] and b['ar'] >= SCL['ar'] and b['solidity'] >= SCL['solidity']
            and b['kappa_area'] >= SCL['kappa'] and b['tail'] <= SCL['tail'])


def bodies_and_lumps(wet, h, N, thick_rel=THICK_REL, lump_frac=LUMP_FRAC, with_geom=True):
    """조각(8-이음) 라벨, 조각 부피 몫, 몸(>=BODY_FRAC)마다 덩이 수·아령·모양"""
    hp = np.where(wet, np.maximum(h, 0.0), 0.0).astype(np.float64)
    lab, n = tlabel(wet)
    Vt = float(hp.sum())
    vol = np.bincount(lab.ravel(), weights=hp.ravel(), minlength=n + 1)
    area = np.bincount(lab.ravel(), minlength=n + 1)
    share = vol / max(Vt, 1e-300)
    pieces = [dict(id=k, share=float(share[k]), area=int(area[k])) for k in range(1, n + 1)]
    bodies_id = [k for k in range(1, n + 1) if share[k] >= BODY_FRAC]
    # 굵은 셀 (몸마다 문턱)
    h2 = np.bincount(lab.ravel(), weights=(hp ** 2).ravel(), minlength=n + 1)
    hv = h2 / np.maximum(vol, 1e-300)                         # 부피 가중 평균 두께
    thick = wet & (hp >= thick_rel * hv[lab]) & (lab > 0)
    ot = topen(thick, D2)
    ll, nl = tlabel(ot)
    lvol = np.bincount(ll.ravel(), weights=hp.ravel(), minlength=nl + 1)
    lbody = np.zeros(nl + 1, np.int64)
    if nl:
        fl = ll.ravel(); lbody[fl[fl > 0]] = lab.ravel()[fl > 0]
    wide = topen(wet, D2)
    lw, _ = tlabel(wide)
    lwide = np.zeros(nl + 1, np.int64)
    if nl:
        fl = ll.ravel(); lwide[fl[fl > 0]] = lw.ravel()[fl > 0]
    out = []
    for b in bodies_id:
        Vb = float(vol[b])
        ls = [k for k in range(1, nl + 1) if lbody[k] == b]
        big = [k for k in ls if lvol[k] >= lump_frac * Vb]
        mf = max([lvol[k] for k in ls], default=0.0) / max(Vb, 1e-300)
        dumb = len(big) >= 2 and len(set(int(lwide[k]) for k in big)) >= 2
        B = lab == b
        tail = float((B & ~wide).sum()) / max(int(area[b]), 1)
        rec = dict(id=int(b), share=round(float(share[b]), 5), vol=round(Vb, 3), area=int(area[b]), hv=round(float(hv[b]), 4), n_lumps=len(big),
                   lump_frac=round(float(mf), 4), lump_shares=sorted([round(float(lvol[k] / Vb), 4) for k in big], reverse=True), dumbbell=bool(dumb), tail=round(tail, 4))
        if with_geom:
            rec.update(geom(B, hp, N))
            rec['scl'] = bool(is_scl(rec))
        out.append(rec)
    return lab, pieces, out


def dead_structures(wet, h, age, Qg, film_h=FILM_H, dead_rel=DEAD_REL):
    """주장 3: 얇은 막, 흐름 없는 실, 흐름 없는 가지 끝"""
    nw = int(wet.sum())
    if nw == 0:
        return dict(film=0, deadthread=0, deadtips=0, thread=0, wet=0)
    w3 = topen(wet, S8)
    thread = wet & ~w3
    old = wet & (age >= OLD_AGE)
    F = node_flux(Qg.astype(np.float64))
    scale = float(np.percentile(F[old], 90)) if old.any() else 0.0
    res = dict(wet=nw, thread=int(thread.sum()), old=int(old.sum()), flux_p90=scale)
    ep, sk = skeleton_endpoints(wet)
    for fh in (0.25, 0.35, 0.5):
        res[f'film_{fh}'] = int((w3 & old & (h < fh)).sum())
    for dr in (0.02, 0.05, 0.10):
        dead = F < dr * scale
        res[f'deadthread_{dr}'] = int((thread & old & dead).sum())
        res[f'deadtips_{dr}'] = int((ep & thread & old & dead).sum())
    res['film'] = res[f'film_{film_h}']; res['deadthread'] = res[f'deadthread_{dead_rel}']; res['deadtips'] = res[f'deadtips_{dead_rel}']
    res['tips_all'] = int((ep & thread).sum())
    return res
