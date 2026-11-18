// A3 벤치마크 — 스텝당 시간과 드로콜 수를 격자·수단별로 잰다
//
// 재는 법
// - 격자마다 굶은 이주를 400스텝 돌려 몸(약 1900셀)을 만들고 그 상태를 읽어 둔다. 변형마다 그 상태로 되돌린 뒤 같은 스텝 수를 재므로
//   모든 변형이 같은 몸을 잰다(변형은 산술이 같아 몸이 똑같이 자란다).
// - 구간 하나는 스텝을 k 번 돌리고 마지막 출력에서 텍셀 하나를 읽어 GPU 가 끝나기를 기다리는 것이다. 그 읽기에는 일의 양과 무관한
//   고정 시간(프로세스 사이의 왕복, 드라이버가 멈추는 시간)이 든다. 그래서 길이가 다른 두 구간(q 스텝, 3q 스텝)을 재서
//   두 가지 값을 낸다: 든 시간을 스텝 수로 나눈 값(msPerStep. 읽기 시간이 들어 있다)과, 두 구간의 차이를 2q 로 나눈 값
//   (msDiff. 읽기의 고정 시간이 빠진다). 고정 시간이 얼마였는지도 적는다(msFixed).
// - 블록 하나: q 스텝 구간, 압력 풀이만 q 번·3q 번 돌린 구간, 3q 스텝 구간. 블록들의 중앙값을 쓴다.
// - 블록의 스텝 수(4q)는 가장 빠른 변형의 블록이 60ms 쯤 되게 격자마다 한 번 정한다(시계의 눈금이 1ms 인 브라우저가 있다).
// - 프레임 루프 시험: 위의 값은 일을 몰아서 시켰을 때의 처리량이다. 게임은 프레임마다 조금씩 시키므로, 화면 갱신(requestAnimationFrame)에
//   맞춰 프레임당 스텝 수를 늘려 가며 프레임 간격이 얼마나 유지되는지를 따로 잰다. 게임에서 쓸 수 있는 속도는 이쪽 값이다.
// - 벽시계로 재므로 드라이버의 CPU 시간까지 들어간다. 드로콜 수가 많은 이 작업에서는 그쪽이 실제 비용에 가깝다.
//   (타이머 질의는 쓰지 않는다. GPU 쪽 시간만 재고, 브라우저에 따라 꺼져 있거나 거칠다.)
// - "몸 주변만" 변형은 경계 상자를 블록마다 그 자리에서 읽는다. 게임 루프에서는 한두 프레임 늦게 도착해 여유가 더 크므로
//   그만큼(LOOP_LAG_MARGIN)을 여유에 더해 잰다. 이 변형은 작은 몸의 비용을, 나머지는 몸이 격자를 다 덮었을 때의 비용을 보여 준다.
// 소프트웨어 렌더러에서는 시간 수치가 뜻이 없다(드로콜 수와 상대 비중만 본다).

import type { Glx } from '../gpu/plasm/glx';
import { PlasmGPU, type PassGroup, type Snapshot } from '../gpu/plasm/PlasmGPU';
import { defaultParams } from '../gpu/plasm/params';
import { totalCalls } from './glCount';
import { applyVariant, VARIANTS, type Log } from './tests';
import { webgpuProbe, type WebGpuProbe } from './webgpuProbe';

