// The Blob - Life Cycle Idle Game Types

export interface Vector2 {
  x: number;
  y: number;
}

// 블롭 상태
export type BlobState = 'active' | 'dormant' | 'sporulating';

// 게임 페이즈
export type GamePhase = 'growing' | 'sporeCollection' | 'sporulating';

// 촉수 (Tendril)
export interface Tendril {
  id: string;
  points: Vector2[];
  thickness: number;
  alpha: number;
  growing: boolean;
  connectedToNutrient: boolean;
  targetNutrient: Nutrient | null;
  age: number;
  direction: number;
}

// 영양분 (오트밀)
export interface Nutrient {
  id: string;
  position: Vector2;
  value: number;
  maxValue: number;
  harvested: boolean;
  connected: boolean;
  glowIntensity: number;
  tier: 1 | 2 | 3; // 1=소, 2=중, 3=대
}

// 포자 (Spore)
export interface Spore {
  id: string;
  position: Vector2;
  velocity: Vector2;
  collected: boolean;
  size: number;
  alpha: number;
  bobPhase: number;
}

// 물방울 파티클
export interface WaterDrop {
  id: string;
  position: Vector2;
  velocity: Vector2;
  size: number;
  alpha: number;
  age: number;
}

// 물방울 링 (퍼지는 원)
export interface WaterRipple {
  id: string;
  position: Vector2;
  radius: number;
  maxRadius: number;
  alpha: number;
}

// 블롭 조각 (스테이지 시작 시)
export interface BlobFragment {
  id: string;
  position: Vector2;
  size: number;
  merged: boolean;
  pulsePhase: number;
}

// 핵 (Nucleus)
export interface Nucleus {
  position: Vector2;
  radius: number;
  pulsePhase: number;
}

// 업그레이드 종류
export interface Upgrades {
  moistureRetention: number;   // 수분 유지력 (감소 속도 감소)
  expansionSpeed: number;      // 확장 속도
  digestiveEnzyme: number;     // 분해 효소 (영양분 흡수 속도)
  autoWatering: number;        // 자동 급수 (0이면 비활성화)
  sporeQuality: number;        // 포자 품질 (다음 스테이지 보너스)
}

// 스테이지 정보
export interface StageInfo {
  stageNumber: number;
  totalNutrients: number;
  remainingNutrients: number;
  nutrientPositions: Vector2[];
}

// 유전 포인트 (환생 보너스)
export interface GeneticBonus {
  points: number;
  permanentBiomassBoost: number;
  permanentMoistureBoost: number;
  permanentATPBoost: number;
}

// 게임 상태
export interface GameState {
  // 핵심 자원
  moisture: number;           // 수분 (0-100)
  maxMoisture: number;
  biomass: number;            // 질량
  atp: number;                // 에너지

  // 스테이지 시스템
  stage: StageInfo;
  gamePhase: GamePhase;
  blobState: BlobState;

  // 유전 시스템
  genetics: GeneticBonus;
  totalSporulations: number;

  // 게임 오브젝트
  nucleus: Nucleus;
  tendrils: Tendril[];
  nutrients: Nutrient[];
  spores: Spore[];
  fragments: BlobFragment[];

  // 업그레이드
  upgrades: Upgrades;

  // 메타
  lastSaveTime: number;
  gameTime: number;
  lastWaterTime: number;
}

// 업그레이드 비용
export const UPGRADE_COSTS: Record<keyof Upgrades, number[]> = {
  moistureRetention: [20, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800],
  expansionSpeed: [15, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240],
  digestiveEnzyme: [25, 60, 120, 240, 480, 960, 1920, 3840, 7680, 15360],
  autoWatering: [100, 300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 76800],
  sporeQuality: [50, 150, 300, 600, 1200, 2400, 4800, 9600, 19200, 38400],
};

export const UPGRADE_MAX_LEVEL = 10;

// 게임 설정
export const GAME_CONFIG = {
  // 수분 시스템
  BASE_MOISTURE_DECAY: 0.5,      // 초당 수분 감소량
  WATER_AMOUNT: 30,              // 물 주기 당 수분 회복량
  DORMANT_THRESHOLD: 5,          // 휴면 진입 수분 임계값

  // 성장 시스템
  BASE_EXPANSION_SPEED: 0.4,
  BASE_NUTRIENT_ABSORPTION: 0.2,
  BIOMASS_PER_NUTRIENT: 1,
  ATP_PER_NUTRIENT: 0.5,

  // 스테이지 시스템
  BASE_STAGE_NUTRIENTS: 100,
  NUTRIENTS_PER_STAGE_INCREASE: 50,
  NUTRIENTS_COUNT_BASE: 25,

  // 포자 시스템
  SPORES_PER_BIOMASS: 0.5,
  GENE_POINTS_PER_SPORE: 0.1,
  MIN_BIOMASS_FOR_SPORULATION: 50,

  // 기타
  MAX_TENDRILS: 40,
  NUTRIENT_DETECTION_RADIUS: 35,
  OFFLINE_ATP_RATE: 0.05,
  AUTO_SAVE_INTERVAL: 30000,
};
