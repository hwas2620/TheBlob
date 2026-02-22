// WebGL2 기반 트레일맵 GPU 처리 (확산 + 감쇠 + 분비물 블렌드)
// Phase 1: diffuseTrailMap() + decayTrailMap()을 GPU로 이전

import {
  FULLSCREEN_QUAD_VERT,
  DIFFUSE_DECAY_FRAG,
  DEPOSIT_BLEND_FRAG,
} from './shaders';
import { AGENT } from '../config';

export class TrailMapGPU {
  private gl: WebGL2RenderingContext;
  private width: number;
  private height: number;

  // 핑퐁 텍스처 & FBO
  private trailTexA: WebGLTexture;
  private trailTexB: WebGLTexture;
  private fboA: WebGLFramebuffer;
  private fboB: WebGLFramebuffer;
  private currentIsA = true; // 현재 소스가 A인지

  // 분비물 텍스처 (에이전트 자기 페로몬용 — 현재 미사용, food로 대체)
  private depositTex: WebGLTexture;

  // 먹이 화학물질 핑퐁 텍스처 & FBO (자기 트레일과 완전 분리)
  private foodTexA: WebGLTexture;
  private foodTexB: WebGLTexture;
  private foodFboA: WebGLFramebuffer;
  private foodFboB: WebGLFramebuffer;
  private foodCurrentIsA = true;
  private foodDepositTex: WebGLTexture;

  // 셰이더 프로그램
  private diffuseDecayProgram: WebGLProgram;
  private depositBlendProgram: WebGLProgram;

  // 풀스크린 쿼드 VAO
  private quadVAO: WebGLVertexArrayObject;

  // 유니폼 위치 캐시
  private ddUniforms: {
    trailMap: WebGLUniformLocation | null;
    texelSize: WebGLUniformLocation | null;
    decayFactor: WebGLUniformLocation | null;
    maxTrail: WebGLUniformLocation | null;
  };
  private dbUniforms: {
    trailMap: WebGLUniformLocation | null;
    depositMap: WebGLUniformLocation | null;
  };

  constructor(gl: WebGL2RenderingContext, width: number, height: number) {
    this.gl = gl;
    this.width = width;
    this.height = height;

    // EXT_color_buffer_float 확인 (R32F 렌더 타겟 필수)
    const ext = gl.getExtension('EXT_color_buffer_float');
    if (!ext) {
      throw new Error('EXT_color_buffer_float not supported');
    }

    // 풀스크린 쿼드 생성
    this.quadVAO = this.createQuadVAO();

    // 셰이더 컴파일
    this.diffuseDecayProgram = this.createProgram(FULLSCREEN_QUAD_VERT, DIFFUSE_DECAY_FRAG);
    this.depositBlendProgram = this.createProgram(FULLSCREEN_QUAD_VERT, DEPOSIT_BLEND_FRAG);

    // 유니폼 위치 캐시
    this.ddUniforms = {
      trailMap: gl.getUniformLocation(this.diffuseDecayProgram, 'u_trailMap'),
      texelSize: gl.getUniformLocation(this.diffuseDecayProgram, 'u_texelSize'),
      decayFactor: gl.getUniformLocation(this.diffuseDecayProgram, 'u_decayFactor'),
      maxTrail: gl.getUniformLocation(this.diffuseDecayProgram, 'u_maxTrail'),
    };
    this.dbUniforms = {
      trailMap: gl.getUniformLocation(this.depositBlendProgram, 'u_trailMap'),
      depositMap: gl.getUniformLocation(this.depositBlendProgram, 'u_depositMap'),
    };

    // 텍스처 생성
    this.trailTexA = this.createR32FTexture(width, height);
    this.trailTexB = this.createR32FTexture(width, height);
    this.depositTex = this.createR32FTexture(width, height);

    // FBO 생성
    this.fboA = this.createFBO(this.trailTexA);
    this.fboB = this.createFBO(this.trailTexB);

    // 먹이 텍스처 & FBO 생성
    this.foodTexA = this.createR32FTexture(width, height);
    this.foodTexB = this.createR32FTexture(width, height);
    this.foodDepositTex = this.createR32FTexture(width, height);
    this.foodFboA = this.createFBO(this.foodTexA);
    this.foodFboB = this.createFBO(this.foodTexB);
  }

