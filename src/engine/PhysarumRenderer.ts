// Physarum Renderer - 유기적 혈관 네트워크 렌더링

import type { PhysarumNode, PhysarumEdge, PhysarumAgent } from '../types/physarum';
import { PHYSARUM_CONFIG } from '../types/physarum';
import type { Vector2 } from '../types/game';

interface RenderOptions {
  isDormant: boolean;
  isSporulating: boolean;
  pulsePhase: number;
  glowEnabled: boolean;
}

export class PhysarumRenderer {
  private ctx: CanvasRenderingContext2D;

  constructor(ctx: CanvasRenderingContext2D, _width: number, _height: number) {
    this.ctx = ctx;
  }

  updateSize(_width: number, _height: number) {
    // Size tracking can be added if needed for future features
  }

  render(
    nodes: PhysarumNode[],
    edges: PhysarumEdge[],
    agents: PhysarumAgent[],
    nucleusPosition: Vector2,
    nucleusRadius: number,
    options: RenderOptions
  ) {
    const { isDormant, isSporulating, pulsePhase, glowEnabled } = options;

    // 색상 결정
    const baseColor = isDormant
      ? PHYSARUM_CONFIG.DORMANT_COLOR
      : isSporulating
        ? { r: 255, g: 200, b: 100 }
        : PHYSARUM_CONFIG.VEIN_COLOR;

    // 1. 엣지(혈관) 렌더링
    this.renderEdges(edges, nodes, baseColor, pulsePhase, glowEnabled, isDormant);

    // 2. 에이전트(탐색 끝) 렌더링
    if (!isDormant) {
      this.renderAgents(agents, baseColor, pulsePhase);
    }

    // 3. 핵 렌더링
    this.renderNucleus(nucleusPosition, nucleusRadius, baseColor, pulsePhase, isDormant, glowEnabled);
  }

