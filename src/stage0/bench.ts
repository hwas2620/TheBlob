// A3 벤치마크 (v5) — 스텝당 시간과 드로콜 수를 격자·수단별로 잰다
//
// 재는 법
// - 격자마다 굶은 이주를 400스텝 돌려 몸(약 1900셀)을 만들고 그 상태를 읽어 둔다. 재는 구성마다 그 상태로 되돌리므로
//   모든 구성이 같은 몸에서 출발한다(변형은 산술이 같아 몸이 똑같이 자란다).
// - 지속 측정: 구성 하나를 쉬지 않고 1초 넘게 돌리고(32스텝마다 한 번 읽어 GPU 를 기다린다) 든 시간을 스텝 수로 나눈다.
//   휴대폰은 일을 조금 시키고 쉬면 클럭을 낮춰 두기 때문에, 짧게 몰아서 재면(v3 까지의 블록 측정) 구간마다 수 ms 의 지연이 섞이고
//   값이 크게 흩어졌다. 계속 시켜야 기기가 낼 수 있는 속도가 나온다.
// - 프레임 루프: 게임처럼 화면 갱신(requestAnimationFrame)마다 스텝을 돌리며 프레임 간격을 잰다. 게임에서 쓸 수 있는 속도는 이쪽 값이다.
//     오름        프레임당 스텝 수를 올려 가며. 게임과 같은 설정(몸 주변만, 경계 상자는 멈춤 없이 읽고 여유는 완만하게 키운다)
//     전체 격자   같은 것을 가위 없이. 몸이 격자를 덮거나 토러스의 가장자리에 걸쳤을 때의 비용이다. 그리는 넓이가 변하지 않으므로 처리량이 넓이 탓인지도 가려 준다
//     지속        한 설정으로 12~14초. 2초마다 처리량과 함께 그린 넓이, 젖은 셀의 상자만의 넓이, 여유(셀)를 적는다.
//                 384² 는 여유 규칙 둘(옛: 스텝당 한 칸, 새: 완만하게)을 차례로 돌려 견준다 (옛 규칙이 먼저. 뒤에 도는 쪽이 더 뜨거운 기기에서 돈다)
//   v4 의 내림 시험과 읽기 대조는 뺐다: 내림은 두 번의 측정에서 오름과 같았고, 읽기 대조는 읽기를 끈 쪽의 상자가 자라지 않아 넓이가 달랐다(읽기의 비용을 가리지 못했다).
// - 탐침은 짧게 몰아서 재는 방식 그대로다(되풀이 횟수를 달리한 차이로 읽기의 고정 시간을 뺀다). 크기의 비만 본다.
//   묶음별 비용은 GL 호출을 셀 때(count=1)만, WebGPU 탐침은 webgpu=1 일 때만 잰다 (둘 다 세 번의 측정으로 결론이 났다).
// - 벽시계로 재므로 드라이버의 CPU 시간까지 들어간다. 드로콜 수가 많은 이 작업에서는 그쪽이 실제 비용이다.
// 소프트웨어 렌더러에서는 시간 수치가 뜻이 없다(드로콜 수와 상대 비중만 본다).

import type { Glx } from '../gpu/plasm/glx';
import { PlasmGPU, type PassGroup, type Snapshot } from '../gpu/plasm/PlasmGPU';
import { defaultParams, foodParams, type PlasmParams } from '../gpu/plasm/params';
import { totalCalls } from './glCount';
import { FOOD3 } from './scenarios';
import { applyVariant, VARIANTS, type Log } from './tests';
import { webgpuProbe, type WebGpuProbe } from './webgpuProbe';

export interface BenchRow {
  N: number;
  variant: string;
  /** 기본 설정이 아닐 때의 이름 (예: 'dt 0.2 + 주기 8') */
  tag?: string;
  cycles: number;
  drawCalls: number;
  /** 스텝당 패스 수: 드로콜에 타깃을 지우는 횟수를 더한 것 */
  passes: number;
  /** 지속 측정의 스텝당 시간: 쉬지 않고 seconds 초 동안 steps 스텝을 돌린 값 */
  msPerStep: number;
  steps: number;
  seconds: number;
  /** 같은 방식으로 압력 풀이(조대 연산자 재구성 + V 사이클)만 돌린 한 번의 시간 */
  msSolve: number;
  /** 그리는 영역이 격자에서 차지하는 비율 (스텝 평균) */
  activeFraction: number;
  /** 초당 스텝 수(1000 / msPerStep)와 그때 화면의 전진 속도(px/s, 지도 1500px 기준) */
  stepsPerSec: number;
  pxPerSec: number;
  /** 두 번 스무딩을 요청했지만 셰이더가 컴파일되지 않아 쓰지 못했으면 true */
  sweep2Missing?: boolean;
  /** 스텝당 GL 함수 호출 수 (count=1 로 열었을 때만) */
  glCalls?: number;
}

/** 패스 묶음 하나를 따로 연달아 돌려 잰 비용 */
export interface GroupCost {
  group: string;
  /** 한 스텝에 이 묶음이 그리는 패스 수 (V 사이클은 사이클 수를 곱한 값) */
  passesPerStep: number;
  usPerPass: number;
  msPerStep: number;
  /** 한 스텝에 이 묶음이 부르는 GL 함수 수 (count=1 로 열었을 때만) */
  glCalls?: number;
}

/** 패스 하나의 고정 비용(µs)을 타깃의 종류별로 잰 것. 모두 4×4 텍셀만 그리는 가벼운 패스다 */
export interface PassProbes {
  /** 가장 작은 레벨(3~4텍셀 타깃)에서 타깃을 번갈아 */
  tinyAlt: number;
  /** 같은 타깃에, 상태를 바꾸지 않고 */
  tinySame: number;
  /** 같은 타깃에, 프로그램만 번갈아 */
  tinyProg: number;
  /** 가장 작은 타깃을 번갈아 지우기 */
  tinyClear: number;
  /** GPU 가 쉬고 있을 때 텍셀 하나를 읽는 데 드는 시간 — 읽기의 고정 비용 */
  syncIdle: number;
  /** 그리기와 무관한 GL 호출 하나 (activeTexture) */
  glCall: number;
  /** 텍스처 묶기 하나 (bindTexture) */
  bindTex: number;
  /** 격자 크기의 R32F 타깃을 번갈아 */
  bigR32F: number;
  /** 격자 크기의 RGBA32F 타깃을 번갈아 */
  bigRGBA: number;
  /** 격자 크기의 RGBA32F 두 장(다중 타깃)을 번갈아 */
  bigMRT: number;
}

