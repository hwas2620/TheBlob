# Physarum 비주얼 개선 — 구현 계획

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/config.ts` | BACKGROUND 섹션 추가, BLOB_BODY 색상 조정, VEINS 계층화 + 노이즈 억제 파라미터 |
| `src/hooks/useGameLoop.ts` | clearColor를 config에서 읽도록 변경 |
| `src/index.css` | CSS background 색상 변경 |
| `src/gpu/shaders/glsl/veins.frag.glsl` | 정맥 계층화 + 맥동 파라미터화 + 상대적 ridge |
| `src/gpu/shaders/veins.ts` | 새 플레이스홀더 치환 추가 |
| `src/store/gameStore.ts` | loadGame 세이브 데이터 검증 |

## 구현 단계

### Step 1: 배경색 + 본체 색상 톤 변경 ✅

**config.ts**
- `BACKGROUND` 섹션 추가: `CLEAR_COLOR: { r: 15, g: 12, b: 8 }` (어두운 한천색)
- `BLOB_BODY.ACTIVE_BASE`: `(255,240,100)` → `(245,225,140)` 크림 황색
- `BLOB_BODY.ACTIVE_DARK`: `(240,200,60)` → `(200,175,80)` 연갈색

**useGameLoop.ts**
- 하드코딩 `10/255` → `BACKGROUND.CLEAR_COLOR.r/255` 등

**index.css**
- `background-color: #000` → `#0f0c08`

### Step 2: 정맥 계층화 (주정맥/모세정맥) ✅

**config.ts**
- `VEINS.ACTIVE_COLOR` 제거 → `MAJOR_COLOR` + `MINOR_COLOR` 분리
- `MAJOR_THRESHOLD: 40`, `MAJOR_ALPHA: 0.9`, `MINOR_ALPHA: 0.35`
- `MAJOR_COLOR: (0.95, 0.88, 0.55)`, `MINOR_COLOR: (0.88, 0.78, 0.45)`

**veins.frag.glsl**
- `smoothstep(MAJOR_THRESHOLD*0.7, MAJOR_THRESHOLD*1.3, value)`로 계층 전환
- 계층별 색상: `mix(minorColor, majorColor, majorT)`

**veins.ts**
- `ACTIVE_R/G/B` → `MAJOR_R/G/B` + `MINOR_R/G/B` 치환

### Step 3: 맥동 진폭 증대 ✅

**config.ts**
- `PULSE_MIN: 0.5`, `PULSE_MAX: 1.0`

**veins.frag.glsl**
- `0.85 + 0.15 * sin(...)` → `PULSE_MIN + (PULSE_MAX - PULSE_MIN) * (0.5 + 0.5 * sin(...))`
- 주정맥: 전체 맥동 범위, 모세정맥: `mix(1.0, pulseBase, 0.3)` (30% 반영)

### Step 4: 노이즈 억제 (튜닝 중 추가) ✅

**veins.frag.glsl**
- 절대 ridge → 상대적 ridge: `relRidge = ridge / max(value, 1.0)`
- `ridgeStrength = clamp(relRidge * RIDGE_SCALE, 0.0, 1.0)`
- 효과: 고밀도 중앙(value=100)에서 개별 에이전트 노이즈 자동 억제

**config.ts**
- `STEP: 2` → `4`: 샘플링 간격 확대로 수송 채널 스케일만 감지

### Step 5: 세이브 데이터 검증 (튜닝 중 발견) ✅

**gameStore.ts**
- `isValidStage()` 타입가드 추가
- `loadGame()`에서 손상된 stage 데이터 방어

### Step 6: 검증 ✅
- `npm run build` 통과
- 브라우저 시각 확인 (11장 스크린샷 반복 확인)

## 최종 파라미터

| 파라미터 | 이전 값 | 최종 값 | 비고 |
|---------|---------|---------|------|
| CLEAR_COLOR | `(10, 10, 10)` | `(15, 12, 8)` | 따뜻한 한천색 |
| ACTIVE_BASE | `(255, 240, 100)` | `(245, 225, 140)` | 크림 황색 |
| ACTIVE_DARK | `(240, 200, 60)` | `(200, 175, 80)` | 연갈색 |
| VEINS.STEP | 2 | 4 | 수송 채널 스케일 |
| VEINS.MAJOR_COLOR | — | `(0.95, 0.88, 0.55)` | 밝은 크림 |
| VEINS.MINOR_COLOR | — | `(0.88, 0.78, 0.45)` | 본체 근접 톤 |
| VEINS.PULSE_MIN | 0.85 | 0.5 | 넓은 맥동 범위 |
| ridge 검출 | 절대값 | 상대값 (ridge/value) | 노이즈 억제 |

## 위험 요소

- ~~**색상 튜닝**: 수치만으로 예측 어려움~~ → 11장 스크린샷으로 반복 확인 완료
- ~~**정맥 계층 임계값**: MAJOR_THRESHOLD 값에 따라 정맥 분포가 크게 달라짐~~ → 40으로 안정
- **에이전트 노이즈**: 절대 ridge 검출은 에이전트 개별 deposit까지 잡음 → 상대적 ridge + STEP 확대로 해결
