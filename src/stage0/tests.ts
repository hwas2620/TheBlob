// 0단계 관문 A 의 시험 — numpy 기준 자료와 대조한다

import { Glx } from '../gpu/plasm/glx';
import { MultigridGPU } from '../gpu/plasm/MultigridGPU';
import { PlasmGPU, type PlainState } from '../gpu/plasm/PlasmGPU';
import { hashNormal, hashU01 } from '../gpu/plasm/hashNoise';
import { defaultParams, foodParams, shaderVars, type PlasmParams } from '../gpu/plasm/params';
import { FOOD3 } from './scenarios';
import type { FoodState } from '../gpu/plasm/food';
import { fluxError, relDiff, solveCG } from './cpuSolver';
import { interleave, loadManifest, loadRef, type RefArrays, type RefFile } from './refData';

export type Log = (line: string) => void;

/** 텍스처 리드백(RGBA)에서 채널 하나를 뽑는다 */
export function channel(rgba: Float32Array, c: number): Float32Array {
  const out = new Float32Array(rgba.length / 4);
  for (let i = 0; i < out.length; i++) out[i] = rgba[i * 4 + c];
  return out;
}

// ref_model.py 가 낸 값 (시드 1): hash_u01(1, 0)[:4], hash_normal(1, 8)[:3]
const PROBE_U = [0.3079317097, 0.1196463037, 0.7929647536, 0.5568542952];
const PROBE_Z = [1.04004203, 1.2537602, -0.72773828];

export interface NoiseResult {
  pass: boolean;
  maxDiff: number;
}

/** JS 해시 잡음이 numpy 와 같은지 */
export function testNoise(log: Log): NoiseResult {
  const u = hashU01(1, 0, 4);
  const z = hashNormal(1, 8, 3);
  let maxDiff = 0;
  PROBE_U.forEach((v, i) => (maxDiff = Math.max(maxDiff, Math.abs(u[i] - v))));
  PROBE_Z.forEach((v, i) => (maxDiff = Math.max(maxDiff, Math.abs(z[i] - v))));
  const pass = maxDiff < 1e-6;
  log(`해시 잡음: numpy 와의 최대 차이 ${maxDiff.toExponential(2)} → ${pass ? '통과' : '실패'}`);
  return { pass, maxDiff };
}

export interface A0Cycle {
  /** 풀이 구성의 이름 (A0_CONFIGS) */
  config: string;
  merged: boolean;
  cycles: number;
  drawCallsPerCycle: number;
  relDiffVsNumpy: number;
  fluxErrGpu: number;
  fluxErrNumpy: number;
  pass: boolean;
}

export interface A0Case {
  tag: string;
  N: number;
  wet: number;
  cycle: A0Cycle[];
  cgRelDiff: number;
  cgIters: number;
  cgMs: number;
  drawCallsPerCycle: number;
  pass: boolean;
}

export interface A0Result {
  pass: boolean;
  cases: A0Case[];
}

/** A0 재생 시험: numpy 가 저장한 풀이 입력을 넣고 1·2·3사이클의 결과를 numpy 멀티그리드, 직접 풀이와 견준다 */
/** A0 에서 견주는 풀이 구성. 셋 다 numpy 와 같은 답을 내야 한다 */
const A0_CONFIGS = [
  { name: '기준형', merged: false, sweep2: false },
  { name: '합친 패스', merged: true, sweep2: false },
  { name: '합친 패스 + 두 번 스무딩', merged: true, sweep2: true },
];

