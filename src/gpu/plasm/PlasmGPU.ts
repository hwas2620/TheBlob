// 원형질체 코어 — 상태 텍스처와 한 스텝의 패스 순서 (spec 의 규칙 1~7)
//
//   cellA  h, wet, age, sage          cellB  θ, slime, p, 직전 p          edgeC  간선 전도도 E, N, NE, SE
//
// 한 스텝: 간선 켜기 → 위상(부분 스텝) → 쉬는 두께·우변·가중치 → 멀티그리드 → 유량·두께 → 전역 평균 → 강화 → 마름 → 젖음
// numpy 기준 모델(specs/plasmodium-core/stage0/ref/ref_model.py)과 연산 순서를 맞췄다.

import type { AsyncRead, Glx, Prog, Rect, Target, Tex } from './glx';
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

/** 한 스텝의 패스 묶음 (압력 풀이는 따로) */
export type PassGroup = 'edges' | 'phase' | 'rest' | 'init' | 'flux' | 'q0' | 'reinforce' | 'dry' | 'blur' | 'wet';
const GROUPS_BEFORE_SOLVE: PassGroup[] = ['edges', 'phase', 'rest', 'init'];
const GROUPS_AFTER_SOLVE: PassGroup[] = ['flux', 'q0', 'reinforce', 'dry', 'blur', 'wet'];

/** snapshot() 이 읽어 둔 상태 (세 상태 텍스처의 RGBA 와 스텝 수) */
export interface Snapshot {
  a: Float32Array;
  b: Float32Array;
  c: Float32Array;
  step: number;
}

