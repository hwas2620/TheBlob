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
  DECAY_FACTOR: 0.97,          // 트레일 감쇠 (가산 블렌딩 기준: 블롭 정상상태 ~133, 먹이 ~500 → 3.75배 차이)
  DECAY_FACTOR_DORMANT: 0.995, // 트레일 감쇠 (휴면: 거의 유지)
  DIFFUSE_STRENGTH: 1,
  DIFFUSE_PASSES: 4,           // 확산 패스 4회 (격자 패턴 방지: lane/gap 구조를 충분히 blur)
  MAX_TRAIL: 500,              // 트레일 값 상한 (가산 블렌딩으로 축적 허용, 먹이 신호 침투)
  SPAWN_RADIUS: 100,           // 초기 스폰 반경 (밀도 ≈ 3.2/셀, 임계값 4.4 이하)
  OCCUPANCY_MULT: 500,         // 점유 임계값 높여서 격자 패턴 제거 (논문의 "one particle per cell"이 격자 원인)
} as const;

// ── 먹이 화학주성(Food Chemotaxis) ────────────────────────────
// 자기 트레일과 분리된 먹이 전용 채널
export const FOOD = {
  DECAY_FACTOR: 0.998,      // 매우 느린 감쇠 → 장거리 그래디언트 유지
  DIFFUSE_PASSES: 4,        // 넓은 확산
  MAX_TRAIL: 1000,          // 높은 상한 (먹이원은 강력)
  CHEMOTAXIS_WEIGHT: 2.0,   // Jeff Jones 센서 가산 가중치 (극외곽만, 강하게: 둥지 형성)
  SENSOR_MULT: 5.0,         // 먹이 센서 거리 배율 (기본 9px × 5 = ~45px)
} as const;

// ── 먹이 등고선 렌더링 ────────────────────────────────────────
// 먹이 채널(foodMap) 전용 등고선 색상/레벨 (자기 페로몬과 분리)
export const FOOD_CONTOUR = {
  MIN_THRESHOLD: 1.0,
  MAX_VALUE: 500,
  LOW_COLOR: { r: 120, g: 60, b: 0 },
  HIGH_COLOR: { r: 255, g: 160, b: 30 },
  BASE_ALPHA: 0.25,
  LINE_WIDTH: 2.0,
  CONTOUR_COLOR: { r: 255, g: 180, b: 50 },
  CONTOUR_ALPHA: 0.7,
  LEVELS: [0.05, 0.15, 0.3, 0.5, 0.7] as readonly number[],
} as const;

// ── 에이전트 유인(Attraction) ────────────────────────────────
// 순수 Jeff Jones: 직접 유인 없음, 페로몬으로만 간접 유도
export const ATTRACTION = {
  RADIUS: 300,             // 어트랙터 감지 범위 (게임 로직용)
  DIRECT_MIN_DIST: 5,     // (미사용 - 순수 Jeff Jones)
  DIRECT_MAX_DIST: 150,   // (미사용 - 순수 Jeff Jones)
  STRENGTH: 0.25,          // (미사용 - 순수 Jeff Jones)
  // 페로몬 주입: 넓은 범위 + 확산으로 구배 확장
  PHEROMONE_INJECT_RADIUS: 80, // 페로몬 주입 반경 (넓게: 원거리 유인)
  PHEROMONE_INJECT_AMOUNT: 200, // 페로몬 주입량 (낮게: 확산 후 자연스러운 구배)
  // (미사용)
  SATURATION_THRESHOLD: 40,
  SATURATION_EXPLORE_CHANCE: 0.6,
} as const;

// ── 에이전트 연결성(Connectivity) + 탐색 ──────────────────────
export const CONNECTIVITY = {
  ISOLATION_THRESHOLD: 1,     // 이 트레일 값 미만이면 '고립' (1: 의사족 탐험자 보호, 완전 빈 공간에서만 복귀)
  SEARCH_DISTANCES: [30],     // 고립 시 탐색 거리
  SEARCH_DIRECTIONS: 8,       // GPU 탐색 방향 수
  RECOVERY_TRAIL_MIN: 3,      // 복귀 목표 최소 트레일
  STRENGTH_SEVERE: 0.7,       // curTrail < 2 일 때 복귀 강도
  STRENGTH_MILD: 0.5,         // curTrail >= 2 일 때 복귀 강도
  JITTER_ATTRACTED: 0.03,     // 유인 중 랜덤 지터
  JITTER_FREE: 0.3,           // 자유 이동 시 랜덤 지터 (탐색 강화)
  FRONTIER_JITTER: 0.4,       // 프론티어(경계) 지터 강도 (rad, 강화: 경계 에이전트 적극 탐험)
  LONG_SENSOR_DIST: 150,      // 장거리 먹이 감지 거리 (px, 경계에서 먼 먹이 감지)
} as const;

