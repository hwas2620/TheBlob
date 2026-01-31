// Jeff Jones Agent-Based Physarum Simulation
// Based on "Characteristics of Pattern Formation and Evolution in Approximations of Physarum Transport Networks"

import { TrailMapGPU } from '../gpu/TrailMapGPU';
import { AgentGPU } from '../gpu/AgentGPU';
import { MAP, AGENT, ATTRACTION, BLOB_BODY, VEINS, PHEROMONE, CUBIC_GLOW, NUCLEUS, MINIMAP, AGENT_TEX } from '../config';

export interface SimulationConfig {
  width: number;
  height: number;
  agentCount: number;
  sensorAngle: number; // 센서 각도 (라디안)
  sensorDistance: number; // 센서 거리
  turnSpeed: number; // 회전 속도 (라디안)
  moveSpeed: number; // 이동 속도
  depositAmount: number; // 페로몬 분비량
  decayFactor: number; // 증발률 (0.9 = 10% 감소)
  diffuseStrength: number; // 확산 강도
}

// 맵 크기 상수 (고정 - 윈도우 리사이즈에 영향 안받음)
export const MAP_WIDTH = MAP.WIDTH;
export const MAP_HEIGHT = MAP.HEIGHT;

const DEFAULT_CONFIG: SimulationConfig = {
  width: MAP_WIDTH,
  height: MAP_HEIGHT,
  agentCount: AGENT.COUNT,
  sensorAngle: AGENT.SENSOR_ANGLE,
  sensorDistance: AGENT.SENSOR_DISTANCE,
  turnSpeed: AGENT.TURN_SPEED,
  moveSpeed: AGENT.MOVE_SPEED,
  depositAmount: AGENT.DEPOSIT_AMOUNT,
  decayFactor: AGENT.DECAY_FACTOR,
  diffuseStrength: AGENT.DIFFUSE_STRENGTH,
};

// 에이전트 (파티클)
interface Agent {
  x: number;
  y: number;
  angle: number;
}

// 유인점 (음식 위치) - 직접 유인력
interface Attractor {
  x: number;
  y: number;
  strength: number;
  radius: number; // 유인 범위
}

export class PhysarumSimulation {
  private config: SimulationConfig;
  private agents: Agent[] = [];
  private trailMap: Float32Array; // 페로몬 맵 (시뮬레이션용 - 음식 포함)
  private trailMapTemp: Float32Array; // 페로몬 맵 (버퍼)
  // visualMap 제거됨 (GPU 렌더링으로 이전)
  private isDormant: boolean = false;
  private nucleusX: number;
  private nucleusY: number;
  private attractors: Attractor[] = []; // 음식 위치 - 직접 유인
  private showCubic: boolean = false; // 큐빅(그리드 글로우) 표시 여부
  private showParticles: boolean = false; // 알갱이(파티클) 표시 여부
  private stepCount = 0; // 맥동 카운터

  // GPU 가속
  private gpu: TrailMapGPU | null = null;        // Phase 1: 트레일맵
  private agentGPU: AgentGPU | null = null;      // Phase 3: 에이전트
  private depositBuffer: Float32Array;             // 에이전트 분비물 버퍼
  private gpuEnabled = false;
  private agentGPUEnabled = false;

  constructor(config: Partial<SimulationConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.trailMap = new Float32Array(this.config.width * this.config.height);
    this.trailMapTemp = new Float32Array(
      this.config.width * this.config.height,
    );
    this.depositBuffer = new Float32Array(this.config.width * this.config.height);
    this.nucleusX = this.config.width / 2;
    this.nucleusY = this.config.height / 2;
    this.initAgents();
  }

  // 에이전트 초기화 - 핵 중심에서 원형 분포
  private initAgents() {
    this.agents = [];
    const { agentCount, width, height } = this.config;
    const centerX = width / 2;
    const centerY = height / 2;
    const spawnRadius = AGENT.SPAWN_RADIUS;

    for (let i = 0; i < agentCount; i++) {
      // 원형 분포로 스폰
      const angle = Math.random() * Math.PI * 2;
      const r = Math.random() * spawnRadius;
      this.agents.push({
        x: centerX + Math.cos(angle) * r,
        y: centerY + Math.sin(angle) * r,
        angle: angle + (Math.random() - 0.5) * 0.5, // 바깥 방향 + 약간의 랜덤
      });
    }
  }

  // 토러스 좌표 래핑 (구체처럼 가장자리 연결)
  private wrapX(x: number): number {
    const w = this.config.width;
    return ((x % w) + w) % w;
  }

  private wrapY(y: number): number {
    const h = this.config.height;
    return ((y % h) + h) % h;
  }

  // 휴면 상태 설정
  setDormant(dormant: boolean) {
    this.isDormant = dormant;
  }

  // 핵 위치 설정
  setNucleusPosition(x: number, y: number) {
    this.nucleusX = x;
    this.nucleusY = y;
  }

  // 큐빅 표시 토글
  setShowCubic(show: boolean) {
    this.showCubic = show;
  }

  getShowCubic(): boolean {
    return this.showCubic;
  }

  // 파티클 표시 토글
  setShowParticles(show: boolean) {
    this.showParticles = show;
  }

