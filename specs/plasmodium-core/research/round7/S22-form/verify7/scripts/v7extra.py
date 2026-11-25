"""verify7 보충 측정 (실행이 시작된 뒤 추가. CRITERIA_CHANGES.md 1절).

등록한 주장 6 의 '외가닥다움'(넓이/길이 <= 4)은 몸 뒤 관 그물(구멍이 많은 그물)도 외가닥으로 셌다.
여기서는 큰 속이 아닌 셀의 골격(skeleton)을 갈림 없는 사슬로 끊어, 사슬 하나 = 외가닥 하나로 잰다.
  - 골격: skimage.skeletonize (토러스: 둘레 24 칸을 감아 붙여 계산하고 가운데만 쓴다)
  - 잔가지 다듬기: 자유 끝에서 갈림까지 30 칸 미만인 가지는 지운다(4 번 되풀이)
  - 사슬 = 차수 2 셀만 지나는 길. 끝 = 갈림(차수 >= 3), 자유 끝(차수 1), 또는 큰 속에 닿은 골격 셀(닻)
  - 사슬 길이 = 걸음 길이 합(1, sqrt2) + 1
  - 종류: 양 끝이 서로 다른 큰 속의 닻 = trunk(굵은 부분끼리 잇는 관), 한 끝이 자유 끝 = tail, 나머지 = link(다리·고리·그물 안 줄기)
"""
import numpy as np
from skimage.morphology import skeletonize
import v7lib as L

PADS = 24
SPUR = 30          # 자유 끝에서 갈림까지 30 칸 미만인 잔가지를 지운다 (그물 끝의 짧은 가지가 긴 실을 끊지 않게)


def _skel_torus(mask):
    N0, N1 = mask.shape
    P = np.pad(mask, PADS, mode='wrap')
    S = skeletonize(P)
    return S[PADS:-PADS, PADS:-PADS]


def _deg(S):
    d = np.zeros(S.shape, np.int16)
    for v in L.ALL8:
        d += L.nb(S, v)
    return np.where(S, d, 0)


def chains(wet, core_lab):
    """core_lab: 큰 속 번호(0 = 아님). 돌려줌: [dict(L, kind, ends)]"""
    N0, N1 = wet.shape
    core = core_lab > 0
    rest = wet & ~core
    if not rest.any():
        return []
    S = _skel_torus(rest) & rest
    near = np.zeros(wet.shape, np.int64)
    for v in L.ALL8:
        near = np.maximum(near, L.nb(core_lab, v))
    anchor = S & (near > 0)
    # 잔가지 다듬기
    for _ in range(4):
        dg = _deg(S)
        ends = np.argwhere(S & (dg == 1) & ~anchor)
        removed = False
        for y, x in ends:
            path = [(y, x)]; py, px = -1, -1; cy, cx = y, x; ok = False
            while True:
                nbrs = [((cy + dy) % N0, (cx + dx) % N1) for dx, dy in L.ALL8 if S[(cy + dy) % N0, (cx + dx) % N1] and ((cy + dy) % N0, (cx + dx) % N1) != (py, px)]
                if len(nbrs) != 1:
                    ok = len(nbrs) >= 2; break
                ny, nx = nbrs[0]
                if _deg_at(S, ny, nx) >= 3 or anchor[ny, nx]:
                    ok = not anchor[ny, nx]; break
                py, px, cy, cx = cy, cx, ny, nx; path.append((cy, cx))
                if len(path) >= SPUR: break
            if ok and len(path) < SPUR:
                for a, b in path: S[a, b] = False
                removed = True
        if not removed:
            break
    dg = _deg(S)
    special = S & ((dg != 2) | anchor)
    seen = set(); out = []; cov = np.zeros(S.shape, bool)
    sp = np.argwhere(special)
    for y, x in sp:
        for dx, dy in L.ALL8:
            ny, nx = (y + dy) % N0, (x + dx) % N1
            if not S[ny, nx] or ((y, x), (ny, nx)) in seen:
                continue
            length = np.hypot(dx, dy); path = [(y, x), (ny, nx)]; seen.add(((y, x), (ny, nx)))
            py, px, cy, cx = y, x, ny, nx
            while not special[cy, cx]:
                nbrs = [((cy + ddy) % N0, (cx + ddx) % N1, ddx, ddy) for ddx, ddy in L.ALL8 if S[(cy + ddy) % N0, (cx + ddx) % N1] and ((cy + ddy) % N0, (cx + ddx) % N1) != (py, px)
                        and ((cy + ddy) % N0, (cx + ddx) % N1) not in path[-3:]]
                if not nbrs: break
                ny2, nx2, ddx, ddy = nbrs[0]
                length += np.hypot(ddx, ddy); py, px, cy, cx = cy, cx, ny2, nx2; path.append((cy, cx))
                if len(path) > 4 * N0: break
            seen.add(((cy, cx), (py, px)))
            for a_, b_ in path: cov[a_, b_] = True
            def endtype(a, b):
                if anchor[a, b]: return ('core', int(near[a, b]))
                if dg[a, b] == 1: return ('free', 0)
                if dg[a, b] >= 3: return ('junction', 0)
                return ('open', 0)
            e1 = endtype(y, x); e2 = endtype(cy, cx)
            if e1[0] == 'core' and e2[0] == 'core' and e1[1] != e2[1]:
                kind = 'trunk'
            elif 'free' in (e1[0], e2[0]):
                kind = 'tail'
            else:
                kind = 'link'
            out.append(dict(L=float(length + 1), kind=kind, ends=[e1[0], e2[0]]))
    # 특수 셀이 없는 닫힌 고리(차수 2 뿐)
    rem = S & ~special
    if rem.any():
        left = rem & ~cov
        if left.any():
            ll, ln = L.torus_label(left)
            for k in range(1, ln + 1):
                out.append(dict(L=float((ll == k).sum()), kind='link', ends=['ring', 'ring']))
    return out


