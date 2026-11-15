// 정적 잡음장 — numpy 기준 모델(specs/plasmodium-core/stage0/ref/ref_model.py)과 같은 정수 해시 난수
// 두 쪽이 같은 시드에서 같은 장을 만들기 때문에 잡음 파일을 주고받지 않아도 초기 조건이 같다.

function lowbias32(x: number): number {
  x >>>= 0;
  x ^= x >>> 16;
  x = Math.imul(x, 0x7feb352d) >>> 0;
  x ^= x >>> 15;
  x = Math.imul(x, 0x846ca68b) >>> 0;
  x ^= x >>> 16;
  return x >>> 0;
}

/** (0,1) 균등 난수 n개. u_i = (lowbias32(lowbias32(i ^ k1) + k2) + 0.5) / 2^32 */
export function hashU01(seed: number, stream: number, n: number): Float64Array {
  const k1 = lowbias32((seed + 0x9e3779b9) >>> 0);
  const k2 = lowbias32((Math.imul(stream, 0x85ebca6b) + 0xc2b2ae35) >>> 0);
  const out = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const x = lowbias32((lowbias32((i ^ k1) >>> 0) + k2) >>> 0);
    out[i] = (x + 0.5) / 4294967296;
  }
  return out;
}

/** 표준 정규 난수 n개 (Box–Muller, 부분 흐름 2·stream 과 2·stream+1) */
export function hashNormal(seed: number, stream: number, n: number): Float64Array {
  const u1 = hashU01(seed, 2 * stream, n);
  const u2 = hashU01(seed, 2 * stream + 1, n);
  const out = new Float64Array(n);
  for (let i = 0; i < n; i++) out[i] = Math.sqrt(-2 * Math.log(u1[i])) * Math.cos(2 * Math.PI * u2[i]);
  return out;
}

export interface NoiseFields {
  /** 간선 잡음 G (E, N, NE, SE) — RGBA 로 끼워 넣은 배열 */
  G: Float32Array;
  /** 새 간선의 전도도 (E, N, NE, SE) — RGBA */
  Cinit: Float32Array;
  /** 항복 잡음 η — 셀당 1개 */
  eta: Float32Array;
}

/** 흐름 번호: G 는 0~3(정규), 새 간선 전도도는 100~103(균등), η 는 8(정규). 색인은 y·N + x */
export function noiseFields(seed: number, N: number, edgeSigma: number, d0: number, d0Noise: number): NoiseFields {
  const n = N * N;
  const G = new Float32Array(n * 4);
  const Cinit = new Float32Array(n * 4);
  for (let k = 0; k < 4; k++) {
    const z = hashNormal(seed, k, n);
    const u = hashU01(seed, 100 + k, n);
    for (let i = 0; i < n; i++) {
      G[i * 4 + k] = Math.exp(edgeSigma * z[i]);
      Cinit[i * 4 + k] = d0 * (1 + d0Noise * (2 * u[i] - 1));
    }
  }
  const eta = Float32Array.from(hashNormal(seed, 8, n));
  return { G, Cinit, eta };
}