  getShowParticles(): boolean {
    return this.showParticles;
  }

  // GPU 초기화 (WebGL2 컨텍스트 전달)
  initGPU(gl: WebGL2RenderingContext): boolean {
    try {
      // Phase 1: 트레일맵 GPU 처리
      this.gpu = new TrailMapGPU(gl, this.config.width, this.config.height);
      this.gpu.uploadTrailMap(this.trailMap);
      this.gpuEnabled = true;
      console.log('GPU 트레일맵 처리 활성화');

      // Phase 3: 에이전트 GPU 처리
      try {
        this.agentGPU = new AgentGPU(gl, this.config.width, this.config.height);
        this.agentGPU.uploadAgents(this.agents);
        this.agentGPUEnabled = true;
        console.log('GPU 에이전트 처리 활성화');
      } catch (e2) {
        console.warn('GPU 에이전트 초기화 실패, CPU 폴백:', e2);
        this.agentGPU = null;
        this.agentGPUEnabled = false;
      }

      return true;
    } catch (e) {
      console.warn('GPU 초기화 실패, CPU 폴백:', e);
      this.gpu = null;
      this.gpuEnabled = false;
      return false;
    }
  }

  isGPUEnabled(): boolean {
    return this.gpuEnabled;
  }

  // 현재 GPU 트레일 텍스처 반환 (렌더링용)
  getCurrentTrailTexture(): WebGLTexture | null {
    return this.gpu ? this.gpu.getCurrentTrailTexture() : null;
  }

  // GPU → CPU 동기화 (프레임당 1회)
  syncTrailMapFromGPU() {
    if (this.gpu) {
      this.gpu.readTrailMap(this.trailMap);
    }
    if (this.agentGPU) {
      this.agentGPU.readbackAgents();
    }
  }

  // GPU 에이전트 어트랙터 업데이트
  syncAttractorsToAgentGPU() {
    if (this.agentGPU) {
      this.agentGPU.updateAttractors(
        this.attractors.map(a => ({ x: a.x, y: a.y, strength: a.strength }))
      );
    }
  }

  // 유인점(음식) 설정 - 매 프레임 갱신
  setAttractors(attractors: Array<{ x: number; y: number; strength: number }>) {
    this.attractors = attractors.map((a) => ({
      ...a,
      radius: ATTRACTION.RADIUS, // 유인 범위 (넓게 - 다른 먹이 감지용)
    }));
  }

  // 유인점 초기화
  clearAttractors() {
    this.attractors = [];
  }