export interface BenchRow {
  N: number;
  variant: string;
  cycles: number;
  drawCalls: number;
  /** 스텝당 패스 수: 드로콜에 타깃을 지우는 횟수를 더한 것 */
  passes: number;
  /** 스텝당 시간: 블록의 두 구간에 든 시간을 스텝 수로 나눈 값의 블록 중앙값 (구간 끝의 읽기 시간이 들어 있다) */
  msPerStep: number;
  /** 블록마다의 스텝당 시간 (흩어짐을 볼 수 있게) */
  msBlocks: number[];
  /** 압력 풀이(조대 연산자 재구성 + V 사이클) 한 번의 시간. 풀이만 따로 연달아 돌려 같은 방법으로 잰 것의 중앙값 */
  msSolve: number;
  /** 길이가 다른 두 구간의 차이로 구한 스텝당 시간과 풀이 한 번의 시간 (읽기의 고정 시간이 빠진 값). 잡음에 더 민감하다 */
  msDiff: number;
  msSolveDiff: number;
  /** 구간 끝의 읽기에 드는 고정 시간(ms)의 중앙값 */
  msFixed: number;
  /** 그리는 영역이 격자에서 차지하는 비율 (스텝 평균) */
  activeFraction: number;
  /** 프레임 4ms 로 돌릴 수 있는 프레임당 스텝 수 */
  stepsPerFrame: number;
  /** 그때 화면의 전진 속도(px/s, 지도 1500px 기준)와 맥동 주기(초) */
  pxPerSec: number;
  pulseSec: number;
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

export interface BenchResult {
  renderer: string;
  userAgent: string;
  /** 작은 타깃에 그리는 드로콜 하나의 시간(µs) — 드로콜마다 드는 고정 비용 */
  usPerTinyDraw: number;
  rows: BenchRow[];
  /** 잰 몸의 넓이(셀) */
  bodyArea: Record<string, number>;
  /** 격자마다 블록 하나의 스텝 수 */
  blockSteps: Record<string, number>;
  blocks: number;
  /** "몸 주변만" 변형의 여유에 더한 셀 수 */
  lagMargin: number;
  /** 두 번 스무딩 셰이더가 컴파일되지 않았으면 그 오류 */
  sweep2Error: string | null;
  /** 끝까지 재지 못한 격자와 그 이유 (메모리 부족으로 컨텍스트를 잃은 경우 등) */
  errors: string[];
  /** 탭이 가려져 버리고 다시 잰 블록 수 */
  hiddenBlocks: number;
  /** 묶음별 비용과 타깃 종류별 고정 비용 (profileN 격자, "합친 패스 + 몸 주변만", 2사이클) */
  profileN: number | null;
  groups: GroupCost[];
  probes: PassProbes | null;
  /** 한 스텝의 GL 함수 호출 수를 이름별로 (profileN 격자, 가장 빠른 변형, 2사이클. count=1 로 열었을 때만) */
  glByName?: Record<string, number>;
  /** 화면 갱신에 맞춘 프레임 루프에서 프레임당 스텝 수별 프레임 간격 (profileN 격자, 가장 빠른 변형) */
  frameLoop: FrameLoop | null;
  /** 같은 기기에서 WebGPU 의 계산 디스패치 하나가 드는 고정 비용 */
  webgpu: WebGpuProbe;
  seconds: number;
}

export interface FrameLoopRow {
  /** 프레임당 스텝 수 */
  spf: number;
  frames: number;
  /** 프레임 간격(ms)의 평균, 중앙값, 95백분위 */
  msMean: number;
  msMedian: number;
  msP95: number;
  /** 초당 스텝 수 (spf × 1000 / 평균 간격) */
  stepsPerSec: number;
}

export interface FrameLoop {
  N: number;
  /** 시뮬레이션 없이 화면만 그릴 때의 프레임 간격(ms) — 화면의 갱신 주기 */
  baseMs: number;
  rows: FrameLoopRow[];
  /** 끝까지 재지 못했으면 그 이유 */
  note?: string;
}

export interface BenchOptions {
  /** 블록 하나의 스텝 수(짝수). 주지 않으면 격자마다 자동으로 정한다. 드로콜 수만 볼 때는 2 */
  block?: number;
  /** 블록 수. 기본 6 */
  blocks?: number;
  /** GL 호출을 세는 껍데기의 계수기 (glCount.ts). 주면 스텝당 GL 호출 수를 함께 적는다 */
  glCounts?: Map<string, number>;
  /** 화면에 그리는 함수. 주면 프레임 루프 시험을 한다 */
  view?: (sim: PlasmGPU) => void;
}

const FRAME_BUDGET_MS = 4;
/** 게임 지도의 한 변(px) */
export const MAP_PX = 1500;
/** 전진면의 속도(셀/스텝). numpy 기준 실행의 값 (dt = 0.1) */
export const CELLS_PER_STEP = 0.02;
/** 맥동 한 주기의 스텝 수 (주기 4, dt = 0.1) */
export const STEPS_PER_PULSE = 40;
const WARMUP_STEPS = 400;
const DEFAULT_BLOCKS = 6;
const MIN_BLOCK = 16;
const MAX_BLOCK = 256;
const TARGET_BLOCK_MS = 60;
/** 프레임 루프 시험에서 해 보는 프레임당 스텝 수 */
const LOOP_SPFS = [1, 2, 3, 4, 6, 8, 12, 16];
/** 이 간격(ms) 안이면 60fps 를 지킨 것으로 본다 */
export const HELD_MS = 18.5;
/** 게임 루프에서 경계 상자가 늦게 도착하는 만큼 여유에 더하는 셀 수 (프레임당 8~16스텝에 한 프레임 늦는 경우쯤) */
const LOOP_LAG_MARGIN = 8;

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

/** 드로콜마다 드는 고정 비용: 가장 작은 레벨에 가벼운 패스를 연달아 그린다 */
function tinyDrawCost(sim: PlasmGPU): number {
  return diffMicros(sim, (k) => sim.mg.benchTinyDraws(k), 1000);
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
  sim.marginExtra = v.scissor ? LOOP_LAG_MARGIN : 0;
  sim.refreshBounds();
  for (let s = 0; s < 4; s++) sim.stepOnce(); // 셰이더와 캐시를 데운다
}

const PROFILE_GROUPS: (PassGroup | 'build' | 'cycle')[] = ['edges', 'phase', 'rest', 'init', 'build', 'cycle', 'flux', 'q0', 'reinforce', 'dry', 'blur', 'wet'];
const GROUP_NAMES: Record<string, string> = {
  edges: '간선 켜기', phase: '위상', rest: '쉬는 두께·가중치', init: '웜스타트', build: '조대 연산자', cycle: 'V 사이클',
  flux: '유량', q0: '전역 평균', reinforce: '강화', dry: '마름', blur: '흐림', wet: '젖음',
};

/** 묶음 하나를 따로 연달아 돌려 패스 하나의 시간을 잰다. 같은 입력으로 되풀이하므로 재기 전에 상태를 되돌린다 */
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
  // 쉬고 있을 때의 읽기 한 번
  const idle: number[] = [];
  sim.sync();
  for (let i = 0; i < 9; i++) {
    const t0 = performance.now();
    sim.sync();
    idle.push((performance.now() - t0) * 1000);
  }
  return {
    tinyAlt: time((k) => sim.mg.benchTinyDraws(k)),
    tinySame: time((k) => sim.mg.benchTinySame(k)),
    tinyProg: time((k) => sim.mg.benchTinyProg(k)),
    tinyClear: time((k) => sim.mg.benchTinyClears(k)),
    syncIdle: median(idle),
    glCall: time((k) => sim.mg.benchCalls(k), n * 5),
    bindTex: time((k) => sim.mg.benchBinds(k), n * 5),
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

/**
 * 게임과 같은 꼴의 루프: 화면 갱신마다 스텝을 spf 번 돌리고 화면을 그린다. 경계 상자도 게임처럼 멈춤 없이 읽는다.
 * 프레임당 스텝 수를 늘려 가며 프레임 간격을 잰다. 간격이 화면의 갱신 주기에 머무는 동안은 그 스텝 수를 감당하는 것이다
 */
async function frameLoop(glx: Glx, sim: PlasmGPU, snap: Snapshot, view: (sim: PlasmGPU) => void, log: Log): Promise<FrameLoop> {
  const out: FrameLoop = { N: sim.N, baseMs: 0, rows: [] };
  // 프레임 간격들. 앞의 몇 프레임은 버린다
  const run = async (spf: number, maxFrames: number, maxMs: number): Promise<number[] | null> => {
    const ts: number[] = [];
    const start = performance.now();
    while (ts.length < maxFrames && (performance.now() - start < maxMs || ts.length < 16)) {
      const t = await nextFrame();
      if (t === null) return null;
      for (let i = 0; i < spf; i++) sim.stepOnce();
      view(sim);
      ts.push(t);
    }
    const dt: number[] = [];
    for (let i = 6; i < ts.length; i++) dt.push(ts[i] - ts[i - 1]);
    return dt;
  };
  const base = await run(0, 40, 1500);
  if (!base) return { ...out, note: '화면 갱신이 오지 않았습니다(탭이 가려짐)' };
  out.baseMs = median(base);
  for (const spf of LOOP_SPFS) {
    prepare(sim, snap, 3, 2);
    sim.asyncBounds = true;
    sim.autoBounds = true;
    sim.marginExtra = 0;
    const dt = await run(spf, 76, 4000);
    if (!dt) return { ...out, note: '화면 갱신이 오지 않았습니다(탭이 가려짐)' };
    if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
    const sorted = dt.slice().sort((a, b) => a - b);
    const msMean = dt.reduce((a, b) => a + b, 0) / dt.length;
    const row: FrameLoopRow = { spf, frames: dt.length, msMean, msMedian: median(dt), msP95: sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))], stepsPerSec: (spf * 1000) / msMean };
    out.rows.push(row);
    log(`  프레임 루프 ${sim.N}² 프레임당 ${spf}스텝: 간격 평균 ${msMean.toFixed(1)}ms (중앙 ${row.msMedian.toFixed(1)}, 95백분위 ${row.msP95.toFixed(1)}) → 초당 ${row.stepsPerSec.toFixed(0)}스텝`);
    // 초당 27프레임 아래로 떨어지면 더 늘려 볼 까닭이 없다
    if (msMean > 2.2 * Math.max(out.baseMs, 16.7)) break;
  }
  return out;
}

