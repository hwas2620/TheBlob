# Physarum 비주얼 개선 — 구현 계획

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/config.ts` | BACKGROUND 섹션 추가, BLOB_BODY 색상 조정, VEINS 계층화 파라미터 + 맥동 파라미터 추가 |
| `src/hooks/useGameLoop.ts` | clearColor를 config에서 읽도록 변경 |
| `src/index.css` | CSS background 색상 변경 |
| `src/gpu/shaders/glsl/veins.frag.glsl` | 정맥 계층화 + 맥동 진폭 파라미터화 |
| `src/gpu/shaders/veins.ts` | 새 플레이스홀더 치환 추가 |

## 구현 단계

### Step 1: 배경색 + 본체 색상 톤 변경

**config.ts**
- `BACKGROUND` 섹션 추가: `CLEAR_COLOR: { r, g, b }` (어두운 한천색)
- `BLOB_BODY.ACTIVE_BASE` 조정: `(255,240,100)` → 크림~연황색 계열
- `BLOB_BODY.ACTIVE_DARK` 조정: 본체 톤에 맞춰
- `VEINS.ACTIVE_COLOR` 조정: 본체 톤과 통일

**useGameLoop.ts (L769)**
- 하드코딩 `10/255` → `BACKGROUND.CLEAR_COLOR` 참조

**index.css**
- `background-color: #000` → BACKGROUND와 일치하는 색상

verify: 브라우저에서 배경+본체 색감이 "네온" → "자연스러운 한천 위 점균류" 느낌 확인

### Step 2: 정맥 계층화 (주정맥/모세정맥)

**config.ts**
- `VEINS`에 계층화 파라미터 추가:
  - `MAJOR_THRESHOLD`: 주정맥 트레일 값 임계 (예: 40)
  - `MAJOR_ALPHA`: 주정맥 최대 알파 (예: 0.9)
  - `MINOR_ALPHA`: 모세정맥 최대 알파 (예: 0.4)
  - `MAJOR_COLOR`, `MINOR_COLOR`: 계층별 색상

**veins.frag.glsl**
- `densityT` 기준으로 분기:
  - `value >= MAJOR_THRESHOLD` → 주정맥 색상/알파
  - `value < MAJOR_THRESHOLD` → 모세정맥 색상/알파
- `smoothstep`으로 두 계층 간 자연스러운 전환

**veins.ts**
- 새 플레이스홀더 치환 추가 (MAJOR_THRESHOLD, MAJOR_ALPHA, MINOR_ALPHA, 색상 등)

verify: 정맥이 굵은 주정맥(밝고 불투명)과 가는 모세정맥(희미)으로 구분되는지 확인

### Step 3: 맥동 진폭 증대

**config.ts**
- `VEINS`에 맥동 파라미터 추가:
  - `PULSE_MIN`: 맥동 최소 강도 (현재 0.85 → 예: 0.5)
  - `PULSE_MAX`: 맥동 최대 강도 (현재 1.0 유지)

**veins.frag.glsl**
- 하드코딩 `0.85 + 0.15 * sin(...)` → `{{PULSE_MIN}} + ({{PULSE_MAX}} - {{PULSE_MIN}}) * sin(...)`
- 주정맥: 전체 맥동 범위 적용
- 모세정맥: 맥동 범위의 일부만 적용 (예: `mix(1.0, pulseIntensity, 0.3)`)

**veins.ts**
- PULSE_MIN, PULSE_MAX 플레이스홀더 치환 추가

verify: 맥동이 육안으로 확인 가능한 수준인지 확인. 주정맥에서 더 강하게 보이는지 확인

### Step 4: 검증
- `npm run build` 통과
- 브라우저에서 시각 확인 (before/after 스크린샷)

## 구현 순서

Step 1 → Step 2 → Step 3 → Step 4

각 Step은 독립적이므로 Step별로 시각 확인 후 다음 진행.

## 위험 요소

- **색상 튜닝**: 수치만으로 예측 어려움 → 브라우저 확인 필수, 파라미터 반복 조정 예상
- **정맥 계층 임계값**: MAJOR_THRESHOLD 값에 따라 정맥 분포가 크게 달라짐 → 여러 값 시도 필요
- **점막과 정맥 색상 조화**: blob_body 색상과 veins 색상이 서로 어울려야 함