export interface LoopRow {
  /** 어떤 시험의 줄인가: '오름'(몸 주변만), '전체 격자' */
  label: string;
  /** 프레임당 스텝 수 */
  spf: number;
  frames: number;
  /** 프레임 간격(ms)의 평균, 중앙값, 95백분위 */
  msMean: number;
  msMedian: number;
  msP95: number;
  /** 화면 갱신 주기의 1.5배를 넘긴 프레임의 비율 */
  late: number;
  /** 초당 스텝 수 (spf × 1000 / 평균 간격) */
  stepsPerSec: number;
  /** 그린 영역이 격자에서 차지한 비율의 평균 */
  area: number;
}

/** 지속 시험의 한 구간 */
export interface LoopWindow {
  /** 구간이 시작한 시각(초) */
  t: number;
  stepsPerSec: number;
  late: number;
  /** 그린 영역이 격자에서 차지한 비율의 평균 (몸이 퍼져 일이 늘어난 것인지, 기기가 느려진 것인지 가리려고 적는다) */
  area: number;
  /** 젖은 셀의 경계 상자만의(여유를 뺀) 넓이 비율의 평균 */
  box: number;
  /** 가위 사각형이 상자 밖으로 둔 여유(셀)의 평균. 경계 상자가 늦게 도착할수록 크다 */
  margin: number;
}

/** 한 설정으로 오래 돌린 것 */
export interface LoopSustained {
  /** 여유 규칙: '완만한 여유'(게임의 설정) 또는 '옛 여유'(잰 뒤 스텝당 한 칸) */
  label: string;
  spf: number;
  seconds: number;
  windows: LoopWindow[];
  /** (경계 상자가 실제로 넓어진 셀 수) / (그동안 여유가 허용한 셀 수) 의 최대, 완만한 규칙이 더 적게 허용한 구간에서만 본 최대, 1 을 넘은 횟수 */
  marginUse: number;
  marginUseSoft: number;
  marginOverruns: number;
}

export interface FrameLoop {
  N: number;
  /** 시뮬레이션 없이 화면만 그릴 때의 프레임 간격(ms) — 화면의 갱신 주기 */
  baseMs: number;
  /** 프레임당 스텝 수를 올려 가며 잰 줄들 (게임과 같은 설정) */
  rows: LoopRow[];
  /** 같은 것을 전체 격자(가위 끔)로 */
  full: LoopRow[];
  /** 한 설정으로 오래 돌린 것 (게임과 같은 설정) */
  sustained: LoopSustained | null;
  /** 같은 것을 옛 여유 규칙으로 (대조. 384² 만) */
  sustainedHard: LoopSustained | null;
  /** 끝까지 재지 못했으면 그 이유 */
  note?: string;
}

export interface BenchResult {
  version: 5;
  renderer: string;
  userAgent: string;
  /** 작은 타깃에 그리는 드로콜 하나의 시간(µs) — 드로콜마다 드는 고정 비용 */
  usPerTinyDraw: number;
  rows: BenchRow[];
  /** 잰 몸의 넓이(셀) */
  bodyArea: Record<string, number>;
  /** 지속 측정에서 구성 하나를 돌린 시간(ms) */
  sustainMs: number;
  /** "몸 주변만" 변형의 여유에 더한 셀 수 */
  lagMargin: number;
  /** 두 번 스무딩 셰이더가 컴파일되지 않았으면 그 오류 */
  sweep2Error: string | null;
  /** 끝까지 재지 못한 격자와 그 이유 (메모리 부족으로 컨텍스트를 잃은 경우 등) */
  errors: string[];
  /** 타깃 종류별 고정 비용을 잰 격자 (재지 못했으면 null). 묶음별 비용(groups)은 GL 호출을 셀 때만 잰다 ("합친 패스 + 몸 주변만", 2사이클) */
  profileN: number | null;
  groups: GroupCost[];
  probes: PassProbes | null;
  /** 한 스텝의 GL 함수 호출 수를 이름별로 (profileN 격자, 합친 패스 + 몸 주변만, 2사이클. count=1 로 열었을 때만) */
  glByName?: Record<string, number>;
  /** 화면 갱신에 맞춘 프레임 루프 (profileN 격자, 합친 패스 + 몸 주변만) */
  frameLoop: FrameLoop | null;
  /** 256² 격자의 프레임 루프. 256² 를 재지 않았으면 null */
  frameLoopSmall: FrameLoop | null;
  /** 같은 기기에서 WebGPU 의 계산 디스패치 하나가 드는 고정 비용 (webgpu=1 로 열었을 때만) */
  webgpu?: WebGpuProbe;
  seconds: number;
}

export interface BenchOptions {
  /** 지속 측정에서 구성 하나를 돌리는 시간(ms). 기본 1200. 드로콜 수만 볼 때는 작게 준다 */
  sustainMs?: number;
  /** false 면 프레임 루프 시험을 건너뛴다 */
  loop?: boolean;
  /** 시험용: 프레임 루프의 지속 시험이 쓸 프레임당 스텝 수의 상한을 잰 값 대신 준다 */
  loopCap?: number;
  /** 시험용: 프레임 루프의 시험 하나하나의 길이를 이 비율로 줄인다 (소프트웨어 렌더러에서 흐름만 확인할 때) */
  loopScale?: number;
  /** true 면 WebGPU 탐침도 돌린다 */
  webgpu?: boolean;
  /** true 면 모든 격자에서 변형 다섯을 다 잰다 (드로콜·GL 호출 수를 기록할 때) */
  allVariants?: boolean;
  /** GL 호출을 세는 껍데기의 계수기 (glCount.ts). 주면 스텝당 GL 호출 수를 함께 적는다 */
  glCounts?: Map<string, number>;
  /** 화면에 그리는 함수. 주면 프레임 루프 시험을 한다 */
  view?: (sim: PlasmGPU) => void;
}

