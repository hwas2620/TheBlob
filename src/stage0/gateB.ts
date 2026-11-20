// 0단계 관문 B — 시나리오를 끝까지 돌리며 판정 도구의 입력을 모은다
//   · 스텝마다: 부피, 음수 두께, 최대 전도도, 먹이별 원반의 평균 두께와 위상, 먹은 양
//   · 구간 통계 (PlasmGPU.enableStats): 맥동 한 주기의 두께 진폭·평균, 다섯 주기의 유량(순·총)과 전도도 평균
//   · 모델 시간 20 마다 상태 덤프를 러너(run_stage0.cjs)로 보낸다. 변환기(metrics/gpu2run.py)가 numpy 실행과 같은 꼴로 바꾼다
// 시점의 규약은 numpy 기준 모델(ref_model.py)과 같다: 스텝 번호 j(0부터)를 돈 뒤의 상태가 t = j·dt 의 덤프다.

import type { Glx } from '../gpu/plasm/glx';
import { PlasmGPU, type PlainState } from '../gpu/plasm/PlasmGPU';
import { PLASM } from '../config';
import { defaultParams, foodParams, type PlasmParams } from '../gpu/plasm/params';
import { fluxError, solveCG } from './cpuSolver';
import { loadManifest, loadRef } from './refData';
import { FOOD3, SCENARIOS } from './scenarios';
import { applyVariant, channel, quantile, refFood, stateHash, toState, VARIANTS, type Log } from './tests';

/** 덤프 한 장에 든 평면의 순서 (metrics/gpu2run.py 의 PLANES 와 같아야 한다) */
export const DUMP_PLANES = [
  'C0', 'C1', 'C2', 'C3', 'wet', 'h', 'age', 'sage', 'theta',
  'Qgross0', 'Qgross1', 'Qgross2', 'Qgross3', 'Qmean0', 'Qmean1', 'Qmean2', 'Qmean3', 'Cmean0', 'Cmean1', 'Cmean2', 'Cmean3', 'hamp', 'hmean',
];

async function post(path: string, data: Float32Array | string): Promise<boolean> {
  try {
    // 실수 배열은 그 구간의 바이트만 복사해서 보낸다 (리틀 엔디언 float32 그대로)
    const body = typeof data === 'string' ? data : new Uint8Array(data.buffer, data.byteOffset, data.byteLength).slice().buffer;
    const r = await fetch('./__dump/' + path, { method: 'POST', body });
    return r.ok;
  } catch {
    return false;
  }
}

/** 구간 통계를 거두고 상태를 덤프한다 */
export class Recorder {
  /** 맥동 한 주기의 스텝 수, 유량 구간(다섯 주기)의 스텝 수, 덤프 간격(모델 시간 20)의 스텝 수 */
  readonly nper: number;
  readonly nwin: number;
  readonly every: number;
  /** 덤프한 시각 */
  readonly dumped: number[] = [];
  /** 덤프를 보내지 못했다 (러너 없이 연 페이지) */
  failed = false;
  private qmean: Float32Array;
  private qgross: Float32Array;
  private cmean: Float32Array;
  private hamp: Float32Array;
  private hmean: Float32Array;
  private sim: PlasmGPU;
  private name: string;
  private on: boolean;
  private log: Log;

  constructor(sim: PlasmGPU, name: string, on: boolean, log: Log) {
    this.sim = sim;
    this.name = name;
    this.on = on;
    this.log = log;
    const p = sim.params;
    const n = sim.N * sim.N;
    this.nper = Math.max(1, Math.round(p.period / p.dt));
    this.nwin = this.nper * 5;
    this.every = Math.max(1, Math.round(20 / p.dt));
    this.qmean = new Float32Array(n * 4);
    this.qgross = new Float32Array(n * 4);
    this.cmean = new Float32Array(n * 4);
    this.hamp = new Float32Array(n);
    this.hmean = new Float32Array(n);
    sim.enableStats();
  }