export async function testA0(glx: Glx, log: Log): Promise<A0Result> {
  const man = await loadManifest();
  const files = man.files.filter((f) => f.kind === 'solver').sort((a, b) => a.N - b.N || a.step - b.step);
  const vars = shaderVars(defaultParams());
  const solvers = new Map<number, MultigridGPU>();
  const cases: A0Case[] = [];
  for (const f of files) {
    const n = f.N * f.N;
    const ref = await loadRef(f);
    const W4 = interleave(ref.get('W')!, n, 4);
    const M = ref.get('M')![0];
    const rhs = ref.get('rhs')![0];
    const pe = ref.get('pe')![0];
    let mg = solvers.get(f.N);
    if (!mg) {
      mg = new MultigridGPU(glx, f.N, vars);
      solvers.set(f.N, mg);
    }
    const texW = glx.tex(f.N, f.N, 'rgba32f', W4);
    const texSM = glx.tex(f.N, f.N, 'rg32f', interleave([rhs, M], n, 2));
    mg.setLevel0(texW, texSM, texSM);
    const cycle: A0Cycle[] = [];
    let drawCallsPerCycle = 0;
    for (const cfg of A0_CONFIGS) {
      const merged = cfg.merged;
      mg.merged = merged;
      mg.zeroStart = merged;
      mg.sweep2 = cfg.sweep2;
      for (let k = 1; k <= 3; k++) {
        mg.clearAll();
        glx.upload(mg.pTex(), ref.get('p0')![0]);
        const d0 = glx.drawCalls;
        mg.build();
        const d1 = glx.drawCalls;
        mg.solve(k, f.nc ?? 4);
        const perCycle = (glx.drawCalls - d1) / k;
        if (!merged) drawCallsPerCycle = perCycle;
        if (k === 1) log(`  ${f.tag} [${cfg.name}]: 레벨 ${mg.L}단 (${mg.sizes.join(', ')}), 조대 연산자 ${d1 - d0} 드로콜, 사이클당 ${perCycle} 드로콜`);
        const pg = channel(glx.read(mg.pTex()), 0);
        const rd = relDiff(pg, ref.get(`p${k}`)![0]);
        const eg = fluxError(f.N, W4, pg, pe);
        const en = f.flux_err![k - 1];
        const pass = rd <= 1e-3 && Math.abs(eg - en) <= 0.01;
        cycle.push({ config: cfg.name, merged, cycles: k, drawCallsPerCycle: perCycle, relDiffVsNumpy: rd, fluxErrGpu: eg, fluxErrNumpy: en, pass });
        log(`  ${f.tag} ${k}사이클: p 상대 차이 ${rd.toExponential(2)}, 유량 오차 GPU ${eg.toFixed(4)} / numpy ${en.toFixed(4)} → ${pass ? '통과' : '실패'}`);
      }
    }
    mg.merged = false;
    mg.zeroStart = false;
    mg.sweep2 = false;
    const t0 = performance.now();
    const cg = solveCG(f.N, W4, M, rhs);
    const cgMs = performance.now() - t0;
    const cgRelDiff = relDiff(cg.p, pe);
    log(`  ${f.tag} CPU 기준 풀이: numpy 직접 풀이와 상대 차이 ${cgRelDiff.toExponential(2)} (${cg.iters}회, ${cgMs.toFixed(0)}ms, 젖은 셀 ${cg.active})`);
    const pass = cycle.every((c) => c.pass) && cgRelDiff <= 1e-6;
    cases.push({ tag: f.tag, N: f.N, wet: f.wet ?? cg.active, cycle, cgRelDiff, cgIters: cg.iters, cgMs, drawCallsPerCycle, pass });
  }
  const pass = cases.length > 0 && cases.every((c) => c.pass);
  log(`A0 재생 시험: ${cases.length}개 상태 → ${pass ? '통과' : '실패'}`);
  return { pass, cases };
}

// ───────────────────────── 스텝 일치 시험 ─────────────────────────


export function toState(ref: RefArrays): PlainState {
  const g = (k: string): Float32Array => ref.get(k)![0];
  const s: PlainState = { h: g('h'), wet: g('wet'), age: g('age'), sage: g('sage'), theta: g('theta'), slime: g('slime'), C: ref.get('C')!, p: g('p'), pm: g('pm') };
  if (ref.has('Hres') && ref.has('hbar')) {
    s.Hres = g('Hres');
    s.hbar = g('hbar');
  }
  return s;
}

/** numpy 가 내보낸 먹이 상태 (manifest 의 fM, famp, t_exh) */
export function refFood(f: RefFile, dt: number): FoodState[] {
  const fM = f.fM ?? [];
  return fM.map((m, k) => {
    const te = f.t_exh?.[k];
    return { M: m < 0 ? Infinity : m, amp: f.famp?.[k] ?? 1, stepExh: te === null || te === undefined ? -1 : Math.round(te / dt) };
  });
}

export interface StateDiff {
  step: number;
  bodyCells: number;
  wetMismatch: number;
  hMaxDiff: number;
  thetaMedDiff: number;
  thetaMaxDiff: number;
  cMedRelDiff: number;
  cMaxRelDiff: number;
  edgeMismatch: number;
  pRelDiff: number;
  slimeMismatch: number;
  volumeGpu: number;
  volumeRef: number;
}

function median(v: number[]): number {
  if (v.length === 0) return 0;
  const s = v.slice().sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
}

/** GPU 의 지금 상태와 numpy 상태의 차이 */
export function diffState(sim: PlasmGPU, ref: PlainState): StateDiff {
  const a = sim.readA();
  const b = sim.readB();
  const c = sim.readC();
  const n = sim.N * sim.N;
  const twoPi = 2 * Math.PI;
  let body = 0, wetMismatch = 0, hMaxDiff = 0, slimeMismatch = 0, volumeGpu = 0, volumeRef = 0, pNum = 0, pDen = 0, edgeMismatch = 0;
  const dTheta: number[] = [];
  const dC: number[] = [];
  for (let i = 0; i < n; i++) {
    const wg = a[i * 4 + 1] > 0.5;
    const wr = ref.wet[i] > 0.5;
    if (wr) body++;
    if (wg !== wr) wetMismatch++;
    hMaxDiff = Math.max(hMaxDiff, Math.abs(a[i * 4] - ref.h[i]));
    volumeGpu += a[i * 4];
    volumeRef += ref.h[i];
    if (Math.abs(b[i * 4 + 1] - ref.slime[i]) > 1e-6) slimeMismatch++;
    pNum += (b[i * 4 + 2] - ref.p[i]) ** 2;
    pDen += ref.p[i] ** 2;
    if (wg && wr) {
      let d = (b[i * 4] - ref.theta[i]) % twoPi;
      if (d > Math.PI) d -= twoPi;
      if (d < -Math.PI) d += twoPi;
      dTheta.push(Math.abs(d));
    }
    for (let k = 0; k < 4; k++) {
      const cg = c[i * 4 + k];
      const cr = ref.C[k][i];
      if (cg > 0 && cr > 0) dC.push(Math.abs(cg - cr) / cr);
      else if (cg > 0 !== cr > 0) edgeMismatch++;
    }
  }
  return {
    step: sim.step,
    bodyCells: body,
    wetMismatch,
    hMaxDiff,
    thetaMedDiff: median(dTheta),
    thetaMaxDiff: dTheta.reduce((m, v) => Math.max(m, v), 0),
    cMedRelDiff: median(dC),
    cMaxRelDiff: dC.reduce((m, v) => Math.max(m, v), 0),
    edgeMismatch,
    pRelDiff: Math.sqrt(pNum / Math.max(pDen, 1e-300)),
    slimeMismatch,
    volumeGpu,
    volumeRef,
  };
}

