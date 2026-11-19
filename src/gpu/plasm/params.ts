// 원형질체 코어의 파라미터 — config.ts 의 PLASM / OSCILLATOR / SLIME 에서 기본값을 만들고
// 셰이더 플레이스홀더 표로 바꾼다. 값을 바꾸려면 PlasmGPU 를 새로 만든다(셰이더를 다시 컴파일한다).

import { PLASM, OSCILLATOR, SLIME, PLASM_FOOD } from '../../config';

/** 먹이의 자리: 초기 원반 중심에서 본 방향(도)과 거리(셀) */
export interface FoodSpot {
  angleDeg: number;
  dist: number;
}

/** 한 번에 둘 수 있는 먹이 수 (먹이별 유인장을 RGBA 두 장에 담는다) */
export const MAX_FOODS = 8;
/** 줄지 않는 먹이의 "남은 양". float32 에서 먹는 양을 빼도 그대로다 */
export const FOOD_UNLIMITED = 1e30;

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
  // ── 규칙 8 (먹이) ──
  /** 먹이의 자리 (MAX_FOODS 개까지. 원반이 서로 겹치면 안 된다) */
  foods: FoodSpot[];
  /** 유인장 c = amp·Σ(주기 상) exp(−r²/2σ²) 의 폭(셀)과 진폭 */
  foodSigma: number;
  foodAmp: number;
  /** 먹이 원반의 반지름(셀). 이 안의 젖은 셀이 먹는다 */
  foodR: number;
  /** 먹이 하나의 양. 0 이면 줄지 않는다 */
  foodM: number;
  /** 젖은 먹이 셀 하나가 단위 시간에 먹는 양. 0 이면 먹지 않는다(유인원 노릇만 한다) */
  eat: number;
  /** 먹은 양이 두께로 바뀌는 비율 */
  gain: number;
  /** 다 먹은 먹이의 유인장이 사라지는 시간 */
  foodFade: number;
  /** 살아 있는 먹이 위의 젖은 셀은 늙지 않고(sage 가 멈춘다) 쉬는 두께의 배율 H 가 오른다 */
  reservoir: boolean;
  /** H 의 상한, 오르는 시간 상수, "쉬는 두께의 이 비율 이상 차 있을 때만 오른다"(0 = 조건 없음) */
  hRes: number;
  resTau: number;
  resGate: number;
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
    // 굶은 이주 시험의 유인원 하나 (numpy 기준 실행 GA 와 같은 값): 넓고 약한 유인장만 있고 먹지도 저장하지도 않는다
    foods: [{ angleDeg: 27, dist: 70 }],
    foodSigma: 60,
    foodAmp: 0.5,
    foodR: 4,
    foodM: 0,
    eat: 0,
    gain: 0,
    foodFade: PLASM_FOOD.FADE,
    reservoir: false,
    hRes: PLASM_FOOD.H_MAX,
    resTau: PLASM_FOOD.TAU_H,
    resGate: PLASM_FOOD.GATE,
    ...over,
  };
}

/** 규칙 8 을 켠 설정: 먹이를 먹고 그 자리에 부피를 쌓는다 (numpy 기준 실행의 FOOD 와 같은 값). defaultParams 의 over 에 넣는다 */
export function foodParams(foods: FoodSpot[], over: Partial<PlasmParams> = {}): Partial<PlasmParams> {
  return {
    foods,
    foodSigma: PLASM_FOOD.SIGMA,
    foodAmp: PLASM_FOOD.AMP,
    foodR: PLASM_FOOD.R,
    foodM: PLASM_FOOD.M,
    eat: PLASM_FOOD.EAT,
    gain: PLASM_FOOD.GAIN,
    foodFade: PLASM_FOOD.FADE,
    reservoir: true,
    hRes: PLASM_FOOD.H_MAX,
    resTau: PLASM_FOOD.TAU_H,
    resGate: PLASM_FOOD.GATE,
    ...over,
  };
}

/** 먹이 패스가 원반을 훑는 창의 반폭(셀). 창의 가운데는 먹이 자리를 반올림한 셀이다 */
export function foodWindow(p: PlasmParams): number {
  return Math.ceil(p.foodR) + 1;
}

/** 먹이 규칙의 어느 부분이 켜져 있는가 (셰이더의 #if 와 패스 구성이 이것을 따른다) */
export interface FoodMode {
  /** 먹이 수 */
  n: number;
  /** 스텝마다 먹는다 → 먹이 상태가 바뀐다 (먹이 패스를 돈다) */
  eats: boolean;
  /** 먹이 상태가 셀의 두께나 노화에 영향을 준다 (유량 패스가 먹이 상태를 읽는다) */
  active: boolean;
  /** 쉬는 두께의 배율 H 를 쓴다 (rest 패스의 출력이 한 장 는다) */
  store: boolean;
  /** 먹이가 떨어질 수 있다 → 유인장의 세기가 바뀐다 */
  fades: boolean;
}

export function foodMode(p: PlasmParams): FoodMode {
  const n = p.foods.length;
  if (n > MAX_FOODS) throw new Error(`먹이는 ${MAX_FOODS}개까지 둘 수 있다 (${n}개)`);
  const eats = n > 0 && p.eat > 0;
  return { n, eats, active: n > 0 && (p.eat > 0 || p.reservoir), store: n > 0 && p.reservoir, fades: eats && p.foodM > 0 };
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
  const fm = foodMode(p);
  return {
    FOOD_N: String(fm.n),
    FOOD_N0: String(Math.min(fm.n, 4)),
    FOOD_ACTIVE: fm.active ? '1' : '0',
    FOOD_STORE: fm.store ? '1' : '0',
    FOOD_FADES: fm.fades ? '1' : '0',
    RESERVOIR: p.reservoir ? '1.0' : '0.0',
    EAT: glf(p.eat),
    GAIN: glf(p.gain),
    FADE: glf(Math.max(p.foodFade, 1e-6)),
    H_MAX: glf(p.hRes),
    TAU_H: glf(p.resTau),
    RES_GATE_ON: p.resGate > 0 ? '1' : '0',
    RES_GATE: glf(p.resGate),
    FOOD_UNLIMITED: '1e29', // 남은 양이 이보다 크면 줄지 않는 먹이다 (FOOD_UNLIMITED 의 1/10)
    FOOD_WIN: String(foodWindow(p)),
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