  /** j = 방금 끝난 스텝의 번호 (0부터) */
  async afterStep(j: number): Promise<void> {
    const n = this.sim.N * this.sim.N;
    if ((j + 1) % this.nper === 0) {
      const s = this.sim.takeThickStats();
      for (let i = 0; i < n; i++) {
        const whole = s.H[i * 4 + 3] > 0.5; // 구간 내내 젖어 있던 셀만
        this.hamp[i] = whole ? 0.5 * (s.H[i * 4 + 1] - s.H[i * 4 + 2]) : 0;
        this.hmean[i] = whole ? s.H[i * 4] / s.n : 0;
      }
    }
    if ((j + 1) % this.nwin === 0) {
      const s = this.sim.takeFlowStats();
      for (let i = 0; i < n * 4; i++) {
        this.qmean[i] = s.Q[i] / s.n;
        this.qgross[i] = s.G[i] / s.n;
        this.cmean[i] = s.C[i] / s.n;
      }
    }
    if (j > 0 && j % this.every === 0) await this.dump(j);
  }

  /** 스텝 j 를 돈 뒤의 상태를 보낸다 */
  async dump(j: number, file?: string): Promise<void> {
    const sim = this.sim;
    const t = j * sim.params.dt;
    if (!this.on || this.failed) return;
    const n = sim.N * sim.N;
    const a = sim.readA();
    const b = sim.readB();
    const c = sim.readC();
    const out = new Float32Array(DUMP_PLANES.length * n);
    for (let i = 0; i < n; i++) {
      for (let k = 0; k < 4; k++) {
        out[k * n + i] = c[i * 4 + k];
        out[(9 + k) * n + i] = this.qgross[i * 4 + k];
        out[(13 + k) * n + i] = this.qmean[i * 4 + k];
        out[(17 + k) * n + i] = this.cmean[i * 4 + k];
      }
      out[4 * n + i] = a[i * 4 + 1];
      out[5 * n + i] = a[i * 4];
      out[6 * n + i] = a[i * 4 + 2];
      out[7 * n + i] = a[i * 4 + 3];
      out[8 * n + i] = b[i * 4];
      out[21 * n + i] = this.hamp[i];
      out[22 * n + i] = this.hmean[i];
    }
    const ok = await post(`${this.name}/${file ?? `vs_t${String(Math.round(t)).padStart(4, '0')}.bin`}`, out);
    if (!ok) {
      this.failed = true;
      this.log('  (상태 덤프를 받는 러너가 없다. 덤프 없이 계속한다)');
      return;
    }
    if (!file) this.dumped.push(t);
  }

  /** 실행의 끝: 스텝마다의 기록과 요약을 보낸다 */
  async finish(meta: unknown, hfood: Float32Array, series: Float32Array): Promise<void> {
    if (!this.on || this.failed) return;
    await post(`${this.name}/hfood.bin`, hfood);
    await post(`${this.name}/series.bin`, series);
    await post(`${this.name}/meta.json`, JSON.stringify(meta));
  }
}

export interface BOptions {
  /** SCENARIOS 의 이름 */
  scn: string;
  seed: number;
  /** 시나리오의 격자를 바꾼다 (384² 확인용) */
  N?: number;
  /** VARIANTS 의 번호 */
  variant: number;
  /** 몸의 경계 상자를 그 자리에서 읽는다 (tests.ts 의 A12Options.syncBounds 와 같다) */
  syncBounds: boolean;
  /** 이 스텝마다 CPU 기준 풀이로 유량 오차를 잰다 */
  checkEvery: number;
  /** 상태 덤프를 러너로 보낸다 */
  dump: boolean;
  /** 실행의 이름 (덤프 폴더의 이름) */
  name: string;
  /** 규칙 8 의 90% 조건을 바꾼다 (0 = 끈다) */
  resGate?: number;
  /** 길이를 바꾼다 (모델 시간. 시험용) */
  T?: number;
  /** 가위 사각형의 여유를 완만하게 키운다 (PlasmGPU.softMargin), 이 스텝마다 이벤트 루프로 돌아간다 (기본 100). tests.ts 의 A12Options 와 같다 */
  softMargin?: boolean;
  yieldEvery?: number;
  /** 규칙 6 의 외톨이 셀 말리기 (기본 켬). 계획 C 이전의 기록과 견줄 때 끈다 */
  crumbDry?: boolean;
  /** 규칙 3 의 얇은 칸 줄임 h_thin (기본 PLASM.THIN_H, 0 = 끔). 계획 D 이전의 기록과 견줄 때 끈다 */
  thinH?: number;
}