  // R32F 텍스처 생성 (GL_REPEAT으로 토러스 래핑)
  private createR32FTexture(w: number, h: number, data?: Float32Array): WebGLTexture {
    const gl = this.gl;
    const tex = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(
      gl.TEXTURE_2D, 0, gl.R32F,
      w, h, 0,
      gl.RED, gl.FLOAT,
      data || null,
    );
    // GL_REPEAT으로 토러스 래핑 자동 처리
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    // NEAREST: R32F 텍스처는 LINEAR 필터 미지원 가능
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.bindTexture(gl.TEXTURE_2D, null);
    return tex;
  }

  // FBO 생성
  private createFBO(texture: WebGLTexture): WebGLFramebuffer {
    const gl = this.gl;
    const fbo = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(
      gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0,
      gl.TEXTURE_2D, texture, 0,
    );
    const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    if (status !== gl.FRAMEBUFFER_COMPLETE) {
      throw new Error(`Framebuffer not complete: ${status}`);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return fbo;
  }

  // 풀스크린 쿼드 VAO 생성 (클립스페이스 [-1,1])
  private createQuadVAO(): WebGLVertexArrayObject {
    const gl = this.gl;
    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);

    const vertices = new Float32Array([
      -1, -1,
       1, -1,
      -1,  1,
       1,  1,
    ]);

    const vbo = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    gl.bindVertexArray(null);
    return vao;
  }