/** 스텝을 싸게 만드는 수단 (결과는 같아야 한다) */
export interface Variant {
  name: string;
  merged: boolean;
  scissor: boolean;
  /** 그리는 영역이 작은 레벨에서 스무딩 두 번을 한 패스로 */
  sweep2: boolean;
}

export const VARIANTS: Variant[] = [
  { name: '기준형', merged: false, scissor: false, sweep2: false },
  { name: '합친 패스', merged: true, scissor: false, sweep2: false },
  { name: '합친 패스 + 몸 주변만', merged: true, scissor: true, sweep2: false },
  { name: '합친 패스 + 몸 주변만 + 두 번 스무딩', merged: true, scissor: true, sweep2: true },
  { name: '합친 패스 + 두 번 스무딩', merged: true, scissor: false, sweep2: true },
];

/** 변형을 시뮬레이션에 건다 */
export function applyVariant(sim: PlasmGPU, v: Variant): void {
  sim.mg.merged = v.merged;
  sim.mg.zeroStart = v.merged; // 기준형만 "해를 0 으로 지우고 시작"하는 원래 길을 남긴다
  sim.mg.sweep2 = v.sweep2;
  sim.scissor = v.scissor;
}

export interface ParityResult {
  variant: string;
  pass: boolean;
  drawCallsPerStep: number;
  mature: StateDiff[];
  initial: StateDiff[];
  initialVolumeRelErr: number;
}

function fmtDiff(d: StateDiff): string {
  return `젖은 마스크 불일치 ${d.wetMismatch}/${d.bodyCells}, h 최대 차이 ${d.hMaxDiff.toExponential(2)}, θ 차이 중앙 ${d.thetaMedDiff.toExponential(2)} 최대 ${d.thetaMaxDiff.toExponential(2)}, `
    + `C 상대 차이 중앙 ${d.cMedRelDiff.toExponential(2)} 최대 ${d.cMaxRelDiff.toExponential(2)}, 간선 불일치 ${d.edgeMismatch}, p 상대 차이 ${d.pRelDiff.toExponential(2)}, 점액 불일치 ${d.slimeMismatch}`;
}

/** 스텝 일치 시험: numpy 상태에서 출발해 GPU 로 돌린 결과를 numpy 의 다음 상태와 견준다 */
export async function testParity(glx: Glx, log: Log, variant: Variant): Promise<ParityResult> {
  const man = await loadManifest();
  const states = new Map<number, RefFile>();
  for (const f of man.files) if (f.kind === 'state' && f.N === 192) states.set(f.step, f);
  const get = async (step: number): Promise<PlainState> => {
    const f = states.get(step);
    if (!f) throw new Error(`기준 상태가 없다: 스텝 ${step}`);
    return toState(await loadRef(f));
  };
  const sim = new PlasmGPU(glx, defaultParams({ N: 192, seed: 1 }));
  applyVariant(sim, variant);
  sim.asyncBounds = false; // 시험에서는 경계 상자를 그 자리에서 읽어 결정적으로 만든다
  log(`[${variant.name}]`);

  // 성숙한 몸 (t = 200): 마름과 젖음이 모두 일어나는 시점
  log('성숙한 상태(스텝 2000)에서 출발');
  sim.loadState(await get(2000), 2000);
  const d0 = glx.drawCalls;
  sim.stepOnce();
  const drawCallsPerStep = glx.drawCalls - d0;
  const m1 = diffState(sim, await get(2001));
  log(`  1스텝 뒤: ${fmtDiff(m1)}`);
  for (let i = 0; i < 9; i++) sim.stepOnce();
  const m10 = diffState(sim, await get(2010));
  log(`  10스텝 뒤: ${fmtDiff(m10)}`);

  // 초기 원반에서 출발
  log('초기 상태에서 출발');
  sim.reset();
  const i0 = diffState(sim, await get(0));
  log(`  0스텝: ${fmtDiff(i0)}`);
  const initial: StateDiff[] = [i0];
  let done = 0;
  for (const target of [1, 10, 50]) {
    for (; done < target; done++) sim.stepOnce();
    const d = diffState(sim, await get(target));
    initial.push(d);
    log(`  ${target}스텝 뒤: ${fmtDiff(d)}`);
  }
  const last = initial[initial.length - 1];
  const initialVolumeRelErr = Math.abs(last.volumeGpu - i0.volumeGpu) / i0.volumeGpu;
  log(`  50스텝 뒤 총 부피의 상대 오차 ${initialVolumeRelErr.toExponential(2)} · 스텝당 드로콜 ${drawCallsPerStep}`);

  const pass =
    m1.wetMismatch === 0 && m1.hMaxDiff <= 1e-3 && m1.thetaMedDiff <= 1e-4 && m1.cMedRelDiff <= 1e-4 &&
    m10.wetMismatch <= 0.005 * m10.bodyCells &&
    i0.wetMismatch === 0 && initialVolumeRelErr <= 1e-5;
  log(`스텝 일치 시험 [${variant.name}] → ${pass ? '통과' : '실패'}`);
  return { variant: variant.name, pass, drawCallsPerStep, mature: [m1, m10], initial, initialVolumeRelErr };
}