  // 엣지(혈관) 렌더링
  private renderEdges(
    edges: PhysarumEdge[],
    nodes: PhysarumNode[],
    baseColor: { r: number; g: number; b: number },
    pulsePhase: number,
    glowEnabled: boolean,
    isDormant: boolean
  ) {
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));

    // 낮은 flow 먼저 (레이어링)
    const sortedEdges = [...edges].sort((a, b) => a.flow - b.flow);

    for (const edge of sortedEdges) {
      const nodeA = nodeMap.get(edge.nodeA);
      const nodeB = nodeMap.get(edge.nodeB);
      if (!nodeA || !nodeB) continue;

      const points = edge.controlPoints;
      if (points.length < 2) continue;

      // 성장 애니메이션 적용
      const visibleLength = edge.growProgress;

      // 펄스 효과 (flow가 높을수록 강하게)
      const pulseMod = isDormant ? 0 : Math.sin(pulsePhase * 2 + edge.age) * 0.15 * edge.flow;
      const thickness = edge.thickness * (1 + pulseMod);

      // 알파 계산
      const alpha = edge.alpha * (0.6 + edge.flow * 0.4);

      // 색상 (flow에 따라 밝기 조절)
      const brightness = 0.5 + edge.flow * 0.5;
      const color = {
        r: Math.min(255, baseColor.r * brightness),
        g: Math.min(255, baseColor.g * brightness),
        b: Math.min(255, baseColor.b * brightness),
      };

      this.ctx.save();

      // 글로우 효과 (flow가 높은 엣지에만)
      if (glowEnabled && edge.flow > 0.3 && !isDormant) {
        this.ctx.shadowColor = `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, ${edge.flow * PHYSARUM_CONFIG.GLOW_INTENSITY})`;
        this.ctx.shadowBlur = thickness * 2 + edge.flow * 10;
      }

      // 메인 혈관 그리기
      this.ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
      this.ctx.lineWidth = thickness;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';

      this.drawOrganicPath(points, visibleLength);
      this.ctx.stroke();

      // 내부 하이라이트 (두꺼운 혈관에만)
      if (thickness > 3 && edge.flow > 0.2) {
        this.ctx.strokeStyle = `rgba(255, 255, 200, ${alpha * 0.3 * edge.flow})`;
        this.ctx.lineWidth = thickness * 0.3;
        this.drawOrganicPath(points, visibleLength);
        this.ctx.stroke();
      }

      this.ctx.restore();
    }
  }

  // 유기적 경로 그리기 (베지어 곡선)
  private drawOrganicPath(points: Vector2[], visibleRatio: number = 1) {
    if (points.length < 2) return;

    this.ctx.beginPath();
    this.ctx.moveTo(points[0].x, points[0].y);

    if (points.length === 2) {
      // 직선이면 약간의 곡선 추가
      const mid = {
        x: (points[0].x + points[1].x) / 2 + (Math.random() - 0.5) * 5,
        y: (points[0].y + points[1].y) / 2 + (Math.random() - 0.5) * 5,
      };
      this.ctx.quadraticCurveTo(mid.x, mid.y, points[1].x, points[1].y);
    } else {
      // 여러 점이면 스무스 베지어
      const visibleCount = Math.ceil(points.length * visibleRatio);

      for (let i = 1; i < Math.min(visibleCount, points.length - 1); i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        this.ctx.quadraticCurveTo(points[i].x, points[i].y, xc, yc);
      }

      // 마지막 점까지
      if (visibleCount >= points.length) {
        const last = points[points.length - 1];
        const secondLast = points[points.length - 2];
        this.ctx.quadraticCurveTo(secondLast.x, secondLast.y, last.x, last.y);
      }
    }
  }

  // 에이전트(탐색 끝) 렌더링
  private renderAgents(
    agents: PhysarumAgent[],
    baseColor: { r: number; g: number; b: number },
    pulsePhase: number
  ) {
    for (const agent of agents) {
      // 에이전트 경로 그리기 (점점 두꺼워지는 선)
      if (agent.pathPoints.length > 1) {
        this.ctx.save();
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        // 글로우 효과
        this.ctx.shadowColor = `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0.5)`;
        this.ctx.shadowBlur = 8;

        // 메인 경로
        this.ctx.strokeStyle = `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0.7)`;
        this.ctx.lineWidth = 2.5;

        this.ctx.beginPath();
        this.ctx.moveTo(agent.pathPoints[0].x, agent.pathPoints[0].y);

        for (let i = 1; i < agent.pathPoints.length; i++) {
          this.ctx.lineTo(agent.pathPoints[i].x, agent.pathPoints[i].y);
        }
        this.ctx.stroke();
        this.ctx.restore();
      }

      // 탐색 끝점 (밝은 점) - 더 크게
      const pulse = Math.sin(pulsePhase * 3 + agent.age * 5) * 0.3 + 0.7;
      const size = 5 + pulse * 3;

      this.ctx.save();
      this.ctx.shadowColor = `rgba(${baseColor.r}, ${baseColor.g}, 150, 0.8)`;
      this.ctx.shadowBlur = 8;

      this.ctx.fillStyle = `rgba(${baseColor.r}, ${baseColor.g}, 150, ${0.8 * agent.energy})`;
      this.ctx.beginPath();
      this.ctx.arc(agent.position.x, agent.position.y, size, 0, Math.PI * 2);
      this.ctx.fill();

      this.ctx.restore();

      // 방향 표시 (작은 삼각형)
      const dirLength = 6;
      const tipX = agent.position.x + Math.cos(agent.direction) * dirLength;
      const tipY = agent.position.y + Math.sin(agent.direction) * dirLength;

      this.ctx.fillStyle = `rgba(255, 255, 200, ${0.5 * agent.energy})`;
      this.ctx.beginPath();
      this.ctx.moveTo(tipX, tipY);
      this.ctx.lineTo(
        agent.position.x + Math.cos(agent.direction + 2.5) * 3,
        agent.position.y + Math.sin(agent.direction + 2.5) * 3
      );
      this.ctx.lineTo(
        agent.position.x + Math.cos(agent.direction - 2.5) * 3,
        agent.position.y + Math.sin(agent.direction - 2.5) * 3
      );
      this.ctx.closePath();
      this.ctx.fill();
    }
  }

  // 핵 렌더링
  private renderNucleus(
    position: Vector2,
    radius: number,
    baseColor: { r: number; g: number; b: number },
    pulsePhase: number,
    isDormant: boolean,
    glowEnabled: boolean
  ) {
    const pulseRadius = radius + (isDormant ? 1 : Math.sin(pulsePhase) * 4);

    this.ctx.save();

    // 글로우
    if (glowEnabled && !isDormant) {
      this.ctx.shadowColor = `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0.8)`;
      this.ctx.shadowBlur = 30;
    }

    // 외부 글로우 그라데이션
    const outerGlow = this.ctx.createRadialGradient(
      position.x, position.y, 0,
      position.x, position.y, pulseRadius * 2.5
    );
    outerGlow.addColorStop(0, `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0.9)`);
    outerGlow.addColorStop(0.4, `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0.3)`);
    outerGlow.addColorStop(1, `rgba(${baseColor.r}, ${baseColor.g}, ${baseColor.b}, 0)`);

    this.ctx.fillStyle = outerGlow;
    this.ctx.beginPath();
    this.ctx.arc(position.x, position.y, pulseRadius * 2.5, 0, Math.PI * 2);
    this.ctx.fill();

    // 핵 본체 - 불규칙한 형태
    this.ctx.fillStyle = `rgb(${baseColor.r}, ${baseColor.g}, ${baseColor.b})`;
    this.ctx.beginPath();

    const irregularPoints = 12;
    for (let i = 0; i <= irregularPoints; i++) {
      const angle = (i / irregularPoints) * Math.PI * 2;
      const variation = isDormant ? 0.05 : 0.15;
      const r = pulseRadius * (1 + Math.sin(angle * 3 + pulsePhase) * variation);
      const x = position.x + Math.cos(angle) * r;
      const y = position.y + Math.sin(angle) * r;

      if (i === 0) {
        this.ctx.moveTo(x, y);
      } else {
        // 부드러운 곡선
        const prevAngle = ((i - 1) / irregularPoints) * Math.PI * 2;
        const prevR = pulseRadius * (1 + Math.sin(prevAngle * 3 + pulsePhase) * variation);
        const prevX = position.x + Math.cos(prevAngle) * prevR;
        const prevY = position.y + Math.sin(prevAngle) * prevR;

        const cpX = (prevX + x) / 2 + Math.cos(angle - Math.PI / 2) * 2;
        const cpY = (prevY + y) / 2 + Math.sin(angle - Math.PI / 2) * 2;

        this.ctx.quadraticCurveTo(cpX, cpY, x, y);
      }
    }
    this.ctx.closePath();
    this.ctx.fill();

    // 내부 하이라이트
    this.ctx.fillStyle = `rgba(255, 255, 255, ${isDormant ? 0.2 : 0.5})`;
    this.ctx.beginPath();
    this.ctx.arc(
      position.x - pulseRadius * 0.25,
      position.y - pulseRadius * 0.25,
      pulseRadius * 0.3,
      0,
      Math.PI * 2
    );
    this.ctx.fill();

    // 내부 텍스처 (작은 점들)
    if (!isDormant) {
      this.ctx.fillStyle = `rgba(200, 180, 0, 0.3)`;
      for (let i = 0; i < 5; i++) {
        const angle = (i / 5) * Math.PI * 2 + pulsePhase * 0.5;
        const dist = pulseRadius * 0.4;
        const dotX = position.x + Math.cos(angle) * dist;
        const dotY = position.y + Math.sin(angle) * dist;
        this.ctx.beginPath();
        this.ctx.arc(dotX, dotY, 2, 0, Math.PI * 2);
        this.ctx.fill();
      }
    }

    this.ctx.restore();
  }
}
