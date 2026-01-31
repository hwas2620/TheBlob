// GPU 에이전트 처리 (Phase 3)
// 에이전트 상태를 RGBA32F 텍스처로 인코딩, 프래그먼트 셰이더로 병렬 업데이트

import { FULLSCREEN_QUAD_VERT } from './shaders';
import { AGENT_UPDATE_FRAG } from './shaders/agent_update';
import { DEPOSIT_POINTS_VERT, DEPOSIT_POINTS_FRAG } from './shaders/deposit_points';
import { AGENT_TEX } from '../config';

const AGENT_TEX_WIDTH = AGENT_TEX.WIDTH;
const AGENT_TEX_HEIGHT = AGENT_TEX.HEIGHT;

export class AgentGPU {
  private gl: WebGL2RenderingContext;
  private mapWidth: number;
  private mapHeight: number;

  // 에이전트 상태 핑퐁 텍스처 (RGBA32F: x, y, angle, flags)
  private agentTexA: WebGLTexture;
  private agentTexB: WebGLTexture;
  private fboA: WebGLFramebuffer;
  private fboB: WebGLFramebuffer;
  private currentIsA = true;

  // 랜덤 텍스처
  private randomTex: WebGLTexture;

  // 어트랙터 텍스처 참조 (SceneRenderer에서 공유하거나 별도 생성)
  private attractorTex: WebGLTexture;
  private attractorData: Float32Array;

  // 셰이더
  private updateProgram: WebGLProgram;
  private depositProgram: WebGLProgram;

  // 풀스크린 쿼드 VAO (에이전트 업데이트용)
  private quadVAO: WebGLVertexArrayObject;

  // 에이전트 수
  private _agentCount = 0;
  private frameIndex = 0;

  // 유니폼 캐시
  private updateUniforms: Record<string, WebGLUniformLocation | null>;
  private depositUniforms: Record<string, WebGLUniformLocation | null>;

  // CPU 리드백 버퍼 (에이전트 위치 캐시)
  private readbackBuffer: Float32Array;

  constructor(gl: WebGL2RenderingContext, mapWidth: number, mapHeight: number) {
    this.gl = gl;
    this.mapWidth = mapWidth;
    this.mapHeight = mapHeight;

    // 랜덤 텍스처 생성 (256x256)
    this.randomTex = this.createRandomTexture(256, 256);

    // 어트랙터 텍스처
    this.attractorData = new Float32Array(AGENT_TEX.MAX_ATTRACTORS * 4);
    this.attractorTex = this.createFloat32Texture(AGENT_TEX.MAX_ATTRACTORS, 1, this.attractorData);

    // 에이전트 텍스처
    this.agentTexA = this.createFloat32Texture(AGENT_TEX_WIDTH, AGENT_TEX_HEIGHT, null);
    this.agentTexB = this.createFloat32Texture(AGENT_TEX_WIDTH, AGENT_TEX_HEIGHT, null);
    this.fboA = this.createFBO(this.agentTexA, AGENT_TEX_WIDTH, AGENT_TEX_HEIGHT);
    this.fboB = this.createFBO(this.agentTexB, AGENT_TEX_WIDTH, AGENT_TEX_HEIGHT);

    // 쿼드 VAO
    this.quadVAO = this.createQuadVAO();

    // 셰이더 컴파일
    this.updateProgram = this.createProgram(FULLSCREEN_QUAD_VERT, AGENT_UPDATE_FRAG);
    this.depositProgram = this.createProgram(DEPOSIT_POINTS_VERT, DEPOSIT_POINTS_FRAG);

    // 유니폼 캐시 (Jeff Jones 알고리즘 — 직접 유인 없음)
    this.updateUniforms = this.cacheUniforms(this.updateProgram, [
      'u_agentState', 'u_trailMap', 'u_random',
      'u_agentCount', 'u_texWidth',
      'u_mapSize', 'u_sensorAngle', 'u_sensorDistance',
      'u_turnSpeed', 'u_moveSpeed', 'u_frameIndex',
    ]);

    this.depositUniforms = this.cacheUniforms(this.depositProgram, [
      'u_agentState', 'u_mapSize', 'u_agentCount', 'u_texWidth', 'u_depositAmount',
    ]);

    // 리드백 버퍼
    this.readbackBuffer = new Float32Array(AGENT_TEX_WIDTH * AGENT_TEX_HEIGHT * 4);
  }