/** 프레임 간격이 이 값(ms) 안이면 화면 갱신을 지킨 것으로 본다. 화면이 초당 60프레임보다 느리게 갱신되는 기기(절전 모드 등)에서는 그 주기를 기준으로 한다 */
export function heldLimit(loop: FrameLoop): number {
  return Math.max(HELD_MS, loop.baseMs * 1.12);
}

/** "초당 60프레임" 또는 그 화면의 갱신 속도 */
export function heldLabel(loop: FrameLoop): string {
  return loop.baseMs > HELD_MS ? `초당 ${Math.round(1000 / loop.baseMs)}프레임(이 화면의 갱신 속도)` : '초당 60프레임';
}

/** 프레임 루프 시험에서 화면 갱신을 지킨 줄 가운데 초당 스텝이 가장 많은 것 */
export function bestHeld(loop: FrameLoop | null): FrameLoopRow | null {
  let best: FrameLoopRow | null = null;
  if (!loop) return null;
  const limit = heldLimit(loop);
  for (const r of loop.rows) if (r.msMean <= limit && (!best || r.stepsPerSec > best.stepsPerSec)) best = r;
  return best;
}

export async function runBench(glx: Glx, renderer: string, sizes: number[], log: Log, opts: BenchOptions = {}): Promise<BenchResult> {
  const blocks = Math.max(1, Math.round(opts.blocks ?? DEFAULT_BLOCKS));
  const tStart = performance.now();
  const rows: BenchRow[] = [];
  const bodyArea: Record<string, number> = {};
  const blockSteps: Record<string, number> = {};
  let usPerTinyDraw = 0;
  let sweep2Error: string | null = null;
  let hiddenBlocks = 0;
  const errors: string[] = [];
  // 묶음별 비용은 격자 하나에서만 잰다 (384² 가 있으면 그것, 없으면 첫 격자)
  const profileN = sizes.includes(384) ? 384 : (sizes[0] ?? null);
  let groups: GroupCost[] = [];
  let probes: PassProbes | null = null;
  const glCounts = opts.glCounts;
  let glByName: Record<string, number> | undefined;
  let loop: FrameLoop | null = null;

  const measure = async (N: number): Promise<void> => {
    log(`${N}² 준비 (${WARMUP_STEPS}스텝)…`);
    await yieldNow();
    glx.reset(); // 앞 격자의 텍스처를 지운다 (768² 는 150MB 쯤 쓴다)
    const sim = new PlasmGPU(glx, defaultParams({ N, seed: 1 }));
    sweep2Error = sim.mg.sweep2Error;
    if (sweep2Error && N === sizes[0]) log(`  (두 번 스무딩 셰이더를 쓸 수 없습니다: ${sweep2Error.slice(0, 200)})`);
    applyVariant(sim, VARIANTS[2]);
    sim.asyncBounds = false;
    sim.autoBounds = false;
    for (let s = 0; s < WARMUP_STEPS; s++) {
      sim.stepOnce();
      if (s % 8 === 7) sim.refreshBounds();
      if (s % 100 === 99) await yieldNow();
    }
    bodyArea[String(N)] = sim.readEndStats().area;
    const snap = sim.snapshot();
    if (usPerTinyDraw === 0) usPerTinyDraw = tinyDrawCost(sim);

    // 블록의 스텝 수: 가장 빠른 변형으로 16스텝을 재서 정한다. 이 격자의 모든 변형이 같은 값을 쓴다
    let block = opts.block === undefined ? 0 : Math.max(4, 4 * Math.round(opts.block / 4));
    if (block === 0) {
      prepare(sim, snap, 3, 2);
      sim.sync();
      const t0 = performance.now();
      for (let s = 0; s < MIN_BLOCK; s++) sim.stepOnce();
      sim.sync();
      const ms16 = Math.max(performance.now() - t0, 0.05);
      block = Math.min(MAX_BLOCK, Math.max(MIN_BLOCK, MIN_BLOCK * Math.ceil(TARGET_BLOCK_MS / ms16)));
    }
    blockSteps[String(N)] = block;
    const q = block / 4;
    const nc = sim.params.mgCoarseSweeps;

    for (const cycles of [2, 3]) {
      for (let vi = 0; vi < VARIANTS.length; vi++) {
        const v = VARIANTS[vi];
        prepare(sim, snap, vi, cycles);
        const stepMs: number[] = [];
        const solveMs: number[] = [];
        const diffMs: number[] = [];
        const solveDiffMs: number[] = [];
        const fixedMs: number[] = [];
        let draws = 0, clears = 0, frac = 0, retries = 0, gls = 0;
        while (stepMs.length < blocks) {
          await whenVisible();
          let bd = 0, bc = 0, bg = 0, bf = 0;
          // 스텝을 k 번 돌리고 끝을 맞춘다. 재기 전에 경계 상자를 새로 읽어 두 구간이 같은 여유에서 출발하게 한다
          const steps = (k: number): number => {
            sim.refreshBounds();
            sim.sync(); // GPU 를 비운다
            const d = glx.drawCalls, c = glx.clearCalls, g = glCounts ? totalCalls(glCounts) : 0;
            const t = performance.now();
            for (let i = 0; i < k; i++) {
              sim.stepOnce();
              bf += sim.activeFraction();
            }
            bd += glx.drawCalls - d;
            bc += glx.clearCalls - c;
            if (glCounts) bg += totalCalls(glCounts) - g;
            sim.sync();
            return performance.now() - t;
          };
          // 풀이만: 같은 상태에서 조대 연산자 재구성과 V 사이클을 연달아 돌린다. 시뮬레이션의 상태는 바뀌지 않는다
          const solves = (k: number): number => {
            const t = performance.now();
            for (let i = 0; i < k; i++) {
              sim.mg.build();
              sim.mg.solve(cycles, nc);
            }
            sim.mg.sync();
            return performance.now() - t;
          };
          const a = steps(q);
          const sa = solves(q);
          const sb = solves(3 * q);
          const b = steps(3 * q);
          if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
          if (document.hidden && retries < 20) {
            // 탭이 가려진 동안 잰 블록은 믿을 수 없다. 버리고 다시 잰다 (몸은 한 블록만큼 더 자란다)
            retries++;
            hiddenBlocks++;
            continue;
          }
          const per = (b - a) / (2 * q);
          stepMs.push((a + b) / block);
          solveMs.push((sa + sb) / block);
          diffMs.push(per);
          solveDiffMs.push((sb - sa) / (2 * q));
          fixedMs.push(a - q * per);
          draws += bd;
          clears += bc;
          gls += bg;
          frac += bf;
          await yieldNow();
        }
        if (!Number.isFinite(sim.readEndStats().volume)) throw new Error('값이 깨졌습니다(유한하지 않은 부피)');
        const msPerStep = median(stepMs);
        const msSolve = median(solveMs);
        const msDiff = median(diffMs);
        const msFixed = median(fixedMs);
        const stepsPerFrame = FRAME_BUDGET_MS / msPerStep;
        const row: BenchRow = {
          N,
          variant: v.name,
          cycles,
          drawCalls: Math.round(draws / (block * blocks)),
          passes: Math.round((draws + clears) / (block * blocks)),
          msPerStep,
          msBlocks: stepMs.map((x) => Math.round(x * 1000) / 1000),
          msSolve,
          msDiff,
          msSolveDiff: median(solveDiffMs),
          msFixed,
          activeFraction: frac / (block * blocks),
          stepsPerFrame,
          pxPerSec: CELLS_PER_STEP * stepsPerFrame * 60 * (MAP_PX / N),
          pulseSec: STEPS_PER_PULSE / (60 * stepsPerFrame),
        };
        if (v.sweep2 && sweep2Error) row.sweep2Missing = true;
        if (glCounts) row.glCalls = Math.round(gls / (block * blocks));
        rows.push(row);
        log(`  ${N}² ${cycles}사이클 ${v.name}: ${row.drawCalls} 드로콜(패스 ${row.passes}${row.glCalls === undefined ? '' : `, GL 호출 ${row.glCalls}`}), ${msPerStep.toFixed(2)}ms/스텝 (풀이 한 번 ${msSolve.toFixed(2)}ms. 차이 방식 ${msDiff.toFixed(2)}ms, 읽기 고정 ${msFixed.toFixed(2)}ms. 영역 ${(row.activeFraction * 100).toFixed(0)}%) → 4ms 예산이면 프레임당 ${stepsPerFrame.toFixed(1)}스텝, 전진 ${row.pxPerSec.toFixed(0)}px/s, 맥동 ${row.pulseSec.toFixed(2)}초`);
      }
    }
    if (N === profileN && opts.view) {
      loop = await frameLoop(glx, sim, snap, opts.view, log);
      const held = bestHeld(loop);
      log(`  프레임 루프: 화면 갱신 주기 ${loop.baseMs.toFixed(1)}ms. ` + (held
        ? `${heldLabel(loop)}을 지키는 최대는 프레임당 ${held.spf}스텝(초당 ${held.stepsPerSec.toFixed(0)}스텝) → 전진 ${(CELLS_PER_STEP * held.stepsPerSec * (MAP_PX / N)).toFixed(0)}px/s`
        : `프레임당 1스텝도 ${heldLabel(loop)}을 지키지 못했습니다`) + (loop.note ? ` (${loop.note})` : ''));
    }
    if (N === profileN) {
      groups = profileGroups(glx, sim, snap, glCounts);
      const sum = groups.reduce((a, g) => a + g.msPerStep, 0);
      if (glCounts) {
        // 가장 빠른 변형의 한 스텝을 이름별로
        prepare(sim, snap, 3, 2);
        const before = new Map(glCounts);
        const steps = 8;
        for (let s = 0; s < steps; s++) sim.stepOnce();
        glByName = {};
        for (const [k, v] of glCounts) {
          const d = (v - (before.get(k) ?? 0)) / steps;
          if (d > 0) glByName[k] = d;
        }
        log(`  ${N}² GL 호출(합친 패스 + 몸 주변만 + 두 번 스무딩, 스텝당): ` + Object.entries(glByName).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v}`).join(', '));
        log(`  ${N}² 묶음별 GL 호출(합친 패스 + 몸 주변만): ` + groups.map((g) => `${g.group} ${g.glCalls}`).join(', '));
      }
      log(`  ${N}² 묶음별(합친 패스 + 몸 주변만, 2사이클): ` + groups.map((g) => `${g.group} ${g.passesPerStep}×${g.usPerPass.toFixed(0)}µs`).join(', ') + ` → 합 ${sum.toFixed(2)}ms`);
      probes = probePasses(sim, snap);
      log(`  GL 호출 하나 ${probes.glCall.toFixed(2)}µs, 텍스처 묶기 하나 ${probes.bindTex.toFixed(2)}µs, 쉬고 있을 때의 읽기 한 번 ${probes.syncIdle.toFixed(0)}µs`);
      log(`  패스 하나의 고정 비용(µs): 작은 타깃 번갈아 ${probes.tinyAlt.toFixed(1)}, 같은 타깃 ${probes.tinySame.toFixed(1)}, 프로그램만 번갈아 ${probes.tinyProg.toFixed(1)}, 지우기 ${probes.tinyClear.toFixed(1)}, `
        + `격자 크기 R32F ${probes.bigR32F.toFixed(1)}, RGBA32F ${probes.bigRGBA.toFixed(1)}, RGBA32F 두 장 ${probes.bigMRT.toFixed(1)}`);
      if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
    }
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
  const webgpu = await webgpuProbe();
  log(webgpu.ok
    ? `  WebGPU(${webgpu.adapter}): 계산 디스패치 하나 ${webgpu.usPerDispatch!.toFixed(1)}µs (한 패스 안에서 잇달아), 패스를 따로 열면 ${webgpu.usPerPass!.toFixed(1)}µs`
    : `  WebGPU: 쓸 수 없음 (${webgpu.error})`);
  return {
    renderer,
    userAgent: navigator.userAgent,
    usPerTinyDraw,
    rows,
    bodyArea,
    blockSteps,
    blocks,
    lagMargin: LOOP_LAG_MARGIN,
    sweep2Error,
    errors,
    hiddenBlocks,
    profileN: groups.length > 0 ? profileN : null,
    groups,
    probes,
    ...(glByName ? { glByName } : {}),
    frameLoop: loop,
    webgpu,
    seconds: (performance.now() - tStart) / 1000,
  };
}

/** 대화창에 붙이기 쉬운 짧은 요약 (표만 복사해도 GPU 이름과 핵심 수치가 따라가게) */
export function benchSummary(b: BenchResult): string {
  const f = (x: number, d = 2): string => x.toFixed(d);
  const lines: string[] = ['[TheBlob 속도 측정 요약 v3]', `GPU: ${b.renderer}`, `브라우저: ${b.userAgent}`];
  if (b.frameLoop) {
    const L = b.frameLoop;
    const held = bestHeld(L);
    lines.push(`프레임 루프 (${L.N}², 화면 갱신 주기 ${f(L.baseMs, 1)}ms) — 프레임당 스텝: 간격 평균/중앙/95백분위 ms${L.note ? ` [${L.note}]` : ''}`);
    lines.push(L.rows.map((r) => `${r.spf}: ${f(r.msMean, 1)}/${f(r.msMedian, 1)}/${f(r.msP95, 1)}`).join(' | '));
    lines.push(held
      ? `→ ${heldLabel(L)}을 지키는 최대: 프레임당 ${held.spf}스텝, 초당 ${f(held.stepsPerSec, 0)}스텝, 전진 ${f(CELLS_PER_STEP * held.stepsPerSec * (MAP_PX / L.N), 0)}px/s`
      : `→ 프레임당 1스텝도 ${heldLabel(L)}을 지키지 못함`);
  }
  if (b.probes) {
    const p = b.probes;
    lines.push(`패스 하나의 고정 비용(µs): 작은 타깃 번갈아 ${f(p.tinyAlt, 1)} / 같은 타깃 ${f(p.tinySame, 1)} / 프로그램만 번갈아 ${f(p.tinyProg, 1)} / 지우기 ${f(p.tinyClear, 1)} / 격자 크기 R32F ${f(p.bigR32F, 1)} / RGBA32F ${f(p.bigRGBA, 1)} / RGBA32F 두 장 ${f(p.bigMRT, 1)}`);
    lines.push(`GL 호출 하나 ${f(p.glCall)}µs / 텍스처 묶기 하나 ${f(p.bindTex)}µs / 쉬고 있을 때의 읽기 한 번 ${f(p.syncIdle, 0)}µs`);
  } else {
    lines.push(`드로콜 하나의 고정 비용: ${f(b.usPerTinyDraw, 1)}µs`);
  }
  lines.push(b.webgpu.ok
    ? `WebGPU(${b.webgpu.adapter}): 디스패치 하나 ${f(b.webgpu.usPerDispatch!, 1)}µs / 패스를 따로 열면 ${f(b.webgpu.usPerPass!, 1)}µs`
    : `WebGPU: 쓸 수 없음 (${b.webgpu.error})`);
  lines.push(`블록 ${b.blocks}개, 블록의 스텝 수 ${Object.entries(b.blockSteps).map(([n, v]) => `${n}²:${v}`).join(' ')}, 몸 ${Object.values(b.bodyArea)[0] ?? '-'}셀, 가려져 버린 블록 ${b.hiddenBlocks}`);
  lines.push('격자 사이클 방식 | 드로콜 패스 ms/스텝 풀이한번 | 차이방식: ms/스텝 풀이한번 읽기고정ms | 영역%');
  for (const r of b.rows) lines.push(`${r.N} ${r.cycles} ${r.variant} | ${r.drawCalls} ${r.passes} ${f(r.msPerStep)} ${f(r.msSolve)} | ${f(r.msDiff)} ${f(r.msSolveDiff)} ${f(r.msFixed)} | ${f(r.activeFraction * 100, 1)}`);
  if (b.groups.length > 0) {
    lines.push(`묶음별 (${b.profileN}², 합친 패스 + 몸 주변만, 2사이클) — 묶음 패스수×µs`);
    lines.push(b.groups.map((g) => `${g.group} ${g.passesPerStep}×${f(g.usPerPass, 1)}`).join(', '));
  }
  if (b.sweep2Error) lines.push(`두 번 스무딩 셰이더 오류: ${b.sweep2Error.slice(0, 200)}`);
  if (b.errors.length > 0) lines.push(`끝까지 재지 못함: ${b.errors.join(' / ')}`);
  return lines.join('\n');
}
