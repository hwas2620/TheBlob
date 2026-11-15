// 원형질체 코어용 WebGL2 도우미
// float 텍스처, 다중 타깃 FBO, 풀스크린 쿼드, 드로콜 계수를 한곳에 모은다.

import { FULLSCREEN_QUAD_VERT } from '../shaders';

export type Fmt = 'rgba32f' | 'rg32f' | 'r32f';

export interface Tex {
  tex: WebGLTexture;
  w: number;
  h: number;
  fmt: Fmt;
}

export interface Target {
  fbo: WebGLFramebuffer;
  w: number;
  h: number;
  n: number; // 색 첨부 수
}

interface UniformInfo {
  loc: WebGLUniformLocation;
  type: number;
}

export interface Prog {
  prog: WebGLProgram;
  name: string;
  uni: Map<string, UniformInfo>;
}

export type UVal = number | readonly number[] | Tex;

/** [x, y, w, h] — 그릴 영역 (타깃 픽셀 좌표) */
export type Rect = readonly [number, number, number, number];

/** 멈춤 없는 읽기의 손잡이 (readAsync 가 만들고 poll 이 거둔다) */
export interface AsyncRead {
  buf: WebGLBuffer;
  sync: WebGLSync;
  w: number;
  h: number;
}

export interface GlCaps {
  renderer: string;
  colorBufferFloat: boolean;
  maxDrawBuffers: number;
  maxTextureSize: number;
  timerQuery: boolean;
}

const CHANNELS: Record<Fmt, number> = { rgba32f: 4, rg32f: 2, r32f: 1 };

export class Glx {
  readonly gl: WebGL2RenderingContext;
  /** 지금까지의 드로콜 수 (비용 측정용) */
  drawCalls = 0;
  readonly timerExt: unknown;
  private vao: WebGLVertexArrayObject;
  private readFbo: WebGLFramebuffer;
  private current: WebGLProgram | null = null;

