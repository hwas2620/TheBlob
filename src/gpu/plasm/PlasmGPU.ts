// 원형질체 코어 — 상태 텍스처와 한 스텝의 패스 순서 (spec 의 규칙 1~7)
//
//   cellA  h, wet, age, sage          cellB  θ, slime, p, 직전 p          edgeC  간선 전도도 E, N, NE, SE
//
// 한 스텝: 간선 켜기 → 위상(부분 스텝) → 쉬는 두께·우변·가중치 → 멀티그리드 → 유량·두께 → 전역 평균 → 강화 → 마름 → 젖음
// numpy 기준 모델(specs/plasmodium-core/stage0/ref/ref_model.py)과 연산 순서를 맞췄다.

import type { Glx, Prog, Target, Tex } from './glx';
import { noiseFields } from './hashNoise';
import { MultigridGPU } from './MultigridGPU';
import { shaderVars, type PlasmParams } from './params';
import { plasmShaders } from './shaders';

/** 스텝 통계 (1×1 축소 결과를 읽은 것) */
export interface StepStats {
  /** 유량 갱신 직후 젖은 셀의 최소 두께 */
  hMinInStep: number;
  /** 강화 전 최대 간선 전도도 */
  cMax: number;
  /** 활성 간선 수 */
  activeEdges: number;
}

export interface EndStats {
  volume: number;
  area: number;
  /** 스텝 끝 젖은 셀의 최소 두께 */
  hMin: number;
  /** 스텝 끝에 음수 두께인 젖은 셀이 있는가 */
  anyNegative: boolean;
}

/** numpy 가 내보낸 상태 (채널별 평면) */
export interface PlainState {
  h: Float32Array;
  wet: Float32Array;
  age: Float32Array;
  sage: Float32Array;
  theta: Float32Array;
  slime: Float32Array;
  C: Float32Array[];
  p: Float32Array;
  pm: Float32Array;
}

export class PlasmGPU {
  readonly params: PlasmParams;
  readonly N: number;
  readonly mg: MultigridGPU;
  /** 지금까지 돈 스텝 수. 모델 시간은 step·dt */
  step = 0;
  private glx: Glx;
  private A: [Tex, Tex];
  private B: [Tex, Tex];
  private C: [Tex, Tex];
  private curA = 0;
  private curB = 0;
  private curC = 0;
  private tB: [Target, Target];
  private tC: [Target, Target];
  private tAB: Target[][]; // [A 의 번호][B 의 번호] — 두 장을 함께 쓰는 패스용
  private aux: Tex;
  private W: Tex;
  private tAuxW: Target;
  private texG: Tex;
  private texCinit: Tex;
  private texField: Tex;
  private dry: [Tex, Tex, Tex];
  private tDry: [Target, Target, Target];
  private blur: [Tex, Tex];
  private tBlur: [Target, Target];
  private plan: Tex;
  private tPlan: Target;
  private red: Tex[] = [];
  private tRed: Target[] = [];
  private redBlock: number[] = [];
  private stat: Tex[] = [];
  private tStat: Target[] = [];
  private prog: Record<string, Prog> = {};

  constructor(glx: Glx, params: PlasmParams) {
    const N = params.N;
    if (N % 8 !== 0) throw new Error('격자 한 변은 8의 배수여야 한다');
    this.glx = glx;
    this.params = params;
    this.N = N;
    const vars = shaderVars(params);
    const src = plasmShaders(vars);
    for (const [name, s] of Object.entries(src)) this.prog[name] = glx.program(name, s);
    this.mg = new MultigridGPU(glx, N, vars);

    const rgba = (): Tex => glx.tex(N, N, 'rgba32f');
    this.A = [rgba(), rgba()];
    this.B = [rgba(), rgba()];
    this.C = [rgba(), rgba()];
    this.tB = [glx.target(this.B[0]), glx.target(this.B[1])];
    this.tC = [glx.target(this.C[0]), glx.target(this.C[1])];
    this.tAB = [0, 1].map((i) => [0, 1].map((j) => glx.target(this.A[i], this.B[j])));
    this.aux = rgba();
    this.W = rgba();
    this.tAuxW = glx.target(this.aux, this.W);
    this.mg.setLevel0(this.W, this.aux, this.aux);

    const noise = noiseFields(params.seed, N, params.edgeSigma, params.d0, params.d0Noise);
    this.texG = glx.tex(N, N, 'rgba32f', noise.G);
    this.texCinit = glx.tex(N, N, 'rgba32f', noise.Cinit);
    const field = new Float32Array(N * N * 2);
    const food = this.attractantField();
    for (let i = 0; i < N * N; i++) {
      field[i * 2] = noise.eta[i];
      field[i * 2 + 1] = food[i];
    }
    this.texField = glx.tex(N, N, 'rg32f', field);

    this.dry = [glx.tex(N, N, 'r32f'), glx.tex(N, N, 'r32f'), rgba()];
    this.tDry = [glx.target(this.dry[0]), glx.target(this.dry[1]), glx.target(this.dry[2])];
    this.blur = [glx.tex(N, N, 'r32f'), glx.tex(N, N, 'r32f')];
    this.tBlur = [glx.target(this.blur[0]), glx.target(this.blur[1])];
    this.plan = glx.tex(N, N, 'rg32f');
    this.tPlan = glx.target(this.plan);

    // 축소 사슬: N/8 → … → 1. 첫 단은 전용 셰이더가 8×8 블록을, 다음 단은 reduce_sum 이 블록 크기 redBlock 으로 줄인다
    let n = N / 8;
    for (;;) {
      this.red.push(glx.tex(n, n, 'rgba32f'));
      this.stat.push(glx.tex(n, n, 'rgba32f'));
      if (n === 1) break;
      const b = n <= 16 ? n : 8;
      this.redBlock.push(b);
      n = Math.ceil(n / b);
    }
    this.tRed = this.red.map((t) => glx.target(t));
    this.tStat = this.stat.map((t) => glx.target(t));
    this.reset();
  }