/** 게임 지도의 한 변(px) */
export const MAP_PX = 1500;
/** 전진면의 속도(셀/스텝). numpy 기준 실행의 값 (dt = 0.1) */
export const CELLS_PER_STEP = 0.02;
/** 맥동 한 주기의 스텝 수 (주기 4, dt = 0.1) */
export const STEPS_PER_PULSE = 40;
/** 한 스텝이 가는 모델 시간을 늘린 후보 설정 (6차 실험 V1. 192² 의 몸 크기에서 독립 검증됨, 큰 몸에서는 미확인) */
export const FAST_DT: Partial<PlasmParams> = { dt: 0.2, period: 8, substeps: 8 };
export const FAST_DT_NAME = 'dt 0.2 + 주기 8';
/** 같은 구성을 측정의 끝에 다시 잰 줄의 이름 */
export const DRIFT_NAME = '끝에 다시';
/** 규칙 8(먹이)을 켠 설정의 줄: 대칭 먹이 셋 + 위상 무늬. 스텝에 먹이 패스 하나와 저장 배율(출력 한 장)이 는다 */
export const FOOD_NAME = '먹이 셋';
const WARMUP_STEPS = 400;
/** 먹이 줄의 준비 스텝: 세 먹이에 모두 닿아 먹고 있는 몸이 되게 한다 (닿는 시각이 모델 시간 59~76) */
const FOOD_WARMUP_STEPS = 1000;
const DEFAULT_SUSTAIN_MS = 1200;
/**
 * 프레임 루프와 돌려 보기가 쓰는 변형: 합친 패스 + 몸 주변만.
 * "두 번 스무딩"은 Adreno 840 의 지속 측정에서 4~20% 느려서 뺐다(묶은 패스의 셰이더가 줄어든 패스보다 무겁다)
 */
export const LOOP_VARIANT = 2;
/** 프레임 루프 시험에서 해 보는 프레임당 스텝 수. 작은 격자(스텝이 싸다)는 높은 쪽만 본다 */
const LOOP_UP = [4, 8, 12, 16, 24, 32];
const LOOP_UP_SMALL = [8, 16, 24, 32, 48];
/** 전체 격자(가위 끔)로 해 보는 프레임당 스텝 수 */
const LOOP_FULL = [4, 6, 8, 12, 16];
const LOOP_FULL_SMALL = [8, 12, 16, 24, 32];
/** 지속 시험에서 쓰는 프레임당 스텝 수의 상한 (게임이 쓸 구간). 기기가 거기까지 못 가면 오름 시험에서 지킨 최대로 낮춘다 */
const LOOP_SUSTAIN_SPF = 12;
const LOOP_SUSTAIN_SPF_SMALL = 16;
/** 지속 시험의 길이(ms). 384² 는 여유 규칙 둘을 이 길이로 한 번씩, 256² 는 새 규칙만 조금 더 길게 */
const LOOP_SUSTAIN_MS = 12000;
const LOOP_SUSTAIN_MS_SMALL = 14000;
/**
 * 오름 시험에서 설정 하나를 재는 시간(ms). 짧으면 틀린다: 감당하지 못하는 부하에서도 브라우저가 밀린 명령을 1초쯤은 쌓아 두어
 * 화면 갱신이 제때 오는 것처럼 보인다(1.2초씩 잰 측정 v3 가 그렇게 "프레임당 16스텝"을 지킨 것으로 냈다)
 */
const LOOP_STEP_MS = 3000;
/** 이 간격(ms) 안이면 60fps 를 지킨 것으로 본다 */
export const HELD_MS = 18.5;
/** 게임 루프에서 경계 상자가 늦게 도착하는 만큼 여유에 더하는 셀 수 (프레임당 8~16스텝에 한 프레임 늦는 경우쯤) */
const LOOP_LAG_MARGIN = 8;
/** 지속 측정에서 경계 상자를 다시 재는 간격(스텝). 그 자리에서 읽는다 */
const SUSTAIN_REFRESH = 32;

const yieldNow = (): Promise<void> => new Promise((r) => setTimeout(r, 0));

/** 탭이 다시 보일 때까지 기다린다 */
function whenVisible(): Promise<void> {
  if (!document.hidden) return Promise.resolve();
  return new Promise((resolve) => {
    const on = (): void => {
      if (document.hidden) return;
      document.removeEventListener('visibilitychange', on);
      resolve();
    };
    document.addEventListener('visibilitychange', on);
  });
}

