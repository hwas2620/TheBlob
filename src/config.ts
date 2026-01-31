// ============================================================
// The Blob — 중앙 설정 파일
// 모든 시뮬레이션/렌더링/게임 수치를 한 곳에서 관리
// ============================================================

// ── 맵 ──────────────────────────────────────────────────────
// 토러스 래핑 맵
export const MAP = {
  WIDTH: 1500,
  HEIGHT: 1500,
} as const;

// ── Jeff Jones 에이전트 파라미터 ─────────────────────────────
// "Characteristics of Pattern Formation and Evolution in
//  Approximations of Physarum Transport Networks" (2010)
export const AGENT = {
  COUNT: 100000,           // 파티클 수 (맵 1500² 기준, 밀도 4.4%)
  SENSOR_ANGLE: Math.PI / 8,   // SA = 22.5° (논문)
  SENSOR_DISTANCE: 9,          // SO = 9 px (논문)
  TURN_SPEED: Math.PI / 4,     // RA = 45° (논문)
  MOVE_SPEED: 1,               // SS = 1 px/step (논문 원본)
  DEPOSIT_AMOUNT: 5,           // depT = 5 (논문 원본값)
  DECAY_FACTOR: 0.95,          // 트레일 감쇠 (느리게: 경로 오래 유지)
  DECAY_FACTOR_DORMANT: 0.98,  // 트레일 감쇠 (휴면)
  DIFFUSE_STRENGTH: 1,
  DIFFUSE_PASSES: 1,           // 확산 패스 1회 (논문 원본)
  SPAWN_RADIUS: 20,            // 초기 스폰 반경 (중간: 중심 밀집하되 확장 가능)
} as const;

// ── 에이전트 유인(Attraction) ────────────────────────────────
export const ATTRACTION = {
  RADIUS: 300,             // 어트랙터 감지 범위
  DIRECT_MIN_DIST: 5,     // 직접 유인 최소 거리
  DIRECT_MAX_DIST: 150,   // 직접 유인 최대 거리 (240→150: 탐험 증가)
  STRENGTH: 0.25,          // 유인 강도 계수 (0.35→0.25: 탐험 증가)
  PHEROMONE_INJECT_RADIUS: 180, // 페로몬 주입 반경 (넓은 구배로 원거리 유도)
  // 포화 기반 탐험 (밀집 지역에서 탐험 유도)
  SATURATION_THRESHOLD: 40,  // 이 트레일값 이상이면 "포화" 상태
  SATURATION_EXPLORE_CHANCE: 0.6, // 포화 시 유인 무시 확률 (60%)
} as const;

// ── 에이전트 연결성(Connectivity) ────────────────────────────
export const CONNECTIVITY = {
  ISOLATION_THRESHOLD: 10,    // 이 트레일 값 미만이면 '고립' (적당히)
  SEARCH_DISTANCES: [30],     // 고립 시 탐색 거리 (1개만, 최적화)
  SEARCH_DIRECTIONS: 8,       // GPU 탐색 방향 수 (8방향으로 간소화)
  RECOVERY_TRAIL_MIN: 3,      // 복귀 목표 최소 트레일
  STRENGTH_SEVERE: 0.7,       // curTrail < 2 일 때 복귀 강도
  STRENGTH_MILD: 0.5,         // curTrail >= 2 일 때 복귀 강도
  JITTER_ATTRACTED: 0.03,     // 유인 중 랜덤 지터
  JITTER_FREE: 0.3,           // 자유 이동 시 랜덤 지터 (탐색 강화)
} as const;

// ── GPU 에이전트 텍스처 ──────────────────────────────────────
export const AGENT_TEX = {
  WIDTH: 512,
  HEIGHT: 256,     // 512×256 = 131072 슬롯 (10만 에이전트 수용)
  MAX_ATTRACTORS: 64,
  MIN_AGENTS: 100, // 제거 시 최소 유지 수
} as const;

// ── 블롭 본체 렌더링 ────────────────────────────────────────
export const BLOB_BODY = {
  FADE_START: 2,       // 이 값 이상이면 본체 (저밀도 노이즈 제거)
  FADE_END: 15,        // 페이드 완료 값 (알파 그라데이션 끝)
  DILATE_RADIUS: 3,    // 막 팽창 반경 (px, 3x3 max 샘플링 범위)
  MAX_VALUE: 60,       // 색상 전환 최대값 (실제 트레일 범위에 맞춤)
  // 알파 설정
  ALPHA_BASE: 50,      // 기본 알파
  ALPHA_FADE: 150,     // 페이드 알파 범위
  ALPHA_SMOOTH: 55,    // smooth 계수에 따른 추가 알파
  // 내부 색상 (고밀도 = 매우 밝은 황금) - 명암 대비 강화
  ACTIVE_BASE: { r: 255, g: 240, b: 100 },    // 더 밝고 선명한 황금
  ACTIVE_DARK: { r: 240, g: 200, b: 60 },     // 저밀도도 더 밝게
  // 막(membrane) 색상 — 경계에서 밝은 연두
  MEMBRANE_COLOR: { r: 100, g: 220, b: 80 },  // 더 밝은 초록
  // 휴면 색상 (더 어둡고 대비 강화)
  DORMANT_BASE: { r: 140, g: 120, b: 80 },    // 약간 더 밝게
  DORMANT_DARK: { r: 80, g: 70, b: 40 },      // 더 어둡게
  DORMANT_MEMBRANE: { r: 60, g: 80, b: 40 },
} as const;