  // 셰이더 컴파일 유틸
  private compileShader(source: string, type: number): WebGLShader {
    const gl = this.gl;
    const shader = gl.createShader(type)!;
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(`Shader compile error: ${log}`);
    }
    return shader;
  }

  // 프로그램 링크
  private createProgram(vertSrc: string, fragSrc: string): WebGLProgram {
    const gl = this.gl;
    const vert = this.compileShader(vertSrc, gl.VERTEX_SHADER);
    const frag = this.compileShader(fragSrc, gl.FRAGMENT_SHADER);
    const program = gl.createProgram()!;
    gl.attachShader(program, vert);
    gl.attachShader(program, frag);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const log = gl.getProgramInfoLog(program);
      throw new Error(`Program link error: ${log}`);
    }
    gl.deleteShader(vert);
    gl.deleteShader(frag);
    return program;
  }

  // 풀스크린 쿼드 그리기
  private drawQuad() {
    const gl = this.gl;
    gl.bindVertexArray(this.quadVAO);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.bindVertexArray(null);
  }

  // CPU → GPU: 트레일맵 업로드 (초기화 또는 동기화용)
  uploadTrailMap(data: Float32Array) {
    const gl = this.gl;
    const tex = this.currentIsA ? this.trailTexA : this.trailTexB;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texSubImage2D(
      gl.TEXTURE_2D, 0, 0, 0,
      this.width, this.height,
      gl.RED, gl.FLOAT, data,
    );
    gl.bindTexture(gl.TEXTURE_2D, null);
  }

  // CPU → GPU: 분비물 맵 업로드
  uploadDeposits(data: Float32Array) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.depositTex);
    gl.texSubImage2D(
      gl.TEXTURE_2D, 0, 0, 0,
      this.width, this.height,
      gl.RED, gl.FLOAT, data,
    );
    gl.bindTexture(gl.TEXTURE_2D, null);
  }

  // GPU 분비물 블렌드: trail += deposit (클램프 255)
  blendDeposits() {
    const gl = this.gl;
    const srcTex = this.currentIsA ? this.trailTexA : this.trailTexB;
    const dstFbo = this.currentIsA ? this.fboB : this.fboA;

    gl.bindFramebuffer(gl.FRAMEBUFFER, dstFbo);
    gl.viewport(0, 0, this.width, this.height);

    gl.useProgram(this.depositBlendProgram);

    // 텍스처 바인딩
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, srcTex);
    gl.uniform1i(this.dbUniforms.trailMap, 0);

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this.depositTex);
    gl.uniform1i(this.dbUniforms.depositMap, 1);

    this.drawQuad();

    // 핑퐁 스왑
    this.currentIsA = !this.currentIsA;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  // GPU 확산 + 감쇠 (핑퐁, 여러 패스 지원)
  runDiffuseDecay(decayFactor: number, passes: number = 1) {
    const gl = this.gl;
    gl.useProgram(this.diffuseDecayProgram);
    gl.uniform2f(this.ddUniforms.texelSize, 1.0 / this.width, 1.0 / this.height);
    gl.uniform1f(this.ddUniforms.maxTrail, AGENT.MAX_TRAIL);

    for (let p = 0; p < passes; p++) {
      const srcTex = this.currentIsA ? this.trailTexA : this.trailTexB;
      const dstFbo = this.currentIsA ? this.fboB : this.fboA;

      gl.bindFramebuffer(gl.FRAMEBUFFER, dstFbo);
      gl.viewport(0, 0, this.width, this.height);

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, srcTex);
      gl.uniform1i(this.ddUniforms.trailMap, 0);
      // 마지막 패스에만 decay 적용, 나머지는 확산만
      gl.uniform1f(this.ddUniforms.decayFactor, p === passes - 1 ? decayFactor : 1.0);

      this.drawQuad();
      this.currentIsA = !this.currentIsA;
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  // === 먹이 채널 메서드 (trail과 동일 구조, 별도 핑퐁) ===

  // CPU → GPU: 먹이 분비물 업로드
  uploadFoodDeposits(data: Float32Array) {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.foodDepositTex);
    gl.texSubImage2D(
      gl.TEXTURE_2D, 0, 0, 0,
      this.width, this.height,
      gl.RED, gl.FLOAT, data,
    );
    gl.bindTexture(gl.TEXTURE_2D, null);
  }

  // 먹이 분비물 블렌드: food += deposit (depositBlendProgram 재사용)
  blendFoodDeposits() {
    const gl = this.gl;
    const srcTex = this.foodCurrentIsA ? this.foodTexA : this.foodTexB;
    const dstFbo = this.foodCurrentIsA ? this.foodFboB : this.foodFboA;

    gl.bindFramebuffer(gl.FRAMEBUFFER, dstFbo);
    gl.viewport(0, 0, this.width, this.height);

    gl.useProgram(this.depositBlendProgram);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, srcTex);
    gl.uniform1i(this.dbUniforms.trailMap, 0);

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this.foodDepositTex);
    gl.uniform1i(this.dbUniforms.depositMap, 1);

    this.drawQuad();

    this.foodCurrentIsA = !this.foodCurrentIsA;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  // 먹이 확산 + 감쇠 (diffuseDecayProgram 재사용, 파라미터만 다름)
  runFoodDiffuseDecay(decayFactor: number, passes: number, maxTrail: number) {
    const gl = this.gl;
    gl.useProgram(this.diffuseDecayProgram);
    gl.uniform2f(this.ddUniforms.texelSize, 1.0 / this.width, 1.0 / this.height);
    gl.uniform1f(this.ddUniforms.maxTrail, maxTrail);

    for (let p = 0; p < passes; p++) {
      const srcTex = this.foodCurrentIsA ? this.foodTexA : this.foodTexB;
      const dstFbo = this.foodCurrentIsA ? this.foodFboB : this.foodFboA;

      gl.bindFramebuffer(gl.FRAMEBUFFER, dstFbo);
      gl.viewport(0, 0, this.width, this.height);

      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, srcTex);
      gl.uniform1i(this.ddUniforms.trailMap, 0);
      gl.uniform1f(this.ddUniforms.decayFactor, p === passes - 1 ? decayFactor : 1.0);

      this.drawQuad();
      this.foodCurrentIsA = !this.foodCurrentIsA;
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  // 현재 먹이 텍스처 반환 (에이전트 셰이더 바인딩용)
  getCurrentFoodTexture(): WebGLTexture {
    return this.foodCurrentIsA ? this.foodTexA : this.foodTexB;
  }

  // GPU → CPU: 트레일맵 리드백 (동기 - 폴백용)
  readTrailMap(dst: Float32Array) {
    const gl = this.gl;
    const fbo = this.currentIsA ? this.fboA : this.fboB;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.readPixels(0, 0, this.width, this.height, gl.RED, gl.FLOAT, dst);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  // 현재 트레일 텍스처 반환 (렌더링용)
  getCurrentTrailTexture(): WebGLTexture {
    return this.currentIsA ? this.trailTexA : this.trailTexB;
  }

  // 현재 트레일 FBO 반환 (에이전트 분비 대상)
  getCurrentFBO(): WebGLFramebuffer {
    return this.currentIsA ? this.fboA : this.fboB;
  }

  // 리소스 해제
  dispose() {
    const gl = this.gl;
    gl.deleteTexture(this.trailTexA);
    gl.deleteTexture(this.trailTexB);
    gl.deleteTexture(this.depositTex);
    gl.deleteTexture(this.foodTexA);
    gl.deleteTexture(this.foodTexB);
    gl.deleteTexture(this.foodDepositTex);
    gl.deleteFramebuffer(this.fboA);
    gl.deleteFramebuffer(this.fboB);
    gl.deleteFramebuffer(this.foodFboA);
    gl.deleteFramebuffer(this.foodFboB);
    gl.deleteProgram(this.diffuseDecayProgram);
    gl.deleteProgram(this.depositBlendProgram);
    gl.deleteVertexArray(this.quadVAO);
  }
}
