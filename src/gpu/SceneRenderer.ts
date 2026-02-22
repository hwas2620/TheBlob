// GPU 씬 렌더러 (Phase 2)
// 블롭 본체, 페로몬 필드, 정맥, 큐빅 글로우를 WebGL2로 렌더링

import { FULLSCREEN_QUAD_VERT } from './shaders';
import { BLOB_BODY_FRAG } from './shaders/blob_body';
import { PHEROMONE_FIELD_FRAG } from './shaders/pheromone_field';
import { PHEROMONE_FIELD_TRAILMAP_FRAG } from './shaders/pheromone_field_trailmap';
import { AGENT_TEX } from '../config';
import { VEINS_FRAG } from './shaders/veins';
import { CUBIC_GLOW_FRAG } from './shaders/cubic_glow';
import { AGENT_DISPLAY_VERT, AGENT_DISPLAY_FRAG } from './shaders/agent_display';

export type PheromoneMode = 'inverse-square' | 'trailmap';
export type ViewMode = 'pheromone' | 'density';  // 페로몬 vs 밀집도

interface SceneUniforms {
  trailMap: WebGLUniformLocation | null;
  mapSize: WebGLUniformLocation | null;
  viewportSize: WebGLUniformLocation | null;
  camera: WebGLUniformLocation | null;
  isDormant?: WebGLUniformLocation | null;
  attractors?: WebGLUniformLocation | null;
  attractorCount?: WebGLUniformLocation | null;
  time?: WebGLUniformLocation | null;
  occupancyMap?: WebGLUniformLocation | null;  // 밀집도 맵
  viewMode?: WebGLUniformLocation | null;       // 뷰 모드
  foodMap?: WebGLUniformLocation | null;        // 먹이 화학물질 맵
}

export class SceneRenderer {
  private gl: WebGL2RenderingContext;

  // 셰이더 프로그램
  private blobProgram: WebGLProgram;
  private pheromoneProgram: WebGLProgram;
  private pheromoneTrailmapProgram: WebGLProgram;
  private veinsProgram: WebGLProgram;
  private cubicProgram: WebGLProgram;
  private agentDisplayProgram: WebGLProgram;

  // 페로몬 모드
  private pheromoneMode: PheromoneMode = 'inverse-square';

  // 뷰 모드 (페로몬 vs 밀집도)
  private viewMode: ViewMode = 'pheromone';

  // 밀집도 맵 텍스처 참조
  private occupancyTex: WebGLTexture | null = null;

  // 유니폼 캐시
  private blobUniforms: SceneUniforms;
  private pheromoneUniforms: SceneUniforms;
  private pheromoneTrailmapUniforms: SceneUniforms;
  private veinsUniforms: SceneUniforms;
  private cubicUniforms: SceneUniforms;
  private agentDisplayUniforms: {
    agentState: WebGLUniformLocation | null;
    mapSize: WebGLUniformLocation | null;
    viewportSize: WebGLUniformLocation | null;
    camera: WebGLUniformLocation | null;
    agentCount: WebGLUniformLocation | null;
    texWidth: WebGLUniformLocation | null;
    instanceOffset: WebGLUniformLocation | null;
  };

  // 풀스크린 쿼드 VAO
  private quadVAO: WebGLVertexArrayObject;

  // 어트랙터 데이터 텍스처
  private attractorTex: WebGLTexture;
  private attractorData: Float32Array;