// ───────────────────────── 먹이가 있는 스텝 일치 시험 (관문 B) ─────────────────────────

/** 스텝 일치 시험의 먹이 설정 하나 (numpy 쪽은 export_ref.py 의 dumpsfood, dumpsfood2) */
interface FoodFamily {
  kind: RefFile['kind'];
  name: string;
  over: Partial<PlasmParams>;
  /** 출발한 뒤 견주는 스텝 수 */
  afters: number[];
}

const FOOD_FAMILIES: FoodFamily[] = [
  // 닿기 직전(580), 먹는 중(2000), 첫 먹이가 떨어지기 직전(3790)
  { kind: 'foodstate', name: '대칭 먹이 셋', over: foodParams(FOOD3), afters: [1, 10, 50] },
  // 먹이별 유인장의 둘째 텍스처(먹이 5번부터)와 "줄지 않는 먹이를 먹는" 길
  { kind: 'food6state', name: '줄지 않는 먹이 여섯', over: foodParams([0, 60, 120, 180, 240, 300].map((angleDeg) => ({ angleDeg, dist: 30 })), { foodM: 0 }), afters: [1, 10] },
  // 떨어지는 순간(+3스텝)과 유인장의 세기가 1e-4 아래에서 멈춘 뒤(+120스텝)까지
  { kind: 'foodfadestate', name: '금방 떨어지는 먹이 셋', over: foodParams(FOOD3, { foodM: 20, foodFade: 1 }), afters: [1, 10, 120] },
  // 외톨이 셀 말리기(계획 C): 규칙 없이 3790스텝까지 돌아 외딴 음수 셀이 남은 상태에서 규칙을 켠다. 그 셀들이 처음 몇 스텝 안에 마른다
  { kind: 'foodcrumbstate', name: '외톨이 셀 말리기', over: foodParams(FOOD3), afters: [1, 10, 50] },
];

export interface FoodDiff extends StateDiff {
  /** 먹이 설정의 이름, 출발한 스텝, 그 뒤로 돈 스텝 수 */
  family: string;
  from: number;
  after: number;
  /** 먹이의 남은 양의 상대 차이 (먹이 가운데 최대. 분모는 처음의 양. 줄지 않는 먹이는 0) */
  mRelDiff: number;
  /** 유인장 세기의 최대 차이 */
  ampDiff: number;
  /** 다 떨어진 스텝이 numpy 와 다른 먹이 수 */
  exhMismatch: number;
  /** 저장 배율 H 의 차이 (양쪽 다 젖은 셀): 최대, 1e-5 를 넘는 셀 수 */
  hresMaxDiff: number;
  hresOver: number;
  /** 직전 스텝의 쉬는 두께의 최대 차이 (젖음이 같은 셀) */
  hbarMaxDiff: number;
  /** 나이와 노화 나이의 차이 (양쪽 다 젖은 셀): 최대, 2e-3 을 넘는 셀 수 */
  ageMaxDiff: number;
  sageMaxDiff: number;
  ageOver: number;
  /** 먹이의 남은 양과 유인장의 세기: GPU, numpy (줄지 않는 먹이의 양은 −1) */
  mGpu: number[];
  mRef: number[];
  ampGpu: number[];
  ampRef: number[];
  /** 기준형(변형 0)의 같은 시점 상태와의 차이. 기준형 자신은 null */
  vsBase: { wetMismatch: number; hMaxDiff: number } | null;
}

export interface ParityFoodResult {
  variant: string;
  pass: boolean;
  /** 대칭 먹이 셋에서 잰 스텝당 드로콜 */
  drawCallsPerStep: number;
  diffs: FoodDiff[];
}

/** 기준형이 낸 상태 (변형끼리 견주는 데 쓴다): "설정:출발 스텝+지난 스텝" → cellA */
export type FoodBase = Map<string, Float32Array>;

function fmtFood(d: FoodDiff): string {
  return `먹이 남은 양 상대 차이 ${d.mRelDiff.toExponential(2)}, 세기 차이 ${d.ampDiff.toExponential(2)}, 떨어진 스텝 불일치 ${d.exhMismatch}, H 최대 차이 ${d.hresMaxDiff.toExponential(2)} (1e-5 넘는 셀 ${d.hresOver}), `
    + `쉬는 두께 최대 차이 ${d.hbarMaxDiff.toExponential(2)}, 나이·노화 나이 최대 차이 ${d.ageMaxDiff.toExponential(2)}·${d.sageMaxDiff.toExponential(2)} (2e-3 넘는 셀 ${d.ageOver})`
    + (d.vsBase ? `, 기준형과 젖음 불일치 ${d.vsBase.wetMismatch} · h 최대 차이 ${d.vsBase.hMaxDiff.toExponential(2)}` : '');
}

