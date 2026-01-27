// Physarum Simulation Engine - 황색망사점균 시뮬레이션 엔진

import type { Vector2 } from '../types/game';
import type {
  PhysarumNode,
  PhysarumEdge,
  PhysarumAgent,
  PhysarumNetwork,
} from '../types/physarum';
import { PHYSARUM_CONFIG } from '../types/physarum';

// 유틸리티 함수
const generateId = () => Math.random().toString(36).substr(2, 9);

const distance = (a: Vector2, b: Vector2): number => {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
};

const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export class PhysarumEngine {
  network: PhysarumNetwork;
  nucleusPosition: Vector2;
  nutrients: Map<string, { position: Vector2; value: number; connected: boolean }>;
  bounds: { width: number; height: number };
  isDormant: boolean;

  constructor(nucleusPos: Vector2, width: number, height: number) {
    this.nucleusPosition = nucleusPos;
    this.bounds = { width, height };
    this.isDormant = false;
    this.nutrients = new Map();

    // 네트워크 초기화
    this.network = {
      nodes: new Map(),
      edges: new Map(),
      agents: [],
    };

    // 핵 노드 생성
    const nucleusNode: PhysarumNode = {
      id: 'nucleus',
      position: { ...nucleusPos },
      connections: [],
      isNucleus: true,
      isNutrient: false,
      flowStrength: 1,
    };
    this.network.nodes.set('nucleus', nucleusNode);

    // 초기 에이전트 생성
    this.spawnInitialAgents(8);
  }

  // 초기 에이전트 생성
  spawnInitialAgents(count: number) {
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2 + Math.random() * 0.3;
      this.spawnAgent('nucleus', angle);
    }
  }

  // 에이전트 생성
  spawnAgent(fromNodeId: string, direction?: number) {
    const node = this.network.nodes.get(fromNodeId);
    if (!node) return;

    if (this.network.agents.length >= PHYSARUM_CONFIG.MAX_AGENTS) return;

    const agent: PhysarumAgent = {
      id: generateId(),
      position: { ...node.position },
      direction: direction ?? Math.random() * Math.PI * 2,
      speed: PHYSARUM_CONFIG.AGENT_SPEED * (0.8 + Math.random() * 0.4),
      parentNodeId: fromNodeId,
      pathPoints: [{ ...node.position }],
      age: 0,
      energy: 1,
      senseAngle: PHYSARUM_CONFIG.AGENT_SENSE_ANGLE,
      senseDistance: PHYSARUM_CONFIG.AGENT_SENSE_DISTANCE,
    };

    this.network.agents.push(agent);
  }

  // 영양분 추가
  addNutrient(id: string, position: Vector2, value: number) {
    this.nutrients.set(id, { position, value, connected: false });
  }

  // 영양분 제거
  removeNutrient(id: string) {
    this.nutrients.delete(id);
  }

  // 영양분 연결 상태 업데이트
  updateNutrientConnection(id: string, connected: boolean) {
    const nutrient = this.nutrients.get(id);
    if (nutrient) {
      nutrient.connected = connected;
    }
  }

  // 메인 업데이트 루프
  update(deltaTime: number): { atpGained: number; biomassGained: number } {
    if (this.isDormant) {
      return { atpGained: 0, biomassGained: 0 };
    }

    let atpGained = 0;
    let biomassGained = 0;

    // 1. 에이전트 업데이트 (탐색)
    this.updateAgents(deltaTime);

    // 2. 네트워크 흐름 계산
    this.calculateFlow();

    // 3. 엣지 두께 업데이트 (강화/쇠퇴)
    this.updateEdgeThickness(deltaTime);

    // 4. 새 에이전트 생성 (분기)
    this.trySpawnNewAgents();

    // 5. 영양분 흡수
    const absorption = this.absorbNutrients(deltaTime);
    atpGained = absorption.atp;
    biomassGained = absorption.biomass;

    // 6. 죽은 엣지 제거
    this.pruneDeadEdges();

    return { atpGained, biomassGained };
  }

  // 에이전트 업데이트
  private updateAgents(deltaTime: number) {
    const agentsToRemove: string[] = [];

    for (const agent of this.network.agents) {
      agent.age += deltaTime;
      agent.energy -= deltaTime * 0.03; // 더 오래 생존

      // 에너지 소진되면 제거
      if (agent.energy <= 0) {
        this.finalizeAgentPath(agent);
        agentsToRemove.push(agent.id);
        continue;
      }

      // 감지 및 방향 조정
      this.senseAndTurn(agent, deltaTime);

      // 이동
      const moveAmount = agent.speed * deltaTime;
      const newPos = {
        x: agent.position.x + Math.cos(agent.direction) * moveAmount,
        y: agent.position.y + Math.sin(agent.direction) * moveAmount,
      };

      // 경계 체크
      const margin = 40;
      if (
        newPos.x < margin ||
        newPos.x > this.bounds.width - margin ||
        newPos.y < margin ||
        newPos.y > this.bounds.height - margin
      ) {
        this.finalizeAgentPath(agent);
        agentsToRemove.push(agent.id);
        continue;
      }

      agent.position = newPos;
      agent.pathPoints.push({ ...newPos });

      // 경로가 너무 길면 중간 노드 생성
      if (agent.pathPoints.length > 30) {
        this.createIntermediateNode(agent);
      }

      // 영양분 도달 체크
      for (const [nutrientId, nutrient] of this.nutrients) {
        if (nutrient.connected) continue;
        if (distance(agent.position, nutrient.position) < 25) {
          this.connectToNutrient(agent, nutrientId, nutrient.position);
          agentsToRemove.push(agent.id);
          break;
        }
      }

      // 기존 노드와 병합 체크
      for (const [nodeId, node] of this.network.nodes) {
        if (nodeId === agent.parentNodeId) continue;
        if (node.isNucleus) continue;
        if (distance(agent.position, node.position) < PHYSARUM_CONFIG.MERGE_DISTANCE) {
          this.mergeAgentToNode(agent, nodeId);
          agentsToRemove.push(agent.id);
          break;
        }
      }
    }

    // 제거할 에이전트 처리
    this.network.agents = this.network.agents.filter(
      (a) => !agentsToRemove.includes(a.id)
    );
  }

  // 감지 및 방향 조정
  private senseAndTurn(agent: PhysarumAgent, deltaTime: number) {
    // 영양분 방향으로 끌림
    let targetDirection = agent.direction;
    let attracted = false;

    for (const [, nutrient] of this.nutrients) {
      if (nutrient.connected) continue;
      const dist = distance(agent.position, nutrient.position);
      if (dist < PHYSARUM_CONFIG.NUTRIENT_SENSE_RANGE) {
        const toNutrient = Math.atan2(
          nutrient.position.y - agent.position.y,
          nutrient.position.x - agent.position.x
        );
        const attraction = PHYSARUM_CONFIG.NUTRIENT_ATTRACTION * (1 - dist / PHYSARUM_CONFIG.NUTRIENT_SENSE_RANGE);
        targetDirection = lerp(agent.direction, toNutrient, attraction);
        attracted = true;
        break;
      }
    }

    // 끌리지 않으면 랜덤 워킹
    if (!attracted) {
      targetDirection += (Math.random() - 0.5) * 0.8 * deltaTime * 60;
    }

    // 부드러운 회전
    const angleDiff = targetDirection - agent.direction;
    const normalizedDiff = Math.atan2(Math.sin(angleDiff), Math.cos(angleDiff));
    agent.direction += normalizedDiff * PHYSARUM_CONFIG.AGENT_TURN_SPEED * deltaTime;
  }

  // 에이전트 경로 확정 (노드와 엣지 생성)
  private finalizeAgentPath(agent: PhysarumAgent) {
    if (agent.pathPoints.length < 3) return; // 최소 길이 줄임

    // 새 노드 생성
    const endNode: PhysarumNode = {
      id: generateId(),
      position: { ...agent.position },
      connections: [],
      isNucleus: false,
      isNutrient: false,
      flowStrength: 0,
    };
    this.network.nodes.set(endNode.id, endNode);

    // 엣지 생성
    this.createEdge(agent.parentNodeId, endNode.id, agent.pathPoints);
  }

  // 영양분에 연결
  private connectToNutrient(agent: PhysarumAgent, nutrientId: string, nutrientPos: Vector2) {
    // 영양분 노드 생성
    const nutrientNode: PhysarumNode = {
      id: `nutrient_${nutrientId}`,
      position: { ...nutrientPos },
      connections: [],
      isNucleus: false,
      isNutrient: true,
      nutrientId,
      flowStrength: 1,
    };
    this.network.nodes.set(nutrientNode.id, nutrientNode);

    // 엣지 생성
    agent.pathPoints.push({ ...nutrientPos });
    this.createEdge(agent.parentNodeId, nutrientNode.id, agent.pathPoints);

    // 영양분 연결 상태 업데이트
    const nutrient = this.nutrients.get(nutrientId);
    if (nutrient) {
      nutrient.connected = true;
    }
  }

  // 기존 노드에 병합
  private mergeAgentToNode(agent: PhysarumAgent, nodeId: string) {
    const node = this.network.nodes.get(nodeId);
    if (!node) return;

    agent.pathPoints.push({ ...node.position });
    this.createEdge(agent.parentNodeId, nodeId, agent.pathPoints);
  }

  // 중간 노드 생성
  private createIntermediateNode(agent: PhysarumAgent) {
    const midIndex = Math.floor(agent.pathPoints.length / 2);
    const midPoint = agent.pathPoints[midIndex];

    const midNode: PhysarumNode = {
      id: generateId(),
      position: { ...midPoint },
      connections: [],
      isNucleus: false,
      isNutrient: false,
      flowStrength: 0,
    };
    this.network.nodes.set(midNode.id, midNode);

    // 첫 번째 엣지 (부모 -> 중간)
    const firstHalf = agent.pathPoints.slice(0, midIndex + 1);
    this.createEdge(agent.parentNodeId, midNode.id, firstHalf);

    // 에이전트 업데이트
    agent.parentNodeId = midNode.id;
    agent.pathPoints = agent.pathPoints.slice(midIndex);
  }

  // 엣지 생성
  private createEdge(nodeAId: string, nodeBId: string, pathPoints: Vector2[]) {
    const nodeA = this.network.nodes.get(nodeAId);
    const nodeB = this.network.nodes.get(nodeBId);
    if (!nodeA || !nodeB) return;

    const edge: PhysarumEdge = {
      id: generateId(),
      nodeA: nodeAId,
      nodeB: nodeBId,
      thickness: PHYSARUM_CONFIG.MIN_EDGE_THICKNESS,
      targetThickness: PHYSARUM_CONFIG.MIN_EDGE_THICKNESS,
      flow: 0,
      age: 0,
      controlPoints: this.simplifyPath(pathPoints),
      alpha: 1,
      growing: true,
      growProgress: 0,
    };

    this.network.edges.set(edge.id, edge);
    nodeA.connections.push(edge.id);
    nodeB.connections.push(edge.id);
  }

  // 경로 단순화 (베지어 곡선용)
  private simplifyPath(points: Vector2[]): Vector2[] {
    if (points.length <= 4) return [...points];

    const simplified: Vector2[] = [points[0]];
    const step = Math.max(1, Math.floor(points.length / 6));

    for (let i = step; i < points.length - 1; i += step) {
      simplified.push(points[i]);
    }
    simplified.push(points[points.length - 1]);

    return simplified;
  }

  // 네트워크 흐름 계산 (영양분에서 핵으로)
  private calculateFlow() {
    // 모든 엣지 흐름 리셋
    for (const edge of this.network.edges.values()) {
      edge.flow *= 1 - PHYSARUM_CONFIG.FLOW_DECAY_RATE;
    }

    // 영양분 노드에서 핵까지 경로 찾기 및 흐름 추가
    for (const node of this.network.nodes.values()) {
      if (node.isNutrient && node.nutrientId) {
        const nutrient = this.nutrients.get(node.nutrientId);
        if (nutrient && nutrient.connected) {
          this.propagateFlow(node.id, new Set(), 1);
        }
      }
    }
  }

  // 흐름 전파 (BFS)
  private propagateFlow(nodeId: string, visited: Set<string>, strength: number) {
    if (visited.has(nodeId) || strength < 0.01) return;
    visited.add(nodeId);

    const node = this.network.nodes.get(nodeId);
    if (!node) return;

    node.flowStrength = Math.max(node.flowStrength, strength);

    if (node.isNucleus) return;

    for (const edgeId of node.connections) {
      const edge = this.network.edges.get(edgeId);
      if (!edge) continue;

      const otherNodeId = edge.nodeA === nodeId ? edge.nodeB : edge.nodeA;
      if (visited.has(otherNodeId)) continue;

      edge.flow = Math.max(edge.flow, strength * 0.9);
      this.propagateFlow(otherNodeId, visited, strength * 0.85);
    }
  }

  // 엣지 두께 업데이트
  private updateEdgeThickness(deltaTime: number) {
    for (const edge of this.network.edges.values()) {
      edge.age += deltaTime;

      // 성장 애니메이션
      if (edge.growing) {
        edge.growProgress += deltaTime * 2;
        if (edge.growProgress >= 1) {
          edge.growing = false;
          edge.growProgress = 1;
        }
      }

      // 목표 두께 계산
      if (edge.flow > 0.1) {
        edge.targetThickness = PHYSARUM_CONFIG.MIN_EDGE_THICKNESS +
          edge.flow * (PHYSARUM_CONFIG.MAX_EDGE_THICKNESS - PHYSARUM_CONFIG.MIN_EDGE_THICKNESS);
      } else {
        edge.targetThickness = PHYSARUM_CONFIG.MIN_EDGE_THICKNESS * 0.5;
        edge.alpha -= PHYSARUM_CONFIG.THICKNESS_DECAY_RATE * deltaTime;
      }

      // 두께 부드럽게 전환
      edge.thickness = lerp(
        edge.thickness,
        edge.targetThickness,
        PHYSARUM_CONFIG.THICKNESS_GROWTH_RATE * deltaTime * 60
      );
    }
  }

  // 새 에이전트 생성 시도 (분기)
  private trySpawnNewAgents() {
    if (this.network.agents.length >= PHYSARUM_CONFIG.MAX_AGENTS) return;

    // 핵에서 새 에이전트
    if (Math.random() < PHYSARUM_CONFIG.AGENT_SPAWN_RATE) {
      this.spawnAgent('nucleus');
    }

    // 고흐름 노드에서 분기
    for (const node of this.network.nodes.values()) {
      if (node.isNucleus || node.isNutrient) continue;
      if (node.flowStrength > 0.5 && Math.random() < PHYSARUM_CONFIG.BRANCH_PROBABILITY) {
        const angle = Math.random() * Math.PI * 2;
        this.spawnAgent(node.id, angle);
      }
    }
  }

  // 영양분 흡수
  private absorbNutrients(deltaTime: number): { atp: number; biomass: number } {
    let atp = 0;
    let biomass = 0;

    for (const [nutrientId, nutrient] of this.nutrients) {
      if (!nutrient.connected) continue;

      const absorptionRate = 0.2 * deltaTime * 60;
      nutrient.value -= absorptionRate;
      atp += absorptionRate * 0.5;
      biomass += absorptionRate * 0.1;

      if (nutrient.value <= 0) {
        // 영양분 고갈 - 노드는 유지하되 흐름 제거
        const nodeId = `nutrient_${nutrientId}`;
        const node = this.network.nodes.get(nodeId);
        if (node) {
          node.isNutrient = false;
          node.flowStrength = 0;
        }
      }
    }

    return { atp, biomass };
  }

  // 죽은 엣지 제거
  private pruneDeadEdges() {
    const edgesToRemove: string[] = [];

    for (const [edgeId, edge] of this.network.edges) {
      if (edge.alpha <= 0 || edge.thickness < 0.1) {
        edgesToRemove.push(edgeId);
      }
    }

    for (const edgeId of edgesToRemove) {
      const edge = this.network.edges.get(edgeId);
      if (!edge) continue;

      // 노드에서 연결 제거
      const nodeA = this.network.nodes.get(edge.nodeA);
      const nodeB = this.network.nodes.get(edge.nodeB);

      if (nodeA) {
        nodeA.connections = nodeA.connections.filter((id) => id !== edgeId);
      }
      if (nodeB) {
        nodeB.connections = nodeB.connections.filter((id) => id !== edgeId);
      }

      this.network.edges.delete(edgeId);
    }

    // 연결이 없는 비핵심 노드 제거
    const nodesToRemove: string[] = [];
    for (const [nodeId, node] of this.network.nodes) {
      if (node.isNucleus) continue;
      if (node.connections.length === 0) {
        nodesToRemove.push(nodeId);
      }
    }

    for (const nodeId of nodesToRemove) {
      this.network.nodes.delete(nodeId);
    }
  }

  // 렌더링 데이터 가져오기
  getRenderData() {
    return {
      nodes: Array.from(this.network.nodes.values()),
      edges: Array.from(this.network.edges.values()),
      agents: this.network.agents,
      nucleusPosition: this.nucleusPosition,
    };
  }

  // 휴면 상태 설정
  setDormant(dormant: boolean) {
    this.isDormant = dormant;
  }

  // 리셋
  reset() {
    this.network = {
      nodes: new Map(),
      edges: new Map(),
      agents: [],
    };

    const nucleusNode: PhysarumNode = {
      id: 'nucleus',
      position: { ...this.nucleusPosition },
      connections: [],
      isNucleus: true,
      isNutrient: false,
      flowStrength: 1,
    };
    this.network.nodes.set('nucleus', nucleusNode);

    this.nutrients.clear();
    this.spawnInitialAgents(8);
  }
}