  constructor(gl: WebGL2RenderingContext) {
    this.gl = gl;

    this.quadVAO = this.createQuadVAO();

    // 셰이더 컴파일
    this.blobProgram = this.createProgram(FULLSCREEN_QUAD_VERT, BLOB_BODY_FRAG);
    this.pheromoneProgram = this.createProgram(FULLSCREEN_QUAD_VERT, PHEROMONE_FIELD_FRAG);
    this.pheromoneTrailmapProgram = this.createProgram(FULLSCREEN_QUAD_VERT, PHEROMONE_FIELD_TRAILMAP_FRAG);
    this.veinsProgram = this.createProgram(FULLSCREEN_QUAD_VERT, VEINS_FRAG);
    this.cubicProgram = this.createProgram(FULLSCREEN_QUAD_VERT, CUBIC_GLOW_FRAG);
    this.agentDisplayProgram = this.createProgram(AGENT_DISPLAY_VERT, AGENT_DISPLAY_FRAG);

    // 유니폼 위치 캐시
    this.blobUniforms = {
      ...this.getUniforms(this.blobProgram, true),
      occupancyMap: gl.getUniformLocation(this.blobProgram, 'u_occupancyMap'),
      viewMode: gl.getUniformLocation(this.blobProgram, 'u_viewMode'),
    };
    this.pheromoneUniforms = {
      ...this.getUniforms(this.pheromoneProgram, false),
      attractors: gl.getUniformLocation(this.pheromoneProgram, 'u_attractors'),
      attractorCount: gl.getUniformLocation(this.pheromoneProgram, 'u_attractorCount'),
    };
    this.pheromoneTrailmapUniforms = {
      ...this.getUniforms(this.pheromoneTrailmapProgram, false),
      foodMap: gl.getUniformLocation(this.pheromoneTrailmapProgram, 'u_foodMap'),
    };
    this.veinsUniforms = {
      ...this.getUniforms(this.veinsProgram, true),
      time: gl.getUniformLocation(this.veinsProgram, 'u_time'),
    };
    this.cubicUniforms = this.getUniforms(this.cubicProgram, false);
    this.agentDisplayUniforms = {
      agentState: gl.getUniformLocation(this.agentDisplayProgram, 'u_agentState'),
      mapSize: gl.getUniformLocation(this.agentDisplayProgram, 'u_mapSize'),
      viewportSize: gl.getUniformLocation(this.agentDisplayProgram, 'u_viewportSize'),
      camera: gl.getUniformLocation(this.agentDisplayProgram, 'u_camera'),
      agentCount: gl.getUniformLocation(this.agentDisplayProgram, 'u_agentCount'),
      texWidth: gl.getUniformLocation(this.agentDisplayProgram, 'u_texWidth'),
      instanceOffset: gl.getUniformLocation(this.agentDisplayProgram, 'u_instanceOffset'),
    };

    // 어트랙터 텍스처
    this.attractorData = new Float32Array(AGENT_TEX.MAX_ATTRACTORS * 4);
    this.attractorTex = this.createAttractorTexture();
  }

  private getUniforms(program: WebGLProgram, hasDormant: boolean): SceneUniforms {
    const gl = this.gl;
    const u: SceneUniforms = {
      trailMap: gl.getUniformLocation(program, 'u_trailMap'),
      mapSize: gl.getUniformLocation(program, 'u_mapSize'),
      viewportSize: gl.getUniformLocation(program, 'u_viewportSize'),
      camera: gl.getUniformLocation(program, 'u_camera'),
    };
    if (hasDormant) {
      u.isDormant = gl.getUniformLocation(program, 'u_isDormant');
    }
    return u;
  }

  private createAttractorTexture(): WebGLTexture {
    const gl = this.gl;
    const tex = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(
      gl.TEXTURE_2D, 0, gl.RGBA32F,
      AGENT_TEX.MAX_ATTRACTORS, 1, 0,
      gl.RGBA, gl.FLOAT,
      this.attractorData,
    );
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.bindTexture(gl.TEXTURE_2D, null);
    return tex;
  }

