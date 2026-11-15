// A3 벤치마크 — 스텝당 시간과 드로콜 수를 격자·수단별로 잰다
//
// 재는 법: 블록(16스텝)마다 앞에서 GPU 를 비우고(1×1 읽기), 스텝을 연달아 돌린 뒤 다시 1×1 을 읽어 끝나기를 기다린다.
// 벽시계로 재므로 드라이버의 CPU 시간까지 들어간다. 드로콜 수가 많은 이 작업에서는 그쪽이 실제 비용에 가깝다.
// (타이머 질의는 쓰지 않는다. GPU 쪽 시간만 재고, 브라우저에 따라 꺼져 있거나 거칠다.)
// 몸은 굶은 이주의 400스텝째 것(약 2700셀)이다. "몸 주변만" 변형은 작은 몸의 비용을, 나머지는 몸이 격자를 다 덮었을 때의 비용을 보여 준다.
// 소프트웨어 렌더러에서는 시간 수치가 뜻이 없다(드로콜 수와 상대 비중만 본다).

import type { Glx } from '../gpu/plasm/glx';
import { PlasmGPU } from '../gpu/plasm/PlasmGPU';
import { defaultParams } from '../gpu/plasm/params';
import { applyVariant, VARIANTS, type Log } from './tests';

export interface BenchRow {
  N: number;
  variant: string;
  cycles: number;
  drawCalls: number;
  msPerStep: number;
  /** 그 가운데 압력 풀이(조대 연산자 재구성 + V 사이클)의 몫. 풀이만 따로 연달아 돌려 잰다 */
  msSolve: number;
  /** 그리는 영역이 격자에서 차지하는 비율 */
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
  bodyArea: Record<string, number>;
  /** 두 번 스무딩 셰이더가 컴파일되지 않았으면 그 오류 */
  sweep2Error: string | null;
  seconds: number;
}

const FRAME_BUDGET_MS = 4;
/** 게임 지도의 한 변(px) */
export const MAP_PX = 1500;
/** 전진면의 속도(셀/스텝). numpy 기준 실행의 값 (dt = 0.1) */
export const CELLS_PER_STEP = 0.02;
/** 맥동 한 주기의 스텝 수 (주기 4, dt = 0.1) */
export const STEPS_PER_PULSE = 40;
const WARMUP_STEPS = 400;
const BLOCK = 16;
const BLOCKS = 6;

const yieldNow = (): Promise<void> => new Promise((r) => setTimeout(r, 0));

/** 드로콜마다 드는 고정 비용: 6×6 타깃에 가벼운 패스를 연달아 그린다 */
function tinyDrawCost(sim: PlasmGPU): number {
  const n = 4000;
  sim.readStepStats();
  const t0 = performance.now();
  sim.mg.benchTinyDraws(n);
  sim.readStepStats();
  return ((performance.now() - t0) / n) * 1000;
}

export async function runBench(glx: Glx, renderer: string, sizes: number[], log: Log): Promise<BenchResult> {
  const tStart = performance.now();
  const rows: BenchRow[] = [];
  const bodyArea: Record<string, number> = {};
  let usPerTinyDraw = 0;
  let sweep2Error: string | null = null;
  for (const N of sizes) {
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
    if (usPerTinyDraw === 0) usPerTinyDraw = tinyDrawCost(sim);
    for (const cycles of [2, 3]) {
      for (const v of VARIANTS) {
        sim.cycles = cycles;
        applyVariant(sim, v);
        sim.refreshBounds();
        for (let s = 0; s < 4; s++) sim.stepOnce(); // 셰이더와 캐시를 데운다
        let ms = 0, draws = 0, frac = 0;
        for (let b = 0; b < BLOCKS; b++) {
          sim.refreshBounds();
          sim.readStepStats(); // GPU 를 비운다
          const d0 = glx.drawCalls;
          const t0 = performance.now();
          for (let s = 0; s < BLOCK; s++) sim.stepOnce();
          sim.readStepStats(); // 끝나기를 기다린다
          ms += performance.now() - t0;
          draws += glx.drawCalls - d0;
          frac += sim.activeFraction();
          await yieldNow();
        }
        const msPerStep = ms / (BLOCK * BLOCKS);
        // 풀이만: 같은 상태에서 조대 연산자 재구성과 V 사이클을 연달아 돌린다 (비용은 상태에 거의 기대지 않는다)
        sim.readStepStats();
        const ts = performance.now();
        for (let s = 0; s < BLOCK * 2; s++) {
          sim.mg.build();
          sim.mg.solve(cycles, sim.params.mgCoarseSweeps);
        }
        sim.readStepStats();
        const msSolve = (performance.now() - ts) / (BLOCK * 2);
        for (let s = 0; s < 4; s++) sim.stepOnce(); // 풀이만 돌리며 흐트러진 압력을 다시 맞춘다
        const stepsPerFrame = FRAME_BUDGET_MS / msPerStep;
        const row: BenchRow = {
          N,
          variant: v.name,
          cycles,
          drawCalls: Math.round(draws / (BLOCK * BLOCKS)),
          msPerStep,
          msSolve,
          activeFraction: frac / BLOCKS,
          stepsPerFrame,
          pxPerSec: CELLS_PER_STEP * stepsPerFrame * 60 * (MAP_PX / N),
          pulseSec: STEPS_PER_PULSE / (60 * stepsPerFrame),
        };
        if (v.sweep2 && sweep2Error) row.sweep2Missing = true;
        rows.push(row);
        log(`  ${N}² ${cycles}사이클 ${v.name}: ${row.drawCalls} 드로콜, ${msPerStep.toFixed(2)}ms/스텝 (그중 풀이 ${msSolve.toFixed(2)}ms, 영역 ${(row.activeFraction * 100).toFixed(0)}%) → 4ms 예산이면 프레임당 ${stepsPerFrame.toFixed(1)}스텝, 전진 ${row.pxPerSec.toFixed(0)}px/s, 맥동 ${row.pulseSec.toFixed(2)}초`);
      }
    }
  }
  return { renderer, userAgent: navigator.userAgent, usPerTinyDraw, rows, bodyArea, sweep2Error, seconds: (performance.now() - tStart) / 1000 };
}