/** 판정: 1스텝 뒤는 엄격하게, 10스텝 뒤는 젖은 셀 0.5% 까지의 어긋남을 받는다. 그 뒤는 기록만 하되, 먹이 상태(떨어진 스텝, 유인장의 세기)는 끝까지 본다 */
function foodDiffPass(d: FoodDiff): boolean {
  const food = d.exhMismatch === 0 && d.ampDiff <= 1e-5;
  if (d.after === 1) return food && d.wetMismatch === 0 && d.hMaxDiff <= 1e-3 && d.thetaMedDiff <= 1e-4 && d.cMedRelDiff <= 1e-4 && d.mRelDiff <= 1e-5 && d.hresMaxDiff <= 1e-5 && d.ageOver === 0;
  if (d.after === 10) return food && d.wetMismatch <= 0.005 * d.bodyCells && d.mRelDiff <= 1e-5 && d.hresOver <= 0.005 * d.bodyCells && d.ageOver <= 0.005 * d.bodyCells;
  return d.family === '금방 떨어지는 먹이 셋' ? food : true;
}

/**
 * 먹이가 있는 스텝 일치 시험: numpy 상태에서 출발해 GPU 로 돌린 결과를 numpy 의 뒤 상태와 견준다.
 * 설정 셋(FOOD_FAMILIES)을 차례로 본다. 50스텝 넘게 지난 상태는 궤적이 float32 때문에 갈라지기 시작하므로 기록만 한다
 */
export async function testParityFood(glx: Glx, log: Log, variant: Variant, base: FoodBase): Promise<ParityFoodResult> {
  const man = await loadManifest();
  const isBase = variant === VARIANTS[0];
  const diffs: FoodDiff[] = [];
  let drawCallsPerStep = 0;
  log(`[${variant.name}]`);
  for (const fam of FOOD_FAMILIES) {
    const files = new Map<number, RefFile>();
    for (const f of man.files) if (f.kind === fam.kind && f.N === 192) files.set(f.step, f);
    const params = defaultParams({ N: 192, seed: 1, triK: (2 * Math.PI) / 100, ...fam.over });
    const get = async (step: number): Promise<{ f: RefFile; s: PlainState }> => {
      const f = files.get(step);
      if (!f) throw new Error(`먹이 기준 상태가 없다: ${fam.kind} 스텝 ${step}`);
      const s = toState(await loadRef(f));
      s.food = refFood(f, params.dt);
      return { f, s };
    };
    const starts = [...files.keys()].filter((s) => fam.afters.every((k) => files.has(s + k))).sort((a, b) => a - b);
    if (starts.length === 0) throw new Error(`먹이 기준 상태가 없다: ${fam.kind} (export_ref.py dumpsfood, dumpsfood2)`);
    glx.reset();
    const sim = new PlasmGPU(glx, params);
    applyVariant(sim, variant);
    sim.asyncBounds = false;
    const n = sim.N * sim.N;
    const showM = (v: number[]): string => v.map((x) => (Number.isFinite(x) ? x.toFixed(1) : '∞')).join(' / ');
    log(`${fam.name}: 먹이 ${params.foods.length}개, 원반의 셀 수 ${sim.foodGeom.discCells.join('/')}`);
    for (const from of starts) {
      const start = await get(from);
      sim.loadState(start.s, from);
      log(` 스텝 ${from} 에서 출발 (먹이 남은 양 ${showM(start.s.food!.map((x) => x.M))})`);
      let done = 0;
      for (const after of fam.afters) {
        for (; done < after; done++) {
          const d0 = glx.drawCalls;
          sim.stepOnce();
          if (drawCallsPerStep === 0) drawCallsPerStep = glx.drawCalls - d0;
        }
        const ref = await get(from + after);
        const sd = diffState(sim, ref.s);
        const a = sim.readA();
        const hv = sim.readH();
        const fg = sim.readFood();
        const fr = ref.s.food!;
        let mRelDiff = 0, ampDiff = 0, exhMismatch = 0, hresMaxDiff = 0, hresOver = 0, hbarMaxDiff = 0, ageMaxDiff = 0, sageMaxDiff = 0, ageOver = 0;
        fg.forEach((g, k) => {
          const r = fr[k];
          if (Number.isFinite(r.M) !== Number.isFinite(g.M)) mRelDiff = Infinity;
          else if (Number.isFinite(r.M)) mRelDiff = Math.max(mRelDiff, Math.abs(g.M - r.M) / params.foodM);
          ampDiff = Math.max(ampDiff, Math.abs(g.amp - r.amp));
          if (g.stepExh !== r.stepExh) exhMismatch++;
        });
        for (let i = 0; i < n; i++) {
          const wg = a[i * 4 + 1] > 0.5;
          const wr = ref.s.wet[i] > 0.5;
          if (wg !== wr) continue;
          if (hv && ref.s.hbar) hbarMaxDiff = Math.max(hbarMaxDiff, Math.abs(hv[i * 4 + 1] - ref.s.hbar[i]));
          if (!wg) continue;
          const da = Math.abs(a[i * 4 + 2] - ref.s.age[i]);
          const ds = Math.abs(a[i * 4 + 3] - ref.s.sage[i]);
          ageMaxDiff = Math.max(ageMaxDiff, da);
          sageMaxDiff = Math.max(sageMaxDiff, ds);
          if (da > 2e-3 || ds > 2e-3) ageOver++;
          if (hv && ref.s.Hres) {
            const d = Math.abs(hv[i * 4] - ref.s.Hres[i]);
            hresMaxDiff = Math.max(hresMaxDiff, d);
            if (d > 1e-5) hresOver++;
          }
        }
        const key = `${fam.kind}:${from}+${after}`;
        let vsBase: FoodDiff['vsBase'] = null;
        const b = base.get(key);
        if (isBase) base.set(key, a);
        else if (b) {
          let wetMismatch = 0, hMaxDiff = 0;
          for (let i = 0; i < n; i++) {
            if (a[i * 4 + 1] > 0.5 !== b[i * 4 + 1] > 0.5) wetMismatch++;
            hMaxDiff = Math.max(hMaxDiff, Math.abs(a[i * 4] - b[i * 4]));
          }
          vsBase = { wetMismatch, hMaxDiff };
        }
        const inf = (x: number): number => (Number.isFinite(x) ? x : -1);
        const d: FoodDiff = {
          ...sd, family: fam.name, from, after, mRelDiff, ampDiff, exhMismatch, hresMaxDiff, hresOver, hbarMaxDiff, ageMaxDiff, sageMaxDiff, ageOver,
          mGpu: fg.map((x) => inf(x.M)), mRef: fr.map((x) => inf(x.M)), ampGpu: fg.map((x) => x.amp), ampRef: fr.map((x) => x.amp), vsBase,
        };
        diffs.push(d);
        log(`  ${after}스텝 뒤${foodDiffPass(d) ? '' : ' ✕'}: ${fmtDiff(sd)}`);
        log(`    ${fmtFood(d)} · 부피 GPU ${sd.volumeGpu.toFixed(3)} / numpy ${sd.volumeRef.toFixed(3)} · 세기 GPU ${fg.map((x) => x.amp.toExponential(2)).join('/')}`);
      }
    }
  }
  const pass = diffs.every(foodDiffPass);
  log(`먹이 스텝 일치 시험 [${variant.name}] → ${pass ? '통과' : '실패'} · 스텝당 드로콜 ${drawCallsPerStep}`);
  return { variant: variant.name, pass, drawCallsPerStep, diffs };
}