  // 어트랙터 데이터 업데이트
  updateAttractors(attractors: Array<{ x: number; y: number; strength: number }>) {
    this.attractorData.fill(0);
    const count = Math.min(attractors.length, AGENT_TEX.MAX_ATTRACTORS);
    for (let i = 0; i < count; i++) {
      const a = attractors[i];
      this.attractorData[i * 4 + 0] = a.x;
      this.attractorData[i * 4 + 1] = a.y;
      this.attractorData[i * 4 + 2] = a.strength;
      this.attractorData[i * 4 + 3] = 0; // reserved
    }
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.attractorTex);
    gl.texSubImage2D(
      gl.TEXTURE_2D, 0, 0, 0,
      AGENT_TEX.MAX_ATTRACTORS, 1,
      gl.RGBA, gl.FLOAT,
      this.attractorData,
    );
    gl.bindTexture(gl.TEXTURE_2D, null);
  }

  // 페로몬 모드 설정
  setPheromoneMode(mode: PheromoneMode) {
    this.pheromoneMode = mode;
  }

  getPheromoneMode(): PheromoneMode {
    return this.pheromoneMode;
  }

  // 뷰 모드 설정 (페로몬 ↔ 밀집도 토글)
  setViewMode(mode: ViewMode) {
    this.viewMode = mode;
  }

  getViewMode(): ViewMode {
    return this.viewMode;
  }

  toggleViewMode(): ViewMode {
    this.viewMode = this.viewMode === 'pheromone' ? 'density' : 'pheromone';
    return this.viewMode;
  }

  // 밀집도 맵 텍스처 설정 (AgentGPU에서 전달받음)
  setOccupancyTexture(tex: WebGLTexture | null) {
    this.occupancyTex = tex;
  }

  // 씬 렌더링 (모든 패스)
  // canvasWidth/Height: 실제 캔버스 픽셀 크기 (gl.viewport용)
  // logicalWidth/Height: 줌 적용된 논리적 뷰포트 크기 (셰이더 u_viewportSize용)
  render(
    trailTexture: WebGLTexture,
    foodTexture: WebGLTexture | null,
    camera: { x: number; y: number },
    mapSize: { width: number; height: number },
    canvasWidth: number,
    canvasHeight: number,
    logicalWidth: number,
    logicalHeight: number,
    isDormant: boolean,
    attractorCount: number,
    showCubic: boolean,
    showParticles: boolean,
    agentTexture: WebGLTexture | null,
    agentCount: number,
    showBlobGraphics: boolean = true,
    time: number = 0,
  ) {
    const gl = this.gl;

    // 뷰포트 설정 (실제 캔버스 크기)
    gl.viewport(0, 0, canvasWidth, canvasHeight);

    // 블렌딩 활성화
    gl.enable(gl.BLEND);

    // 1. 페로몬 등고선 (항상 표시)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    if (this.pheromoneMode === 'inverse-square' && attractorCount > 0) {
      // 역제곱 필드 등고선
      this.renderPass(
        this.pheromoneProgram,
        this.pheromoneUniforms,
        trailTexture,
        camera, mapSize, logicalWidth, logicalHeight,
        isDormant,
        attractorCount,
      );
    } else if (this.pheromoneMode === 'trailmap') {
      // 트레일맵 기반 등고선 (trail + food 이중 채널)
      this.renderPass(
        this.pheromoneTrailmapProgram,
        this.pheromoneTrailmapUniforms,
        trailTexture,
        camera, mapSize, logicalWidth, logicalHeight,
        isDormant,
        undefined,
        undefined,
        foodTexture,
      );
    }

    if (showBlobGraphics) {
      // 2. 블롭 본체 (에이전트 밀집도 기반 렌더링)
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      this.renderPass(
        this.blobProgram,
        this.blobUniforms,
        trailTexture,
        camera, mapSize, logicalWidth, logicalHeight,
        isDormant,
      );

      // 3. 정맥 (맥동 효과) - 밀집도 뷰에서는 숨김
      if (this.viewMode !== 'density') {
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        this.renderPass(
          this.veinsProgram,
          this.veinsUniforms,
          trailTexture,
          camera, mapSize, logicalWidth, logicalHeight,
          isDormant,
          undefined,
          time,
        );
      }
    }

    // 4. 큐빅 글로우 (독립 토글)
    if (showCubic) {
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE); // 가산 블렌딩
      this.renderPass(
        this.cubicProgram,
        this.cubicUniforms,
        trailTexture,
        camera, mapSize, logicalWidth, logicalHeight,
        isDormant,
      );
    }

    // 5. 에이전트 표시 (토글)
    if (showParticles && agentTexture && agentCount > 0) {
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      this.renderAgents(agentTexture, camera, mapSize, logicalWidth, logicalHeight, agentCount);
    }

    gl.disable(gl.BLEND);
  }

  private renderPass(
    program: WebGLProgram,
    uniforms: SceneUniforms,
    trailTexture: WebGLTexture,
    camera: { x: number; y: number },
    mapSize: { width: number; height: number },
    viewportWidth: number,
    viewportHeight: number,
    isDormant: boolean,
    attractorCount?: number,
    time?: number,
    foodTexture?: WebGLTexture | null,
  ) {
    const gl = this.gl;

    gl.useProgram(program);

    // 공통 유니폼
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, trailTexture);
    gl.uniform1i(uniforms.trailMap, 0);

    gl.uniform2f(uniforms.mapSize, mapSize.width, mapSize.height);
    gl.uniform2f(uniforms.viewportSize, viewportWidth, viewportHeight);
    gl.uniform2f(uniforms.camera, camera.x, camera.y);

    if (uniforms.isDormant !== undefined) {
      gl.uniform1i(uniforms.isDormant!, isDormant ? 1 : 0);
    }

    // 시간 유니폼 (정맥 맥동용)
    if (uniforms.time !== undefined && time !== undefined) {
      gl.uniform1f(uniforms.time!, time);
    }

    // 페로몬 필드 전용 유니폼
    if (attractorCount !== undefined && uniforms.attractors) {
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, this.attractorTex);
      gl.uniform1i(uniforms.attractors, 1);
      gl.uniform1i(uniforms.attractorCount!, attractorCount);
    }

    // 먹이 맵 (food 등고선용)
    if (foodTexture && uniforms.foodMap) {
      gl.activeTexture(gl.TEXTURE3);
      gl.bindTexture(gl.TEXTURE_2D, foodTexture);
      gl.uniform1i(uniforms.foodMap, 3);
    }

    // 밀집도 맵 + 뷰 모드 (블롭 본체 셰이더용)
    if (uniforms.viewMode) {
      gl.uniform1i(uniforms.viewMode, this.viewMode === 'density' ? 1 : 0);
    }
    if (uniforms.occupancyMap && this.occupancyTex) {
      gl.activeTexture(gl.TEXTURE2);
      gl.bindTexture(gl.TEXTURE_2D, this.occupancyTex);
      gl.uniform1i(uniforms.occupancyMap!, 2);
    }

    this.drawQuad();
  }

  private drawQuad() {
    const gl = this.gl;
    gl.bindVertexArray(this.quadVAO);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.bindVertexArray(null);
  }

  // 에이전트 렌더링 (GL_POINTS, 토러스 반복용 9x 렌더링)
  private renderAgents(
    agentTexture: WebGLTexture,
    camera: { x: number; y: number },
    mapSize: { width: number; height: number },
    viewportWidth: number,
    viewportHeight: number,
    agentCount: number,
  ) {
    const gl = this.gl;
    gl.useProgram(this.agentDisplayProgram);

    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, agentTexture);
    gl.uniform1i(this.agentDisplayUniforms.agentState, 0);

    gl.uniform2f(this.agentDisplayUniforms.mapSize, mapSize.width, mapSize.height);
    gl.uniform2f(this.agentDisplayUniforms.viewportSize, viewportWidth, viewportHeight);
    gl.uniform2f(this.agentDisplayUniforms.camera, camera.x, camera.y);
    gl.uniform1i(this.agentDisplayUniforms.agentCount, agentCount);
    gl.uniform1i(this.agentDisplayUniforms.texWidth, AGENT_TEX.WIDTH);

    // 토러스 맵 반복을 위해 3x3 그리드로 렌더링 (총 9번)
    // 뷰포트가 맵보다 작으면 중앙(인스턴스 4)만 렌더링
    const needsRepeat = viewportWidth > mapSize.width || viewportHeight > mapSize.height;
    const instanceCount = needsRepeat ? 9 : 1;
    const startInstance = needsRepeat ? 0 : 4; // 중앙 = 인스턴스 4 (1*3+1)

    for (let i = 0; i < instanceCount; i++) {
      const instance = needsRepeat ? i : startInstance;
      gl.uniform1i(this.agentDisplayUniforms.instanceOffset, instance);
      gl.drawArrays(gl.POINTS, 0, agentCount);
    }
  }

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

  dispose() {
    const gl = this.gl;
    gl.deleteProgram(this.blobProgram);
    gl.deleteProgram(this.pheromoneProgram);
    gl.deleteProgram(this.pheromoneTrailmapProgram);
    gl.deleteProgram(this.veinsProgram);
    gl.deleteProgram(this.cubicProgram);
    gl.deleteProgram(this.agentDisplayProgram);
    gl.deleteTexture(this.attractorTex);
    gl.deleteVertexArray(this.quadVAO);
  }
}