  // 특정 위치에 페로몬 주입 (음식 위치)
  injectPheromone(x: number, y: number, amount: number = 255) {
    const { width, height } = this.config;
    const ix = Math.floor(x);
    const iy = Math.floor(y);
    const radius = ATTRACTION.PHEROMONE_INJECT_RADIUS;

    for (let dy = -radius; dy <= radius; dy++) {
      for (let dx = -radius; dx <= radius; dx++) {
        const px = ix + dx;
        const py = iy + dy;
        if (px < 0 || px >= width || py < 0 || py >= height) continue;

        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= radius) {
          // 거리에 따라 자연스럽게 감쇠
          const falloff = Math.pow(1 - dist / radius, 0.5);
          const idx = py * width + px;
          const newValue = amount * falloff;
          // 누적 대신 최댓값만 유지 (프레임 누적 방지)
          if (this.gpuEnabled) {
            this.depositBuffer[idx] = Math.max(this.depositBuffer[idx], newValue);
          } else {
            this.trailMap[idx] = Math.max(this.trailMap[idx], newValue);
          }
        }
      }
    }
  }

  // 특정 위치의 파티클 밀도 확인
  getParticleDensity(x: number, y: number, radius: number = 20): number {
    // GPU 모드: 리드백 데이터에서 계산
    if (this.agentGPUEnabled && this.agentGPU) {
      return this.agentGPU.getParticleDensity(x, y, radius);
    }

    // CPU 모드
    let count = 0;
    const r2 = radius * radius;

    for (const agent of this.agents) {
      const dx = agent.x - x;
      const dy = agent.y - y;
      if (dx * dx + dy * dy < r2) {
        count++;
      }
    }

    return count;
  }

  // 메인 업데이트 루프
  update() {
    if (this.isDormant) {
      // 휴면 상태: 느린 감쇠만
      if (this.gpuEnabled && this.gpu) {
        this.gpu.runDiffuseDecay(AGENT.DECAY_FACTOR_DORMANT);
      } else {
        this.decayTrailMap(AGENT.DECAY_FACTOR_DORMANT);
      }
      return;
    }

    // 맥동: deposit과 speed를 사인파로 변조 (주기 ~3초 @60fps)
    this.stepCount++;
    const pulse = Math.sin(this.stepCount * 0.035); // 주기 ≈ 180스텝 ≈ 3초
    const depositPulse = this.config.depositAmount * (1.0 + pulse * 0.4); // ±40%
    const speedPulse = this.config.moveSpeed * (1.0 + pulse * 0.2); // ±20%

    if (this.agentGPUEnabled && this.agentGPU && this.gpu) {
      // === 전체 GPU 경로 (Phase 1+3) ===
      const trailTex = this.gpu.getCurrentTrailTexture();

      // 1. GPU 에이전트 업데이트 (Jeff Jones 알고리즘 — 직접 유인 없음)
      this.agentGPU.runUpdate(
        trailTex,
        {
          sensorAngle: this.config.sensorAngle,
          sensorDistance: this.config.sensorDistance,
          turnSpeed: this.config.turnSpeed,
          moveSpeed: speedPulse,
        },
      );

      // 2. GPU 분비: 에이전트 위치에 페로몬 추가
      const currentFbo = this.gpu.getCurrentFBO();
      this.agentGPU.runDeposit(
        currentFbo,
        this.config.width, this.config.height,
        depositPulse,
      );

      // 3. GPU 확산+감쇠
      this.gpu.runDiffuseDecay(this.config.decayFactor, AGENT.DIFFUSE_PASSES);
    } else {
      // === CPU/하이브리드 경로 ===
      // 1. 에이전트 업데이트 (CPU, 맥동 적용)
      this.updateAgents(depositPulse, speedPulse);

      // 2. 환경 업데이트
      if (this.gpuEnabled && this.gpu) {
        // GPU 트레일맵 처리
        this.gpu.uploadDeposits(this.depositBuffer);
        this.gpu.blendDeposits();
        this.depositBuffer.fill(0);
        this.gpu.runDiffuseDecay(this.config.decayFactor, AGENT.DIFFUSE_PASSES);
      } else {
        // 전체 CPU 폴백 (멀티패스 확산, 마지막에만 감쇠)
        for (let p = 0; p < AGENT.DIFFUSE_PASSES; p++) {
          this.diffuseTrailMap();
        }
        this.decayTrailMap(this.config.decayFactor);
      }
    }
  }

  // 에이전트 업데이트 - Jeff Jones 알고리즘 + 충돌 감지
  // "at most one particle in each grid square" (논문)
  private updateAgents(pulseDeposit?: number, pulseSpeed?: number) {
    const {
      width,
      sensorAngle,
      sensorDistance,
      turnSpeed,
    } = this.config;
    const moveSpeed = pulseSpeed ?? this.config.moveSpeed;
    const depositAmount = pulseDeposit ?? this.config.depositAmount;
    const densityThreshold = 50; // 과밀 임계값

    for (const agent of this.agents) {
      // 현재 위치의 페로몬 (밀도 체크)
      const curIdx = Math.floor(agent.y) * width + Math.floor(agent.x);
      const currentTrail = this.trailMap[curIdx] || 0;

      // === SENSE ===
      const frontSense = this.sense(agent.x, agent.y, agent.angle, sensorDistance);
      const leftSense = this.sense(agent.x, agent.y, agent.angle - sensorAngle, sensorDistance);
      const rightSense = this.sense(agent.x, agent.y, agent.angle + sensorAngle, sensorDistance);

      // === COLLISION DETECTION (밀도 기반) ===
      const isOvercrowded = currentTrail > densityThreshold;

      if (isOvercrowded) {
        // 과밀 상태: 페로몬이 가장 낮은 방향으로 탈출
        if (frontSense <= leftSense && frontSense <= rightSense) {
          // 앞이 가장 낮음 → 직진 (탈출)
        } else if (leftSense < rightSense) {
          agent.angle -= turnSpeed;
        } else {
          agent.angle += turnSpeed;
        }
      } else {
        // === ROTATE (일반 Jeff Jones) ===
        if (frontSense > leftSense && frontSense > rightSense) {
          // Case 1: 전방이 가장 강함 → 직진
        } else if (frontSense < leftSense && frontSense < rightSense) {
          // Case 2: 전방이 가장 약함 → 랜덤 좌/우
          agent.angle += (Math.random() > 0.5 ? 1 : -1) * turnSpeed;
        } else if (leftSense > rightSense) {
          // Case 3: 좌측이 더 강함 → 좌회전
          agent.angle -= turnSpeed;
        } else if (rightSense > leftSense) {
          // Case 4: 우측이 더 강함 → 우회전
          agent.angle += turnSpeed;
        }
        // Case 5: 모두 동일 → 직진
      }

      // === MOVE ===
      const newX = this.wrapX(agent.x + Math.cos(agent.angle) * moveSpeed);
      const newY = this.wrapY(agent.y + Math.sin(agent.angle) * moveSpeed);
      const targetIdx = Math.floor(newY) * width + Math.floor(newX);
      const targetTrail = this.trailMap[targetIdx] || 0;

      // 과밀 상태면 무조건 이동 (탈출), 아니면 충돌 감지
      if (isOvercrowded || targetTrail < densityThreshold * 1.5) {
        agent.x = newX;
        agent.y = newY;
      } else {
        // 이동 실패: 랜덤 회전
        agent.angle += (Math.random() - 0.5) * Math.PI;
      }

      // === DEPOSIT ===
      const ix = Math.floor(agent.x);
      const iy = Math.floor(agent.y);
      const idx = iy * width + ix;
      if (this.gpuEnabled) {
        this.depositBuffer[idx] = Math.min(255, this.depositBuffer[idx] + depositAmount);
      } else {
        this.trailMap[idx] = Math.min(255, this.trailMap[idx] + depositAmount);
      }
    }
  }

  // 센서 읽기 - 해당 위치의 페로몬 밀도 반환 (토러스 래핑)
  private sense(x: number, y: number, angle: number, distance: number): number {
    const { width } = this.config;
    const sensorX = Math.floor(this.wrapX(x + Math.cos(angle) * distance));
    const sensorY = Math.floor(this.wrapY(y + Math.sin(angle) * distance));
    return this.trailMap[sensorY * width + sensorX];
  }

  // 트레일 맵 확산 (3x3 Box Blur, 토러스 래핑)
  private diffuseTrailMap() {
    const { width, height } = this.config;

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        let sum = 0;
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            const nx = (x + dx + width) % width;
            const ny = (y + dy + height) % height;
            sum += this.trailMap[ny * width + nx];
          }
        }
        this.trailMapTemp[y * width + x] = sum / 9;
      }
    }

    // 스왑
    [this.trailMap, this.trailMapTemp] = [this.trailMapTemp, this.trailMap];
  }

  // 트레일 맵 감쇠
  private decayTrailMap(factor: number) {
    for (let i = 0; i < this.trailMap.length; i++) {
      this.trailMap[i] *= factor;
    }
  }

  // 뷰포트 정보
  private viewport = { x: 0, y: 0, width: 800, height: 600 };

  // 뷰포트 설정 (카메라 위치)
  setViewport(x: number, y: number, width: number, height: number) {
    this.viewport = { x, y, width, height };
  }

  getViewport() {
    return this.viewport;
  }

  // 렌더링 - 페로몬 필드 → 블롭 본체 → 연결선 → 큐빅
  // 페로몬 필드를 먼저 그려야 putImageData에 의해 보존됨
  render(ctx: CanvasRenderingContext2D) {
    const { x: camX, y: camY, width: vw, height: vh } = this.viewport;

    // 1. 페로몬 필드 (배경 위에 먼저 그림)
    this.renderPheromoneField(ctx, camX, camY, vw, vh);

    // 2. 블롭 본체 (getImageData로 필드 포함해서 읽고, trail 영역만 덮어씀)
    this.renderBlobBody(ctx, camX, camY, vw, vh);

    // 3. 연결선(vein)
    this.renderVeins(ctx, camX, camY, vw, vh);

    // 4. 큐빅 글로우 (토글)
    if (this.showCubic) {
      this.renderCubicGlow(ctx, camX, camY, vw, vh);
    }
  }

  // 연결선(vein) 렌더링 - 스크린 좌표 기반 + 토러스 래핑
  private renderVeins(
    ctx: CanvasRenderingContext2D,
    camX: number,
    camY: number,
    vw: number,
    vh: number,
  ) {
    const { width, height } = this.config;
    ctx.save();

    const veinColor = this.isDormant
      ? "rgba(100, 85, 50, 0.6)"
      : "rgba(220, 180, 40, 0.5)";

    ctx.strokeStyle = veinColor;
    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";

    const veinMin = VEINS.MIN;
    const veinMax = VEINS.MAX;
    const step = VEINS.STEP;

    // 스크린 좌표로 순회
    for (let sy = 0; sy < vh; sy += step) {
      for (let sx = 0; sx < vw; sx += step) {
        // 스크린 → 월드 (토러스 래핑)
        const wx = ((camX + sx) % width + width) % width;
        const wy = ((camY + sy) % height + height) % height;
        const value = this.trailMap[wy * width + wx];

        if (value >= veinMin && value <= veinMax) {
          let maxNeighborVal = 0;
          let maxNsx = sx, maxNsy = sy;

          for (let dy = -step; dy <= step; dy += step) {
            for (let dx = -step; dx <= step; dx += step) {
              if (dx === 0 && dy === 0) continue;
              const nwx = ((camX + sx + dx) % width + width) % width;
              const nwy = ((camY + sy + dy) % height + height) % height;
              const nVal = this.trailMap[nwy * width + nwx];
              if (nVal > maxNeighborVal) {
                maxNeighborVal = nVal;
                maxNsx = sx + dx;
                maxNsy = sy + dy;
              }
            }
          }

          if (maxNeighborVal > value) {
            const alpha = Math.min(1, (value - veinMin) / (veinMax - veinMin));
            ctx.globalAlpha = alpha * 0.7;
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            ctx.lineTo(maxNsx, maxNsy);
            ctx.stroke();
          }
        }
      }
    }

    ctx.restore();
  }

  // 페로몬 필드용 오프스크린 캔버스 (재사용)
  private fieldCanvas: HTMLCanvasElement | null = null;
  private fieldCtx: CanvasRenderingContext2D | null = null;
  private fieldW = 0;
  private fieldH = 0;

  // 페로몬 필드 렌더링 - 역제곱 법칙으로 전체 필드 합산 → 등고선
  private renderPheromoneField(
    ctx: CanvasRenderingContext2D,
    camX: number,
    camY: number,
    vw: number,
    vh: number,
  ) {
    if (this.attractors.length === 0) return;

    const { width: mapW, height: mapH } = this.config;
    const scale = PHEROMONE.SCALE;
    const fieldRadius = PHEROMONE.FIELD_RADIUS;
    const softening = PHEROMONE.SOFTENING;
    const smallW = Math.ceil(vw / scale);
    const smallH = Math.ceil(vh / scale);

    // 오프스크린 캔버스 (크기 변경 시에만 재생성)
    if (!this.fieldCanvas || this.fieldW !== smallW || this.fieldH !== smallH) {
      this.fieldCanvas = document.createElement("canvas");
      this.fieldCanvas.width = smallW;
      this.fieldCanvas.height = smallH;
      this.fieldCtx = this.fieldCanvas.getContext("2d");
      this.fieldW = smallW;
      this.fieldH = smallH;
    }

    const fctx = this.fieldCtx;
    if (!fctx) return;

    // === 1단계: 그라데이션 배경 (저해상도 → 업스케일) ===
    const fieldGrid = new Float32Array(smallW * smallH);
    const imageData = fctx.createImageData(smallW, smallH);
    const data = imageData.data;

    for (let sy = 0; sy < smallH; sy++) {
      const screenY = sy * scale + scale / 2;
      const wy = ((camY + screenY) % mapH + mapH) % mapH;

      for (let sx = 0; sx < smallW; sx++) {
        const screenX = sx * scale + scale / 2;
        const wx = ((camX + screenX) % mapW + mapW) % mapW;

        let totalField = 0;
        for (const att of this.attractors) {
          let dx = att.x - wx;
          let dy = att.y - wy;
          if (dx > mapW / 2) dx -= mapW;
          if (dx < -mapW / 2) dx += mapW;
          if (dy > mapH / 2) dy -= mapH;
          if (dy < -mapH / 2) dy += mapH;

          const distSq = dx * dx + dy * dy;
          if (distSq > fieldRadius * fieldRadius) continue;

          totalField += att.strength * softening / (distSq + softening);
        }

        const gridIdx = sy * smallW + sx;
        const intensity = totalField / (totalField + PHEROMONE.NORMALIZATION);
        fieldGrid[gridIdx] = intensity;

        if (totalField < PHEROMONE.MIN_THRESHOLD) continue;

        const idx = gridIdx * 4;
        data[idx] = Math.round(PHEROMONE.COLOR.r * intensity);
        data[idx + 1] = Math.round(PHEROMONE.COLOR.g * intensity);
        data[idx + 2] = Math.round(PHEROMONE.COLOR.b * intensity);
        data[idx + 3] = Math.round(PHEROMONE.COLOR.a * intensity);
      }
    }

    fctx.putImageData(imageData, 0, 0);

    // 그라데이션 업스케일
    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(this.fieldCanvas, 0, 0, vw, vh);
    ctx.restore();

    // === 2단계: 등고선을 벡터(marching squares)로 그리기 ===
    const contourLevels = PHEROMONE.CONTOUR_LEVELS;

    ctx.save();
    const cc = PHEROMONE.CONTOUR_COLOR;
    ctx.strokeStyle = `rgba(${cc.r}, ${cc.g}, ${cc.b}, ${cc.a})`;
    ctx.lineWidth = PHEROMONE.CONTOUR_LINE_WIDTH;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    for (const level of contourLevels) {
      ctx.beginPath();

      for (let sy = 0; sy < smallH - 1; sy++) {
        for (let sx = 0; sx < smallW - 1; sx++) {
          // 4 corners of cell
          const tl = fieldGrid[sy * smallW + sx];
          const tr = fieldGrid[sy * smallW + sx + 1];
          const bl = fieldGrid[(sy + 1) * smallW + sx];
          const br = fieldGrid[(sy + 1) * smallW + sx + 1];

          // Marching squares case
          const msCase =
            (tl >= level ? 8 : 0) |
            (tr >= level ? 4 : 0) |
            (br >= level ? 2 : 0) |
            (bl >= level ? 1 : 0);

          if (msCase === 0 || msCase === 15) continue;

          // Cell screen coords
          const x0 = sx * scale;
          const x1 = (sx + 1) * scale;
          const y0 = sy * scale;
          const y1 = (sy + 1) * scale;

          // Interpolated edge points
          const lerpX = (a: number, b: number, xA: number, xB: number) =>
            b !== a ? xA + (level - a) / (b - a) * (xB - xA) : (xA + xB) / 2;

          const top = lerpX(tl, tr, x0, x1);
          const bottom = lerpX(bl, br, x0, x1);
          const left = lerpX(tl, bl, y0, y1);
          const right = lerpX(tr, br, y0, y1);

          // Draw line segments based on case
          const segments: [number, number, number, number][] = [];
          switch (msCase) {
            case 1:  segments.push([x0, left, bottom, y1]); break;
            case 2:  segments.push([bottom, y1, x1, right]); break;
            case 3:  segments.push([x0, left, x1, right]); break;
            case 4:  segments.push([top, y0, x1, right]); break;
            case 5:  segments.push([x0, left, top, y0], [bottom, y1, x1, right]); break;
            case 6:  segments.push([top, y0, bottom, y1]); break;
            case 7:  segments.push([x0, left, top, y0]); break;
            case 8:  segments.push([top, y0, x0, left]); break;
            case 9:  segments.push([top, y0, bottom, y1]); break;
            case 10: segments.push([top, y0, x1, right], [x0, left, bottom, y1]); break;
            case 11: segments.push([top, y0, x1, right]); break;
            case 12: segments.push([x0, left, x1, right]); break;
            case 13: segments.push([bottom, y1, x1, right]); break;
            case 14: segments.push([x0, left, bottom, y1]); break;
          }

          for (const [ax, ay, bx, by] of segments) {
            ctx.moveTo(ax, ay);
            ctx.lineTo(bx, by);
          }
        }
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  // 큐빅 글로우 렌더링 - 스크린 좌표 기반 + 토러스 래핑
  private renderCubicGlow(
    ctx: CanvasRenderingContext2D,
    camX: number,
    camY: number,
    vw: number,
    vh: number,
  ) {
    const { width, height } = this.config;
    ctx.save();
    ctx.globalCompositeOperation = "lighter";

    const step = CUBIC_GLOW.BLOCK_SIZE;

    // 스크린 좌표로 순회
    for (let sy = 0; sy < vh; sy += step) {
      for (let sx = 0; sx < vw; sx += step) {
        let sum = 0;
        let count = 0;

        for (let dy = 0; dy < step; dy++) {
          for (let dx = 0; dx < step; dx++) {
            const wx = ((camX + sx + dx) % width + width) % width;
            const wy = ((camY + sy + dy) % height + height) % height;
            sum += this.trailMap[wy * width + wx];
            count++;
          }
        }

        const avgDensity = sum / count;

        if (avgDensity > CUBIC_GLOW.THRESHOLD) {
          const intensity = Math.min(1, (avgDensity - CUBIC_GLOW.THRESHOLD) / CUBIC_GLOW.INTENSITY_RANGE);
          const gradient = ctx.createRadialGradient(
            sx + step / 2,
            sy + step / 2,
            0,
            sx + step / 2,
            sy + step / 2,
            step,
          );
          gradient.addColorStop(0, `rgba(255, 220, 50, ${intensity * CUBIC_GLOW.ALPHA_MULTIPLIER})`);
          gradient.addColorStop(1, "rgba(255, 200, 0, 0)");
          ctx.fillStyle = gradient;
          ctx.fillRect(sx, sy, step, step);
        }
      }
    }

    ctx.restore();
  }

  // 블롭 본체 렌더링 - 뷰포트 영역만 점진적 페이드인
  private renderBlobBody(
    ctx: CanvasRenderingContext2D,
    camX: number,
    camY: number,
    vw: number,
    vh: number,
  ) {
    const { width, height } = this.config;

    // getImageData/putImageData는 canvas transform 무시 → 항상 (0,0) 기준
    const imageData = ctx.getImageData(0, 0, vw, vh);
    const data = imageData.data;

    const baseColor = this.isDormant ? BLOB_BODY.DORMANT_BASE : BLOB_BODY.ACTIVE_BASE;
    const darkColor = this.isDormant ? BLOB_BODY.DORMANT_DARK : BLOB_BODY.ACTIVE_DARK;

    const fadeStart = BLOB_BODY.FADE_START;
    const fadeEnd = BLOB_BODY.FADE_END;
    const maxValue = BLOB_BODY.MAX_VALUE;

    for (let vy = 0; vy < vh; vy++) {
      const mapY = (((camY + vy) % height) + height) % height;
      for (let vx = 0; vx < vw; vx++) {
        const mapX = (((camX + vx) % width) + width) % width;
        const value = this.trailMap[mapY * width + mapX];

        if (value > fadeStart) {
          const pixelIdx = (vy * vw + vx) * 4;

          const fadeT = Math.min(
            1,
            (value - fadeStart) / (fadeEnd - fadeStart),
          );
          const colorT = Math.min(
            1,
            (value - fadeStart) / (maxValue - fadeStart),
          );
          const smooth = colorT * colorT * (3 - 2 * colorT);

          const r = darkColor.r + (baseColor.r - darkColor.r) * smooth;
          const g = darkColor.g + (baseColor.g - darkColor.g) * smooth;
          const b = darkColor.b + (baseColor.b - darkColor.b) * smooth;
          const alpha = Math.min(255, BLOB_BODY.ALPHA_BASE + fadeT * BLOB_BODY.ALPHA_FADE + smooth * BLOB_BODY.ALPHA_SMOOTH);

          data[pixelIdx] = Math.round(r);
          data[pixelIdx + 1] = Math.round(g);
          data[pixelIdx + 2] = Math.round(b);
          data[pixelIdx + 3] = Math.round(alpha);
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);
  }

  // 핵 렌더링
  renderNucleus(ctx: CanvasRenderingContext2D, pulsePhase: number) {
    const x = this.nucleusX;
    const y = this.nucleusY;
    const baseRadius = NUCLEUS.BASE_RADIUS;
    const pulseRadius = baseRadius + Math.sin(pulsePhase) * NUCLEUS.PULSE_AMPLITUDE;

    ctx.save();

    // 글로우
    if (!this.isDormant) {
      ctx.shadowColor = "rgba(255, 200, 50, 0.6)";
      ctx.shadowBlur = 25;
    }

    // 외부 글로우
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, pulseRadius * 2);
    if (this.isDormant) {
      gradient.addColorStop(0, "rgba(100, 100, 80, 0.8)");
      gradient.addColorStop(0.5, "rgba(80, 80, 60, 0.3)");
      gradient.addColorStop(1, "rgba(60, 60, 40, 0)");
    } else {
      gradient.addColorStop(0, "rgba(255, 220, 50, 0.9)");
      gradient.addColorStop(0.5, "rgba(255, 180, 0, 0.4)");
      gradient.addColorStop(1, "rgba(255, 150, 0, 0)");
    }

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, pulseRadius * 2, 0, Math.PI * 2);
    ctx.fill();

    // 본체
    const bodyColor = this.isDormant ? "rgb(100, 90, 70)" : "rgb(255, 210, 50)";
    ctx.fillStyle = bodyColor;
    ctx.beginPath();

    // 불규칙한 형태
    const points = NUCLEUS.SHAPE_POINTS;
    for (let i = 0; i <= points; i++) {
      const angle = (i / points) * Math.PI * 2;
      const variation = Math.sin(angle * 3 + pulsePhase) * NUCLEUS.SHAPE_VARIATION;
      const r = pulseRadius * (1 + variation);
      const px = x + Math.cos(angle) * r;
      const py = y + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();

    // 하이라이트
    ctx.fillStyle = this.isDormant
      ? "rgba(255, 255, 255, 0.1)"
      : "rgba(255, 255, 200, 0.4)";
    ctx.beginPath();
    ctx.arc(
      x - pulseRadius * NUCLEUS.HIGHLIGHT_OFFSET,
      y - pulseRadius * NUCLEUS.HIGHLIGHT_OFFSET,
      pulseRadius * NUCLEUS.HIGHLIGHT_SIZE,
      0,
      Math.PI * 2,
    );
    ctx.fill();

    ctx.restore();
  }

  // 에이전트 배열 반환 (디버깅/외부 접근용)
  getAgents(): readonly Agent[] {
    return this.agents;
  }

  // GPU 에이전트 인스턴스 반환
  getAgentGPU(): AgentGPU | null {
    return this.agentGPU;
  }

  // 트레일 맵 반환
  getTrailMap(): Float32Array {
    return this.trailMap;
  }

  // 에이전트 수 반환
  getAgentCount(): number {
    if (this.agentGPUEnabled && this.agentGPU) {
      return this.agentGPU.agentCount;
    }
    return this.agents.length;
  }

  // 에이전트 추가 (바이오매스 증가, 지정 위치 근처에 스폰)
  addAgents(count: number, nearX?: number, nearY?: number) {
    if (this.agentGPUEnabled && this.agentGPU) {
      this.agentGPU.addAgents(count, nearX, nearY);
      return;
    }

    const { width, height } = this.config;
    const spawnX = nearX ?? width / 2;
    const spawnY = nearY ?? height / 2;

    for (let i = 0; i < count; i++) {
      this.agents.push({
        x: this.wrapX(spawnX + (Math.random() - 0.5) * 20),
        y: this.wrapY(spawnY + (Math.random() - 0.5) * 20),
        angle: Math.random() * Math.PI * 2,
      });
    }
  }

  // 에이전트 제거 (바이오매스 감소)
  removeAgents(count: number) {
    if (this.agentGPUEnabled && this.agentGPU) {
      this.agentGPU.removeAgents(count);
      return;
    }
    for (let i = 0; i < count && this.agents.length > AGENT_TEX.MIN_AGENTS; i++) {
      this.agents.pop();
    }
  }

  // 에이전트를 중심으로 수축 (포자화 준비)
  retractToCenter(strength: number = 0.02) {
    for (const agent of this.agents) {
      const dx = this.nucleusX - agent.x;
      const dy = this.nucleusY - agent.y;
      agent.x += dx * strength;
      agent.y += dy * strength;
    }
  }

  // 미니맵 렌더링 - 뷰포트 중심 기준
  renderMinimap(ctx: CanvasRenderingContext2D, miniW: number, miniH: number) {
    const { width, height } = this.config;
    const vp = this.viewport;

    // 뷰포트와 동일한 영역 (줌 레벨 반영)
    const minimapWorldSize = Math.max(vp.width, vp.height);

    // 뷰포트 중심을 기준으로 정사각형 범위 계산
    const viewCenterX = vp.x + vp.width / 2;
    const viewCenterY = vp.y + vp.height / 2;
    const minimapWorldX = viewCenterX - minimapWorldSize / 2;
    const minimapWorldY = viewCenterY - minimapWorldSize / 2;

    const imageData = ctx.createImageData(miniW, miniH);
    const data = imageData.data;

    const scale = minimapWorldSize / miniW;
    const sampleRadius = Math.max(1, Math.ceil(scale / 2));

    // 페로몬 필드 파라미터
    const fieldRadius = PHEROMONE.FIELD_RADIUS;
    const fieldRadiusSq = fieldRadius * fieldRadius;
    const softening = PHEROMONE.SOFTENING;
    const normalization = PHEROMONE.NORMALIZATION;
    const minThreshold = PHEROMONE.MIN_THRESHOLD;
    const contourLevels = PHEROMONE.CONTOUR_LEVELS;
    const lineWidthPx = PHEROMONE.CONTOUR_LINE_WIDTH_PX;

    // smoothstep 함수
    const smoothstep = (edge0: number, edge1: number, x: number): number => {
      const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
      return t * t * (3 - 2 * t);
    };

    // 필드 강도 계산 함수
    const computeField = (wx: number, wy: number): number => {
      let total = 0;
      for (const att of this.attractors) {
        let dx = att.x - wx;
        let dy = att.y - wy;
        dx = dx - Math.round(dx / width) * width;
        dy = dy - Math.round(dy / height) * height;
        const distSq = dx * dx + dy * dy;
        if (distSq > fieldRadiusSq) continue;
        const fadeStart = fieldRadiusSq * 0.7;
        const falloff = 1.0 - smoothstep(fadeStart, fieldRadiusSq, distSq);
        total += att.strength * softening / (distSq + softening) * falloff;
      }
      return total;
    };

    // 모든 픽셀을 한 번에 처리 (페로몬 먼저, 블롭이 덮어씀)
    for (let my = 0; my < miniH; my++) {
      for (let mx = 0; mx < miniW; mx++) {
        const wx = minimapWorldX + mx * scale;
        const wy = minimapWorldY + my * scale;
        const pixelIdx = (my * miniW + mx) * 4;

        // 1. 배경색으로 초기화
        data[pixelIdx] = MINIMAP.EMPTY_COLOR.r;
        data[pixelIdx + 1] = MINIMAP.EMPTY_COLOR.g;
        data[pixelIdx + 2] = MINIMAP.EMPTY_COLOR.b;
        data[pixelIdx + 3] = MINIMAP.EMPTY_COLOR.a;

        // 2. 페로몬 필드 계산
        const totalField = computeField(wx, wy);
        if (totalField >= minThreshold) {
          const intensity = totalField / (totalField + normalization);

          let r = PHEROMONE.COLOR.r * intensity;
          let g = PHEROMONE.COLOR.g * intensity;
          let b = PHEROMONE.COLOR.b * intensity;
          let a = PHEROMONE.COLOR.a * intensity;

          // 등고선
          const fieldR = computeField(wx + scale, wy);
          const fieldU = computeField(wx, wy + scale);
          const iR = fieldR / (fieldR + normalization);
          const iU = fieldU / (fieldU + normalization);
          const gradLen = Math.sqrt((iR - intensity) ** 2 + (iU - intensity) ** 2);

          let contourColor = 0;
          for (const level of contourLevels) {
            const dist = Math.abs(intensity - level);
            const pixelDist = gradLen > 0.0001 ? dist / gradLen : 9999;
            contourColor = Math.max(contourColor, 1.0 - smoothstep(0, lineWidthPx, pixelDist));
          }

          const cR = PHEROMONE.CONTOUR_COLOR.r * contourColor;
          const cG = PHEROMONE.CONTOUR_COLOR.g * contourColor;
          const cB = PHEROMONE.CONTOUR_COLOR.b * contourColor;
          const cA = PHEROMONE.CONTOUR_COLOR.a * 255 * contourColor;

          r += cR * (1 - a / 255);
          g += cG * (1 - a / 255);
          b += cB * (1 - a / 255);
          a = Math.min(255, a + cA);

          data[pixelIdx] = Math.round(r);
          data[pixelIdx + 1] = Math.round(g);
          data[pixelIdx + 2] = Math.round(b);
          data[pixelIdx + 3] = Math.round(a);
        }

        // 3. 블롭 본체 (페로몬 위에 덮어씀)
        const mapCX = Math.floor(wx);
        const mapCY = Math.floor(wy);
        let blobValue = 0;
        for (let dy = -sampleRadius; dy <= sampleRadius; dy += sampleRadius) {
          for (let dx = -sampleRadius; dx <= sampleRadius; dx += sampleRadius) {
            const sx = ((mapCX + dx) % width + width) % width;
            const sy = ((mapCY + dy) % height + height) % height;
            blobValue = Math.max(blobValue, this.trailMap[sy * width + sx]);
          }
        }

        if (blobValue > MINIMAP.DENSITY_THRESHOLD) {
          const t = Math.min(1, blobValue / MINIMAP.INTENSITY_NORM);
          data[pixelIdx] = Math.round(MINIMAP.BLOB_COLOR.r * t + MINIMAP.BLOB_BASE.r);
          data[pixelIdx + 1] = Math.round(MINIMAP.BLOB_COLOR.g * t + MINIMAP.BLOB_BASE.g);
          data[pixelIdx + 2] = Math.round(MINIMAP.BLOB_COLOR.b * t + MINIMAP.BLOB_BASE.b);
          data[pixelIdx + 3] = 255;  // 블롭은 불투명
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);
  }

  getMapSize() {
    return { width: this.config.width, height: this.config.height };
  }

  // 리셋
  reset() {
    this.trailMap.fill(0);
    this.trailMapTemp.fill(0);
    this.depositBuffer.fill(0);
    this.initAgents();
    // GPU 텍스처도 초기화
    if (this.gpu) {
      this.gpu.uploadTrailMap(this.trailMap);
    }
    if (this.agentGPU) {
      this.agentGPU.uploadAgents(this.agents);
    }
  }
}