  /** 유인장 c = amp·Σ(주기 상) exp(−r²/2σ²). numpy 기준과 같은 식 */
  private attractantField(): Float32Array {
    const N = this.N;
    const out = new Float32Array(N * N);
    const a = this.params.attractant;
    if (!a) return out;
    const c0 = N / 2 - 0.5;
    const fx = c0 + a.dist * Math.cos((a.angleDeg * Math.PI) / 180);
    const fy = c0 + a.dist * Math.sin((a.angleDeg * Math.PI) / 180);
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        let g = 0;
        for (let sx = -N; sx <= N; sx += N) {
          for (let sy = -N; sy <= N; sy += N) {
            g += Math.exp(-((x - fx - sx) ** 2 + (y - fy - sy) ** 2) / (2 * a.sigma * a.sigma));
          }
        }
        out[y * N + x] = a.amp * g;
      }
    }
    return out;
  }

  /** 초기 상태: 격자 가운데의 원반 */
  reset(): void {
    const { N } = this;
    const { rInit, hInit } = this.params;
    const a = new Float32Array(N * N * 4);
    const c0 = N / 2 - 0.5;
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        if (Math.hypot(x - c0, y - c0) < rInit) {
          const i = (y * N + x) * 4;
          a[i] = hInit;
          a[i + 1] = 1;
        }
      }
    }
    const zero = new Float32Array(N * N * 4);
    this.curA = this.curB = this.curC = 0;
    this.glx.upload(this.A[0], a);
    this.glx.upload(this.B[0], zero);
    this.glx.upload(this.C[0], zero);
    this.step = 0;
  }

  /** numpy 가 내보낸 "스텝 시작 시점의 상태"를 넣는다 */
  loadState(s: PlainState, step: number): void {
    const n = this.N * this.N;
    const a = new Float32Array(n * 4);
    const b = new Float32Array(n * 4);
    const c = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
      a[i * 4] = s.h[i];
      a[i * 4 + 1] = s.wet[i];
      a[i * 4 + 2] = s.age[i];
      a[i * 4 + 3] = s.sage[i];
      b[i * 4] = s.theta[i];
      b[i * 4 + 1] = s.slime[i];
      b[i * 4 + 2] = s.p[i];
      b[i * 4 + 3] = s.pm[i];
      for (let k = 0; k < 4; k++) c[i * 4 + k] = s.C[k][i];
    }
    this.curA = this.curB = this.curC = 0;
    this.glx.upload(this.A[0], a);
    this.glx.upload(this.B[0], b);
    this.glx.upload(this.C[0], c);
    this.step = step;
  }

  /** 한 스텝. afterSolve 는 압력을 푼 직후(유량 갱신 전)에 불린다 — 시험이 풀이의 입력과 해를 읽는 자리 */
  stepOnce(afterSolve?: () => void): void {
    const { glx, prog, params: p } = this;
    const t = this.step * p.dt;
    const flipAB = (): Target => {
      this.curA = 1 - this.curA;
      this.curB = 1 - this.curB;
      return this.tAB[this.curA][this.curB];
    };

    // 1. 간선 켜기
    glx.draw(prog.edgeActivate, this.tC[1 - this.curC], { uA: this.A[this.curA], uC: this.C[this.curC], uCinit: this.texCinit });
    this.curC = 1 - this.curC;

    // 2. 위상
    for (let s = 0; s < p.substeps; s++) {
      glx.draw(prog.phase, this.tB[1 - this.curB], { uA: this.A[this.curA], uB: this.B[this.curB] });
      this.curB = 1 - this.curB;
    }

    // 3. 쉬는 두께, 우변, 간선 가중치
    glx.draw(prog.rest, this.tAuxW, { uA: this.A[this.curA], uB: this.B[this.curB], uC: this.C[this.curC], uG: this.texG, uT: t });

    // 4~6. 압력
    glx.draw(prog.mgInit, this.mg.p0Target(), { uA: this.A[this.curA], uB: this.B[this.curB] });
    this.mg.build();
    this.mg.solve(p.mgCycles, p.mgCoarseSweeps);
    if (afterSolve) afterSolve();
    const P = this.mg.pTex();

    // 7. 유량과 두께
    {
      const srcA = this.A[this.curA];
      const srcB = this.B[this.curB];
      glx.draw(prog.flux, flipAB(), { uA: srcA, uB: srcB, uW: this.W, uP: P });
    }

    // 8. 전역 평균 (Q0)
    glx.draw(prog.reduceQ0, this.tRed[0], { uW: this.W, uP: P, uA: this.A[this.curA], uC: this.C[this.curC] });
    for (let i = 1; i < this.red.length; i++) glx.draw(prog.reduceSum, this.tRed[i], { uSrc: this.red[i - 1], uBlock: this.redBlock[i - 1] });

    // 9. 강화
    glx.draw(prog.reinforce, this.tC[1 - this.curC], { uC: this.C[this.curC], uW: this.W, uP: P, uRed: this.red[this.red.length - 1] });
    this.curC = 1 - this.curC;

    // 10. 마름
    glx.draw(prog.dryMark, this.tDry[0], { uA: this.A[this.curA], uAux: this.aux, uStep: this.step });
    glx.draw(prog.dryConfirm, this.tDry[1], { uA: this.A[this.curA], uD: this.dry[0] });
    glx.draw(prog.dryShare, this.tDry[2], { uA: this.A[this.curA], uD: this.dry[1] });
    {
      const srcA = this.A[this.curA];
      const srcB = this.B[this.curB];
      glx.draw(prog.dryApply, flipAB(), { uA: srcA, uB: srcB, uD: this.dry[2] });
    }

    // 11. 젖은 마스크의 흐림
    glx.draw(prog.blur, this.tBlur[0], { uSrc: this.A[this.curA], uDir: [1, 0], uCh: 1 });
    glx.draw(prog.blur, this.tBlur[1], { uSrc: this.blur[0], uDir: [0, 1], uCh: 0 });

    // 12. 젖음
    glx.draw(prog.wetMark, this.tPlan, { uA: this.A[this.curA], uB: this.B[this.curB], uF: this.blur[1], uField: this.texField });
    {
      const srcA = this.A[this.curA];
      const srcB = this.B[this.curB];
      glx.draw(prog.wetApply, flipAB(), { uA: srcA, uB: srcB, uPlan: this.plan });
    }
    this.step++;
  }

  /** 방금 돈 스텝의 통계 (1×1 텍셀 읽기 — 파이프라인을 멈춘다) */
  readStepStats(): StepStats {
    const v = this.glx.read(this.red[this.red.length - 1]);
    return { hMinInStep: v[2], cMax: v[3], activeEdges: v[1] };
  }

  /** 스텝 끝 상태의 통계 (축소 패스를 따로 돌리고 읽는다. 시험용) */
  readEndStats(): EndStats {
    const { glx, prog } = this;
    glx.draw(prog.reduceStats, this.tStat[0], { uA: this.A[this.curA] });
    for (let i = 1; i < this.stat.length; i++) glx.draw(prog.reduceSum, this.tStat[i], { uSrc: this.stat[i - 1], uBlock: this.redBlock[i - 1] });
    const v = glx.read(this.stat[this.stat.length - 1]);
    return { volume: v[0], area: v[1], hMin: v[2], anyNegative: v[3] > 0.5 };
  }

  /** 캔버스에 지금 상태를 그린다 */
  view(width: number, height: number): void {
    this.glx.draw(this.prog.view, this.glx.screen(width, height), { uA: this.A[this.curA], uB: this.B[this.curB], uC: this.C[this.curC], uCanvas: [width, height] });
  }

  // ── 읽기 (RGBA float, N·N·4) ──
  readA(): Float32Array {
    return this.glx.read(this.A[this.curA]);
  }
  readB(): Float32Array {
    return this.glx.read(this.B[this.curB]);
  }
  readC(): Float32Array {
    return this.glx.read(this.C[this.curC]);
  }
  /** 이번 스텝의 간선 가중치 (afterSolve 안에서 읽는다) */
  readW(): Float32Array {
    return this.glx.read(this.W);
  }
  /** 우변, 차폐 항, 인접 최대 전도도, h* (afterSolve 안에서 읽는다) */
  readAux(): Float32Array {
    return this.glx.read(this.aux);
  }
  /** 풀이의 해 (r 채널) */
  readP(): Float32Array {
    return this.glx.read(this.mg.pTex());
  }
}