/** 경계 상자를 다시 재는 주기(스텝) */
const BOUNDS_EVERY = 8;
/** 경계 상자 밖으로 두는 여유(셀). 젖은 마스크 흐림의 반경 6 보다 커야 한다 */
const BOUNDS_MARGIN = 10;

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
  /**
   * 몸 주변만 계산한다. 모든 패스에 "젖은 셀의 경계 상자 + 여유"만 그리는 가위 사각형을 건다.
   * 젖은 영역은 한 스텝에 한 칸씩만 넓어지므로, 상자를 잰 뒤 지난 스텝 수만큼 여유를 키우면 상자 밖은 늘 변하지 않는 마른 땅이다.
   * 상자가 격자 가장자리를 넘으면 전체를 그린다.
   */
  scissor = false;
  /** 경계 상자를 멈춤 없이 읽는다(게임 루프용). false 면 그 자리에서 읽는다(시험용. 파이프라인이 멈춘다) */
  asyncBounds = true;
  /** false 면 경계 상자를 스스로 다시 재지 않는다 (벤치마크가 refreshBounds 로 직접 잰다) */
  autoBounds = true;
  /**
   * 가위 사각형의 여유에 더하는 셀 수. 게임 루프에서는 경계 상자가 한두 프레임 늦게 도착해 여유가 그만큼 크다.
   * 그 자리에서 읽는 측정(벤치마크)이 그 크기를 흉내 낼 때 쓴다. 키우는 쪽은 언제나 안전하다
   */
  marginExtra = 0;
  /** 스텝당 V 사이클 수 (params.mgCycles 에서 시작. 돌리는 중에 바꿀 수 있다) */
  cycles: number;
  private bounds: [number, number, number, number] | null = null; // 젖은 셀의 x0, y0, x1, y1
  private boundsStep = 0;
  private pending: { read: AsyncRead; step: number } | null = null;
  private box: Tex[] = [];
  private tBox: Target[] = [];

  constructor(glx: Glx, params: PlasmParams) {
    const N = params.N;
    if (N % 8 !== 0) throw new Error('격자 한 변은 8의 배수여야 한다');
    this.glx = glx;
    this.params = params;
    this.N = N;
    this.cycles = params.mgCycles;
    // 가위 사각형 밖이 "변하지 않는 마른 땅"이려면 가장 멀리 읽는 패스(젖은 마스크의 흐림)의 반경이 여유보다 작아야 한다
    const blurRadius = Math.floor(3.0 * params.curvSigma + 0.5);
    if (blurRadius >= BOUNDS_MARGIN) throw new Error(`흐림 반경(${blurRadius})이 가위 사각형의 여유(${BOUNDS_MARGIN})보다 작아야 한다`);
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
    // 타깃에 붙지 않는 텍스처는 할당에 실패해도 타깃의 완전성 검사에 걸리지 않는다
    glx.checkError(`${N}² 격자의 텍스처 만들기`);

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
      this.box.push(glx.tex(n, n, 'rgba32f'));
      if (n === 1) break;
      const b = n <= 16 ? n : 8;
      this.redBlock.push(b);
      n = Math.ceil(n / b);
    }
    this.tRed = this.red.map((t) => glx.target(t));
    this.tStat = this.stat.map((t) => glx.target(t));
    this.tBox = this.box.map((t) => glx.target(t));
    this.reset();
  }

  /**
   * 상태를 통째로 바꾼다. 핑퐁 두 장 모두에 올린다 — "몸 주변만 계산"은 가위 밖을 다시 쓰지 않으므로
   * 다른 한 장에 이전 몸이 남아 있으면 안 된다. 작업 텍스처도 비우고 경계 상자를 CPU 에서 다시 잰다
   */
  private setState(a: Float32Array, b: Float32Array, c: Float32Array, step: number): void {
    const { glx, N } = this;
    this.curA = this.curB = this.curC = 0;
    for (let i = 0; i < 2; i++) {
      glx.upload(this.A[i], a);
      glx.upload(this.B[i], b);
      glx.upload(this.C[i], c);
    }
    this.step = step;
    glx.clear(this.tAuxW, 0);
    for (const t of this.tDry) glx.clear(t, 0);
    for (const t of this.tBlur) glx.clear(t, 0);
    glx.clear(this.tPlan, 0);
    for (const t of this.tRed) glx.clear(t, [0, 0, 1e30, 0]);
    for (const t of this.tBox) glx.clear(t, 1e9);
    this.mg.clearAll();
    let x0 = N, y0 = N, x1 = -1, y1 = -1;
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        if (a[(y * N + x) * 4 + 1] > 0.5) {
          if (x < x0) x0 = x;
          if (x > x1) x1 = x;
          if (y < y0) y0 = y;
          if (y > y1) y1 = y;
        }
      }
    }
    this.bounds = x1 >= 0 ? [x0, y0, x1, y1] : null;
    this.boundsStep = this.step;
    this.dropPending();
  }

  /** 거두지 않은 경계 상자 읽기를 버린다 */
  private dropPending(): void {
    if (this.pending) this.glx.cancel(this.pending.read);
    this.pending = null;
  }

  /** 지금 상태를 통째로 읽어 둔다 (벤치마크가 변형마다 같은 몸에서 출발하게 하는 데 쓴다. 파이프라인이 멈춘다) */
  snapshot(): Snapshot {
    return { a: this.readA(), b: this.readB(), c: this.readC(), step: this.step };
  }

  /** snapshot 으로 읽어 둔 상태로 되돌린다 */
  restore(s: Snapshot): void {
    this.setState(s.a, s.b, s.c, s.step);
  }

  /** 방금 끝난 스텝의 마지막 출력에서 텍셀 하나를 읽어, 그 스텝까지의 명령이 모두 끝나기를 기다린다 (벽시계 측정용) */
  sync(): void {
    this.glx.readPixel(this.A[this.curA]);
  }

  /** 이번 스텝에 그릴 영역. null 이면 전체 */
  private activeRect(): Rect | null {
    if (!this.scissor || !this.bounds) return null;
    const m = BOUNDS_MARGIN + (this.step - this.boundsStep) + this.marginExtra;
    const x0 = this.bounds[0] - m;
    const y0 = this.bounds[1] - m;
    const x1 = this.bounds[2] + m;
    const y1 = this.bounds[3] + m;
    if (x0 < 0 || y0 < 0 || x1 >= this.N || y1 >= this.N) return null;
    return [x0, y0, x1 - x0 + 1, y1 - y0 + 1];
  }

  /** 8×8 블록 축소의 첫 단에 쓸 영역 */
  private static blockRect(r: Rect | null): Rect | null {
    if (!r) return null;
    const x0 = Math.floor(r[0] / 8);
    const y0 = Math.floor(r[1] / 8);
    return [x0, y0, Math.ceil((r[0] + r[2]) / 8) - x0, Math.ceil((r[1] + r[3]) / 8) - y0];
  }

  /** 경계 상자를 다시 잰다 (축소 패스 뒤 1×1 텍셀을 읽는다) */
  private updateBounds(rect: Rect | null): void {
    const { glx, prog } = this;
    if (this.pending) {
      const v = glx.poll(this.pending.read);
      if (v !== 'pending') {
        // 실패했으면 버리고 아래에서 다시 잰다 (여유는 그동안 스텝마다 커져 있으므로 안전하다)
        if (v !== 'failed') this.applyBounds(v, this.pending.step);
        this.pending = null;
      }
    }
    if (this.step % BOUNDS_EVERY !== 0 || this.pending) return;
    glx.draw(prog.bbox0, this.tBox[0], { uA: this.A[this.curA] }, PlasmGPU.blockRect(rect));
    for (let i = 1; i < this.box.length; i++) glx.draw(prog.reduceMin, this.tBox[i], { uSrc: this.box[i - 1], uBlock: this.redBlock[i - 1] });
    const last = this.box[this.box.length - 1];
    if (this.asyncBounds) {
      const read = glx.readAsync(last);
      if (read) this.pending = { read, step: this.step };
    } else {
      this.applyBounds(glx.read(last), this.step);
    }
  }

  /** 경계 상자를 지금 재서 바로 적용한다 (파이프라인이 멈춘다) */
  refreshBounds(): void {
    const { glx, prog } = this;
    glx.draw(prog.bbox0, this.tBox[0], { uA: this.A[this.curA] });
    for (let i = 1; i < this.box.length; i++) glx.draw(prog.reduceMin, this.tBox[i], { uSrc: this.box[i - 1], uBlock: this.redBlock[i - 1] });
    this.applyBounds(glx.read(this.box[this.box.length - 1]), this.step);
    this.dropPending();
  }

  /** 지금 그리는 영역의 넓이가 격자에서 차지하는 비율 (가위를 쓰지 않으면 1) */
  activeFraction(): number {
    const r = this.activeRect();
    return r ? (r[2] * r[3]) / (this.N * this.N) : 1;
  }

  private applyBounds(v: Float32Array, step: number): void {
    this.bounds = v[0] > 1e8 ? null : [v[0], v[1], -v[2], -v[3]];
    this.boundsStep = step;
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
    this.setState(a, zero, zero, 0);
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
    this.setState(a, b, c, step);
  }

  /** 한 스텝. afterSolve 는 압력을 푼 직후(유량 갱신 전)에 불린다 — 시험이 풀이의 입력과 해를 읽는 자리 */
  stepOnce(afterSolve?: () => void): void {
    const p = this.params;
    const r = this.activeRect();
    this.mg.rect = r;
    for (const g of GROUPS_BEFORE_SOLVE) this.runGroup(g, r);
    this.mg.build();
    this.mg.solve(this.cycles, p.mgCoarseSweeps);
    if (afterSolve) afterSolve();
    for (const g of GROUPS_AFTER_SOLVE) this.runGroup(g, r);
    this.step++;
    if (this.scissor && this.autoBounds) this.updateBounds(r);
  }

  private flipAB(): Target {
    this.curA = 1 - this.curA;
    this.curB = 1 - this.curB;
    return this.tAB[this.curA][this.curB];
  }

  /** 스텝의 패스 묶음 하나를 그린다. 압력 풀이(조대 연산자, V 사이클)는 MultigridGPU 가 한다 */
  private runGroup(g: PassGroup, r: Rect | null): void {
    const { glx, prog, params: p } = this;
    switch (g) {
      case 'edges': // 1. 간선 켜기
        glx.draw(prog.edgeActivate, this.tC[1 - this.curC], { uA: this.A[this.curA], uC: this.C[this.curC], uCinit: this.texCinit }, r);
        this.curC = 1 - this.curC;
        break;
      case 'phase': // 2. 위상
        for (let s = 0; s < p.substeps; s++) {
          glx.draw(prog.phase, this.tB[1 - this.curB], { uA: this.A[this.curA], uB: this.B[this.curB] }, r);
          this.curB = 1 - this.curB;
        }
        break;
      case 'rest': // 3. 쉬는 두께, 우변, 간선 가중치
        glx.draw(prog.rest, this.tAuxW, { uA: this.A[this.curA], uB: this.B[this.curB], uC: this.C[this.curC], uG: this.texG, uT: this.step * p.dt }, r);
        break;
      case 'init': // 4. 압력의 웜스타트
        glx.draw(prog.mgInit, this.mg.p0Target(), { uA: this.A[this.curA], uB: this.B[this.curB] }, r);
        break;
      case 'flux': {
        // 7. 유량과 두께
        const srcA = this.A[this.curA];
        const srcB = this.B[this.curB];
        glx.draw(prog.flux, this.flipAB(), { uA: srcA, uB: srcB, uW: this.W, uP: this.mg.pTex() }, r);
        break;
      }
      case 'q0': // 8. 전역 평균 (Q0)
        glx.draw(prog.reduceQ0, this.tRed[0], { uW: this.W, uP: this.mg.pTex(), uA: this.A[this.curA], uC: this.C[this.curC] }, PlasmGPU.blockRect(r));
        for (let i = 1; i < this.red.length; i++) glx.draw(prog.reduceSum, this.tRed[i], { uSrc: this.red[i - 1], uBlock: this.redBlock[i - 1] });
        break;
      case 'reinforce': // 9. 강화
        glx.draw(prog.reinforce, this.tC[1 - this.curC], { uC: this.C[this.curC], uW: this.W, uP: this.mg.pTex(), uRed: this.red[this.red.length - 1] }, r);
        this.curC = 1 - this.curC;
        break;
      case 'dry': {
        // 10. 마름
        glx.draw(prog.dryMark, this.tDry[0], { uA: this.A[this.curA], uAux: this.aux, uStep: this.step }, r);
        glx.draw(prog.dryConfirm, this.tDry[1], { uA: this.A[this.curA], uD: this.dry[0] }, r);
        glx.draw(prog.dryShare, this.tDry[2], { uA: this.A[this.curA], uD: this.dry[1] }, r);
        const srcA = this.A[this.curA];
        const srcB = this.B[this.curB];
        glx.draw(prog.dryApply, this.flipAB(), { uA: srcA, uB: srcB, uD: this.dry[2] }, r);
        break;
      }
      case 'blur': // 11. 젖은 마스크의 흐림
        glx.draw(prog.blur, this.tBlur[0], { uSrc: this.A[this.curA], uDir: [1, 0], uCh: 1 }, r);
        glx.draw(prog.blur, this.tBlur[1], { uSrc: this.blur[0], uDir: [0, 1], uCh: 0 }, r);
        break;
      case 'wet': {
        // 12. 젖음
        glx.draw(prog.wetMark, this.tPlan, { uA: this.A[this.curA], uB: this.B[this.curB], uF: this.blur[1], uField: this.texField }, r);
        const srcA = this.A[this.curA];
        const srcB = this.B[this.curB];
        glx.draw(prog.wetApply, this.flipAB(), { uA: srcA, uB: srcB, uPlan: this.plan }, r);
        break;
      }
    }
  }

  /**
   * 측정용: 패스 묶음 하나를 k 번 연달아 그리고 끝나기를 기다린다. 같은 입력으로 되풀이하므로 상태는 망가진다
   * (재고 나면 restore 로 되돌린다). 'build' 와 'cycle' 은 압력 풀이의 조대 연산자 재구성과 V 사이클 한 번이다
   */
  profileGroup(g: PassGroup | 'build' | 'cycle', k: number): void {
    const r = this.activeRect();
    this.mg.rect = r;
    for (let i = 0; i < k; i++) {
      if (g === 'build') this.mg.build();
      else if (g === 'cycle') this.mg.solve(1, this.params.mgCoarseSweeps);
      else this.runGroup(g, r);
    }
    // 묶음의 마지막 출력을 읽어 끝을 맞춘다
    const glx = this.glx;
    if (g === 'build') this.mg.syncBuild();
    else if (g === 'cycle' || g === 'init') this.mg.sync();
    else if (g === 'edges' || g === 'reinforce') glx.readPixel(this.C[this.curC]);
    else if (g === 'phase') glx.readPixel(this.B[this.curB]);
    else if (g === 'rest') glx.readPixel(this.W);
    else if (g === 'q0') glx.readPixel(this.red[this.red.length - 1]);
    else if (g === 'blur') glx.readPixel(this.blur[1]);
    else glx.readPixel(this.A[this.curA]);
  }

  /**
   * 측정용: 타깃의 크기와 종류에 따라 패스 하나의 고정 비용이 얼마나 다른지 보려고, 가위를 4×4 로 좁힌 가벼운 패스를 n 번 그린다.
   * 'r32f' 는 격자 크기의 R32F 타깃(레벨 0 의 압력), 'rgba' 는 RGBA32F 타깃(위상), 'mrt' 는 RGBA32F 두 장(두께와 위상)을 번갈아 쓴다
   */
  probe(kind: 'r32f' | 'rgba' | 'mrt', n: number): void {
    const { glx, prog } = this;
    const r: Rect = [0, 0, 4, 4];
    if (kind === 'r32f') {
      this.mg.probeLevel0(n, r);
      return;
    }
    for (let i = 0; i < n; i++) {
      if (kind === 'rgba') {
        glx.draw(prog.phase, this.tB[1 - this.curB], { uA: this.A[this.curA], uB: this.B[this.curB] }, r);
        this.curB = 1 - this.curB;
      } else {
        const srcA = this.A[this.curA];
        const srcB = this.B[this.curB];
        glx.draw(prog.wetApply, this.flipAB(), { uA: srcA, uB: srcB, uPlan: this.plan }, r);
      }
    }
    glx.readPixel(kind === 'rgba' ? this.B[this.curB] : this.A[this.curA]);
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