def _deg_at(S, y, x):
    N0, N1 = S.shape
    return sum(bool(S[(y + dy) % N0, (x + dx) % N1]) for dx, dy in L.ALL8)


def frame_chains(wet, h):
    wet = np.asarray(wet, bool); hp = np.where(wet, np.maximum(h, 0), 0.0); Vtot = hp.sum()
    o = L.open3(wet); ol, on = L.torus_label(o)
    oa = np.bincount(ol.ravel(), minlength=on + 1); ov = np.bincount(ol.ravel(), weights=np.where(o, hp, 0).ravel(), minlength=on + 1)
    bigc = (oa >= L.CORE_AREA) & (ov >= L.CORE_VOL * Vtot); bigc[0] = False
    core_lab = np.where(bigc[ol], ol, 0)
    ch = chains(wet, core_lab)
    nt = [c['L'] for c in ch if c['kind'] != 'trunk']
    return dict(chain_max=float(max(nt, default=0.0)), chain_tail_max=float(max([c['L'] for c in ch if c['kind'] == 'tail'], default=0.0)),
                chain_trunk_max=float(max([c['L'] for c in ch if c['kind'] == 'trunk'], default=0.0)),
                n_chain100=int(sum(L_ > 100 for L_ in nt)), n_tail30c=int(sum(c['L'] >= 30 for c in ch if c['kind'] == 'tail')),
                chain100_kinds=sorted(set(c['kind'] for c in ch if c['kind'] != 'trunk' and c['L'] > 100)))


# ---------------------------------------------------------------- 나무꼴 외가닥 (그물 고리를 뺀 골격)
MESH_CYC = 8      # 골격 그래프의 이중연결 성분 가운데 셀 9 개 이상 = 그물 고리 -> 그 간선을 뺀다 (8 이하는 갈림 자리의 작은 세모)


def tree_strands(wet, core_lab):
    """큰 속이 아닌 셀의 골격에서 그물 고리(큰 이중연결 성분)를 빼고 남은 나무꼴 부분마다 가장 긴 길(측지 지름).
    돌려줌: [dict(L, ncore)] ncore = 그 부분이 닿은 큰 속의 수 (2 이상 = 굵은 부분끼리 잇는 관)"""
    import networkx as nx
    N0, N1 = wet.shape
    core = core_lab > 0
    rest = wet & ~core
    if not rest.any():
        return []
    S = _skel_torus(rest) & rest
    near = np.zeros(wet.shape, np.int64)
    for v in L.ALL8:
        near = np.maximum(near, L.nb(core_lab, v))
    ys, xs = np.nonzero(S); idx = ys * N1 + xs
    G = nx.Graph(); G.add_nodes_from(idx.tolist())
    sset = set(idx.tolist())
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        nb_ = ((ys + dy) % N0) * N1 + (xs + dx) % N1
        for a, b in zip(idx.tolist(), nb_.tolist()):
            if b in sset: G.add_edge(a, b, weight=float(np.hypot(dx, dy)))
    rm = []
    for comp in nx.biconnected_component_edges(G):
        nodes = set(u for e in comp for u in e)
        if len(nodes) > MESH_CYC: rm += comp
    G.remove_edges_from(rm)
    out = []
    for cc in nx.connected_components(G):
        if len(cc) < 2: continue
        H = G.subgraph(cc); s0 = next(iter(cc))
        d0 = nx.single_source_dijkstra_path_length(H, s0); u = max(d0, key=d0.get)
        d1 = nx.single_source_dijkstra_path_length(H, u); v = max(d1, key=d1.get)
        cores = set(int(near.ravel()[c]) for c in cc if near.ravel()[c] > 0)
        free = any(H.degree(c) == 1 and near.ravel()[c] == 0 for c in cc)
        out.append(dict(L=float(d1[v] + 1), ncore=len(cores), free=bool(free)))
    return out


def frame_trees(wet, h):
    wet = np.asarray(wet, bool); hp = np.where(wet, np.maximum(h, 0), 0.0); Vtot = hp.sum()
    o = L.open3(wet); ol, on = L.torus_label(o)
    oa = np.bincount(ol.ravel(), minlength=on + 1); ov = np.bincount(ol.ravel(), weights=np.where(o, hp, 0).ravel(), minlength=on + 1)
    bigc = (oa >= L.CORE_AREA) & (ov >= L.CORE_VOL * Vtot); bigc[0] = False
    core_lab = np.where(bigc[ol], ol, 0)
    tr = tree_strands(wet, core_lab)
    nt = [t['L'] for t in tr if t['ncore'] <= 1]
    tails = [t['L'] for t in tr if t['ncore'] == 1 and t['free']]
    # 몸에서의 거리: 큰 속을 가진 몸의 젖은 셀 가운데 큰 속에서 가장 먼 셀까지의 유클리드(토러스) 거리
    reach = 0.0
    if (core_lab > 0).any():
        lab, n = L.torus_label(wet)
        cb = np.unique(lab[core_lab > 0])
        dist = L.edt_torus(~(core_lab > 0), pad=wet.shape[0])
        m = wet & np.isin(lab, cb) & (core_lab == 0)
        if m.any(): reach = float(dist[m].max())
    return dict(tree_max=float(max(nt, default=0.0)), n_tree100=int(sum(x > 100 for x in nt)), n_tree30=int(sum(x >= 30 for x in nt)),
                tree_tail_max=float(max(tails, default=0.0)), n_tree_tail30=int(sum(x >= 30 for x in tails)), reach=reach,
                tree_trunk_max=float(max([t['L'] for t in tr if t['ncore'] >= 2], default=0.0)))