  constructor(gl: WebGL2RenderingContext) {
    this.gl = gl;
    if (!gl.getExtension('EXT_color_buffer_float')) {
      throw new Error('EXT_color_buffer_float 를 지원하지 않는 기기입니다');
    }
    this.timerExt = gl.getExtension('EXT_disjoint_timer_query_webgl2');
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.pixelStorei(gl.PACK_ALIGNMENT, 1);

    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);
    const vbo = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    this.vao = vao;
    this.readFbo = gl.createFramebuffer()!;
  }

  static caps(gl: WebGL2RenderingContext): GlCaps {
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    return {
      renderer: String(dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)),
      colorBufferFloat: !!gl.getExtension('EXT_color_buffer_float'),
      maxDrawBuffers: gl.getParameter(gl.MAX_DRAW_BUFFERS) as number,
      maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE) as number,
      timerQuery: !!gl.getExtension('EXT_disjoint_timer_query_webgl2'),
    };
  }

  tex(w: number, h: number, fmt: Fmt, data?: Float32Array): Tex {
    const gl = this.gl;
    const tex = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    const [internal, format] = this.glFormat(fmt);
    gl.texImage2D(gl.TEXTURE_2D, 0, internal, w, h, 0, format, gl.FLOAT, data ?? new Float32Array(w * h * CHANNELS[fmt]));
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    return { tex, w, h, fmt };
  }

  upload(t: Tex, data: Float32Array): void {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, t.tex);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, t.w, t.h, this.glFormat(t.fmt)[1], gl.FLOAT, data);
  }

  /** 색 첨부가 여럿이면 셰이더의 layout(location=i) 출력에 차례로 대응한다 */
  target(...texs: Tex[]): Target {
    const gl = this.gl;
    const fbo = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    const bufs: number[] = [];
    texs.forEach((t, i) => {
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0 + i, gl.TEXTURE_2D, t.tex, 0);
      bufs.push(gl.COLOR_ATTACHMENT0 + i);
    });
    gl.drawBuffers(bufs);
    const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    if (status !== gl.FRAMEBUFFER_COMPLETE) throw new Error(`FBO 불완전: 0x${status.toString(16)}`);
    return { fbo, w: texs[0].w, h: texs[0].h, n: texs.length };
  }

  /** 캔버스(기본 프레임버퍼)를 타깃으로 */
  screen(w: number, h: number): Target {
    return { fbo: null as unknown as WebGLFramebuffer, w, h, n: 1 };
  }

  program(name: string, fragSrc: string): Prog {
    const gl = this.gl;
    const compile = (type: number, src: string): WebGLShader => {
      const sh = gl.createShader(type)!;
      gl.shaderSource(sh, src);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        const log = gl.getShaderInfoLog(sh);
        gl.deleteShader(sh);
        throw new Error(`셰이더 컴파일 오류 (${name}): ${log}`);
      }
      return sh;
    };
    const vs = compile(gl.VERTEX_SHADER, FULLSCREEN_QUAD_VERT);
    const fs = compile(gl.FRAGMENT_SHADER, fragSrc);
    const prog = gl.createProgram()!;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.bindAttribLocation(prog, 0, 'a_position');
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      throw new Error(`프로그램 링크 오류 (${name}): ${gl.getProgramInfoLog(prog)}`);
    }
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    const uni = new Map<string, UniformInfo>();
    const count = gl.getProgramParameter(prog, gl.ACTIVE_UNIFORMS) as number;
    for (let i = 0; i < count; i++) {
      const info = gl.getActiveUniform(prog, i)!;
      const loc = gl.getUniformLocation(prog, info.name);
      if (loc) uni.set(info.name, { loc, type: info.type });
    }
    return { prog, name, uni };
  }

  /** 풀스크린 쿼드 한 번. 텍스처 유니폼은 넘긴 순서대로 유닛에 묶는다 */
  draw(p: Prog, t: Target, u: Record<string, UVal>, rect?: Rect | null): void {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, t.fbo);
    gl.viewport(0, 0, t.w, t.h);
    if (rect) {
      gl.enable(gl.SCISSOR_TEST);
      gl.scissor(rect[0], rect[1], rect[2], rect[3]);
    } else {
      gl.disable(gl.SCISSOR_TEST);
    }
    if (this.current !== p.prog) {
      gl.useProgram(p.prog);
      this.current = p.prog;
    }
    let unit = 0;
    for (const key in u) {
      const info = p.uni.get(key);
      if (!info) continue; // 셰이더가 쓰지 않아 지워진 유니폼
      const v = u[key];
      if (typeof v === 'number') {
        if (info.type === gl.INT) gl.uniform1i(info.loc, v);
        else gl.uniform1f(info.loc, v);
      } else if (Array.isArray(v)) {
        if (info.type === gl.INT_VEC2) gl.uniform2i(info.loc, v[0], v[1]);
        else if (info.type === gl.FLOAT_VEC2) gl.uniform2f(info.loc, v[0], v[1]);
        else if (info.type === gl.FLOAT_VEC4) gl.uniform4f(info.loc, v[0], v[1], v[2], v[3]);
        else throw new Error(`지원하지 않는 유니폼 형식: ${p.name}.${key}`);
      } else {
        gl.activeTexture(gl.TEXTURE0 + unit);
        gl.bindTexture(gl.TEXTURE_2D, (v as Tex).tex);
        gl.uniform1i(info.loc, unit);
        unit++;
      }
    }
    gl.bindVertexArray(this.vao);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    this.drawCalls++;
  }

  /** 타깃의 모든 첨부를 한 값(또는 RGBA)으로 채운다 (드로콜이 아니다) */
  clear(t: Target, v: number | readonly number[] = 0): void {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, t.fbo);
    gl.disable(gl.SCISSOR_TEST);
    const c = typeof v === 'number' ? new Float32Array([v, v, v, v]) : new Float32Array(v);
    for (let i = 0; i < t.n; i++) gl.clearBufferfv(gl.COLOR, i, c);
  }

  /** 텍스처 전체를 RGBA float 로 읽는다 (파이프라인을 멈추므로 시험·확인용) */
  read(t: Tex): Float32Array {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.readFbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t.tex, 0);
    const out = new Float32Array(t.w * t.h * 4);
    gl.readPixels(0, 0, t.w, t.h, gl.RGBA, gl.FLOAT, out);
    return out;
  }

  /** 텍스처를 파이프라인을 멈추지 않고 읽기 시작한다. 결과는 poll 로 거둔다 */
  readAsync(t: Tex): AsyncRead {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.readFbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t.tex, 0);
    const buf = gl.createBuffer()!;
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, buf);
    gl.bufferData(gl.PIXEL_PACK_BUFFER, t.w * t.h * 16, gl.STREAM_READ);
    gl.readPixels(0, 0, t.w, t.h, gl.RGBA, gl.FLOAT, 0);
    gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);
    const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0)!;
    gl.flush();
    return { buf, sync, w: t.w, h: t.h };
  }

  /** 읽기가 끝났으면 값을, 아니면 null */
  poll(a: AsyncRead): Float32Array | null {
    const gl = this.gl;
    const s = gl.clientWaitSync(a.sync, 0, 0);
    if (s === gl.TIMEOUT_EXPIRED) return null;
    gl.deleteSync(a.sync);
    const out = new Float32Array(a.w * a.h * 4);
    if (s !== gl.WAIT_FAILED) {
      gl.bindBuffer(gl.PIXEL_PACK_BUFFER, a.buf);
      gl.getBufferSubData(gl.PIXEL_PACK_BUFFER, 0, out);
      gl.bindBuffer(gl.PIXEL_PACK_BUFFER, null);
    }
    gl.deleteBuffer(a.buf);
    return s === gl.WAIT_FAILED ? null : out;
  }

  /** 대기 중인 명령을 모두 끝낸다 (벽시계 측정용) */
  finish(): void {
    this.gl.finish();
  }

  private glFormat(fmt: Fmt): [number, number] {
    const gl = this.gl;
    if (fmt === 'rgba32f') return [gl.RGBA32F, gl.RGBA];
    if (fmt === 'rg32f') return [gl.RG32F, gl.RG];
    return [gl.R32F, gl.RED];
  }
}
