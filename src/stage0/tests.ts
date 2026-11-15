// 0단계 관문 A 의 시험 — numpy 기준 자료와 대조한다

import { Glx } from '../gpu/plasm/glx';
import { MultigridGPU } from '../gpu/plasm/MultigridGPU';
import { hashNormal, hashU01 } from '../gpu/plasm/hashNoise';
import { defaultParams, shaderVars } from '../gpu/plasm/params';
import { fluxError, relDiff, solveCG } from './cpuSolver';
import { interleave, loadManifest, loadRef } from './refData';

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
  cycles: number;
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
    for (let k = 1; k <= 3; k++) {
      glx.upload(mg.pTex(), ref.get('p0')![0]);
      const d0 = glx.drawCalls;
      mg.build();
      const d1 = glx.drawCalls;
      mg.solve(k, f.nc ?? 4);
      drawCallsPerCycle = (glx.drawCalls - d1) / k;
      if (k === 1) log(`  ${f.tag}: 레벨 ${mg.L}단 (${mg.sizes.join(', ')}), 조대 연산자 ${d1 - d0} 드로콜, 사이클당 ${drawCallsPerCycle} 드로콜`);
      const pg = channel(glx.read(mg.pTex()), 0);
      const rd = relDiff(pg, ref.get(`p${k}`)![0]);
      const eg = fluxError(f.N, W4, pg, pe);
      const en = f.flux_err![k - 1];
      const pass = rd <= 1e-3 && Math.abs(eg - en) <= 0.01;
      cycle.push({ cycles: k, relDiffVsNumpy: rd, fluxErrGpu: eg, fluxErrNumpy: en, pass });
      log(`  ${f.tag} ${k}사이클: p 상대 차이 ${rd.toExponential(2)}, 유량 오차 GPU ${eg.toFixed(4)} / numpy ${en.toFixed(4)} → ${pass ? '통과' : '실패'}`);
    }
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
