// Jeff Jones Agent-Based Physarum Simulation
// Based on "Characteristics of Pattern Formation and Evolution in Approximations of Physarum Transport Networks"

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
export const MAP_WIDTH = 1500;
export const MAP_HEIGHT = 1500;

const DEFAULT_CONFIG: SimulationConfig = {
  width: MAP_WIDTH,
  height: MAP_HEIGHT,
  agentCount: 5000, // 1500x1500 맵
  sensorAngle: Math.PI / 8, // 22.5도 (논문 표준 SA)
  sensorDistance: 9, // 논문 표준 SO
  turnSpeed: Math.PI / 4, // 45도 (논문 표준 RA)
  moveSpeed: 1, // 논문 표준 SS (1px/step)
  depositAmount: 5, // 논문 표준 depT
  decayFactor: 0.9, // 논문 표준 (트레일 빠르게 사라짐 → 응집력 유지)
  diffuseStrength: 1,
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
  private visualMap: Float32Array; // 시각화 맵 (에이전트만 - 렌더링용)
  private isDormant: boolean = false;
  private nucleusX: number;
  private nucleusY: number;
  private attractors: Attractor[] = []; // 음식 위치 - 직접 유인
  private showCubic: boolean = false; // 큐빅(그리드 글로우) 표시 여부

  constructor(config: Partial<SimulationConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.trailMap = new Float32Array(this.config.width * this.config.height);
    this.trailMapTemp = new Float32Array(
      this.config.width * this.config.height,
    );
    this.visualMap = new Float32Array(this.config.width * this.config.height);
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
    const spawnRadius = 30;

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

  // 유인점(음식) 설정 - 매 프레임 갱신
  setAttractors(attractors: Array<{ x: number; y: number; strength: number }>) {
    this.attractors = attractors.map((a) => ({
      ...a,
      radius: 300, // 유인 범위 (넓게 - 다른 먹이 감지용)
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
    const radius = 50; // 넓은 범위로 멀리까지 신호 전달

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
          this.trailMap[idx] = Math.max(this.trailMap[idx], newValue);
        }
      }
    }
  }

  // 특정 위치의 파티클 밀도 확인
  getParticleDensity(x: number, y: number, radius: number = 20): number {
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
      this.decayTrailMap(0.98);
      return;
    }

    // 1. 에이전트 업데이트 (Sense → Rotate → Move → Deposit)
    this.updateAgents();

    // 2. 환경 업데이트 (Diffuse → Decay)
    this.diffuseTrailMap();
    this.decayTrailMap(this.config.decayFactor);
  }

  // 에이전트 업데이트
  private updateAgents() {
    const {
      width,
      height,
      sensorAngle,
      sensorDistance,
      turnSpeed,
      moveSpeed,
      depositAmount,
    } = this.config;

    for (const agent of this.agents) {
      // === 직접 유인력 체크 (가까운 에이전트만 - 촉수 형성 유지) ===
      let directAttraction = false;
      let closestAttractor: Attractor | null = null;
      let closestDist = Infinity;

      for (const attractor of this.attractors) {
        const dx = attractor.x - agent.x;
        const dy = attractor.y - agent.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < closestDist) {
          closestDist = dist;
          closestAttractor = attractor;
        }
      }

      // 가까울 때만 직접 유인 (멀면 페로몬 따라가게)
      if (closestAttractor && closestDist > 5 && closestDist < 120) {
        const dx = closestAttractor.x - agent.x;
        const dy = closestAttractor.y - agent.y;
        const targetAngle = Math.atan2(dy, dx);
        let angleDiff = targetAngle - agent.angle;

        // 각도 정규화 (-PI ~ PI)
        while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
        while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

        // 거리 기반 강도 (가까울수록 강하게)
        const strength = (1 - closestDist / 120) * 0.4;
        agent.angle += angleDiff * strength;
        directAttraction = true;
      }

      // === SENSE (기존 Jeff Jones 알고리즘) ===
      // 3개의 센서로 페로몬 밀도 측정
      const frontSense = this.sense(
        agent.x,
        agent.y,
        agent.angle,
        sensorDistance,
      );
      const leftSense = this.sense(
        agent.x,
        agent.y,
        agent.angle - sensorAngle,
        sensorDistance,
      );
      const rightSense = this.sense(
        agent.x,
        agent.y,
        agent.angle + sensorAngle,
        sensorDistance,
      );

      // === ROTATE (직접 유인이 없을 때만 페로몬 기반 회전) ===
      if (!directAttraction) {
        if (frontSense > leftSense && frontSense > rightSense) {
          // 앞이 가장 강함 - 직진
        } else if (frontSense < leftSense && frontSense < rightSense) {
          // 앞이 가장 약함 - 랜덤하게 좌우 회전
          agent.angle += (Math.random() > 0.5 ? 1 : -1) * turnSpeed;
        } else if (leftSense > rightSense) {
          // 왼쪽이 강함 - 왼쪽으로
          agent.angle -= turnSpeed;
        } else if (rightSense > leftSense) {
          // 오른쪽이 강함 - 오른쪽으로
          agent.angle += turnSpeed;
        }
      }

      // 약간의 랜덤 회전 (탐색 행동) - 직접 유인 시 약하게
      agent.angle += (Math.random() - 0.5) * (directAttraction ? 0.03 : 0.1);

      // === CONNECTIVITY (물리적 연속성 보장) ===
      // 실제 점균류는 단일 유기체이므로 끊어지면 안 됨
      // 현재 위치의 trail이 낮으면 → 고립된 상태 → 고밀도 방향으로 회귀
      const curIdx = Math.floor(agent.y) * width + Math.floor(agent.x);
      const curTrail = this.trailMap[curIdx] || 0;

      if (curTrail < 8 && !directAttraction) {
        // 고립됨: 여러 거리에서 trail 탐색
        let bestTrail = 0;
        let bestAngle = agent.angle;

        // 가까운 거리(20px)와 먼 거리(60px) 모두 탐색
        for (const searchDist of [20, 60]) {
          for (let i = 0; i < 16; i++) {
            const a = (i / 16) * Math.PI * 2;
            const sx = Math.floor(this.wrapX(agent.x + Math.cos(a) * searchDist));
            const sy = Math.floor(this.wrapY(agent.y + Math.sin(a) * searchDist));
            const trail = this.trailMap[sy * width + sx];
            if (trail > bestTrail) {
              bestTrail = trail;
              bestAngle = a;
            }
          }
        }

        if (bestTrail > 3) {
          // 고밀도 방향으로 강하게 회전 (고립도에 따라 강도 조절)
          let angleDiff = bestAngle - agent.angle;
          while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
          while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
          const isolationStrength = curTrail < 2 ? 0.6 : 0.4;
          agent.angle += angleDiff * isolationStrength;
        }
      }

      // === MOVE (토러스 래핑 - 구체처럼 가장자리 연결) ===
      agent.x = this.wrapX(agent.x + Math.cos(agent.angle) * moveSpeed);
      agent.y = this.wrapY(agent.y + Math.sin(agent.angle) * moveSpeed);

      // === DEPOSIT ===
      const ix = Math.floor(agent.x);
      const iy = Math.floor(agent.y);
      const idx = iy * width + ix;
      this.trailMap[idx] = Math.min(255, this.trailMap[idx] + depositAmount);
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

    const veinMin = 5;
    const veinMax = 25;
    const step = 4;

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
    const scale = 8; // 그라데이션은 저해상도 OK
    const fieldRadius = 600;
    const softening = 8000;
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
        const intensity = totalField / (totalField + 0.5);
        fieldGrid[gridIdx] = intensity;

        if (totalField < 0.02) continue;

        const idx = gridIdx * 4;
        data[idx] = Math.round(60 * intensity);
        data[idx + 1] = Math.round(140 * intensity);
        data[idx + 2] = Math.round(40 * intensity);
        data[idx + 3] = Math.round(180 * intensity);
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
    const contourLevels = [0.10, 0.22, 0.34, 0.46, 0.58, 0.70];

    ctx.save();
    ctx.strokeStyle = 'rgba(120, 220, 100, 0.35)';
    ctx.lineWidth = 1.2;
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

    const step = 20;

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

        if (avgDensity > 30) {
          const intensity = Math.min(1, (avgDensity - 30) / 100);
          const gradient = ctx.createRadialGradient(
            sx + step / 2,
            sy + step / 2,
            0,
            sx + step / 2,
            sy + step / 2,
            step,
          );
          gradient.addColorStop(0, `rgba(255, 220, 50, ${intensity * 0.3})`);
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

    const baseColor = this.isDormant
      ? { r: 120, g: 100, b: 60 }
      : { r: 255, g: 200, b: 50 };

    const darkColor = this.isDormant
      ? { r: 80, g: 65, b: 40 }
      : { r: 200, g: 150, b: 20 };

    const fadeStart = 10;
    const fadeEnd = 60;
    const maxValue = 150;

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
          const alpha = Math.min(255, 20 + fadeT * 180 + smooth * 55);

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
    const baseRadius = 20;
    const pulseRadius = baseRadius + Math.sin(pulsePhase) * 3;

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
    const points = 10;
    for (let i = 0; i <= points; i++) {
      const angle = (i / points) * Math.PI * 2;
      const variation = Math.sin(angle * 3 + pulsePhase) * 0.1;
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
      x - pulseRadius * 0.3,
      y - pulseRadius * 0.3,
      pulseRadius * 0.25,
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

  // 트레일 맵 반환
  getTrailMap(): Float32Array {
    return this.trailMap;
  }

  // 에이전트 수 반환
  getAgentCount(): number {
    return this.agents.length;
  }

  // 에이전트 추가 (바이오매스 증가)
  addAgents(count: number) {
    const { width, height } = this.config;

    for (let i = 0; i < count; i++) {
      // 기존 에이전트 근처에 스폰
      if (this.agents.length > 0) {
        const parent =
          this.agents[Math.floor(Math.random() * this.agents.length)];
        this.agents.push({
          x: parent.x + (Math.random() - 0.5) * 10,
          y: parent.y + (Math.random() - 0.5) * 10,
          angle: Math.random() * Math.PI * 2,
        });
      } else {
        this.agents.push({
          x: width / 2 + (Math.random() - 0.5) * 30,
          y: height / 2 + (Math.random() - 0.5) * 30,
          angle: Math.random() * Math.PI * 2,
        });
      }
    }
  }

  // 에이전트 제거 (바이오매스 감소)
  removeAgents(count: number) {
    for (let i = 0; i < count && this.agents.length > 100; i++) {
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

  // 미니맵 렌더링 - 전체 맵을 축소해서 그림
  renderMinimap(ctx: CanvasRenderingContext2D, miniW: number, miniH: number) {
    const { width, height } = this.config;
    const imageData = ctx.createImageData(miniW, miniH);
    const data = imageData.data;

    const scaleX = width / miniW;
    const scaleY = height / miniH;

    for (let my = 0; my < miniH; my++) {
      for (let mx = 0; mx < miniW; mx++) {
        // 해당 미니맵 픽셀에 대응하는 맵 영역의 평균값
        const mapX = Math.floor(mx * scaleX);
        const mapY = Math.floor(my * scaleY);
        const value = this.trailMap[mapY * width + mapX];

        const pixelIdx = (my * miniW + mx) * 4;

        if (value > 5) {
          const t = Math.min(1, value / 100);
          data[pixelIdx] = Math.round(200 * t + 50); // R
          data[pixelIdx + 1] = Math.round(180 * t + 30); // G
          data[pixelIdx + 2] = Math.round(20 * t + 10); // B
          data[pixelIdx + 3] = Math.round(100 + 155 * t); // A
        } else {
          data[pixelIdx] = 15;
          data[pixelIdx + 1] = 15;
          data[pixelIdx + 2] = 15;
          data[pixelIdx + 3] = 200;
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);

    // 뷰포트 영역 표시
    const vp = this.viewport;
    const vpX = (vp.x / width) * miniW;
    const vpY = (vp.y / height) * miniH;
    const vpW = (vp.width / width) * miniW;
    const vpH = (vp.height / height) * miniH;

    ctx.strokeStyle = "rgba(255, 255, 255, 0.8)";
    ctx.lineWidth = 1;
    ctx.strokeRect(vpX, vpY, vpW, vpH);

    // 영양분 위치 표시
    for (const attractor of this.attractors) {
      const ax = (attractor.x / width) * miniW;
      const ay = (attractor.y / height) * miniH;
      ctx.fillStyle = `rgba(100, 200, 50, ${0.5 + attractor.strength * 0.5})`;
      ctx.beginPath();
      ctx.arc(ax, ay, 2, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  getMapSize() {
    return { width: this.config.width, height: this.config.height };
  }

  // 리셋
  reset() {
    this.trailMap.fill(0);
    this.trailMapTemp.fill(0);
    this.initAgents();
  }
}