// ───────────────────────── A1·A2: 긴 실행 ─────────────────────────

export interface A12Options {
  N: number;
  seed: number;
  cycles: number;
  steps: number;
  /** 위상 무늬 (나) 삼각 격자를 켠다 */
  tri: boolean;
  /** 이 스텝마다 CPU 기준 풀이로 유량 오차를 잰다 */
  checkEvery: number;
  /** VARIANTS 의 번호 (0 기준형) */
  variant: number;
  /**
   * 몸의 경계 상자를 그 자리에서 읽는다(8스텝마다). 끄면 게임처럼 멈춤 없이 읽는데, 그 결과는 이벤트 루프로 돌아가야 도착한다.
   * 이 시험은 100스텝마다만 돌아가므로 끄면 여유 폭이 100셀 넘게 커져 가위 사각형이 격자를 거의 다 덮는다(결과는 같고 느려질 뿐이다).
   */
  syncBounds: boolean;
  /** 기본 설정을 덮어쓴다 (dt, 맥동 주기, 진폭, 위상 부분 스텝 수). numpy 기준 실행도 같은 설정으로 만든 것과 견준다 */
  over?: { dt?: number; period?: number; eps?: number; substeps?: number };
  /** 덮어쓴 설정의 이름. 판정 스크립트가 ref/a12_N…_<tag>.json 을 찾는다 */
  tag?: string;
  /** 가위 사각형의 여유를 완만하게 키운다 (PlasmGPU.softMargin. 게임 루프의 설정) */
  softMargin?: boolean;
  /** 이 스텝마다 이벤트 루프로 돌아간다 (기본 100). 멈춤 없는 읽기는 돌아간 뒤에야 도착하므로, 이 값이 경계 상자가 늦는 스텝 수를 정한다 */
  yieldEvery?: number;
}

export interface A12Result extends A12Options {
  drawCallsPerStep: number;
  seconds: number;
  stepsDone: number;
  nan: boolean;
  /** 스텝 끝에 음수 두께인 젖은 셀이 있던 스텝 수 */
  negEndSteps: number;
  hMinEnd: number;
  hMinInStep: number;
  cMaxRun: number;
  volumeRelErr: number;
  fluxErr: { n: number; median: number; p90: number; p99: number; max: number };
  fluxErrSeries: number[];
  variantName: string;
  /** 그린 영역이 격자에서 차지한 비율의 평균 (가위를 쓰지 않으면 1) */
  activeFractionMean: number;
  /** [t, 무게중심 x, y, 넓이, 무게중심에서 가장 먼 젖은 셀까지의 거리(축별 최대)] (50스텝마다) */
  traj: number[][];
  /** 몸이 무게중심에서 격자 절반 가까이(N/2 − 4)까지 퍼진 첫 시각. 그 뒤로는 토러스에서 무게중심을 믿을 수 없다 */
  tWrap: number | null;
  disp_0_300: number | null;
  disp_0_400: number | null;
  disp_100_300: number | null;
  tTouch: number | null;
  areaEnd: number;
  /** 끝 상태의 요약 (stateHash). 가위 사각형이 달라도 같은 계산이면 같은 값이 나온다 */
  stateHash: string;
  /** 여유의 사용률: (경계 상자가 실제로 넓어진 셀 수) / (그동안 여유가 허용한 셀 수) 의 최대, 완만한 규칙이 더 적게 허용한 구간에서만 본 최대, 1 을 넘은 횟수 */
  marginUse: number;
  marginUseSoft: number;
  marginOverruns: number;
}