  get agentCount(): number {
    return this._agentCount;
  }

  // CPU 에이전트 배열을 GPU 텍스처에 업로드
  uploadAgents(agents: ReadonlyArray<{ x: number; y: number; angle: number }>) {
    const data = new Float32Array(AGENT_TEX_WIDTH * AGENT_TEX_HEIGHT * 4);
    for (let i = 0; i < agents.length; i++) {
      const a = agents[i];
      data[i * 4 + 0] = a.x;
      data[i * 4 + 1] = a.y;
      data[i * 4 + 2] = a.angle;
      data[i * 4 + 3] = 1.0; // active flag
    }
    this._agentCount = agents.length;

    const gl = this.gl;
    const tex = this.currentIsA ? this.agentTexA : this.agentTexB;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texSubImage2D(
      gl.TEXTURE_2D, 0, 0, 0,
      AGENT_TEX_WIDTH, AGENT_TEX_HEIGHT,
      gl.RGBA, gl.FLOAT, data,
    );
    gl.bindTexture(gl.TEXTURE_2D, null);
  }

  // 어트랙터 데이터 업데이트
  updateAttractors(attractors: Array<{ x: number; y: number; strength: number }>) {
    this.attractorData.fill(0);
    const count = Math.min(attractors.length, 64);
    for (let i = 0; i < count; i++) {
      const a = attractors[i];
      this.attractorData[i * 4 + 0] = a.x;
      this.attractorData[i * 4 + 1] = a.y;
      this.attractorData[i * 4 + 2] = a.strength;
    }
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.attractorTex);
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, AGENT_TEX.MAX_ATTRACTORS, 1, gl.RGBA, gl.FLOAT, this.attractorData);
    gl.bindTexture(gl.TEXTURE_2D, null);
  }

  // 에이전트 업데이트 실행 (1 스텝) — Jeff Jones 알고리즘
  runUpdate(
    trailTexture: WebGLTexture,
    config: {
      sensorAngle: number;
      sensorDistance: number;
      turnSpeed: number;
      moveSpeed: number;
    },
  ) {
    const gl = this.gl;
    const srcTex = this.currentIsA ? this.agentTexA : this.agentTexB;
    const dstFbo = this.currentIsA ? this.fboB : this.fboA;

    // 디버깅: 첫 프레임만 로그
    if (this.frameIndex === 0) {
      console.log(`[AgentGPU] 첫 업데이트 (Jeff Jones): 에이전트 수=${this._agentCount}, 맵=${this.mapWidth}x${this.mapHeight}`);
    }

    gl.bindFramebuffer(gl.FRAMEBUFFER, dstFbo);
    gl.viewport(0, 0, AGENT_TEX_WIDTH, AGENT_TEX_HEIGHT);

    gl.useProgram(this.updateProgram);

    // 텍스처 바인딩
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, srcTex);
    gl.uniform1i(this.updateUniforms['u_agentState'], 0);

    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, trailTexture);
    gl.uniform1i(this.updateUniforms['u_trailMap'], 1);

    gl.activeTexture(gl.TEXTURE2);
    gl.bindTexture(gl.TEXTURE_2D, this.randomTex);
    gl.uniform1i(this.updateUniforms['u_random'], 2);

    // 유니폼 설정 (Jeff Jones 파라미터만)
    gl.uniform1i(this.updateUniforms['u_agentCount'], this._agentCount);
    gl.uniform1i(this.updateUniforms['u_texWidth'], AGENT_TEX_WIDTH);
    gl.uniform2f(this.updateUniforms['u_mapSize'], this.mapWidth, this.mapHeight);
    gl.uniform1f(this.updateUniforms['u_sensorAngle'], config.sensorAngle);
    gl.uniform1f(this.updateUniforms['u_sensorDistance'], config.sensorDistance);
    gl.uniform1f(this.updateUniforms['u_turnSpeed'], config.turnSpeed);
    gl.uniform1f(this.updateUniforms['u_moveSpeed'], config.moveSpeed);
    gl.uniform1f(this.updateUniforms['u_frameIndex'], this.frameIndex++);

    this.drawQuad();

    this.currentIsA = !this.currentIsA;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  // 분비 패스: 에이전트 위치에 페로몬 분비 (GL_POINTS → 트레일맵 FBO)
  runDeposit(
    trailFbo: WebGLFramebuffer,
    trailMapWidth: number,
    trailMapHeight: number,
    depositAmount: number,
  ) {
    const gl = this.gl;
    const agentTex = this.currentIsA ? this.agentTexA : this.agentTexB;

    // 디버깅: 첫 분비만 로그
    if (this.frameIndex === 1) {
      console.log(`[AgentGPU] 첫 분비: 에이전트 수=${this._agentCount}, 트레일맵=${trailMapWidth}x${trailMapHeight}, 분비량=${depositAmount}`);
    }

    gl.bindFramebuffer(gl.FRAMEBUFFER, trailFbo);
    gl.viewport(0, 0, trailMapWidth, trailMapHeight);

    // 가산 블렌딩
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);

    gl.useProgram(this.depositProgram);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, agentTex);
    gl.uniform1i(this.depositUniforms['u_agentState'], 0);

    gl.uniform2f(this.depositUniforms['u_mapSize'], this.mapWidth, this.mapHeight);
    gl.uniform1i(this.depositUniforms['u_agentCount'], this._agentCount);
    gl.uniform1i(this.depositUniforms['u_texWidth'], AGENT_TEX_WIDTH);
    gl.uniform1f(this.depositUniforms['u_depositAmount'], depositAmount);

    // 포인트 렌더링 (VAO 없이 gl_VertexID 사용)
    gl.drawArrays(gl.POINTS, 0, this._agentCount);

    gl.disable(gl.BLEND);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  // 에이전트 추가 (CPU에서 새 위치 생성 후 텍스처에 기록)
  addAgents(count: number, nearX?: number, nearY?: number) {
    const startIdx = this._agentCount;
    const maxAgents = AGENT_TEX_WIDTH * AGENT_TEX_HEIGHT;
    const newCount = Math.min(startIdx + count, maxAgents);
    const actualAdd = newCount - startIdx;
    if (actualAdd <= 0) return;

    // 새 에이전트 데이터 생성 (지정 위치 또는 기존 에이전트 근처)
    const newData = new Float32Array(actualAdd * 4);
    for (let i = 0; i < actualAdd; i++) {
      let px: number, py: number;
      if (nearX != null && nearY != null) {
        px = nearX;
        py = nearY;
      } else {
        const parentIdx = Math.floor(Math.random() * Math.max(1, startIdx));
        px = this.readbackBuffer[parentIdx * 4 + 0] || this.mapWidth / 2;
        py = this.readbackBuffer[parentIdx * 4 + 1] || this.mapHeight / 2;
      }
      newData[i * 4 + 0] = px + (Math.random() - 0.5) * 20;
      newData[i * 4 + 1] = py + (Math.random() - 0.5) * 20;
      newData[i * 4 + 2] = Math.random() * Math.PI * 2;
      newData[i * 4 + 3] = 1.0; // active
    }

    // 텍스처의 해당 영역에 기록
    const gl = this.gl;
    const tex = this.currentIsA ? this.agentTexA : this.agentTexB;
    gl.bindTexture(gl.TEXTURE_2D, tex);

    // 행 단위로 업로드 (texSubImage2D는 연속 행만 지원)
    for (let i = 0; i < actualAdd; i++) {
      const idx = startIdx + i;
      const tx = idx % AGENT_TEX_WIDTH;
      const ty = Math.floor(idx / AGENT_TEX_WIDTH);
      gl.texSubImage2D(
        gl.TEXTURE_2D, 0, tx, ty, 1, 1,
        gl.RGBA, gl.FLOAT,
        new Float32Array(newData.buffer, i * 16, 4),
      );
    }

    gl.bindTexture(gl.TEXTURE_2D, null);
    this._agentCount = newCount;
  }

  // 에이전트 제거
  removeAgents(count: number) {
    this._agentCount = Math.max(100, this._agentCount - count);
  }

  // GPU → CPU 리드백 (프레임당 1회, 80KB)
  readbackAgents() {
    const gl = this.gl;
    const fbo = this.currentIsA ? this.fboA : this.fboB;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.readPixels(
      0, 0, AGENT_TEX_WIDTH, AGENT_TEX_HEIGHT,
      gl.RGBA, gl.FLOAT, this.readbackBuffer,
    );
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    // 디버깅: 10프레임 후 에이전트 위치 샘플 출력
    if (this.frameIndex === 10) {
      console.log('[AgentGPU] 10프레임 후 에이전트 위치 샘플:');
      for (let i = 0; i < 5; i++) {
        const x = this.readbackBuffer[i * 4 + 0];
        const y = this.readbackBuffer[i * 4 + 1];
        const angle = this.readbackBuffer[i * 4 + 2];
        const flags = this.readbackBuffer[i * 4 + 3];
        console.log(`  [${i}] x=${x.toFixed(1)}, y=${y.toFixed(1)}, angle=${angle.toFixed(2)}, flags=${flags}`);
      }
    }
  }

  // 특정 위치의 파티클 밀도 계산 (CPU 리드백 데이터 기반)
  getParticleDensity(x: number, y: number, radius: number): number {
    const r2 = radius * radius;
    let count = 0;
    for (let i = 0; i < this._agentCount; i++) {
      const ax = this.readbackBuffer[i * 4 + 0];
      const ay = this.readbackBuffer[i * 4 + 1];
      const dx = ax - x;
      const dy = ay - y;
      if (dx * dx + dy * dy < r2) {
        count++;
      }
    }
    return count;
  }

  // 에이전트 위치 배열 반환 (CPU 리드백 기반)
  getAgentPositions(): ReadonlyArray<{ x: number; y: number; angle: number }> {
    const result: Array<{ x: number; y: number; angle: number }> = [];
    for (let i = 0; i < this._agentCount; i++) {
      result.push({
        x: this.readbackBuffer[i * 4 + 0],
        y: this.readbackBuffer[i * 4 + 1],
        angle: this.readbackBuffer[i * 4 + 2],
      });
    }
    return result;
  }

  // 현재 에이전트 텍스처 반환
  getCurrentAgentTexture(): WebGLTexture {
    return this.currentIsA ? this.agentTexA : this.agentTexB;
  }

  // --- 유틸리티 ---

  private createFloat32Texture(w: number, h: number, data: Float32Array | null): WebGLTexture {
    const gl = this.gl;
    const tex = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, w, h, 0, gl.RGBA, gl.FLOAT, data);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.bindTexture(gl.TEXTURE_2D, null);
    return tex;
  }

  private createFBO(texture: WebGLTexture, _w: number, _h: number): WebGLFramebuffer {
    const gl = this.gl;
    const fbo = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
    const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    if (status !== gl.FRAMEBUFFER_COMPLETE) {
      throw new Error(`Agent FBO not complete: ${status}`);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return fbo;
  }

  private createRandomTexture(w: number, h: number): WebGLTexture {
    const data = new Float32Array(w * h * 4);
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random();
    }
    return this.createFloat32Texture(w, h, data);
  }

  private createQuadVAO(): WebGLVertexArrayObject {
    const gl = this.gl;
    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);
    const vertices = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
    const vbo = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    return vao;
  }

  private drawQuad() {
    const gl = this.gl;
    gl.bindVertexArray(this.quadVAO);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.bindVertexArray(null);
  }

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

  private cacheUniforms(program: WebGLProgram, names: string[]): Record<string, WebGLUniformLocation | null> {
    const result: Record<string, WebGLUniformLocation | null> = {};
    for (const name of names) {
      result[name] = this.gl.getUniformLocation(program, name);
    }
    return result;
  }

  dispose() {
    const gl = this.gl;
    gl.deleteTexture(this.agentTexA);
    gl.deleteTexture(this.agentTexB);
    gl.deleteTexture(this.randomTex);
    gl.deleteTexture(this.attractorTex);
    gl.deleteFramebuffer(this.fboA);
    gl.deleteFramebuffer(this.fboB);
    gl.deleteProgram(this.updateProgram);
    gl.deleteProgram(this.depositProgram);
    gl.deleteVertexArray(this.quadVAO);
  }
}
