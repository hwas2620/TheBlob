// 원형질체 코어의 파라미터 — config.ts 의 PLASM / OSCILLATOR / SLIME 에서 기본값을 만들고
// 셰이더 플레이스홀더 표로 바꾼다. 값을 바꾸려면 PlasmGPU 를 새로 만든다(셰이더를 다시 컴파일한다).

import { PLASM, OSCILLATOR, SLIME } from '../../config';

export interface Attractant {
  /** 초기 원반 중심에서 본 방향(도)과 거리(셀) */
  angleDeg: number;
  dist: number;
  /** 가우스 폭(셀)과 진폭 */
  sigma: number;
  amp: number;
}

export interface PlasmParams {
  N: number;
  seed: number;
  dt: number;
  kappa: number;
  h0: number;
  tauA: number;
  tauF: number;
  hFill: number;
  hMin: number;
  grace: number;
  beta: number;
  cap: number;
  hy0: number;
  ySigma: number;
  lambdaC: number;
  curvGain: number;
  curvRef: number;
  curvSigma: number;
  wetRho: number;
  yC: number;
  yS: number;
  gamma: number;
  rate: number;
  q0Auto: number;
  q0Floor: number;
  cMax: number;
  d0: number;
  d0Noise: number;
  r: number;
  edgeSigma: number;
  bridgeBreak: number;
  rInit: number;
  hInit: number;
  period: number;
  eps: number;
  dOmega: number;
  dTheta: number;
  substeps: number;
  triK: number;
  triP: number;
  triT: number;
  triV: number;
  mgCycles: number;
  mgCoarseSweeps: number;
  mgOmega: number;
  mgCoarseScale: number;
  mgExtrap: number;
  attractant: Attractant | null;
}

export function defaultParams(over: Partial<PlasmParams> = {}): PlasmParams {
  return {
    N: PLASM.GRID,
    seed: 1,
    dt: PLASM.DT,
    kappa: PLASM.KAPPA,
    h0: PLASM.H0,
    tauA: PLASM.TAU_A,
    tauF: PLASM.TAU_F,
    hFill: PLASM.H_FILL,
    hMin: PLASM.H_MIN,
    grace: PLASM.GRACE,
    beta: PLASM.BETA,
    cap: PLASM.CAP,
    hy0: PLASM.HY0,
    ySigma: PLASM.Y_SIGMA,
    lambdaC: PLASM.LAMBDA_C,
    curvGain: PLASM.CURV_GAIN,
    curvRef: PLASM.CURV_REF,
    curvSigma: PLASM.CURV_SIGMA,
    wetRho: PLASM.WET_RHO,
    yC: PLASM.Y_C,
    yS: SLIME.Y_S,
    gamma: PLASM.GAMMA,
    rate: PLASM.RATE,
    q0Auto: PLASM.Q0_AUTO,
    q0Floor: PLASM.Q0_FLOOR,
    cMax: PLASM.C_MAX,
    d0: PLASM.D0,
    d0Noise: PLASM.D0_NOISE,
    r: PLASM.R,
    edgeSigma: PLASM.EDGE_SIGMA,
    bridgeBreak: PLASM.BRIDGE_BREAK,
    rInit: PLASM.R_INIT,
    hInit: PLASM.H_INIT,
    period: OSCILLATOR.PERIOD,
    eps: OSCILLATOR.EPS,
    dOmega: OSCILLATOR.D_OMEGA,
    dTheta: OSCILLATOR.D_THETA,
    substeps: OSCILLATOR.SUBSTEPS,
    triK: OSCILLATOR.TRI_K,
    triP: OSCILLATOR.TRI_P,
    triT: OSCILLATOR.TRI_T,
    triV: OSCILLATOR.TRI_V,
    mgCycles: PLASM.MG_CYCLES,
    mgCoarseSweeps: PLASM.MG_COARSE_SWEEPS,
    mgOmega: PLASM.MG_OMEGA,
    mgCoarseScale: PLASM.MG_COARSE_SCALE,
    mgExtrap: PLASM.MG_EXTRAP,
    // 굶은 이주 시험의 유인장 (numpy 기준 실행과 같은 값)
    attractant: { angleDeg: 27, dist: 70, sigma: 60, amp: 0.5 },
    ...over,
  };
}

/** GLSL float 리터럴 */
export function glf(x: number): string {
  if (!Number.isFinite(x)) throw new Error(`셰이더 상수가 유한하지 않다: ${x}`);
  return Number.isInteger(x) ? x.toFixed(1) : String(x);
}

/** 셰이더 플레이스홀더 표 ({{NAME}} → 값). COMMON 은 shaders.ts 가 더한다 */
export function shaderVars(p: PlasmParams): Record<string, string> {
  const twoPi = 2 * Math.PI;
  // 가우스 핵: scipy.ndimage.gaussian_filter(sigma, truncate=3.0) 과 같은 반경과 가중치
  const radius = Math.floor(3.0 * p.curvSigma + 0.5);
  const w: number[] = [];
  let sum = 0;
  for (let i = -radius; i <= radius; i++) {
    const v = Math.exp((-0.5 * i * i) / (p.curvSigma * p.curvSigma));
    w.push(v);
    sum += v;
  }
  const kernel = w.map((v) => glf(v / sum)).join(', ');
  const a = Math.min(1, p.wetRho / Math.SQRT2);
  return {
    DT: glf(p.dt),
    DTS: glf(p.dt / p.substeps),
    OMEGA0: glf(twoPi / p.period),
    D_OMEGA: glf(p.dOmega),
    D_THETA: glf(p.dTheta),
    TAU_A: glf(p.tauA),
    TAU_F: glf(p.tauF),
    H0: glf(p.h0),
    H_FILL: glf(p.hFill),
    H_MIN: glf(p.hMin),
    GRACE: glf(p.grace),
    BETA: glf(p.beta),
    CAP: glf(p.cap),
    EPS: glf(p.eps),
    INV_KAPPA_DT: glf(1 / (p.kappa * p.dt)),
    R_BASE: glf(p.r),
    GAMMA: glf(p.gamma),
    RATE: glf(p.rate),
    Q0_AUTO: glf(p.q0Auto),
    Q0_FLOOR: glf(p.q0Floor),
    C_MAX: glf(p.cMax),
    BRIDGE_BREAK: glf(p.bridgeBreak),
    HY0: glf(p.hy0),
    Y_SIGMA: glf(p.ySigma),
    CURV_K: glf(p.lambdaC * p.curvGain),
    CURV_REF: glf(p.curvRef),
    Y_S: glf(p.yS),
    Y_C: glf(p.yC),
    WET_WA: glf(a * (1 - a)),
    WET_WD: glf(a * a),
    BLUR_RADIUS: String(radius),
    BLUR_TAPS: String(2 * radius + 1),
    BLUR_KERNEL: kernel,
    TRI_K: glf(p.triK),
    TRI_P: glf(p.triP),
    TRI_OMEGA: glf(twoPi / p.triT),
    TRI_V: glf(p.triV),
    MG_EXTRAP: glf(p.mgExtrap),
    MG_OMEGA: glf(p.mgOmega),
    MG_COARSE_F: glf(1 / p.mgCoarseScale),
  };
}