// ── 정맥(Vein) 렌더링 ───────────────────────────────────────
export const VEINS = {
  MIN: 20,         // 정맥 표시 최소 트레일 값 (본체 내부만)
  MAX: 120,        // 정맥 표시 최대 트레일 값
  STEP: 2,         // 샘플링 간격 (px)
  MAX_ALPHA: 0.8,  // 최대 투명도
  RIDGE_SCALE: 6.0,  // 능선 강도 스케일 (value - avg 를 확대)
  // 색상 (vec3 형식, 0-1)
  ACTIVE_COLOR: { r: 0.95, g: 0.85, b: 0.3 },    // 밝은 황금색 (정맥 하이라이트)
  DORMANT_COLOR: { r: 0.45, g: 0.38, b: 0.22 },
} as const;

// ── 페로몬 필드 렌더링 ──────────────────────────────────────
export const PHEROMONE = {
  FIELD_RADIUS: 360,
  SOFTENING: 4800,
  MIN_THRESHOLD: 0.02,
  NORMALIZATION: 0.5,       // intensity = total / (total + 이 값)
  SCALE: 8,                 // CPU 다운샘플 스케일
  // 그라데이션 색상 (0-255 스케일) - 더 밝고 선명하게
  COLOR: { r: 80, g: 200, b: 80, a: 200 },
  // 등고선 - 더 밝고 눈에 띄게
  CONTOUR_LEVELS: [0.10, 0.22, 0.34, 0.46, 0.58, 0.70] as readonly number[],
  CONTOUR_COLOR: { r: 150, g: 255, b: 130, a: 0.5 },
  CONTOUR_LINE_WIDTH: 1.2,       // CPU 렌더링용 선 두께
  CONTOUR_LINE_WIDTH_PX: 1.5,   // GPU 셰이더용 등고선 두께 (픽셀 단위)
} as const;

// ── 큐빅 글로우 렌더링 ──────────────────────────────────────
export const CUBIC_GLOW = {
  BLOCK_SIZE: 20,            // 블록 크기 (px)
  SAMPLE_STEP: 4,            // 블록 내 샘플 간격
  THRESHOLD: 30,             // 이 밀도 이상만 글로우
  INTENSITY_RANGE: 100,      // 강도 스케일 범위
  ALPHA_MULTIPLIER: 0.3,
  COLOR: { r: 1.0, g: 0.863, b: 0.196 }, // 황금빛 (255, 220, 50)
} as const;

// ── 핵(Nucleus) 렌더링 ──────────────────────────────────────
export const NUCLEUS = {
  BASE_RADIUS: 20,
  PULSE_AMPLITUDE: 3,
  SHAPE_POINTS: 10,
  SHAPE_VARIATION: 0.1,
  HIGHLIGHT_OFFSET: 0.3,    // 하이라이트 위치 비율
  HIGHLIGHT_SIZE: 0.25,     // 하이라이트 크기 비율
} as const;

// ── 미니맵 ───────────────────────────────────────────────────
export const MINIMAP = {
  DENSITY_THRESHOLD: 2,
  INTENSITY_NORM: 100,
  BLOB_COLOR: { r: 255, g: 230, b: 80 },  // 밝은 영역 (더 밝게)
  BLOB_BASE: { r: 100, g: 80, b: 20 },    // 오프셋 (더 밝게)
  EMPTY_COLOR: { r: 10, g: 26, b: 10, a: 200 }, // 배경색과 일치
} as const;

// ── 줌 ───────────────────────────────────────────────────────
export const ZOOM = {
  MIN: 0.25,     // 최소 0.25배까지 축소 (전체 맵 보기)
  MAX: 8.0,      // 최대 8배까지 확대 (세밀한 관찰)
  FACTOR: 1.15,  // 한 스크롤당 줌 배율
} as const;

// ── 게임 메카닉 ──────────────────────────────────────────────
export const GAME = {
  DENSITY_THRESHOLD: 30,     // 파티클 밀도 연결 기준
  DENSITY_GLOW_NORM: 50,     // glowIntensity 정규화
  NUTRIENT_ABSORB_RATE: 0.05, // 영양분 초당 흡수량 (10배 느리게)
  AGENT_SPAWN_CHANCE: 30,    // 흡수량당 에이전트 추가 수 (absorb * 이 값)
  NUTRIENT_MIN_RADIUS: 80,   // 핵에서 최소 스폰 거리
  // 티어별 수치
  TIER_DISTRIBUTION: [0.6, 0.9] as readonly number[], // 소<0.6, 중<0.9, 대
  TIER_NUTRIENT_MULT: [0.5, 1.5, 4] as readonly number[],
  TIER_ATP_BONUS: [1, 1.5, 3] as readonly number[],
  TIER_SMELL_STRENGTH: [0.7, 1.0, 1.8] as readonly number[],
  TIER_BASE_SIZE: [4, 7, 12] as readonly number[],
  MAX_DELTA_TIME: 0.1,      // 최대 deltaTime 클램프 (초)
} as const;