/**
 * 모델 상태를 비트 단위로 요약한다. 두 실행이 같은 상태에 닿았는지 볼 때 쓴다.
 * 젖은 셀은 상태 전부(두께·나이·위상·점액·압력·전도도), 마른 셀은 두께와 점액만 넣는다: 마른 셀의 나머지 값(압력 따위)은 모델이 쓰지 않고,
 * 가위 사각형 안에 들었는지에 따라 달라질 수 있다. +0 과 −0 은 같은 것으로 친다
 */
export function stateHash(sim: PlasmGPU): string {
  const s = sim.snapshot();
  const n = sim.N * sim.N;
  const bits = (v: Float32Array): Uint32Array => new Uint32Array(v.buffer, v.byteOffset, v.length);
  const a = bits(s.a), b = bits(s.b), c = bits(s.c);
  const hr = s.hres ? bits(s.hres) : null;
  let h1 = 0x811c9dc5, h2 = 0x9747b28c;
  const eat = (u: number): void => {
    const w = u === 0x80000000 ? 0 : u;
    h1 = Math.imul(h1 ^ w, 0x01000193);
    h2 = Math.imul((h2 << 5) | (h2 >>> 27), 0x85ebca6b) ^ w;
  };
  for (let i = 0; i < n; i++) {
    const wet = s.a[i * 4 + 1] > 0.5;
    eat(wet ? 1 : 0);
    eat(a[i * 4]);
    eat(b[i * 4 + 1]);
    if (!wet) continue;
    eat(a[i * 4 + 2]);
    eat(a[i * 4 + 3]);
    eat(b[i * 4]);
    eat(b[i * 4 + 2]);
    eat(b[i * 4 + 3]);
    for (let k = 0; k < 4; k++) eat(c[i * 4 + k]);
    if (hr) {
      eat(hr[i * 2]);
      eat(hr[i * 2 + 1]);
    }
  }
  if (s.food) for (const u of bits(s.food)) eat(u);
  const hex = (x: number): string => (x >>> 0).toString(16).padStart(8, '0');
  return hex(h1) + hex(h2);
}

export function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return NaN;
  const pos = (sorted.length - 1) * q;
  const lo = Math.floor(pos);
  const hi = Math.min(sorted.length - 1, lo + 1);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

