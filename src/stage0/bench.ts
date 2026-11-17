// A3 벤치마크 — 스텝당 시간과 드로콜 수를 격자·수단별로 잰다
//
// 재는 법
// - 격자마다 굶은 이주를 400스텝 돌려 몸(약 1900셀)을 만들고 그 상태를 읽어 둔다. 변형마다 그 상태로 되돌린 뒤 같은 스텝 수를 재므로
//   모든 변형이 같은 몸을 잰다(변형은 산술이 같아 몸이 똑같이 자란다).
// - 블록 하나: 앞에서 GPU 를 비우고, 스텝을 절반 돌리고, 압력 풀이만 따로 연달아 돌리고, 나머지 절반을 돌린다. 구간마다 그 구간의
//   마지막 출력에서 텍셀 하나를 읽어 끝나기를 기다린다. 스텝 시간과 풀이 시간을 따로 모으고 블록들의 중앙값을 쓴다.
// - 블록의 스텝 수는 가장 빠른 변형의 블록이 40ms 쯤 되게 격자마다 한 번 정한다(시계의 눈금이 1ms 인 브라우저가 있다).
// - 벽시계로 재므로 드라이버의 CPU 시간까지 들어간다. 드로콜 수가 많은 이 작업에서는 그쪽이 실제 비용에 가깝다.
//   (타이머 질의는 쓰지 않는다. GPU 쪽 시간만 재고, 브라우저에 따라 꺼져 있거나 거칠다.)
// - "몸 주변만" 변형은 경계 상자를 블록마다 그 자리에서 읽는다. 게임 루프에서는 한두 프레임 늦게 도착해 여유가 더 크므로
//   그만큼(LOOP_LAG_MARGIN)을 여유에 더해 잰다. 이 변형은 작은 몸의 비용을, 나머지는 몸이 격자를 다 덮었을 때의 비용을 보여 준다.
// 소프트웨어 렌더러에서는 시간 수치가 뜻이 없다(드로콜 수와 상대 비중만 본다).

import type { Glx } from '../gpu/plasm/glx';
import { PlasmGPU, type Snapshot } from '../gpu/plasm/PlasmGPU';
import { defaultParams } from '../gpu/plasm/params';
import { applyVariant, VARIANTS, type Log } from './tests';

export interface BenchRow {
  N: number;
  variant: string;
  cycles: number;
  drawCalls: number;
  /** 스텝당 시간: 블록들의 중앙값 */
  msPerStep: number;
  /** 블록마다의 스텝당 시간 (흩어짐을 볼 수 있게) */
  msBlocks: number[];
  /** 압력 풀이(조대 연산자 재구성 + V 사이클) 한 번의 시간. 블록 가운데에서 풀이만 따로 연달아 돌려 잰 것의 중앙값 */
  msSolve: number;
  /** 그리는 영역이 격자에서 차지하는 비율 (스텝 평균) */
  activeFraction: number;
  /** 프레임 4ms 로 돌릴 수 있는 프레임당 스텝 수 */
  stepsPerFrame: number;
  /** 그때 화면의 전진 속도(px/s, 지도 1500px 기준)와 맥동 주기(초) */
  pxPerSec: number;
  pulseSec: number;
  /** 두 번 스무딩을 요청했지만 셰이더가 컴파일되지 않아 쓰지 못했으면 true */
  sweep2Missing?: boolean;
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
  seconds: number;
}

export interface BenchOptions {
  /** 블록 하나의 스텝 수(짝수). 주지 않으면 격자마다 자동으로 정한다. 드로콜 수만 볼 때는 2 */
  block?: number;
  /** 블록 수. 기본 6 */
  blocks?: number;
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
const TARGET_BLOCK_MS = 40;
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
  const n = 4000;
  sim.sync();
  const t0 = performance.now();
  sim.mg.benchTinyDraws(n);
  return ((performance.now() - t0) / n) * 1000;
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

