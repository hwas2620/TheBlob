// 토러스 격자의 멀티그리드 — numpy 기준(specs/plasmodium-core/stage0/ref/mgt.py)을 그대로 옮긴 것
//
// 연산자:  M_i·p_i + Σ_e W_e·(p_i − p_j) = S_i     (M_i = 차폐 항. M = 0 인 셀은 비활성)
// 구성:    감쇠 Jacobi, V(2,2), 2×2 합 제한, 조각 상수 보간.
//          조대 연산자는 간선 가중치만 1/scale 로 줄이고 차폐 항은 자식 합 그대로 둔다. 매 스텝 다시 만든다.

import type { Glx, Prog, Target, Tex } from './glx';
import { multigridShaders, type ShaderVars } from './shaders';

export class MultigridGPU {
  /** 레벨별 격자 한 변. [0] 이 가장 촘촘하다 */
  readonly sizes: number[];
  readonly L: number;
  private glx: Glx;
  private W: Tex[] = []; // [0] 은 setLevel0 으로 받는다
  private M: Tex[] = []; // g 채널이 차폐 항. [0] 은 setLevel0
  private S: Tex[] = []; // r 채널이 우변. [0] 은 setLevel0
  private P: [Tex, Tex][] = [];
  private tP: [Target, Target][] = [];
  private cur: number[] = [];
  private R: Tex[] = [];
  private tR: Target[] = [];
  private tS: Target[] = [];
  private tWM: Target[] = [];
  private pJacobi: Prog;
  private pResidual: Prog;
  private pRestrict: Prog;
  private pProlong: Prog;
  private pCoarsen: Prog;

  /** 2로 나눠지는 동안, 한 변이 nmin 보다 클 때까지 줄인다 (mgt.py 와 같은 규칙) */
  static levels(N: number, nmin = 4): number[] {
    const sizes = [N];
    while (sizes[sizes.length - 1] > nmin && sizes[sizes.length - 1] % 2 === 0) sizes.push(sizes[sizes.length - 1] / 2);
    return sizes;
  }

  constructor(glx: Glx, N: number, vars: ShaderVars) {
    this.glx = glx;
    this.sizes = MultigridGPU.levels(N);
    this.L = this.sizes.length;
    const src = multigridShaders(vars);
    this.pJacobi = glx.program('mg_jacobi', src.jacobi);
    this.pResidual = glx.program('mg_residual', src.residual);
    this.pRestrict = glx.program('mg_restrict', src.restrict);
    this.pProlong = glx.program('mg_prolong', src.prolong);
    this.pCoarsen = glx.program('mg_coarsen', src.coarsen);
    for (let l = 0; l < this.L; l++) {
      const n = this.sizes[l];
      const a = glx.tex(n, n, 'r32f');
      const b = glx.tex(n, n, 'r32f');
      this.P.push([a, b]);
      this.tP.push([glx.target(a), glx.target(b)]);
      this.cur.push(0);
      if (l < this.L - 1) {
        const r = glx.tex(n, n, 'r32f');
        this.R[l] = r;
        this.tR[l] = glx.target(r);
      }
      if (l > 0) {
        this.W[l] = glx.tex(n, n, 'rgba32f');
        this.M[l] = glx.tex(n, n, 'rg32f');
        this.S[l] = glx.tex(n, n, 'r32f');
        this.tWM[l] = glx.target(this.W[l], this.M[l]);
        this.tS[l] = glx.target(this.S[l]);
      }
    }
  }

  /** 레벨 0 의 입력. S 는 r 채널, M 은 g 채널을 읽는다 (같은 텍스처여도 된다) */
  setLevel0(W: Tex, S: Tex, M: Tex): void {
    this.W[0] = W;
    this.S[0] = S;
    this.M[0] = M;
  }

  /** 웜스타트를 써 넣을 타깃 */
  p0Target(): Target {
    return this.tP[0][this.cur[0]];
  }

  /** 지금의 해 (r 채널) */
  pTex(): Tex {
    return this.P[0][this.cur[0]];
  }

  /** 조대 연산자를 레벨 0 에서부터 다시 만든다 */
  build(): void {
    for (let l = 1; l < this.L; l++) {
      this.glx.draw(this.pCoarsen, this.tWM[l], { uWf: this.W[l - 1], uMf: this.M[l - 1] });
    }
  }

  /** V(2,2) 사이클을 ncyc 번. 최조 격자에서는 Jacobi 를 nc 번 */
  solve(ncyc: number, nc: number): void {
    for (let i = 0; i < ncyc; i++) this.vcycle(0, nc);
  }

  private vcycle(l: number, nc: number): void {
    if (l === this.L - 1) {
      this.jacobi(l, nc);
      return;
    }
    this.jacobi(l, 2);
    this.glx.draw(this.pResidual, this.tR[l], { uP: this.P[l][this.cur[l]], uW: this.W[l], uS: this.S[l], uM: this.M[l] });
    this.glx.draw(this.pRestrict, this.tS[l + 1], { uR: this.R[l] });
    this.glx.clear(this.tP[l + 1][this.cur[l + 1]], 0);
    this.vcycle(l + 1, nc);
    const dst = 1 - this.cur[l];
    this.glx.draw(this.pProlong, this.tP[l][dst], { uP: this.P[l][this.cur[l]], uE: this.P[l + 1][this.cur[l + 1]], uM: this.M[l] });
    this.cur[l] = dst;
    this.jacobi(l, 2);
  }

  private jacobi(l: number, k: number): void {
    for (let i = 0; i < k; i++) {
      const dst = 1 - this.cur[l];
      this.glx.draw(this.pJacobi, this.tP[l][dst], { uP: this.P[l][this.cur[l]], uW: this.W[l], uS: this.S[l], uM: this.M[l] });
      this.cur[l] = dst;
    }
  }
}
