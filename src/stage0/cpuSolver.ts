// CPU 기준 풀이 — 젖은 셀 위의 9점 연산자를 float64 켤레기울기로 푼다
//
//   M_i·p_i + Σ_e W_e·(p_i − p_j) = S_i
//
// spec 의 "CPU 직접 풀이" 자리에 쓴다. 상대 잔차 1e-10 까지 풀므로 직접 분해와 같은 해를 준다
// (numpy 직접 풀이와 같다는 것은 A0 의 기준 자료에서 확인한다).

/** 간선 방향 E, N, NE, SE 의 (dx, dy) */
const DX = [1, 0, 1, 1];
const DY = [0, 1, 1, -1];

export interface CgResult {
  p: Float64Array;
  iters: number;
  relres: number;
  active: number;
}

/**
 * @param W4  간선 가중치, RGBA 로 끼워 넣은 N·N·4
 * @param M   차폐 항 (0 이면 비활성 셀)
 * @param rhs 우변
 */
export function solveCG(N: number, W4: ArrayLike<number>, M: ArrayLike<number>, rhs: ArrayLike<number>, tol = 1e-10, maxIter = 50000): CgResult {
  const n = N * N;
  // 활성 셀에 번호를 매기고 이웃 여덟 개의 번호와 가중치를 펼쳐 둔다
  const idx = new Int32Array(n).fill(-1);
  let m = 0;
  for (let i = 0; i < n; i++) if (M[i] > 0) idx[i] = m++;
  const nb = new Int32Array(m * 8).fill(-1);
  const wt = new Float64Array(m * 8);
  const diag = new Float64Array(m);
  const b = new Float64Array(m);
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const i = y * N + x;
      const a = idx[i];
      if (a < 0) continue;
      let d = M[i];
      for (let k = 0; k < 4; k++) {
        // 나가는 간선 k
        const jx = (x + DX[k] + N) % N;
        const jy = (y + DY[k] + N) % N;
        const j = jy * N + jx;
        const w = W4[i * 4 + k];
        if (w > 0 && idx[j] >= 0) {
          nb[a * 8 + k] = idx[j];
          wt[a * 8 + k] = w;
          d += w;
        }
        // 들어오는 간선 k (이웃 i − d_k 가 갖고 있다)
        const hx = (x - DX[k] + N) % N;
        const hy = (y - DY[k] + N) % N;
        const hI = hy * N + hx;
        const w2 = W4[hI * 4 + k];
        if (w2 > 0 && idx[hI] >= 0) {
          nb[a * 8 + 4 + k] = idx[hI];
          wt[a * 8 + 4 + k] = w2;
          d += w2;
        }
      }
      diag[a] = d;
      b[a] = rhs[i];
    }
  }
  const apply = (v: Float64Array, out: Float64Array): void => {
    for (let a = 0; a < m; a++) {
      let s = diag[a] * v[a];
      const o = a * 8;
      for (let q = 0; q < 8; q++) {
        const j = nb[o + q];
        if (j >= 0) s -= wt[o + q] * v[j];
      }
      out[a] = s;
    }
  };
  // Jacobi 선조건 켤레기울기
  const x = new Float64Array(m);
  const r = Float64Array.from(b);
  const z = new Float64Array(m);
  const pv = new Float64Array(m);
  const Ap = new Float64Array(m);
  let bnorm = 0;
  for (let a = 0; a < m; a++) bnorm += b[a] * b[a];
  bnorm = Math.sqrt(bnorm);
  let rz = 0;
  for (let a = 0; a < m; a++) {
    z[a] = r[a] / diag[a];
    pv[a] = z[a];
    rz += r[a] * z[a];
  }
  let iters = 0;
  let relres = bnorm > 0 ? 1 : 0;
  while (iters < maxIter && relres > tol) {
    apply(pv, Ap);
    let pAp = 0;
    for (let a = 0; a < m; a++) pAp += pv[a] * Ap[a];
    const alpha = rz / pAp;
    let rr = 0;
    for (let a = 0; a < m; a++) {
      x[a] += alpha * pv[a];
      r[a] -= alpha * Ap[a];
      rr += r[a] * r[a];
    }
    relres = Math.sqrt(rr) / bnorm;
    let rzNew = 0;
    for (let a = 0; a < m; a++) {
      z[a] = r[a] / diag[a];
      rzNew += r[a] * z[a];
    }
    const beta = rzNew / rz;
    rz = rzNew;
    for (let a = 0; a < m; a++) pv[a] = z[a] + beta * pv[a];
    iters++;
  }
  const p = new Float64Array(n);
  for (let i = 0; i < n; i++) if (idx[i] >= 0) p[i] = x[idx[i]];
  return { p, iters, relres, active: m };
}

/** 유량 오차 ‖Q(pa) − Q(pe)‖ / ‖Q(pe)‖,  Q_e = W_e·(p_i − p_j) */
export function fluxError(N: number, W4: ArrayLike<number>, pa: ArrayLike<number>, pe: ArrayLike<number>): number {
  let num = 0;
  let den = 0;
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const i = y * N + x;
      for (let k = 0; k < 4; k++) {
        const w = W4[i * 4 + k];
        if (w === 0) continue;
        const j = ((y + DY[k] + N) % N) * N + ((x + DX[k] + N) % N);
        const qa = w * (pa[i] - pa[j]);
        const qe = w * (pe[i] - pe[j]);
        num += (qa - qe) * (qa - qe);
        den += qe * qe;
      }
    }
  }
  return Math.sqrt(num / Math.max(den, 1e-300));
}

/** 상대 차이 ‖a − b‖ / ‖b‖ */
export function relDiff(a: ArrayLike<number>, b: ArrayLike<number>): number {
  let num = 0;
  let den = 0;
  for (let i = 0; i < b.length; i++) {
    num += (a[i] - b[i]) * (a[i] - b[i]);
    den += b[i] * b[i];
  }
  return Math.sqrt(num / Math.max(den, 1e-300));
}