  const measure = async (N: number): Promise<void> => {
    log(`${N}² 준비 (${WARMUP_STEPS}스텝)…`);
    await yieldNow();
    glx.reset(); // 앞 격자의 텍스처를 지운다 (768² 는 150MB 쯤 쓴다)
    const sim = new PlasmGPU(glx, defaultParams({ N, seed: 1 }));
    sweep2Error = sim.mg.sweep2Error;
    if (sweep2Error && N === sizes[0]) log(`  (두 번 스무딩 셰이더를 쓸 수 없습니다: ${sweep2Error.slice(0, 200)})`);
    sim.asyncBounds = false;
    sim.autoBounds = false;
    sim.mg.merged = true;
    sim.scissor = true;
    for (let s = 0; s < WARMUP_STEPS; s++) {
      sim.stepOnce();
      if (s % 8 === 7) sim.refreshBounds();
      if (s % 100 === 99) await yieldNow();
    }
    bodyArea[String(N)] = sim.readEndStats().area;
    const snap = sim.snapshot();
    if (usPerTinyDraw === 0) usPerTinyDraw = tinyDrawCost(sim);

    // 블록의 스텝 수: 가장 빠른 변형으로 16스텝을 재서 정한다. 이 격자의 모든 변형이 같은 값을 쓴다
    let block = opts.block === undefined ? 0 : Math.max(2, 2 * Math.round(opts.block / 2));
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
    const half = block / 2;
    const nc = sim.params.mgCoarseSweeps;

    for (const cycles of [2, 3]) {
      for (let vi = 0; vi < VARIANTS.length; vi++) {
        const v = VARIANTS[vi];
        prepare(sim, snap, vi, cycles);
        const stepMs: number[] = [];
        const solveMs: number[] = [];
        let draws = 0, frac = 0, retries = 0;
        while (stepMs.length < blocks) {
          await whenVisible();
          sim.refreshBounds();
          sim.sync(); // GPU 를 비운다
          const d0 = glx.drawCalls;
          const t0 = performance.now();
          let f = 0;
          for (let s = 0; s < half; s++) {
            sim.stepOnce();
            f += sim.activeFraction();
          }
          sim.sync();
          const t1 = performance.now();
          const d1 = glx.drawCalls;
          // 풀이만: 같은 상태에서 조대 연산자 재구성과 V 사이클을 연달아 돌린다. 시뮬레이션의 상태는 바뀌지 않는다
          for (let s = 0; s < half; s++) {
            sim.mg.build();
            sim.mg.solve(cycles, nc);
          }
          sim.mg.sync();
          const t2 = performance.now();
          const d2 = glx.drawCalls;
          for (let s = 0; s < half; s++) {
            sim.stepOnce();
            f += sim.activeFraction();
          }
          sim.sync();
          const t3 = performance.now();
          if (glx.lost()) throw new Error('GPU 컨텍스트를 잃었습니다');
          if (document.hidden && retries < 20) {
            // 탭이 가려진 동안 잰 블록은 믿을 수 없다. 버리고 다시 잰다 (몸은 한 블록만큼 더 자란다)
            retries++;
            hiddenBlocks++;
            continue;
          }
          stepMs.push((t1 - t0 + (t3 - t2)) / block);
          solveMs.push((t2 - t1) / half);
          draws += d1 - d0 + (glx.drawCalls - d2);
          frac += f;
          await yieldNow();
        }
        if (!Number.isFinite(sim.readEndStats().volume)) throw new Error('값이 깨졌습니다(유한하지 않은 부피)');
        const msPerStep = median(stepMs);
        const msSolve = median(solveMs);
        const stepsPerFrame = FRAME_BUDGET_MS / msPerStep;
        const row: BenchRow = {
          N,
          variant: v.name,
          cycles,
          drawCalls: Math.round(draws / (block * blocks)),
          msPerStep,
          msBlocks: stepMs.map((x) => Math.round(x * 1000) / 1000),
          msSolve,
          activeFraction: frac / (block * blocks),
          stepsPerFrame,
          pxPerSec: CELLS_PER_STEP * stepsPerFrame * 60 * (MAP_PX / N),
          pulseSec: STEPS_PER_PULSE / (60 * stepsPerFrame),
        };
        if (v.sweep2 && sweep2Error) row.sweep2Missing = true;
        rows.push(row);
        log(`  ${N}² ${cycles}사이클 ${v.name}: ${row.drawCalls} 드로콜, ${msPerStep.toFixed(2)}ms/스텝 (풀이 한 번 ${msSolve.toFixed(2)}ms, 영역 ${(row.activeFraction * 100).toFixed(0)}%) → 4ms 예산이면 프레임당 ${stepsPerFrame.toFixed(1)}스텝, 전진 ${row.pxPerSec.toFixed(0)}px/s, 맥동 ${row.pulseSec.toFixed(2)}초`);
      }
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
    seconds: (performance.now() - tStart) / 1000,
  };
}