function median(v: number[]): number {
  const s = v.slice().sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length === 0 ? NaN : s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * f(k) 가 무언가를 k 번 하고 끝에서 텍셀 하나를 읽어 GPU 를 기다리는 함수일 때, 한 번의 시간(µs)을 낸다.
 * k = n 과 k = 3n 을 재서 차이를 2n 으로 나눈다(읽기의 고정 시간이 빠진다). 세 번 재서 중앙값을 쓴다
 */
function diffMicros(sim: PlasmGPU, f: (k: number) => void, n: number): number {
  const v: number[] = [];
  for (let s = 0; s < 3; s++) {
    sim.sync();
    const t0 = performance.now();
    f(n);
    const t1 = performance.now();
    f(3 * n);
    const t2 = performance.now();
    v.push(((t2 - t1 - (t1 - t0)) / (2 * n)) * 1000);
  }
  return Math.max(0, median(v));
}

/** 변형과 사이클 수를 걸고 읽어 둔 상태로 되돌린다 */
function prepare(sim: PlasmGPU, snap: Snapshot, variant: number, cycles: number): void {
  const v = VARIANTS[variant];
  sim.restore(snap);
  sim.cycles = cycles;
  applyVariant(sim, v);
  sim.asyncBounds = false;
  sim.autoBounds = false;
  sim.softMargin = false;
  sim.fixedMargin = null;
  sim.marginExtra = v.scissor ? LOOP_LAG_MARGIN : 0;
  sim.refreshBounds();
  for (let s = 0; s < 4; s++) sim.stepOnce(); // 셰이더와 캐시를 데운다
}

interface Sustained {
  msPerStep: number;
  steps: number;
  seconds: number;
  msSolve: number;
  drawsPerStep: number;
  passesPerStep: number;
  glPerStep: number;
  activeFraction: number;
}

/**
 * 지속 측정: 쉬지 않고 ms 동안 스텝을 돌린다. 앞의 4분의 1만큼은 데우는 구간으로 버린다.
 * SUSTAIN_REFRESH 스텝마다 한 번 읽어서 GPU 를 기다린다(명령이 처리보다 빨리 쌓이는 것을 막는다. 그 읽기도 시간에 들어간다).
 * "몸 주변만" 변형은 그 읽기가 경계 상자를 다시 재는 것이다(게임 루프의 읽기를 대신한다).
 * 이어서 압력 풀이만 같은 방식으로 돌려 한 번의 시간을 낸다.
 */
function sustained(glx: Glx, sim: PlasmGPU, cycles: number, ms: number, glCounts?: Map<string, number>): Sustained {
  const nc = sim.params.mgCoarseSweeps;
  const chunk = 4;
  const run = (limitMs: number): { ms: number; steps: number; draws: number; clears: number; gl: number; frac: number } => {
    let steps = 0, draws = 0, clears = 0, gl = 0, frac = 0;
    sim.refreshBounds();
    sim.sync(); // GPU 를 비운다
    const t0 = performance.now();
    for (;;) {
      const d = glx.drawCalls, c = glx.clearCalls, g = glCounts ? totalCalls(glCounts) : 0;
      for (let i = 0; i < chunk; i++) {
        sim.stepOnce();
        frac += sim.activeFraction();
      }
      draws += glx.drawCalls - d;
      clears += glx.clearCalls - c;
      if (glCounts) gl += totalCalls(glCounts) - g;
      steps += chunk;
      // 명령은 GPU 가 처리하는 것보다 빨리 쌓을 수 있다. SUSTAIN_REFRESH 스텝마다 읽어서 기다려야 시계가 실제 진행을 따른다
      if (steps % SUSTAIN_REFRESH === 0) {
        if (sim.scissor) sim.refreshBounds();
        else sim.sync();
      }
      if (steps >= 8 && performance.now() - t0 >= limitMs) break;
    }
    sim.sync();
    return { ms: performance.now() - t0, steps, draws, clears, gl, frac };
  };
  run(ms / 4);
  const r = run(ms);
  // 풀이만: 같은 상태에서 조대 연산자 재구성과 V 사이클을 연달아 돌린다. 시뮬레이션의 상태는 바뀌지 않는다
  const t0 = performance.now();
  let solves = 0;
  do {
    for (let i = 0; i < chunk; i++) {
      sim.mg.build();
      sim.mg.solve(cycles, nc);
    }
    solves += chunk;
    if (solves % 16 === 0) sim.mg.sync();
  } while (performance.now() - t0 < ms / 4);
  sim.mg.sync();
  const msSolve = (performance.now() - t0) / solves;
  return {
    msPerStep: r.ms / r.steps,
    steps: r.steps,
    seconds: r.ms / 1000,
    msSolve,
    drawsPerStep: r.draws / r.steps,
    passesPerStep: (r.draws + r.clears) / r.steps,
    glPerStep: r.gl / r.steps,
    activeFraction: r.frac / r.steps,
  };
}

const PROFILE_GROUPS: (PassGroup | 'build' | 'cycle')[] = ['edges', 'phase', 'rest', 'init', 'build', 'cycle', 'flux', 'q0', 'reinforce', 'dry', 'blur', 'wet'];
const GROUP_NAMES: Record<string, string> = {
  edges: '간선 켜기', phase: '위상', rest: '쉬는 두께·가중치', init: '웜스타트', build: '조대 연산자', cycle: 'V 사이클',
  flux: '유량', q0: '전역 평균', reinforce: '강화', dry: '마름', blur: '흐림', wet: '젖음',
};

/**
 * 묶음 하나를 따로 연달아 돌려 패스 하나의 시간을 잰다. 같은 입력으로 되풀이하므로 재기 전에 상태를 되돌린다.
 * 한 패스짜리 묶음 가운데 같은 타깃에 되풀이해 그리는 것(쉬는 두께, 웜스타트)은 타깃 전환이 빠진 값이 나온다
 */
function profileGroups(glx: Glx, sim: PlasmGPU, snap: Snapshot, glCounts?: Map<string, number>): GroupCost[] {
  const out: GroupCost[] = [];
  for (const g of PROFILE_GROUPS) {
    prepare(sim, snap, 2, 2);
    const count = (): number => glx.drawCalls + glx.clearCalls;
    const c0 = count();
    sim.profileGroup(g, 1); // 한 번에 그리는 패스 수를 세고, 끝을 맞춘다
    const per = Math.max(1, count() - c0);
    let glCalls: number | undefined;
    if (glCounts) {
      // 끝을 맞추는 읽기의 호출을 빼려고 두 번 돌린 것에서 한 번 돌린 것을 뺀다
      const g0 = totalCalls(glCounts);
      sim.profileGroup(g, 1);
      const g1 = totalCalls(glCounts);
      sim.profileGroup(g, 2);
      glCalls = (totalCalls(glCounts) - g1 - (g1 - g0)) * (g === 'cycle' ? 2 : 1);
    }
    const reps = Math.max(2, Math.ceil(96 / per));
    const usPerPass = diffMicros(sim, (k) => sim.profileGroup(g, k), reps) / per;
    const passesPerStep = per * (g === 'cycle' ? 2 : 1);
    out.push({ group: GROUP_NAMES[g], passesPerStep, usPerPass, msPerStep: (usPerPass * passesPerStep) / 1000, ...(glCalls === undefined ? {} : { glCalls }) });
  }
  return out;
}

/** 타깃의 종류별로 가벼운 패스 하나의 시간(µs)을 잰다. 상태를 망가뜨리므로 그 격자의 마지막에 부른다 */
function probePasses(sim: PlasmGPU, snap: Snapshot): PassProbes {
  const n = 1000;
  prepare(sim, snap, 2, 2);
  // 저마다 k 번 하고 마지막 출력을 읽어 끝을 맞춘다
  const time = (f: (k: number) => void, k = n): number => diffMicros(sim, f, k);
  // 쉬고 있을 때의 읽기 한 번. 시계의 눈금(0.1~1ms)보다 짧을 수 있어 20번을 묶어 잰다
  const idle: number[] = [];
  sim.sync();
  for (let i = 0; i < 5; i++) {
    const t0 = performance.now();
    for (let j = 0; j < 20; j++) sim.sync();
    idle.push(((performance.now() - t0) / 20) * 1000);
  }
  return {
    tinyAlt: time((k) => sim.mg.benchTinyDraws(k)),
    tinySame: time((k) => sim.mg.benchTinySame(k)),
    tinyProg: time((k) => sim.mg.benchTinyProg(k)),
    tinyClear: time((k) => sim.mg.benchTinyClears(k)),
    syncIdle: median(idle),
    glCall: time((k) => sim.mg.benchCalls(k), n * 20), // 호출 하나가 1µs 에 못 미치므로 많이 되풀이해야 시계의 눈금(0.1~1ms)을 넘는다
    bindTex: time((k) => sim.mg.benchBinds(k), n * 20),
    bigR32F: time((k) => sim.probe('r32f', k)),
    bigRGBA: time((k) => sim.probe('rgba', k)),
    bigMRT: time((k) => sim.probe('mrt', k)),
  };
}

/** 다음 화면 갱신을 기다린다. 탭이 가려져 갱신이 오지 않으면 null */
function nextFrame(timeoutMs = 2000): Promise<number | null> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), timeoutMs);
    requestAnimationFrame((t) => {
      clearTimeout(timer);
      resolve(t);
    });
  });
}

/** 프레임마다 모으는 값 (프레임의 스텝을 다 돌린 뒤의 값. ts 와 같은 번호) */
interface LoopTrace {
  ts: number[];
  /** 그린 넓이, 젖은 셀의 상자만의 넓이 (격자에서 차지하는 비율), 가위 사각형의 여유(셀) */
  area: number[];
  box: number[];
  margin: number[];
}

