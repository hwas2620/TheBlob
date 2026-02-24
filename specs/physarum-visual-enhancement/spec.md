# Physarum 비주얼 개선 — 리얼리스틱 색상/정맥/맥동

## 현재 상태

Jeff Jones 알고리즘은 논문 100% 준수 상태. 렌더링만 개선하면 실제 점균류에 가까워짐.

### 관련 파일
- `src/config.ts` — 모든 렌더링 파라미터
- `src/gpu/shaders/glsl/blob_body.frag.glsl` — 본체 셰이더
- `src/gpu/shaders/glsl/veins.frag.glsl` — 정맥 셰이더
- `src/gpu/shaders/veins.ts` — 정맥 플레이스홀더 치환
- `src/hooks/useGameLoop.ts` — clearColor 설정
- `src/index.css` — CSS 배경색
- `src/store/gameStore.ts` — loadGame 검증

## 문제 정의

1. **배경+색상 톤**: 현재 황금색 + 검정 배경은 "네온 게임" 느낌. 실제 Physarum은 크림~연황색 본체 + 어두운 한천(agar) 배경
2. **정맥 단일 레이어**: 모든 정맥이 동일 색상/두께. 실제 Physarum은 주정맥(굵고 밝음)과 모세정맥(가늘고 희미)이 뚜렷이 구분됨
3. **맥동 미약**: 15% 변동은 거의 인지 불가. 실제 Physarum의 원형질 유동(cytoplasmic streaming)은 육안으로 보일 정도로 뚜렷

## 요구사항

### 1. 배경색 + 색상 톤 (임팩트 ⭐⭐⭐⭐⭐)
- [x] clearColor를 어두운 한천색으로 변경 → `rgb(15, 12, 8)`
- [x] 본체 색상을 크림~연황색 계열로 조정 → `ACTIVE_BASE: (245, 225, 140)`, `ACTIVE_DARK: (200, 175, 80)`
- [x] 정맥 색상도 본체 톤에 맞춰 조정 → MAJOR_COLOR/MINOR_COLOR 분리

### 2. 정맥 계층화 (임팩트 ⭐⭐⭐⭐)
- [x] 트레일 값 기준으로 주정맥/모세정맥 2단계 분리 → `MAJOR_THRESHOLD: 40`
- [x] 주정맥: 높은 트레일 값 → 더 밝고 불투명 (`MAJOR_ALPHA: 0.9`)
- [x] 모세정맥: 낮은 트레일 값 → 가늘고 희미 (`MINOR_ALPHA: 0.35`)
- [x] 두 계층 간 자연스러운 그라데이션 → `smoothstep` 전환

### 3. 맥동 진폭 증대 (임팩트 ⭐⭐⭐)
- [x] 맥동 범위 확대: 85~100% → 50~100% (`PULSE_MIN: 0.5`)
- [x] 주정맥에서 더 강한 맥동, 모세정맥에서 약한 맥동 (30% 반영)

## 튜닝 중 발견된 문제 및 해결

### 에이전트 노이즈 깜박임
- **문제**: 절대 ridge 검출 (`ridge * RIDGE_SCALE`)이 개별 에이전트 deposit까지 감지 → 고밀도 중앙부에서 알갱이 깜박임
- **원인**: ridge=0.5, value=100 → `clamp(0.5 * 12, 0, 1) = 1.0` (풀 강도)
- **해결**: 상대적 ridge (`ridge / value * RIDGE_SCALE`) → 같은 조건에서 `clamp(0.005 * 12, 0, 1) = 0.06` (거의 안 보임)

### 수송 채널 스케일
- **문제**: `STEP: 2` (±2px 비교)는 에이전트 1개의 deposit(1px)도 ridge로 감지
- **비유**: 헤모글로빈 개별이 보이면 안 됨 → 혈류(수송 채널)만 보여야 함
- **해결**: `STEP: 4` (±4px 비교)로 넓혀서 수송 네트워크 채널만 감지

### StatsPanel null 에러
- **문제**: localStorage 세이브 데이터의 stage 필드 손상 → `formatNumber(null)` 크래시
- **해결**: `loadGame()`에서 `isValidStage()` 검증 추가 → 손상 시 `createInitialStage()` 재생성

## 접근 방식

모든 변경은 config.ts 파라미터 + 셰이더 수정만으로 구현.
알고리즘(AgentGPU, TrailMapGPU) 변경 없음.

| 항목 | 수정 파일 | 방식 |
|------|-----------|------|
| 배경색 | config.ts, useGameLoop.ts, index.css | clearColor + CSS 값 변경 |
| 본체 색상 | config.ts | ACTIVE_BASE/DARK 값 조정 |
| 정맥 계층화 | config.ts, veins.frag.glsl, veins.ts | smoothstep 분기 + 색상/알파 차등 |
| 맥동 증대 | config.ts, veins.frag.glsl | pulseIntensity 범위 파라미터화 |
| 노이즈 억제 | veins.frag.glsl, config.ts | 상대적 ridge + STEP 증가 |
| 세이브 검증 | gameStore.ts | isValidStage 타입가드 |