// ── 물 이펙트 ────────────────────────────────────────────────
export const WATER_EFFECT = {
  DROP_COUNT: 12,
  DROP_SPEED_MIN: 30,
  DROP_SPEED_RANGE: 60,
  DROP_GRAVITY_OFFSET: -20,
  DROP_SIZE_MIN: 2,
  DROP_SIZE_RANGE: 4,
  DROP_INITIAL_ALPHA: 0.8,
  DROP_GRAVITY: 150,
  DROP_ALPHA_DECAY: 1.5,
  RIPPLE_INITIAL_RADIUS: 5,
  RIPPLE_MAX_RADIUS_MIN: 50,
  RIPPLE_MAX_RADIUS_RANGE: 30,
  RIPPLE_INITIAL_ALPHA: 0.6,
  RIPPLE_EXPANSION_RATE: 80,
  RIPPLE_ALPHA_DECAY: 1.2,
  SECONDARY_DELAY: 100,      // ms
  SECONDARY_MAX_RADIUS_MIN: 30,
  SECONDARY_MAX_RADIUS_RANGE: 20,
  SECONDARY_ALPHA: 0.4,
} as const;

// ── 포자화 ───────────────────────────────────────────────────
export const SPORULATION = {
  RETRACT_BASE_SPEED: 0.05,
  RETRACT_ACCEL: 0.02,
  RETRACT_DURATION: 2,         // 초
  FORM_RETRACT_STRENGTH: 0.1,
  FORM_DURATION: 1.5,          // 초
  SPORANGIUM_COUNT_MIN: 3,
  SPORANGIUM_COUNT_RANGE: 3,
  SPORANGIUM_DIST_MIN: 30,
  SPORANGIUM_DIST_RANGE: 20,
  SPORANGIUM_SIZE_MIN: 15,
  SPORANGIUM_SIZE_RANGE: 10,
  SPORANGIUM_FADE_IN: 2,
  SPORANGIUM_FADE_OUT: 3,
  SPORE_FRICTION: 0.97,
  SPORE_BOB_RATE: 3,
  SPORE_ALPHA_DECAY: 0.15,
  SPORE_SIZE_MIN: 4,           // 포자 최소 크기
  SPORE_SIZE_RANGE: 4,         // 포자 크기 범위
  SPORE_MAX_COUNT: 50,         // 포자 최대 개수
  SPORE_BOB_OFFSET: 3,         // 포자 떠다니기 오프셋
} as const;

// ── 조각(Fragment) ───────────────────────────────────────────
export const FRAGMENT = {
  MAX_COUNT: 12,               // 최대 조각 개수
  DISTANCE_MIN: 100,           // 배치 최소 거리
  DISTANCE_RANGE: 150,         // 배치 거리 범위
  COLLECTION_RANGE: 15,        // 수집 범위
  MERGE_RANGE: 20,             // 병합 범위
  GENETICS_RATIO: 0.1,         // 조각당 유전자 포인트 비율 (조각수 * 0.1)
} as const;

// ── UI 설정 ──────────────────────────────────────────────────
export const UI = {
  // 캔버스
  CANVAS_DEFAULT_WIDTH: 800,
  CANVAS_DEFAULT_HEIGHT: 600,

  // 미니맵
  MINIMAP_SIZE: 150,
  MINIMAP_UPDATE_INTERVAL: 500,  // ms

  // 토스트
  TOAST_DURATION: 3000,          // ms
  TOAST_FADE_OUT: 300,           // ms

  // 게임 초기값
  INITIAL_MOISTURE: 80,
  MAX_MOISTURE: 100,
  INITIAL_ATP: 30,
  AUTO_WATER_THRESHOLD: 30,      // 자동 급수 활성화 임계값

  // 오프라인 수익
  OFFLINE_MAX_HOURS: 24,         // 오프라인 수익 최대 시간 (시간)

  // 유전자 부스트
  GENETICS_BIOMASS_BOOST: 5,
  GENETICS_MOISTURE_BOOST: 10,
  GENETICS_ATP_BOOST: 0.1,       // 10%

  // 물 이펙트
  WATER_RIPPLE_THICKNESS: 2,
  WATER_RIPPLE_SECONDARY_SCALE: 0.6,
  WATER_DROP_SHADOW_BLUR: 5,
  WATER_EFFECT_THRESHOLD: 20,

  // 기타
  DRAG_THRESHOLD: 5,             // 드래그 감지 최소 거리
  SIMULATION_STEPS: 1,           // 시뮬레이션 업데이트 스텝 수 (느린 시간 스케일)
  DENSITY_CHECK_RADIUS: 25,      // 파티클 밀도 체크 반경
  SPORANGIUM_RENDER_MARGIN: 30,  // 포자낭 렌더링 마진
} as const;
