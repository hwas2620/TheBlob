// 실시간 파라미터 튜닝 스토어
import { create } from 'zustand';
import { VEINS, BLOB_BODY, PHEROMONE, GAME, AGENT } from '../config';

// 튜닝 가능한 파라미터 정의
export interface TunableParams {
  // 정맥
  veinsMin: number;
  veinsMax: number;
  veinsRidgeThreshold: number;
  veinsMaxAlpha: number;

  // 블롭 본체
  blobFadeStart: number;
  blobFadeEnd: number;
  blobMaxValue: number;
  blobOccupancyThreshold: number;

  // 페로몬 필드
  pheromoneFieldRadius: number;
  pheromoneSoftening: number;
  pheromoneMinThreshold: number;
  pheromoneNormalization: number;

  // 먹이
  foodDepositAmount: number;
  foodDepositRadius: number;

  // 에이전트
  agentSensorAngle: number;
  agentSensorDistance: number;
  agentTurnSpeed: number;
  agentMoveSpeed: number;
  agentDepositAmount: number;
  agentDecayFactor: number;
}

// 기본값 (config.ts에서 가져옴)
export const DEFAULT_PARAMS: TunableParams = {
  // 정맥
  veinsMin: VEINS.MIN,
  veinsMax: VEINS.MAX,
  veinsRidgeThreshold: VEINS.RIDGE_THRESHOLD,
  veinsMaxAlpha: VEINS.MAX_ALPHA,

  // 블롭 본체
  blobFadeStart: BLOB_BODY.FADE_START,
  blobFadeEnd: BLOB_BODY.FADE_END,
  blobMaxValue: BLOB_BODY.MAX_VALUE,
  blobOccupancyThreshold: 3.0, // 셰이더 하드코딩 값

  // 페로몬 필드
  pheromoneFieldRadius: PHEROMONE.FIELD_RADIUS,
  pheromoneSoftening: PHEROMONE.SOFTENING,
  pheromoneMinThreshold: PHEROMONE.MIN_THRESHOLD,
  pheromoneNormalization: PHEROMONE.NORMALIZATION,

  // 먹이
  foodDepositAmount: GAME.FOOD_DEPOSIT_AMOUNT,
  foodDepositRadius: GAME.FOOD_DEPOSIT_RADIUS,

  // 에이전트
  agentSensorAngle: AGENT.SENSOR_ANGLE,
  agentSensorDistance: AGENT.SENSOR_DISTANCE,
  agentTurnSpeed: AGENT.TURN_SPEED,
  agentMoveSpeed: AGENT.MOVE_SPEED,
  agentDepositAmount: AGENT.DEPOSIT_AMOUNT,
  agentDecayFactor: AGENT.DECAY_FACTOR,
};

// 파라미터 메타데이터 (min, max, step, label)
export interface ParamMeta {
  min: number;
  max: number;
  step: number;
  label: string;
  category: string;
}

export const PARAM_META: Record<keyof TunableParams, ParamMeta> = {
  // 정맥
  veinsMin: { min: 1, max: 50, step: 1, label: 'Min Trail', category: '정맥' },
  veinsMax: { min: 50, max: 255, step: 5, label: 'Max Trail', category: '정맥' },
  veinsRidgeThreshold: { min: 0.01, max: 1.0, step: 0.01, label: 'Ridge Threshold', category: '정맥' },
  veinsMaxAlpha: { min: 0.1, max: 1, step: 0.05, label: 'Max Alpha', category: '정맥' },

  // 블롭 본체
  blobFadeStart: { min: 1, max: 20, step: 0.5, label: 'Fade Start', category: '본체' },
  blobFadeEnd: { min: 5, max: 50, step: 1, label: 'Fade End', category: '본체' },
  blobMaxValue: { min: 20, max: 200, step: 5, label: 'Max Value', category: '본체' },
  blobOccupancyThreshold: { min: 0.5, max: 10, step: 0.5, label: 'Occupancy Threshold', category: '본체' },

  // 페로몬 필드
  pheromoneFieldRadius: { min: 100, max: 600, step: 20, label: 'Field Radius', category: '페로몬' },
  pheromoneSoftening: { min: 1000, max: 10000, step: 200, label: 'Softening', category: '페로몬' },
  pheromoneMinThreshold: { min: 0.001, max: 0.1, step: 0.005, label: 'Min Threshold', category: '페로몬' },
  pheromoneNormalization: { min: 0.1, max: 2, step: 0.1, label: 'Normalization', category: '페로몬' },

  // 먹이
  foodDepositAmount: { min: 50, max: 500, step: 10, label: 'Deposit Amount', category: '먹이' },
  foodDepositRadius: { min: 20, max: 150, step: 5, label: 'Deposit Radius', category: '먹이' },

  // 에이전트
  agentSensorAngle: { min: 0.1, max: 1.5, step: 0.05, label: 'Sensor Angle', category: '에이전트' },
  agentSensorDistance: { min: 3, max: 20, step: 1, label: 'Sensor Distance', category: '에이전트' },
  agentTurnSpeed: { min: 0.1, max: 1.5, step: 0.05, label: 'Turn Speed', category: '에이전트' },
  agentMoveSpeed: { min: 0.5, max: 3, step: 0.1, label: 'Move Speed', category: '에이전트' },
  agentDepositAmount: { min: 1, max: 20, step: 1, label: 'Deposit Amount', category: '에이전트' },
  agentDecayFactor: { min: 0.9, max: 0.999, step: 0.001, label: 'Decay Factor', category: '에이전트' },
};

interface TuningStore {
  params: TunableParams;
  isOpen: boolean;
  version: number; // 셰이더 재컴파일 트리거

  setParam: <K extends keyof TunableParams>(key: K, value: TunableParams[K]) => void;
  resetParam: (key: keyof TunableParams) => void;
  resetAll: () => void;
  toggle: () => void;
}

export const useTuningStore = create<TuningStore>((set) => ({
  params: { ...DEFAULT_PARAMS },
  isOpen: false,
  version: 0,

  setParam: (key, value) => set((state) => ({
    params: { ...state.params, [key]: value },
    version: state.version + 1,
  })),

  resetParam: (key) => set((state) => ({
    params: { ...state.params, [key]: DEFAULT_PARAMS[key] },
    version: state.version + 1,
  })),

  resetAll: () => set((state) => ({
    params: { ...DEFAULT_PARAMS },
    version: state.version + 1,
  })),

  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
}));