/** A1·A2: 통합 모델을 길게 돌리며 안정성(NaN, 음수 두께, 최대 전도도)과 정확도(유량 오차, 이동)를 잰다 */
export async function testA12(glx: Glx, opts: A12Options, log: Log, onFrame?: (sim: PlasmGPU) => void): Promise<A12Result> {
  const params = defaultParams({ N: opts.N, seed: opts.seed, mgCycles: opts.cycles, triK: opts.tri ? (2 * Math.PI) / 100 : 0, ...(opts.over ?? {}) });
  const sim = new PlasmGPU(glx, params);
  const variant = VARIANTS[opts.variant] ?? VARIANTS[0];
  applyVariant(sim, variant);
  sim.asyncBounds = !opts.syncBounds;
  sim.softMargin = opts.softMargin === true;
  const yieldEvery = Math.max(1, opts.yieldEvery ?? 100);
  const N = opts.N;
  const n = N * N;
  const dt = params.dt;
  const t0 = performance.now();
  const d0 = glx.drawCalls;
  sim.stepOnce();
  const drawCallsPerStep = glx.drawCalls - d0;
  sim.reset();

  const v0 = sim.readEndStats().volume;
  const c0 = N / 2 - 0.5;
  const cen = [c0, c0];
  // 닿았는지는 첫 먹이(굶은 이주의 유인원)의 원반으로 본다
  const att = sim.foodGeom.pos.length > 0 ? sim.foodGeom.pos[0] : null;
  const fx = att ? att[0] : 0;
  const fy = att ? att[1] : 0;
  const mimg = (v: number): number => ((((v + N / 2) % N) + N) % N) - N / 2;
  const fluxErrSeries: number[] = [];
  const traj: number[][] = [];
  let fracSum = 0;
  let nan = false, negEndSteps = 0, hMinEnd = Infinity, hMinInStep = Infinity, cMaxRun = 0, tTouch: number | null = null, tWrap: number | null = null, areaEnd = 0, volumeEnd = v0, stepsDone = 0;

  /** 읽은 cellA 로 무게중심(토러스 최소 상)을 갱신하고 유인원에 닿았는지 본다 */
  const track = (a: Float32Array, t: number, record: boolean): void => {
    let m = 0, sx = 0, sy = 0, area = 0, touch = false, extent = 0;
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
          if (att && Math.hypot(mimg(x - fx), mimg(y - fy)) < params.foodR) touch = true;
        }
      }
    }
    if (m > 0) {
      cen[0] += sx / m;
      cen[1] += sy / m;
    }
    if (touch && tTouch === null) tTouch = t;
    if (extent >= N / 2 - 4 && tWrap === null) tWrap = t;
    areaEnd = area;
    if (record) traj.push([t, cen[0], cen[1], area, extent]);
  };
  track(sim.readA(), 0, true);

  for (let step = 0; step < opts.steps && !nan; step++) {
    const check = step > 0 && step % opts.checkEvery === 0;
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
    stepsDone = step + 1;
    fracSum += sim.activeFraction();
    const st = sim.readStepStats();
    const es = sim.readEndStats();
    if (![st.hMinInStep, st.cMax, es.volume, es.hMin].every(Number.isFinite) && es.area > 0) nan = true;
    hMinInStep = Math.min(hMinInStep, st.hMinInStep);
    cMaxRun = Math.max(cMaxRun, st.cMax);
    hMinEnd = Math.min(hMinEnd, es.hMin);
    if (es.anyNegative) negEndSteps++;
    volumeEnd = es.volume;
    if (stepsDone % 20 === 0) track(sim.readA(), stepsDone * dt, stepsDone % 50 === 0);
    if (stepsDone % 100 === 0) {
      if (onFrame) onFrame(sim);
      if (stepsDone % 1000 === 0) {
        const last = fluxErrSeries.slice(-20).sort((a, b) => a - b);
        log(`  스텝 ${stepsDone}: 넓이 ${areaEnd}, 무게중심 (${cen[0].toFixed(1)}, ${cen[1].toFixed(1)}), 최대 전도도 ${cMaxRun.toFixed(0)}, 최근 유량 오차 중앙 ${quantile(last, 0.5).toFixed(3)}, ${((performance.now() - t0) / 1000).toFixed(0)}초`);
      }
    }
    if (stepsDone % yieldEvery === 0) await new Promise((r) => setTimeout(r, 0));
  }
  const at = (t: number): number[] | null => traj.find((r) => Math.abs(r[0] - t) < 1e-6) ?? null;
  const disp = (ta: number, tb: number): number | null => {
    const a = at(ta);
    const b = at(tb);
    return a && b ? Math.hypot(b[1] - a[1], b[2] - a[2]) : null;
  };
  const sorted = fluxErrSeries.slice().sort((a, b) => a - b);
  const res: A12Result = {
    ...opts,
    drawCallsPerStep,
    seconds: (performance.now() - t0) / 1000,
    stepsDone,
    nan,
    negEndSteps,
    hMinEnd,
    hMinInStep,
    cMaxRun,
    volumeRelErr: Math.abs(volumeEnd - v0) / v0,
    fluxErr: { n: sorted.length, median: quantile(sorted, 0.5), p90: quantile(sorted, 0.9), p99: quantile(sorted, 0.99), max: sorted.length ? sorted[sorted.length - 1] : NaN },
    fluxErrSeries,
    variantName: variant.name,
    activeFractionMean: stepsDone > 0 ? fracSum / stepsDone : 1,
    traj,
    tWrap,
    disp_0_300: disp(0, 300),
    disp_0_400: disp(0, 400),
    disp_100_300: disp(100, 300),
    tTouch,
    areaEnd,
    stateHash: stateHash(sim),
    marginUse: sim.marginUse,
    marginUseSoft: sim.marginUseSoft,
    marginOverruns: sim.marginOverruns,
  };
  log(`${N}² 시드 ${opts.seed} ${opts.cycles}사이클${opts.tri ? ' 삼각 격자' : ''} [${variant.name}${variant.scissor ? (opts.syncBounds ? ', 경계 상자 즉시 읽기' : `, 경계 상자 비동기(${yieldEvery}스텝마다 도착)`) + (opts.softMargin ? ', 완만한 여유' : '') : ''}]: ${stepsDone}스텝, NaN ${nan ? '있음' : '없음'}, 스텝 끝 음수 두께 ${negEndSteps}스텝(최소 ${hMinEnd.toExponential(2)}), `
    + `스텝 안 최소 두께 ${hMinInStep.toExponential(2)}, 최대 전도도 ${cMaxRun.toFixed(0)}, 부피 오차 ${res.volumeRelErr.toExponential(2)}`);
  log(`  유량 오차 중앙 ${res.fluxErr.median.toFixed(3)} / 90백분위 ${res.fluxErr.p90.toFixed(3)} / 99백분위 ${res.fluxErr.p99.toFixed(3)} / 최대 ${res.fluxErr.max.toFixed(3)} (${sorted.length}회)`);
  log(`  이동 t=0~300 ${res.disp_0_300?.toFixed(1) ?? '-'}셀, t=0~400 ${res.disp_0_400?.toFixed(1) ?? '-'}셀, t=100~300 ${res.disp_100_300?.toFixed(1) ?? '-'}셀, 유인원에 닿은 시각 ${tTouch ?? '-'}, `
    + `몸이 격자 절반까지 퍼진 시각 ${tWrap ?? '-'}, 스텝당 드로콜 ${drawCallsPerStep}, 그린 영역 평균 ${(res.activeFractionMean * 100).toFixed(1)}%, ${res.seconds.toFixed(0)}초`);
  log(`  끝 상태 요약 ${res.stateHash}, 여유 사용률 최대 ${(res.marginUse * 100).toFixed(0)}% (완만한 구간 ${(res.marginUseSoft * 100).toFixed(0)}%, 넘친 횟수 ${res.marginOverruns})`);
  return res;
}