/**
 * 화면 갱신마다 스텝을 spf 번 돌리고 화면을 그린다. settleMs 가 지난 뒤부터 ms 동안의 화면 갱신 시각을 모은다.
 * 탭이 가려져 갱신이 오지 않으면 null
 */
async function loopRun(sim: PlasmGPU, view: (sim: PlasmGPU) => void, spf: number, ms: number, settleMs: number): Promise<LoopTrace | null> {
  const tr: LoopTrace = { ts: [], area: [], box: [], margin: [] };
  const start = performance.now();
  for (;;) {
    const t = await nextFrame();
    if (t === null) return null;
    for (let i = 0; i < spf; i++) sim.stepOnce();
    view(sim);
    const el = performance.now() - start;
    if (el >= settleMs) {
      tr.ts.push(t);
      tr.area.push(sim.activeFraction());
      tr.box.push(sim.boundsFraction());
      tr.margin.push(sim.activeMargin());
    }
    if ((el >= settleMs + ms && tr.ts.length >= 12) || tr.ts.length >= 4000) break;
  }
  return tr;
}

const mean = (v: number[]): number => (v.length === 0 ? NaN : v.reduce((a, b) => a + b, 0) / v.length);

function loopStats(label: string, spf: number, tr: LoopTrace, baseMs: number): LoopRow {
  const { ts } = tr;
  const dt: number[] = [];
  for (let i = 1; i < ts.length; i++) dt.push(ts[i] - ts[i - 1]);
  const sorted = dt.slice().sort((a, b) => a - b);
  const msMean = mean(dt);
  const limit = 1.5 * baseMs;
  return {
    label,
    spf,
    frames: dt.length,
    msMean,
    msMedian: median(dt),
    msP95: sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))],
    late: dt.filter((x) => x > limit).length / dt.length,
    stepsPerSec: (spf * 1000) / msMean,
    area: mean(tr.area),
  };
}

/** 게임과 같은 설정: 몸 주변만, 경계 상자를 멈춤 없이 읽는다. soft 면 여유를 완만하게 키우고(기본), 아니면 잰 뒤 지난 스텝 수만큼 키운다(v4 까지의 규칙) */
function gameLike(sim: PlasmGPU, snap: Snapshot, soft = true): void {
  prepare(sim, snap, LOOP_VARIANT, 2);
  sim.asyncBounds = true;
  sim.autoBounds = true;
  sim.marginExtra = 0;
  sim.softMargin = soft;
}

/** 전체 격자: 합친 패스, 가위 없음 */
const FULL_VARIANT = 1;

/**
 * 프레임 루프 시험. 프레임 간격이 화면의 갱신 주기에 머무는 동안은 그 스텝 수를 감당하는 것이다.
 * 몸은 재는 동안 계속 자라고 움직인다(설정마다 처음 상태로 되돌린다). 지속 시험에서는 되돌리지 않는다.
 * big 은 대표 격자(384²): 프레임당 스텝을 낮은 데서 시작하고, 지속 시험을 여유 규칙 둘로 한다. scale 은 시험 하나하나의 길이에 곱하는 값(시험용)
 */
async function frameLoop(glx: Glx, sim: PlasmGPU, snap: Snapshot, view: (sim: PlasmGPU) => void, log: Log, big: boolean, scale: number, capOverride?: number): Promise<FrameLoop> {
  const out: FrameLoop = { N: sim.N, baseMs: 0, rows: [], full: [], sustained: null, sustainedHard: null };
  const hidden = '화면 갱신이 오지 않았습니다(탭이 가려짐)';
  const fmt = (r: LoopRow): string => `간격 평균 ${r.msMean.toFixed(1)}ms (95백분위 ${r.msP95.toFixed(1)}, 늦은 프레임 ${(r.late * 100).toFixed(0)}%, 그린 넓이 ${(r.area * 100).toFixed(0)}%) → 초당 ${r.stepsPerSec.toFixed(0)}스텝`;
  const base = await loopRun(sim, view, 0, 700 * scale, 200 * scale);
  if (!base) return { ...out, note: hidden };
  out.baseMs = median(base.ts.slice(1).map((t, i) => t - base.ts[i]));
  const tooSlow = (r: LoopRow): boolean => r.msMean > 2.5 * Math.max(out.baseMs, 16.7);

  // 올려 가며: 게임과 같은 설정, 그리고 전체 격자
  for (const full of [false, true]) {
    for (const spf of full ? (big ? LOOP_FULL : LOOP_FULL_SMALL) : big ? LOOP_UP : LOOP_UP_SMALL) {
      if (full) prepare(sim, snap, FULL_VARIANT, 2);
      else gameLike(sim, snap);
      const tr = await loopRun(sim, view, spf, LOOP_STEP_MS * scale, 400 * scale);
      if (!tr) return { ...out, note: hidden };
      if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
      const r = loopStats(full ? '전체 격자' : '오름', spf, tr, out.baseMs);
      (full ? out.full : out.rows).push(r);
      log(`  프레임 루프 ${sim.N}² ${full ? '전체 격자' : '몸 주변만'} 프레임당 ${spf}스텝: ${fmt(r)}`);
      if (tooSlow(r)) break; // 초당 24프레임 아래로 떨어지면 더 늘려 볼 까닭이 없다
    }
  }
  // 지속 시험은 이 기기가 화면 갱신을 지키며 감당한 범위 안에서 한다
  const cap = capOverride ?? bestHeld(out)?.spf ?? 0;
  if (cap < 2) return out;
  const longSpf = Math.min(cap, big ? LOOP_SUSTAIN_SPF : LOOP_SUSTAIN_SPF_SMALL);
  const long = async (soft: boolean, ms: number): Promise<LoopSustained | null> => {
    gameLike(sim, snap, soft);
    const tr = await loopRun(sim, view, longSpf, ms * scale, 400 * scale);
    if (!tr) return null;
    if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
    const { ts } = tr;
    const windows: LoopWindow[] = [];
    const limit = 1.5 * out.baseMs;
    for (let w0 = ts[0]; w0 + 1000 < ts[ts.length - 1]; w0 += 2000) {
      const idx = ts.map((t, i) => (i > 0 && t > w0 && t <= w0 + 2000 ? i : -1)).filter((i) => i > 0);
      if (idx.length < 2) continue;
      const span = ts[idx[idx.length - 1]] - ts[idx[0] - 1];
      const avg = (v: number[]): number => idx.reduce((a, i) => a + v[i], 0) / idx.length;
      windows.push({
        t: (w0 - ts[0]) / 1000,
        stepsPerSec: (idx.length * longSpf * 1000) / span,
        late: idx.filter((i) => ts[i] - ts[i - 1] > limit).length / idx.length,
        area: avg(tr.area),
        box: avg(tr.box),
        margin: avg(tr.margin),
      });
    }
    const S: LoopSustained = { label: soft ? SOFT_NAME : HARD_NAME, spf: longSpf, seconds: (ts[ts.length - 1] - ts[0]) / 1000, windows, marginUse: sim.marginUse, marginUseSoft: sim.marginUseSoft, marginOverruns: sim.marginOverruns };
    log(`  프레임 루프 (지속 ${S.seconds.toFixed(0)}초, ${S.label}, 프레임당 ${longSpf}스텝) ${sustainedCells(S)}`);
    return S;
  };
  // 옛 규칙을 먼저 돌린다. 새 규칙이 더 나으면 더 뜨거운 기기에서 그랬다는 뜻이 된다
  if (big) {
    out.sustainedHard = await long(false, LOOP_SUSTAIN_MS);
    if (!out.sustainedHard) return { ...out, note: hidden };
  }
  out.sustained = await long(true, big ? LOOP_SUSTAIN_MS : LOOP_SUSTAIN_MS_SMALL);
  if (!out.sustained) return { ...out, note: hidden };
  return out;
}

