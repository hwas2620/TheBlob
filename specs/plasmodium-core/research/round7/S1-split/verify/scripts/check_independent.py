#!/usr/bin/env python3
"""[검증 2 — 이어받은 검증자] extra_metrics.py 의 값(out, out_strip, 최소 절단 cutQ, 병목 bnC, carry)을
vmet 도 extra_metrics 도 쓰지 않고 networkx 로 다시 계산해 견준다. 정수 최대 유량(1e4/p10 척도, 2e6 천장) 대신 실수 용량을 쓴다.

usage: check_independent.py RUN_DIR T [T ...]
"""
import json, os, sys
import numpy as np
import networkx as nx

DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]          # (dx, dy): 채널 k 의 간선은 (y, x) → (y+dy, x+dx)
LS = [1.0, 1.0, 2 ** 0.5, 2 ** 0.5]


def load(rd, t):
    Z = np.load(os.path.join(rd, 'vs_t%04d.npz' % int(t))); P = json.load(open(os.path.join(rd, 'params.json')))
    return {k: Z[k] for k in Z.files}, P


def graph(wet, C, Qg, N):
    G = nx.Graph(); ys, xs = np.nonzero(wet)
    G.add_nodes_from((int(y) * N + int(x)) for y, x in zip(ys, xs))
    for k, (dx, dy) in enumerate(DIRS):
        for y, x in zip(ys, xs):
            y2 = (y + dy) % N; x2 = (x + dx) % N
            if wet[y2, x2]:
                G.add_edge(int(y) * N + int(x), int(y2) * N + int(x2), C=float(C[k, y, x]), Q=float(Qg[k, y, x]))
    return G


def comps_by_vol(G, h, N):
    cs = [(sum(float(h.flat[n]) for n in c), c) for c in nx.connected_components(G)]
    cs.sort(key=lambda v: -v[0]); return cs


def main():
    rd = sys.argv[1]; e = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'summaries', 'extra_' + os.path.basename(rd.rstrip('/')) + '.json')))
    rec = {round(q['t']): q for q in e['cuts']}; sr = e['series']
    for t in sys.argv[2:]:
        S, P = load(rd, t); N = P['N']
        wet = S['wet'].astype(bool); h = S['h'].astype(float); C = S['C'].astype(float); age = S['age'].astype(float); Qg = S['Qgross'].astype(float)
        Cn = np.zeros((N, N))
        for k, (dx, dy) in enumerate(DIRS):
            Cn = np.maximum(Cn, C[k]); Cn = np.maximum(Cn, np.roll(C[k], (dy, dx), (0, 1)))      # 들어오는 간선: (y-dy, x-dx) 의 채널 k
        thin = wet & (h < P['h_min']) & (age > P['grace']); mem = thin & (Cn < P['bridge_break'])
        G = graph(wet, C, Qg, N); cs = comps_by_vol(G, h, N); tot = float(h[wet].sum())
        out = 1 - cs[0][0] / tot
        wet2 = wet & ~mem; G2 = G.subgraph([n for n in G.nodes if not mem.flat[n]]).copy(); cs2 = comps_by_vol(G2, h, N); tot2 = sum(v for v, _ in cs2)
        out_s = 1 - cs2[0][0] / tot2
        i = int(round(float(t)) / 20); j = [k for k, tt in enumerate(sr['t']) if round(tt) == round(float(t))][0]
        line = f"t={t}: out {out:.4f} (extra {sr['out'][j]:.4f}) out_strip {out_s:.4f} (extra {sr['out_strip'][j]:.4f}) thin {int(thin.sum())} ({sr['thin'][j]}) memonly {int(mem.sum())} ({sr['memonly'][j]})"
        if len(cs2) > 1:
            A, B = cs2[0][1], cs2[1][1]; VB = cs2[1][0]
            H = nx.DiGraph()
            for u, v, d in G.edges(data=True):
                H.add_edge(u, v, capacity=d['Q']); H.add_edge(v, u, capacity=d['Q'])
            for a in A: H.add_edge('s', a)          # 용량 없음 = 무한
            for b in B: H.add_edge(b, 't')
            cut, _ = nx.minimum_cut(H, 's', 't')
            # 병목: 간선을 C 가 큰 순서로 더해 A 와 B 가 처음 이어지는 C (최대-최소 경로)
            uf = nx.utils.UnionFind(); ea = sorted(G.edges(data=True), key=lambda z: -z[2]['C']); a0 = next(iter(A)); b0 = next(iter(B)); bn = 0.0
            for a in A: uf.union(a0, a)
            for b in B: uf.union(b0, b)
            for u, v, d in ea:
                uf.union(u, v)
                if uf[a0] == uf[b0]: bn = d['C']; break
            q = rec.get(round(float(t)), {})
            carry = cut * P['period'] / VB
            line += f" | cutQ {cut:.3g} (extra {q.get('cutQ', float('nan')):.3g}) bnC {bn:.3g} (extra {q.get('bnC', float('nan')):.3g}) V_B {VB:.1f} ({q.get('lobeB_vol', float('nan')):.1f}) carry {carry:.2e} ({q.get('carry', float('nan')):.2e})"
            # 견줌: 같은 몸의 정맥(C>4) 간선 하나의 Qgross 중앙으로 잰 carry
            qv = [d['Q'] for _, _, d in G.edges(data=True) if d['C'] > 4]
            if qv: line += f" | 정맥 간선 하나(중앙 Qgross {np.median(qv):.3g})라면 carry {np.median(qv) * P['period'] / VB:.1e}"
        print(line, flush=True)


if __name__ == '__main__':
    main()
