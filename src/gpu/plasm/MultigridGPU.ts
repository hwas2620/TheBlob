// 토러스 격자의 멀티그리드 — numpy 기준(specs/plasmodium-core/stage0/ref/mgt.py)을 그대로 옮긴 것
//
// 연산자:  M_i·p_i + Σ_e W_e·(p_i − p_j) = S_i     (M_i = 차폐 항. M = 0 인 셀은 비활성)
// 구성:    감쇠 Jacobi, V(2,2), 2×2 합 제한, 조각 상수 보간.
//          조대 연산자는 간선 가중치만 1/scale 로 줄이고 차폐 항은 자식 합 그대로 둔다. 매 스텝 다시 만든다.

import type { Glx, Prog, Rect, Target, Tex } from './glx';
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
  private pResRestrict: Prog;
  private pProlongJacobi: Prog;
  private pJacobi2: Prog | null = null;
  private pProlongJacobi2: Prog | null = null;
  private pJacobi0: Prog;
  private pJacobi2z: Prog | null = null;
  /** 두 번 스무딩 셰이더가 이 기기에서 컴파일되지 않았으면 그 이유 (그때는 sweep2 를 켜도 쓰지 않는다) */
  sweep2Error: string | null = null;
  /** true 면 "잔차+제한", "보간+첫 뒤 스무딩"을 한 패스씩으로 합친다 (레벨당 7 → 5 드로콜. 산술은 같다) */
  merged = false;
  /** 레벨 0 에서 그릴 영역. null 이면 전체. 활성 셀이 모두 이 안에 있어야 한다 */
  rect: Rect | null = null;
  /**
   * true 면 그리는 영역이 sweep2MaxArea 텍셀 이하인 레벨에서 스무딩 두 번을 한 패스로 한다(산술은 같다).
   * 그런 레벨에서는 채우기보다 드로콜 수가 비용이라 텍셀 읽기를 늘려 드로콜을 줄이는 쪽이 싸다.
   */
  sweep2 = false;
  sweep2MaxArea = 4096;
  /**
   * true 면 조대 레벨의 해를 0 으로 지우는 패스 없이, 0 에서 출발한 첫 스무딩을 전용 패스로 한다(산술은 같다).
   * 사이클마다 레벨 수만큼의 지우기 패스가 준다
   */
  zeroStart = false;

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
    this.pResRestrict = glx.program('mg_resrestrict', src.resRestrict);
    this.pProlongJacobi = glx.program('mg_prolong_jacobi', src.prolongJacobi);
    this.pJacobi0 = glx.program('mg_jacobi0', src.jacobi0);
    try {
      // 텍셀 읽기가 수백 번인 큰 셰이더라 드라이버에 따라 컴파일이 안 될 수 있다. 그때는 한 번씩 그리는 길로 돌아간다
      this.pJacobi2 = glx.program('mg_jacobi2', src.jacobi2);
      this.pProlongJacobi2 = glx.program('mg_prolong_jacobi2', src.prolongJacobi2);
      this.pJacobi2z = glx.program('mg_jacobi2z', src.jacobi2z);
    } catch (e) {
      this.pJacobi2 = null;
      this.pProlongJacobi2 = null;
      this.pJacobi2z = null;
      this.sweep2Error = e instanceof Error ? e.message : String(e);
    }
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

  /** 레벨 l 에서 그릴 영역: 레벨 0 의 영역을 덮는 조대 셀에 한 칸 여유. 작은 레벨은 전체 */
  private lr(l: number): Rect | null {
    const n = this.sizes[l];
    if (!this.rect || n <= 32) return null;
    const s = 1 << l;
    const [x, y, w, h] = this.rect;
    const x0 = Math.max(0, Math.floor(x / s) - 1);
    const y0 = Math.max(0, Math.floor(y / s) - 1);
    const x1 = Math.min(n, Math.ceil((x + w) / s) + 1);
    const y1 = Math.min(n, Math.ceil((y + h) / s) + 1);
    return [x0, y0, x1 - x0, y1 - y0];
  }

  /** 이 레벨에서 스무딩 두 번을 한 패스로 할지 */
  private dbl(l: number): boolean {
    if (!this.sweep2 || !this.pJacobi2 || !this.pProlongJacobi2 || !this.pJacobi2z) return false;
    const r = this.lr(l);
    const area = r ? r[2] * r[3] : this.sizes[l] * this.sizes[l];
    return area <= this.sweep2MaxArea;
  }

  /** 작업 텍스처를 모두 0 으로 (상태를 새로 넣을 때) */
  clearAll(): void {
    for (let l = 0; l < this.L; l++) {
      this.glx.clear(this.tP[l][0], 0);
      this.glx.clear(this.tP[l][1], 0);
      if (l < this.L - 1) this.glx.clear(this.tR[l], 0);
      if (l > 0) {
        this.glx.clear(this.tWM[l], 0);
        this.glx.clear(this.tS[l], 0);
      }
    }
  }

  /** 조대 연산자를 레벨 0 에서부터 다시 만든다 */
  build(): void {
    for (let l = 1; l < this.L; l++) {
      this.glx.draw(this.pCoarsen, this.tWM[l], { uWf: this.W[l - 1], uMf: this.M[l - 1] }, this.lr(l));
    }
  }

  /** 벤치마크용: 가장 작은 레벨에 Jacobi 를 n 번 그리고 끝나기를 기다린다 (드로콜 하나의 고정 비용을 재는 데 쓴다) */
  benchTinyDraws(n: number): void {
    const l = this.L - 1;
    this.jacobi(l, n);
    this.glx.readPixel(this.P[l][this.cur[l]]);
  }

  /** 측정용: 가장 작은 레벨의 같은 타깃에, 상태를 하나도 바꾸지 않고 n 번 그린다 (타깃을 바꾸지 않는 드로콜의 비용) */
  benchTinySame(n: number): void {
    const l = this.L - 1;
    const dst = 1 - this.cur[l];
    for (let i = 0; i < n; i++) this.glx.draw(this.pJacobi0, this.tP[l][dst], { uW: this.W[l], uS: this.S[l], uM: this.M[l] });
    this.glx.readPixel(this.P[l][dst]);
  }

  /** 측정용: 가장 작은 레벨의 같은 타깃에, 프로그램 둘을 번갈아 n 번 그린다 (텍스처 묶음은 그대로 — 프로그램 전환의 비용) */
  benchTinyProg(n: number): void {
    const l = this.L - 1;
    const dst = 1 - this.cur[l];
    // 유니폼을 같은 순서로 넘겨 두 프로그램이 같은 유닛을 쓰게 한다 (uP 는 뒤에)
    const u = { uW: this.W[l], uS: this.S[l], uM: this.M[l], uP: this.P[l][this.cur[l]] };
    for (let i = 0; i < n; i++) this.glx.draw(i & 1 ? this.pJacobi : this.pJacobi0, this.tP[l][dst], u);
    this.glx.readPixel(this.P[l][dst]);
  }

  /** 측정용: 그리기와 무관한 GL 호출 n 번, 텍스처 묶기 n 번. 끝을 맞추려고 텍셀 하나를 읽는다 */
  benchCalls(n: number): void {
    this.glx.benchCalls(n);
    this.sync();
  }

  benchBinds(n: number): void {
    const l = this.L - 1;
    this.glx.benchBinds(n, this.P[l][0], this.P[l][1]);
    this.sync();
  }

  /** 측정용: 가장 작은 레벨의 타깃 둘을 번갈아 n 번 지운다 */
  benchTinyClears(n: number): void {
    const l = this.L - 1;
    for (let i = 0; i < n; i++) this.glx.clear(this.tP[l][i & 1], 0);
    this.glx.readPixel(this.P[l][(n - 1) & 1]);
  }

  /** 측정용: 레벨 0 (격자 크기의 R32F 타깃)에 가위를 좁힌 Jacobi 를 타깃을 번갈아 n 번 그린다 */
  probeLevel0(n: number, r: Rect): void {
    for (let i = 0; i < n; i++) {
      const dst = 1 - this.cur[0];
      this.glx.draw(this.pJacobi, this.tP[0][dst], { uP: this.P[0][this.cur[0]], uW: this.W[0], uS: this.S[0], uM: this.M[0] }, r);
      this.cur[0] = dst;
    }
    this.glx.readPixel(this.P[0][this.cur[0]]);
  }

  /** 조대 연산자의 마지막 레벨에서 텍셀 하나를 읽어 재구성이 끝나기를 기다린다 (측정용) */
  syncBuild(): void {
    this.glx.readPixel(this.W[this.L - 1]);
  }

  /** 방금 푼 해에서 텍셀 하나를 읽어 풀이의 명령이 모두 끝나기를 기다린다 (벽시계 측정용) */
  sync(): void {
    this.glx.readPixel(this.P[0][this.cur[0]]);
  }

  /** V(2,2) 사이클을 ncyc 번. 최조 격자에서는 Jacobi 를 nc 번 */
  solve(ncyc: number, nc: number): void {
    for (let i = 0; i < ncyc; i++) this.vcycle(0, nc);
  }

  /** fromZero: 이 레벨의 해가 0 에서 출발한다(조대 레벨). zeroStart 가 켜져 있으면 지우지 않고 전용 패스로 시작한다 */
  private vcycle(l: number, nc: number, fromZero = false): void {
    if (l === this.L - 1) {
      this.smooth(l, nc, fromZero);
      return;
    }
    this.smooth(l, 2, fromZero);
    const fine = { uP: this.P[l][this.cur[l]], uW: this.W[l], uS: this.S[l], uM: this.M[l] };
    if (this.merged) {
      this.glx.draw(this.pResRestrict, this.tS[l + 1], fine, this.lr(l + 1));
    } else {
      this.glx.draw(this.pResidual, this.tR[l], fine, this.lr(l));
      this.glx.draw(this.pRestrict, this.tS[l + 1], { uR: this.R[l] }, this.lr(l + 1));
    }
    if (this.zeroStart) {
      this.vcycle(l + 1, nc, true);
    } else {
      this.glx.clear(this.tP[l + 1][this.cur[l + 1]], 0);
      this.vcycle(l + 1, nc);
    }
    const dst = 1 - this.cur[l];
    if (this.merged) {
      const two = this.dbl(l);
      this.glx.draw(two ? this.pProlongJacobi2! : this.pProlongJacobi, this.tP[l][dst], { ...fine, uE: this.P[l + 1][this.cur[l + 1]] }, this.lr(l));
      this.cur[l] = dst;
      if (!two) this.jacobi(l, 1);
    } else {
      this.glx.draw(this.pProlong, this.tP[l][dst], { uP: this.P[l][this.cur[l]], uE: this.P[l + 1][this.cur[l + 1]], uM: this.M[l] }, this.lr(l));
      this.cur[l] = dst;
      this.smooth(l, 2);
    }
  }

  /** 스무딩 k 번. 두 번씩 묶을 수 있는 레벨에서는 묶는다. fromZero 면 지금의 해를 읽지 않고 0 에서 출발한다 */
  private smooth(l: number, k: number, fromZero = false): void {
    const two = this.dbl(l);
    let done = 0;
    if (fromZero && k > 0) {
      // 0 에서 출발한 첫 스무딩(묶을 수 있으면 두 번)을 전용 패스로. 대상 텍스처의 이전 내용은 읽지 않는다
      const pair = two && k >= 2;
      const dst = 1 - this.cur[l];
      this.glx.draw(pair ? this.pJacobi2z! : this.pJacobi0, this.tP[l][dst], { uW: this.W[l], uS: this.S[l], uM: this.M[l] }, this.lr(l));
      this.cur[l] = dst;
      done = pair ? 2 : 1;
    }
    k -= done;
    if (!two) {
      this.jacobi(l, k);
      return;
    }
    for (let i = 0; i + 1 < k; i += 2) {
      const dst = 1 - this.cur[l];
      this.glx.draw(this.pJacobi2!, this.tP[l][dst], { uP: this.P[l][this.cur[l]], uW: this.W[l], uS: this.S[l], uM: this.M[l] }, this.lr(l));
      this.cur[l] = dst;
    }
    if (k % 2 === 1) this.jacobi(l, 1);
  }

  private jacobi(l: number, k: number): void {
    for (let i = 0; i < k; i++) {
      const dst = 1 - this.cur[l];
      this.glx.draw(this.pJacobi, this.tP[l][dst], { uP: this.P[l][this.cur[l]], uW: this.W[l], uS: this.S[l], uM: this.M[l] }, this.lr(l));
      this.cur[l] = dst;
    }
  }
}