export interface BResult extends BOptions {
  what: string;
  variantName: string;
  steps: number;
  stepsDone: number;
  /** '' = 끝까지, 'touched' = 모든 먹이에 닿아서 멈춤, 'all dry' = 몸이 사라짐 */
  stop: string;
  seconds: number;
  drawCallsPerStep: number;
  activeFractionMean: number;
  nan: boolean;
  /** 스텝 끝에 음수 두께인 젖은 셀이 있던 스텝 수, 스텝 끝의 최소 두께, 스텝 안의 최소 두께 */
  negEndSteps: number;
  hMinEnd: number;
  hMinInStep: number;
  cMaxRun: number;
  /** 총 부피: 처음, 끝, 먹은 양, |Σh − 처음 − 먹은 양| / 처음 의 최대 */
  v0: number;
  vEnd: number;
  eaten: number;
  massErrMax: number;
  fluxErr: { n: number; median: number; p90: number; p99: number; max: number };
  /** 먹이마다: 처음 닿은 시각, 원반의 절반을 덮은 시각, 다 떨어진 시각, 끝에 남은 양 */
  tTouch: (number | null)[];
  tCover: (number | null)[];
  tExh: (number | null)[];
  mEnd: number[];
  /** [t, 무게중심 x, y, 넓이, 몸의 범위] (50스텝마다) */
  traj: number[][];
  areaEnd: number;
  /** 새로 젖은 셀 수: 전체, 가운데의 왼쪽 절반 (점액 시나리오에서만 센다) */
  newTotal: number;
  newLeft: number;
  /** 덤프한 시각 */
  dumped: number[];
  dumpFailed: boolean;
  /** 끝 상태의 요약과 여유의 사용률 (tests.ts 의 A12Result 와 같다) */
  stateHash: string;
  marginUse: number;
  marginUseSoft: number;
  marginOverruns: number;
}

/** 점액 시나리오의 처음 상태: 가운데의 원반 + 원반 밖의 점액 흔적 */
function slimeStart(p: PlasmParams, kind: 'half' | 'all'): PlainState {
  const N = p.N;
  const n = N * N;
  const c0 = N / 2 - 0.5;
  const zero = (): Float32Array => new Float32Array(n);
  const s: PlainState = { h: zero(), wet: zero(), age: zero(), sage: zero(), theta: zero(), slime: zero(), C: [zero(), zero(), zero(), zero()], p: zero(), pm: zero() };
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const i = y * N + x;
      if (Math.hypot(x - c0, y - c0) < p.rInit) {
        s.h[i] = p.hInit;
        s.wet[i] = 1;
      } else if (kind === 'all' || x < c0) {
        s.slime[i] = 1;
      }
    }
  }
  return s;
}