/** 지속 시험의 여유 규칙 이름 */
export const SOFT_NAME = '완만한 여유';
export const HARD_NAME = '옛 여유';

/** 지속 시험의 구간들을 한 줄로 */
export function sustainedCells(S: LoopSustained): string {
  return '2초마다 초당 스텝/늦은 프레임%/그린 넓이%/상자%/여유 셀: '
    + S.windows.map((w) => `${w.stepsPerSec.toFixed(0)}/${(w.late * 100).toFixed(0)}/${(w.area * 100).toFixed(0)}/${(w.box * 100).toFixed(0)}/${w.margin.toFixed(0)}`).join(', ')
    + ` · 여유 사용률 최대 ${(S.marginUse * 100).toFixed(0)}% (완만한 구간 ${(S.marginUseSoft * 100).toFixed(0)}%)${S.marginOverruns > 0 ? `, 넘침 ${S.marginOverruns}회` : ''}`;
}

/** 프레임 간격이 이 값(ms) 안이면 화면 갱신을 지킨 것으로 본다. 화면이 초당 60프레임보다 느리게 갱신되는 기기(절전 모드 등)에서는 그 주기를 기준으로 한다 */
export function heldLimit(loop: FrameLoop): number {
  return Math.max(HELD_MS, loop.baseMs * 1.12);
}

/** "초당 60프레임" 또는 그 화면의 갱신 속도 */
export function heldLabel(loop: FrameLoop): string {
  return loop.baseMs > HELD_MS ? `초당 ${Math.round(1000 / loop.baseMs)}프레임(이 화면의 갱신 속도)` : '초당 60프레임';
}

/** 프레임 루프의 오름 시험(full 이면 전체 격자 쪽)에서 화면 갱신을 지킨 줄 가운데 초당 스텝이 가장 많은 것 */
export function bestHeld(loop: FrameLoop | null, full = false): LoopRow | null {
  let best: LoopRow | null = null;
  if (!loop) return null;
  const limit = heldLimit(loop);
  for (const r of full ? loop.full : loop.rows) if (r.msMean <= limit && (!best || r.stepsPerSec > best.stepsPerSec)) best = r;
  return best;
}