// ── GPU 에이전트 텍스처 ──────────────────────────────────────
export const AGENT_TEX = {
  WIDTH: 512,
  HEIGHT: 256,     // 512×256 = 131072 슬롯 (10만 에이전트 수용)
  MAX_ATTRACTORS: 64,
  MIN_AGENTS: 100, // 제거 시 최소 유지 수
} as const;

// ── 배경 ─────────────────────────────────────────────────────
export const BACKGROUND = {
  // 어두운 초록 — 한천(agar) 기질 색 (본체 노란 막이 위에 겹치면 올리브그린)
  CLEAR_COLOR: { r: 8, g: 20, b: 10 },
} as const;

// ── 블롭 본체 렌더링 ────────────────────────────────────────
export const BLOB_BODY = {
  FADE_START: 2,       // 본체 시작 임계값
  NOISE_FLOOR: 0.3,    // 이 값 미만은 완전 투명 (낮게 유지 → 내부 채움. 높이면 내부 검은 구멍 발생)
  MEMBRANE_ALPHA: 0.15, // 점막 영역 최대 알파 (0.06=6%는 안 보임, 0.25=25%는 넓어서 과함, 0.15=15%가 희미하게 보임)
  FADE_END: 15,        // 페이드 완료 값 (알파 그라데이션 끝)
  DILATE_RADIUS: 3,    // 막 팽창 반경 (px, 3x3 max 샘플링 범위)
  MAX_VALUE: 150,      // 색상 전환 최대값 (트레일 실분포: 중심~130, 의사족~30 → 넓은 알파 레인지)
  // 알파 설정
  ALPHA_BASE: 50,      // 기본 알파
  ALPHA_FADE: 150,     // 페이드 알파 범위
  ALPHA_SMOOTH: 55,    // smooth 계수에 따른 추가 알파
  BODY_MAX_ALPHA: 0.85,  // 본체 최대 알파 (고밀도=거의 불투명, 저밀도=반투명→초록 비침)
  // 내부 색상 — 노란색 원형질 (반투명으로 초록 바닥과 합쳐져 올리브로 보임)
  ACTIVE_BASE: { r: 220, g: 200, b: 60 },     // 고밀도: 밝은 황색
  ACTIVE_DARK: { r: 160, g: 140, b: 30 },     // 저밀도: 어두운 황색
  // 막(membrane) 색상 — 경계 희미한 노란색
  MEMBRANE_COLOR: { r: 180, g: 170, b: 40 },  // 연한 황색
  // 휴면 색상 (더 어둡고 대비 강화)
  DORMANT_BASE: { r: 140, g: 120, b: 80 },    // 약간 더 밝게
  DORMANT_DARK: { r: 80, g: 70, b: 40 },      // 더 어둡게
  DORMANT_MEMBRANE: { r: 60, g: 80, b: 40 },
} as const;

// ── 정맥(Vein) 렌더링 ───────────────────────────────────────
export const VEINS = {
  MIN: 25,         // 정맥 표시 최소 트레일 값 (확산 맵 기준, 본체 마스킹)
  MAX: 120,        // 정맥 표시 최대 트레일 값
  HESSIAN_STEP: 1, // Hessian 샘플 간격 (px, 2~5px 정맥에 최적)
  MAX_ALPHA: 0.8,  // 최대 투명도
  RIDGE_THRESHOLD: 0.1,  // Hessian ridgeness 최소 임계값 (정규화된 값)
  RIDGE_SATURATE: 0.3,   // Hessian ridgeness 포화 값
  // 계층화 — 주정맥/모세정맥 분리
  MAJOR_THRESHOLD: 40,   // 이 값 이상 = 주정맥
  MAJOR_ALPHA: 0.4,      // 주정맥 알파 (additive 보정: 낮춰야 포화 방지)
  MINOR_ALPHA: 0.08,     // 모세정맥: 거의 안 보이게 (노이즈 원인)
  // 맥동 파라미터
  PULSE_MIN: 0.5,        // 맥동 최소 강도 (기존 0.85 → 더 넓은 범위)
  PULSE_MAX: 1.0,        // 맥동 최대 강도
  // 색상 (vec3 형식, 0-1) — additive이므로 명도 하향 (포화 방지)
  MAJOR_COLOR: { r: 0.6, g: 0.5, b: 0.2 },        // 주정맥: additive 합산 시 밝은 노랑
  MINOR_COLOR: { r: 0.45, g: 0.38, b: 0.15 },     // 모세정맥: additive 합산 시 중간 황색
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
  // 먹이 페로몬 분비 (에이전트가 먹이를 감지할 수 있게)
  FOOD_DEPOSIT_AMOUNT: 150,  // 먹이가 뿌리는 페로몬 양 (에이전트 5의 30배)
  FOOD_DEPOSIT_RADIUS: 80,   // 먹이 페로몬 확산 반경 (넓게)
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