/** 관문 B 의 시나리오 하나를 돌린다 */
export async function testB(glx: Glx, opts: BOptions, log: Log, onFrame?: (sim: PlasmGPU) => void): Promise<BResult> {
  const scn = SCENARIOS[opts.scn];
  if (!scn) throw new Error(`모르는 시나리오: ${opts.scn} (${Object.keys(SCENARIOS).join(', ')})`);
  const N = opts.N ?? scn.N;
  const over: Partial<PlasmParams> = { ...scn.over };
  if (opts.resGate !== undefined) over.resGate = opts.resGate;
  // 관문 B 의 시나리오는 모두 외톨이 셀 말리기(계획 C)와 얇은 칸 줄임(계획 D)을 켠다 (numpy 기준 실행의 GB 와 같다). crumb=0, thin=0 으로 끈 길을 돌릴 수 있다
  const params = defaultParams({ N, seed: opts.seed, triK: (2 * Math.PI) / 100, crumbDry: opts.crumbDry ?? true, thinH: opts.thinH ?? PLASM.THIN_H, ...over });
  const sim = new PlasmGPU(glx, params);
  const variant = VARIANTS[opts.variant] ?? VARIANTS[2];
  applyVariant(sim, variant);
  sim.asyncBounds = !opts.syncBounds;
  sim.softMargin = opts.softMargin === true;
  const yieldEvery = Math.max(1, opts.yieldEvery ?? 100);
  if (scn.slime0) sim.loadState(slimeStart(params, scn.slime0), 0);
  const n = N * N;
  const dt = params.dt;
  const T = opts.T ?? scn.T;
  const steps = Math.round(T / dt) + 1; // numpy 기준 모델은 스텝 0 … T/dt 를 돈다
  const nf = params.foods.length;
  const rec = new Recorder(sim, opts.name, opts.dump, log);
  log(`[${opts.scn}] ${scn.what} · ${N}² 시드 ${opts.seed} · ${variant.name} · ${steps}스텝`);

  const t0 = performance.now();
  const v0 = sim.readEndStats().volume;
  const c0 = N / 2 - 0.5;
  const cen = [c0, c0];
  const mimg = (v: number): number => ((((v + N / 2) % N) + N) % N) - N / 2;
  const fluxErrSeries: number[] = [];
  const traj: number[][] = [];
  const hfood = new Float32Array(steps * 2 * Math.max(nf, 1));
  const series = new Float32Array(steps * 4); // 부피, 넓이, 새로 젖은 셀, 그 가운데 왼쪽 절반
  const tTouch: (number | null)[] = params.foods.map(() => null);
  const tCover: (number | null)[] = params.foods.map(() => null);
  const tExh: (number | null)[] = params.foods.map(() => null);
  let mEnd: number[] = params.foods.map(() => (params.foodM > 0 ? params.foodM : Infinity));
  const countNew = !!scn.slime0;
  let prevWet: Uint8Array | null = null;
  if (countNew) {
    const a = sim.readA();
    prevWet = new Uint8Array(n);
    for (let i = 0; i < n; i++) prevWet[i] = a[i * 4 + 1] > 0.5 ? 1 : 0;
  }
  let fracSum = 0, drawCallsPerStep = 0;
  let nan = false, negEndSteps = 0, hMinEnd = Infinity, hMinInStep = Infinity, cMaxRun = 0, areaEnd = 0, vEnd = v0, eaten = 0, massErrMax = 0, stepsDone = 0, newTotal = 0, newLeft = 0;
  let stop = '';

  /** 읽은 cellA 로 무게중심(토러스 최소 상)을 갱신한다 */
  const track = (a: Float32Array, t: number, record: boolean): void => {
    let m = 0, sx = 0, sy = 0, area = 0, extent = 0;
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        const i = (y * N + x) * 4;
        const h = a[i];
        if (!Number.isFinite(h)) nan = true;
        const dx = mimg(x - cen[0]);
        const dy = mimg(y - cen[1]);
        m += h;
        sx += h * dx;
        sy += h * dy;
        if (a[i + 1] > 0.5) {
          area++;
          extent = Math.max(extent, Math.abs(dx), Math.abs(dy));
        }
      }
    }
    if (m > 0) {
      cen[0] += sx / m;
      cen[1] += sy / m;
    }
    if (record) traj.push([t, cen[0], cen[1], area, extent]);
  };
  track(sim.readA(), 0, true);

  for (let j = 0; j < steps && !nan; j++) {
    const check = j > 0 && j % opts.checkEvery === 0;
    const d0 = glx.drawCalls;
    sim.stepOnce(
      check
        ? () => {
            const W4 = sim.readW();
            const aux = sim.readAux();
            const pg = channel(sim.readP(), 0);
            const rhs = new Float32Array(n);
            const M = new Float32Array(n);
            for (let i = 0; i < n; i++) {
              rhs[i] = aux[i * 4];
              M[i] = aux[i * 4 + 1];
            }
            const cg = solveCG(N, W4, M, rhs);
            fluxErrSeries.push(fluxError(N, W4, pg, cg.p));
          }
        : undefined,
    );
    if (j === 0) drawCallsPerStep = glx.drawCalls - d0;
    stepsDone = j + 1;
    fracSum += sim.activeFraction();
    const st = sim.readStepStats();
    const es = sim.readEndStats();
    if (![st.hMinInStep, st.cMax, es.volume, es.hMin].every(Number.isFinite) && es.area > 0) nan = true;
    hMinInStep = Math.min(hMinInStep, st.hMinInStep);
    cMaxRun = Math.max(cMaxRun, st.cMax);
    hMinEnd = Math.min(hMinEnd, es.hMin);
    if (es.anyNegative) negEndSteps++;
    vEnd = es.volume;
    areaEnd = es.area;
    series[j * 4] = es.volume;
    series[j * 4 + 1] = es.area;

    // 먹이: 원반의 평균 두께와 위상(스텝 끝), 닿은 시각, 먹은 양
    if (nf > 0) {
      const fs = sim.readFoodStat();
      const fd = sim.readFood();
      eaten = 0;
      for (let k = 0; k < nf; k++) {
        hfood[j * 2 * nf + k] = fs[k].hMean;
        hfood[j * 2 * nf + nf + k] = fs[k].phase;
        // 이 스텝 끝의 젖은 마스크는 numpy 의 다음 스텝이 먹을 때 보는 마스크다
        if (fs[k].wet > 0 && tTouch[k] === null) tTouch[k] = (j + 1) * dt;
        if (fs[k].wet >= 0.5 * sim.foodGeom.discCells[k] && tCover[k] === null) tCover[k] = (j + 1) * dt;
        if (fd[k].stepExh >= 0 && tExh[k] === null) tExh[k] = fd[k].stepExh * dt;
        if (params.foodM > 0) eaten += params.gain * (params.foodM - fd[k].M);
      }
      mEnd = fd.map((x) => x.M);
    }
    massErrMax = Math.max(massErrMax, Math.abs(es.volume - v0 - eaten) / v0);

    let a: Float32Array | null = null;
    if (countNew && prevWet) {
      a = sim.readA();
      let nw = 0, nl = 0;
      for (let y = 0; y < N; y++) {
        for (let x = 0; x < N; x++) {
          const i = y * N + x;
          const w = a[i * 4 + 1] > 0.5 ? 1 : 0;
          if (w && !prevWet[i]) {
            nw++;
            if (x < c0) nl++;
          }
          prevWet[i] = w;
        }
      }
      series[j * 4 + 2] = nw;
      series[j * 4 + 3] = nl;
      newTotal += nw;
      newLeft += nl;
    }
    await rec.afterStep(j);
    if (stepsDone % 20 === 0) track(a ?? sim.readA(), stepsDone * dt, stepsDone % 50 === 0);
    if (es.area === 0) {
      stop = 'all dry';
      break;
    }
    if (scn.stopOnTouch && nf > 0 && tTouch.every((t) => t !== null)) {
      stop = 'touched';
      break;
    }
    if (stepsDone % 100 === 0) {
      if (onFrame) onFrame(sim);
      if (stepsDone % 1000 === 0) {
        const last = fluxErrSeries.slice(-20).sort((x, y) => x - y);
        log(`  스텝 ${stepsDone}: 넓이 ${areaEnd}, 부피 ${vEnd.toFixed(1)}, 최대 전도도 ${cMaxRun.toFixed(0)}, 최근 유량 오차 중앙 ${quantile(last, 0.5).toFixed(3)}, 먹이 남은 양 ${mEnd.map((m) => (Number.isFinite(m) ? m.toFixed(0) : '∞')).join('/') || '-'}, ${((performance.now() - t0) / 1000).toFixed(0)}초`);
      }
    }
    if (stepsDone % yieldEvery === 0) await new Promise((r) => setTimeout(r, 0));
  }

  const sorted = fluxErrSeries.slice().sort((x, y) => x - y);
  const fluxErr = { n: sorted.length, median: quantile(sorted, 0.5), p90: quantile(sorted, 0.9), p99: quantile(sorted, 0.99), max: sorted.length ? sorted[sorted.length - 1] : NaN };
  const finite = (v: number): number | null => (Number.isFinite(v) ? v : null);
  // 변환기가 numpy 실행의 params.json·metrics.json 과 같은 꼴로 쓰는 값
  await rec.finish(
    {
      name: opts.name, scn: opts.scn, seed: opts.seed, N, nf, steps_done: stepsDone, stop, planes: DUMP_PLANES, dumped: rec.dumped,
      params: {
        N, seed: opts.seed, dt, T, period: params.period, eps: params.eps, h0: params.h0, r: params.r, edge_sigma: params.edgeSigma, D0: params.d0,
        foods: params.foods.map((f) => [f.angleDeg, f.dist]), food_r: params.foodR, food_sigma: params.foodSigma, food_amp: params.foodAmp, food_M: params.foodM,
        eat: params.eat, gain: params.gain, reservoir: params.reservoir ? 1 : 0, h_res: params.hRes, res_tau: params.resTau, res_gate: params.resGate,
        tri_k: params.triK, tri_P: params.triP, tri_T: params.triT, tri_v: params.triV, ncyc: params.mgCycles, slime0: scn.slime0 ?? '',
      },
      metrics: {
        t_touch: tTouch, t_cover: tCover, t_exh: tExh, fM_end: mEnd.map(finite), V0: v0, V_end: vEnd, Vinj: eaten, mass_err_max: massErrMax,
        h_min_seen: hMinInStep, h_min_end_of_step: hMinEnd, neg_end_steps: negEndSteps, steps_done: stepsDone, stop, nan,
        mg_err: sorted.length ? [fluxErr.median, fluxErr.p90, fluxErr.max] : null, mg_err_n: sorted.length, Cmax_run: cMaxRun,
      },
    },
    hfood.subarray(0, stepsDone * 2 * Math.max(nf, 1)),
    series.subarray(0, stepsDone * 4),
  );
  const res: BResult = {
    ...opts,
    N,
    what: scn.what,
    variantName: variant.name,
    steps,
    stepsDone,
    stop,
    seconds: (performance.now() - t0) / 1000,
    drawCallsPerStep,
    activeFractionMean: stepsDone > 0 ? fracSum / stepsDone : 1,
    nan,
    negEndSteps,
    hMinEnd,
    hMinInStep,
    cMaxRun,
    v0,
    vEnd,
    eaten,
    massErrMax,
    fluxErr,
    tTouch,
    tCover,
    tExh,
    mEnd: mEnd.map((m) => (Number.isFinite(m) ? m : -1)),
    traj,
    areaEnd,
    newTotal,
    newLeft,
    dumped: rec.dumped,
    dumpFailed: rec.failed,
    stateHash: stateHash(sim),
    marginUse: sim.marginUse,
    marginUseSoft: sim.marginUseSoft,
    marginOverruns: sim.marginOverruns,
  };
  log(`[${opts.scn}] ${stepsDone}스텝${stop ? ` (${stop})` : ''}, NaN ${nan ? '있음' : '없음'}, 스텝 끝 음수 두께 ${negEndSteps}스텝(최소 ${hMinEnd.toExponential(2)}), 스텝 안 최소 두께 ${hMinInStep.toExponential(2)}, `
    + `최대 전도도 ${cMaxRun.toFixed(0)}, 부피 ${v0.toFixed(1)} → ${vEnd.toFixed(1)} (먹은 양 ${eaten.toFixed(1)}, 오차 ${massErrMax.toExponential(2)})`);
  log(`  유량 오차 중앙 ${fluxErr.median.toFixed(3)} / 90백분위 ${fluxErr.p90.toFixed(3)} / 99백분위 ${fluxErr.p99.toFixed(3)} / 최대 ${fluxErr.max.toFixed(3)} (${sorted.length}회)`);
  if (nf > 0) log(`  먹이에 닿은 시각 ${tTouch.map((t) => t?.toFixed(1) ?? '-').join(' / ')}, 다 떨어진 시각 ${tExh.map((t) => t?.toFixed(1) ?? '-').join(' / ')}`);
  if (countNew) log(`  새로 젖은 셀 ${newTotal}개 가운데 흔적이 없는 쪽(오른쪽) ${newTotal - newLeft}개 (${newTotal > 0 ? (((newTotal - newLeft) / newTotal) * 100).toFixed(1) : '-'}%)`);
  log(`  스텝당 드로콜 ${drawCallsPerStep}, 그린 영역 평균 ${(res.activeFractionMean * 100).toFixed(1)}%, 덤프 ${rec.dumped.length}장${rec.failed ? ' (보내지 못함)' : ''}, ${res.seconds.toFixed(0)}초`);
  log(`  끝 상태 요약 ${res.stateHash}, 여유 사용률 최대 ${(res.marginUse * 100).toFixed(0)}% (완만한 구간 ${(res.marginUseSoft * 100).toFixed(0)}%, 넘친 횟수 ${res.marginOverruns})${opts.syncBounds ? '' : ` · 경계 상자 비동기(${yieldEvery}스텝마다 도착)${opts.softMargin ? ', 완만한 여유' : ''}`}`);
  return res;
}

