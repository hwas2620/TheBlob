// Physarum Network Types - 황색망사점균 네트워크 시스템

import type { Vector2 } from './game';

// 네트워크 노드 (분기점)
export interface PhysarumNode {
  id: string;
  position: Vector2;
  connections: string[]; // 연결된 edge IDs
  isNucleus: boolean;
  isNutrient: boolean;
  nutrientId?: string;
  flowStrength: number; // 0-1, 이 노드를 통과하는 흐름의 강도
}

// 네트워크 엣지 (혈관)
export interface PhysarumEdge {
  id: string;
  nodeA: string;
  nodeB: string;
  thickness: number;      // 현재 두께
  targetThickness: number; // 목표 두께 (부드러운 전환용)
  flow: number;           // 흐름량 (0-1)
  age: number;
  controlPoints: Vector2[]; // 베지어 곡선용 제어점
  alpha: number;
  growing: boolean;
  growProgress: number;   // 0-1, 성장 애니메이션용
}

// 탐색 중인 촉수 끝 (Agent)
export interface PhysarumAgent {
  id: string;
  position: Vector2;
  direction: number;
  speed: number;
  parentNodeId: string;
  pathPoints: Vector2[];   // 이동 경로
  age: number;
  energy: number;
  senseAngle: number;      // 탐지 각도
  senseDistance: number;   // 탐지 거리
}

// 전체 네트워크
export interface PhysarumNetwork {
  nodes: Map<string, PhysarumNode>;
  edges: Map<string, PhysarumEdge>;
  agents: PhysarumAgent[];
}

// Physarum 설정
export const PHYSARUM_CONFIG = {
  // Agent 설정
  AGENT_SPEED: 40, // 더 빠르게
  AGENT_SENSE_ANGLE: Math.PI / 4,    // 45도
  AGENT_SENSE_DISTANCE: 100, // 더 멀리 감지
  AGENT_TURN_SPEED: 3,
  AGENT_SPAWN_RATE: 0.05, // 더 자주 생성
  MAX_AGENTS: 50, // 더 많이

  // 네트워크 설정
  MIN_EDGE_THICKNESS: 0.5,
  MAX_EDGE_THICKNESS: 8,
  THICKNESS_GROWTH_RATE: 0.5,
  THICKNESS_DECAY_RATE: 0.15,
  FLOW_DECAY_RATE: 0.02,

  // 분기 설정
  BRANCH_PROBABILITY: 0.008,
  BRANCH_ANGLE_VARIANCE: Math.PI / 3,
  MIN_BRANCH_DISTANCE: 30,

  // 영양분 감지
  NUTRIENT_SENSE_RANGE: 120,
  NUTRIENT_ATTRACTION: 0.15,

  // 병합 설정
  MERGE_DISTANCE: 15,

  // 시각 효과
  GLOW_INTENSITY: 0.6,
  VEIN_COLOR: { r: 255, g: 255, b: 0 },
  DORMANT_COLOR: { r: 120, g: 120, b: 120 },
};