export async function runBench(glx: Glx, renderer: string, sizes: number[], log: Log, opts: BenchOptions = {}): Promise<BenchResult> {
  const sustainMs = Math.max(20, opts.sustainMs ?? DEFAULT_SUSTAIN_MS);
  const tStart = performance.now();
  const rows: BenchRow[] = [];
  const bodyArea: Record<string, number> = {};
  let usPerTinyDraw = 0;
  let sweep2Error: string | null = null;
  const errors: string[] = [];
  // 탐침과 묶음별 비용, 후보 설정의 줄은 격자 하나에서만 잰다 (384² 가 있으면 그것, 없으면 첫 격자). 프레임 루프는 그 격자와 256² 에서 잰다
  const profileN = sizes.includes(384) ? 384 : (sizes[0] ?? null);
  const loopScale = Math.min(1, Math.max(0.01, opts.loopScale ?? 1));
  let groups: GroupCost[] = [];
  let probes: PassProbes | null = null;
  const glCounts = opts.glCounts;
  let glByName: Record<string, number> | undefined;
  let loop: FrameLoop | null = null;
  let loopSmall: FrameLoop | null = null;

  /** 굶은 이주를 WARMUP_STEPS 스텝 돌려 몸을 만든다 */
  const grow = async (N: number, over: Partial<PlasmParams>, warmup = WARMUP_STEPS): Promise<{ sim: PlasmGPU; snap: Snapshot }> => {
    glx.reset(); // 앞의 텍스처를 지운다 (768² 는 150MB 쯤 쓴다)
    const sim = new PlasmGPU(glx, defaultParams({ N, seed: 1, ...over }));
    applyVariant(sim, VARIANTS[2]);
    sim.asyncBounds = false;
    sim.autoBounds = false;
    for (let s = 0; s < warmup; s++) {
      sim.stepOnce();
      if (s % 8 === 7) sim.refreshBounds();
      if (s % 100 === 99) await yieldNow();
    }
    return { sim, snap: sim.snapshot() };
  };

  /** 구성 하나를 지속 측정으로 재서 줄을 더한다 */
  const row = async (sim: PlasmGPU, snap: Snapshot, vi: number, cycles: number, tag?: string): Promise<void> => {
    await whenVisible();
    await yieldNow();
    const v = VARIANTS[vi];
    prepare(sim, snap, vi, cycles);
    const m = sustained(glx, sim, cycles, sustainMs, glCounts);
    if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
    if (!Number.isFinite(sim.readEndStats().volume)) throw new Error('값이 깨졌습니다(유한하지 않은 부피)');
    const N = sim.N;
    const stepsPerSec = 1000 / m.msPerStep;
    const r: BenchRow = {
      N,
      variant: v.name,
      ...(tag ? { tag } : {}),
      cycles,
      drawCalls: Math.round(m.drawsPerStep),
      passes: Math.round(m.passesPerStep),
      msPerStep: m.msPerStep,
      steps: m.steps,
      seconds: m.seconds,
      msSolve: m.msSolve,
      activeFraction: m.activeFraction,
      stepsPerSec,
      pxPerSec: CELLS_PER_STEP * stepsPerSec * (MAP_PX / N),
    };
    if (v.sweep2 && sweep2Error) r.sweep2Missing = true;
    if (glCounts) r.glCalls = Math.round(m.glPerStep);
    rows.push(r);
    log(`  ${N}² ${cycles}사이클 ${v.name}${tag ? ` [${tag}]` : ''}: ${r.drawCalls} 드로콜(패스 ${r.passes}${r.glCalls === undefined ? '' : `, GL 호출 ${r.glCalls}`}), `
      + `${r.msPerStep.toFixed(2)}ms/스텝 (${m.steps}스텝을 ${m.seconds.toFixed(1)}초. 풀이 한 번 ${r.msSolve.toFixed(2)}ms, 영역 ${(r.activeFraction * 100).toFixed(0)}%) → 초당 ${stepsPerSec.toFixed(0)}스텝`);
  };

  /** 규칙 8 을 켠 설정의 줄 (먹고 있는 몸). 위상 무늬의 주기는 격자 한 변의 약수여야 한다 */
  const foodRow = async (N: number): Promise<void> => {
    log(`${N}² 준비 [${FOOD_NAME}] (${FOOD_WARMUP_STEPS}스텝)…`);
    await yieldNow();
    const fed = await grow(N, { triK: (2 * Math.PI) / 100, triP: N % 96 === 0 ? 96 : 128, ...foodParams(FOOD3) }, FOOD_WARMUP_STEPS);
    await row(fed.sim, fed.snap, LOOP_VARIANT, 2, FOOD_NAME);
  };

  const measure = async (N: number): Promise<void> => {
    log(`${N}² 준비 (${WARMUP_STEPS}스텝)…`);
    await yieldNow();
    const { sim, snap } = await grow(N, {});
    sweep2Error = sim.mg.sweep2Error;
    if (sweep2Error && N === sizes[0]) log(`  (두 번 스무딩 셰이더를 쓸 수 없습니다: ${sweep2Error.slice(0, 200)})`);
    bodyArea[String(N)] = sim.readEndStats().area;
    if (usPerTinyDraw === 0) {
      prepare(sim, snap, 2, 2);
      usPerTinyDraw = diffMicros(sim, (k) => sim.mg.benchTinyDraws(k), 1000);
    }
    // 격자마다: 전체 격자(몸이 격자를 덮었을 때의 비용), 몸 주변만, 몸 주변만 + 두 번 스무딩.
    // 드로콜·GL 호출 수를 기록할 때(all=1)는 기준형과 전체 격자 + 두 번 스무딩, 3사이클도
    for (const vi of opts.allVariants ? [0, 1, 2, 3, 4] : [1, 2, 3]) await row(sim, snap, vi, 2);
    if (opts.allVariants && N === profileN) await row(sim, snap, LOOP_VARIANT, 3);
    const loopLine = (L: FrameLoop): void => {
      const one = (full: boolean): string => {
        const held = bestHeld(L, full);
        return `${full ? '전체 격자' : '몸 주변만'} ` + (held ? `프레임당 ${held.spf}스텝(초당 ${held.stepsPerSec.toFixed(0)}스텝, 전진 ${(CELLS_PER_STEP * held.stepsPerSec * (MAP_PX / N)).toFixed(0)}px/s)` : '지킨 설정 없음');
      };
      log(`  프레임 루프 ${N}²: 화면 갱신 주기 ${L.baseMs.toFixed(1)}ms. ${heldLabel(L)}을 지키는 최대 — ${one(false)}, ${one(true)}` + (L.note ? ` (${L.note})` : ''));
    };
    if (opts.view && opts.loop !== false && (N === profileN || N === 256)) {
      const L = await frameLoop(glx, sim, snap, opts.view, log, N === profileN, loopScale, opts.loopCap);
      if (N === profileN) loop = L;
      else loopSmall = L;
      loopLine(L);
      // 처음에 잰 구성 둘을 끝에 한 번 더: 그사이 기기가 뜨거워져 느려졌는지 본다 (전체 격자와 몸 주변만이 다르게 느려지는지도)
      await row(sim, snap, FULL_VARIANT, 2, DRIFT_NAME);
      await row(sim, snap, LOOP_VARIANT, 2, DRIFT_NAME);
    }
    if (N === profileN) {
      if (glCounts) {
        groups = profileGroups(glx, sim, snap, glCounts);
        const sum = groups.reduce((a, g) => a + g.msPerStep, 0);
        // 기본 변형의 한 스텝을 이름별로
        prepare(sim, snap, LOOP_VARIANT, 2);
        const before = new Map(glCounts);
        const steps = 8;
        for (let s = 0; s < steps; s++) sim.stepOnce();
        glByName = {};
        for (const [k, v] of glCounts) {
          const d = (v - (before.get(k) ?? 0)) / steps;
          if (d > 0) glByName[k] = d;
        }
        log(`  ${N}² GL 호출(${VARIANTS[LOOP_VARIANT].name}, 스텝당): ` + Object.entries(glByName).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v}`).join(', '));
        log(`  ${N}² 묶음별 GL 호출(합친 패스 + 몸 주변만): ` + groups.map((g) => `${g.group} ${g.glCalls}`).join(', '));
        log(`  ${N}² 묶음별(합친 패스 + 몸 주변만, 2사이클): ` + groups.map((g) => `${g.group} ${g.passesPerStep}×${g.usPerPass.toFixed(0)}µs`).join(', ') + ` → 합 ${sum.toFixed(2)}ms`);
      }
      probes = probePasses(sim, snap);
      log(`  GL 호출 하나 ${probes.glCall.toFixed(2)}µs, 텍스처 묶기 하나 ${probes.bindTex.toFixed(2)}µs, 쉬고 있을 때의 읽기 한 번 ${probes.syncIdle.toFixed(0)}µs`);
      log(`  패스 하나의 고정 비용(µs): 작은 타깃 번갈아 ${probes.tinyAlt.toFixed(1)}, 같은 타깃 ${probes.tinySame.toFixed(1)}, 프로그램만 번갈아 ${probes.tinyProg.toFixed(1)}, 지우기 ${probes.tinyClear.toFixed(1)}, `
        + `격자 크기 R32F ${probes.bigR32F.toFixed(1)}, RGBA32F ${probes.bigRGBA.toFixed(1)}, RGBA32F 두 장 ${probes.bigMRT.toFixed(1)}`);
      if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
      // 한 스텝이 가는 모델 시간을 늘린 후보 설정 (위상 패스가 4개 는다)
      log(`${N}² 준비 [${FAST_DT_NAME}] (${WARMUP_STEPS}스텝)…`);
      await yieldNow();
      const fast = await grow(N, FAST_DT);
      await row(fast.sim, fast.snap, LOOP_VARIANT, 2, FAST_DT_NAME);
    }
    if (N === profileN || N === 256) await foodRow(N);
  };

  for (const N of sizes) {
    // 큰 격자에서 메모리가 모자라도 앞에서 잰 결과는 남긴다
    try {
      await measure(N);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      errors.push(`${N}²: ${msg}`);
      log(`  ${N}² 는 끝까지 재지 못했습니다: ${msg}`);
      if (glx.lost()) break;
    }
  }
  if (!glx.lost()) glx.reset();
  let webgpu: WebGpuProbe | undefined;
  if (opts.webgpu) {
    webgpu = await webgpuProbe();
    log(`  ${webgpuLine(webgpu)}`);
  }
  return {
    version: 5,
    renderer,
    userAgent: navigator.userAgent,
    usPerTinyDraw,
    rows,
    bodyArea,
    sustainMs,
    lagMargin: LOOP_LAG_MARGIN,
    sweep2Error,
    errors,
    profileN: probes || groups.length > 0 ? profileN : null,
    groups,
    probes,
    ...(glByName ? { glByName } : {}),
    frameLoop: loop,
    frameLoopSmall: loopSmall,
    ...(webgpu ? { webgpu } : {}),
    seconds: (performance.now() - tStart) / 1000,
  };
}

function webgpuLine(w: WebGpuProbe): string {
  if (!w.ok) return `WebGPU: 쓸 수 없음 (${w.error})`;
  let s = `WebGPU(${w.adapter}): 디스패치 하나 ${w.usPerDispatch!.toFixed(1)}µs (한 패스 안에서 잇달아) / 패스를 따로 열면 ${w.usPerPass!.toFixed(1)}µs`;
  if (w.solveRectMs !== undefined) {
    s += ` · 풀이 한 번 흉내(${w.solveN}², 디스패치 ${w.solveDispatches}번): 몸 주변만 ${w.solveRectMs.toFixed(2)}ms` + (w.solveFullMs === undefined ? '' : `, 전체 격자 ${w.solveFullMs.toFixed(2)}ms`);
    if (w.solveRectSustainedMs !== undefined) s += `, 쉬지 않고 돌리면 몸 주변만 ${w.solveRectSustainedMs.toFixed(2)}ms`;
  }
  if (w.error) s += ` (도중에 멈춤: ${w.error})`;
  return s;
}

/** 대화창에 붙이기 쉬운 짧은 요약 (표만 복사해도 GPU 이름과 핵심 수치가 따라가게) */
export function benchSummary(b: BenchResult): string {
  const f = (x: number, d = 2): string => x.toFixed(d);
  const lines: string[] = ['[TheBlob 속도 측정 요약 v5]', `GPU: ${b.renderer}`, `브라우저: ${b.userAgent}`];
  for (const L of [b.frameLoopSmall, b.frameLoop]) {
    if (!L) continue;
    const cell = (r: LoopRow): string => `${r.spf}: ${f(r.msMean, 1)}/${f(r.msP95, 1)}/${f(r.late * 100, 0)}%/${f(r.area * 100, 0)}%`;
    const held = (full: boolean): string => {
      const r = bestHeld(L, full);
      return r ? `프레임당 ${r.spf}스텝, 초당 ${f(r.stepsPerSec, 0)}스텝, 전진 ${f(CELLS_PER_STEP * r.stepsPerSec * (MAP_PX / L.N), 0)}px/s` : '지킨 설정이 없음';
    };
    lines.push(`프레임 루프 (${L.N}², 화면 갱신 주기 ${f(L.baseMs, 1)}ms) — 프레임당 스텝: 간격 평균/95백분위 ms/늦은 프레임/그린 넓이${L.note ? ` [${L.note}]` : ''}`);
    lines.push(`몸 주변만: ${L.rows.map(cell).join(' | ')}`);
    if (L.full.length > 0) lines.push(`전체 격자: ${L.full.map(cell).join(' | ')}`);
    for (const S of [L.sustainedHard, L.sustained]) if (S) lines.push(`지속 ${f(S.seconds, 0)}초 [${S.label}] (프레임당 ${S.spf}스텝) ${sustainedCells(S)}`);
    lines.push(`→ ${heldLabel(L)}을 지키는 최대: 몸 주변만 ${held(false)} · 전체 격자 ${held(true)}`);
  }
  lines.push(`지속 측정 (구성마다 쉬지 않고 ${f(b.sustainMs / 1000, 1)}초, 몸 ${Object.values(b.bodyArea)[0] ?? '-'}셀)`);
  lines.push('격자 사이클 방식 | 드로콜 패스 ms/스텝 초당스텝 풀이한번ms 영역%');
  for (const r of b.rows) lines.push(`${r.N} ${r.cycles} ${r.variant}${r.tag ? ` [${r.tag}]` : ''} | ${r.drawCalls} ${r.passes} ${f(r.msPerStep)} ${f(r.stepsPerSec, 0)} ${f(r.msSolve)} ${f(r.activeFraction * 100, 1)}`);
  if (b.probes) {
    const p = b.probes;
    lines.push(`패스 하나의 고정 비용(µs): 작은 타깃 번갈아 ${f(p.tinyAlt, 1)} / 같은 타깃 ${f(p.tinySame, 1)} / 프로그램만 번갈아 ${f(p.tinyProg, 1)} / 지우기 ${f(p.tinyClear, 1)} / 격자 크기 R32F ${f(p.bigR32F, 1)} / RGBA32F ${f(p.bigRGBA, 1)} / RGBA32F 두 장 ${f(p.bigMRT, 1)}`);
    lines.push(`GL 호출 하나 ${f(p.glCall)}µs / 텍스처 묶기 하나 ${f(p.bindTex)}µs / 쉬고 있을 때의 읽기 한 번 ${f(p.syncIdle, 0)}µs`);
  } else {
    lines.push(`드로콜 하나의 고정 비용: ${f(b.usPerTinyDraw, 1)}µs`);
  }
  if (b.webgpu) lines.push(webgpuLine(b.webgpu));
  if (b.groups.length > 0) {
    lines.push(`묶음별 (${b.profileN}², 합친 패스 + 몸 주변만, 2사이클) — 묶음 패스수×µs`);
    lines.push(b.groups.map((g) => `${g.group} ${g.passesPerStep}×${f(g.usPerPass, 1)}`).join(', '));
  }
  if (b.sweep2Error) lines.push(`두 번 스무딩 셰이더 오류: ${b.sweep2Error.slice(0, 200)}`);
  if (b.errors.length > 0) lines.push(`끝까지 재지 못함: ${b.errors.join(' / ')}`);
  return lines.join('\n');
}