/**
 * 판정 도구의 확인용: numpy 상태(대칭 먹이 셋, 스텝 2000)를 넣고
 *   1) 그대로 내보낸다 (덤프 경로와 변환기가 값을 바꾸지 않는지)
 *   2) 201스텝을 돌려 t = 200 과 t = 220 의 덤프를 낸다 (구간 통계가 numpy 의 같은 구간과 맞는지. metrics/check_dump.py 가 견준다)
 */
export async function testBStats(glx: Glx, log: Log): Promise<{ ok: boolean; dumped: number[] }> {
  const man = await loadManifest();
  const f = man.files.find((x) => x.kind === 'foodstate' && x.N === 192 && x.step === 2000);
  if (!f) throw new Error('먹이 기준 상태(스텝 2000)가 없다');
  const params = defaultParams({ N: 192, seed: 1, triK: (2 * Math.PI) / 100, ...foodParams(FOOD3) });
  const sim = new PlasmGPU(glx, params);
  applyVariant(sim, VARIANTS[2]);
  sim.asyncBounds = false;
  const s = toState(await loadRef(f));
  s.food = refFood(f, params.dt);
  sim.loadState(s, 2000);
  const rec = new Recorder(sim, 'bstats', true, log);
  await rec.dump(2000, 'roundtrip.bin');
  for (let j = 2000; j <= 2200; j++) {
    sim.stepOnce();
    await rec.afterStep(j);
  }
  const ok = !rec.failed && rec.dumped.length === 2;
  log(`구간 통계 확인용 덤프: ${rec.dumped.map((t) => `t=${t}`).join(', ')} → ${ok ? '보냄' : '실패'}`);
  return { ok, dumped: rec.dumped };
}
