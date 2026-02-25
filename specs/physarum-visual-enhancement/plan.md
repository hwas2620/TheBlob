# Physarum 비주얼 개선 — 구현 계획

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/config.ts` | BACKGROUND, BLOB_BODY, VEINS 색상 + BODY_MAX_ALPHA |
| `src/gpu/shaders/glsl/blob_body.frag.glsl` | BODY_MAX_ALPHA 적용 + 알파 공식 |
| `src/gpu/shaders/blob_body.ts` | BODY_MAX_ALPHA 플레이스홀더 치환 |
| `src/gpu/shaders/glsl/veins.frag.glsl` | 정맥 노이즈 억제 강화 |
| `src/gpu/shaders/veins.ts` | (필요 시) 새 플레이스홀더 |
| `src/index.css` | CSS 배경색 |

## Phase 1: 구조 개선 ✅ (커밋: 882870b)

### Step 1: 배경색 + 본체 색상 톤 변경 ✅
### Step 2: 정맥 계층화 (주정맥/모세정맥) ✅
### Step 3: 맥동 진폭 증대 ✅
### Step 4: 노이즈 억제 ✅
### Step 5: 세이브 데이터 검증 ✅

## Phase 2: 레퍼런스 색상 매칭 (진행 중)

### 물리 모델: 노란 원형질 + 초록 기질 = 올리브 합성

### Step 6: 배경 + 본체 + 정맥 색상 ✅ (구현 완료, 미커밋)

**config.ts**
- `BACKGROUND.CLEAR_COLOR`: `(15,12,8)` → `(8,20,10)` 어두운 초록 (한천)
- `BLOB_BODY.BODY_MAX_ALPHA`: 신규 `0.85`
- `BLOB_BODY.ACTIVE_BASE`: `(245,225,140)` → `(220,200,60)` 밝은 황색
- `BLOB_BODY.ACTIVE_DARK`: `(200,175,80)` → `(160,140,30)` 어두운 황색
- `BLOB_BODY.MEMBRANE_COLOR`: `(100,220,80)` → `(180,170,40)` 연한 황색
- `VEINS.MAJOR_COLOR`: `(0.95,0.88,0.55)` → `(0.95,0.88,0.35)` 밝은 황금
- `VEINS.MINOR_COLOR`: `(0.88,0.78,0.45)` → `(0.80,0.72,0.25)` 중간 황색
- `VEINS.MIN`: 8 → 25, `VEINS.STEP`: 4 → 8, `VEINS.RIDGE_SCALE`: 12 → 3
- `VEINS.MINOR_ALPHA`: 0.35 → 0.15

**blob_body.frag.glsl**
- 본체 알파: `sqrt(densityT) * {{BODY_MAX_ALPHA}}`

**blob_body.ts**
- `BODY_MAX_ALPHA` 플레이스홀더 추가

**index.css**
- `#0f0c08` → `#08140a`

### Step 7: 본체 알파 다이나믹 레인지 확대 ✅

**config.ts**
- `BLOB_BODY.MAX_VALUE`: 60 → 150

**blob_body.frag.glsl**
- 알파: `sqrt(densityT)` → `smoothstep(0.1, 0.5, densityT)` (S커브)
- 색상도 동일 S커브: `mix(dark, base, alphaT)`

### Step 8: 정맥 에이전트 노이즈 제거 ✅

**veins.frag.glsl** — A안 채택 + 추가 개선:
- 입력: 1포인트 → 3x3 블러 (STEP 간격 기준)
- 능선 검출: STEP → STEP×2 범위 이웃 비교 (더 넓은 스케일)
- ridgeStrength: `clamp()` → `smoothstep(0.2, 0.5)` (약한 릿지 제거, 선명한 라인)

### Step 9: 검증 (진행 중)
- [x] `npm run build` 통과
- [ ] 브라우저 시각 확인 (레퍼런스 05~08과 비교)
- 체크포인트:
  - [ ] 중심 불투명 노랑, 의사족 반투명 올리브
  - [ ] 정맥이 깨끗한 노란 라인 (에이전트 패턴 없음)
  - [ ] 배경 어두운 초록

## 파라미터 변경 이력

### Phase 1 (커밋 완료: 882870b)

| 파라미터 | 이전 값 | Phase 1 값 |
|---------|---------|-----------|
| CLEAR_COLOR | `(10, 10, 10)` | `(15, 12, 8)` |
| ACTIVE_BASE | `(255, 240, 100)` | `(245, 225, 140)` |
| ACTIVE_DARK | `(240, 200, 60)` | `(200, 175, 80)` |
| VEINS.STEP | 2 | 4 |
| VEINS.MAJOR_COLOR | — | `(0.95, 0.88, 0.55)` |
| VEINS.MINOR_COLOR | — | `(0.88, 0.78, 0.45)` |
| VEINS.PULSE_MIN | 0.85 | 0.5 |
| ridge 검출 | 절대값 | 상대값 (ridge/value) |

### Phase 2 (진행 중, 미커밋)

| 파라미터 | Phase 1 값 | 현재 값 | 비고 |
|---------|-----------|---------|------|
| CLEAR_COLOR | `(15, 12, 8)` | `(8, 20, 10)` | 초록 기질 |
| ACTIVE_BASE | `(245, 225, 140)` | `(220, 200, 60)` | 황색 원형질 |
| ACTIVE_DARK | `(200, 175, 80)` | `(160, 140, 30)` | 어두운 황색 |
| BODY_MAX_ALPHA | — (1.0) | `0.85` | 반투명 |
| MEMBRANE_COLOR | `(100, 220, 80)` | `(180, 170, 40)` | 황색 |
| MAJOR_COLOR | `(0.95, 0.88, 0.55)` | `(0.95, 0.88, 0.35)` | 황금 |
| MINOR_COLOR | `(0.88, 0.78, 0.45)` | `(0.80, 0.72, 0.25)` | 황색 |
| VEINS.MIN | 8 | 25 | 노이즈 컷오프 |
| VEINS.STEP | 4 | 8 | 넓은 감지 |
| VEINS.RIDGE_SCALE | 12 | 3 | 노이즈 축소 |
| VEINS.MINOR_ALPHA | 0.35 | 0.15 | 모세정맥 약화 |

### Phase 2 추가 변경 (Step 7~8에서 구현)

| 파라미터 | 변경 전 | 변경 후 | 비고 |
|---------|---------|---------|------|
| MAX_VALUE | 60 | 150 | 알파 다이나믹 레인지 확대 |
| 본체 알파 곡선 | sqrt(densityT) | smoothstep(0.1, 0.5, densityT) | S커브: 유령감 제거 |
| 정맥 입력 | 1포인트 | 3x3 블러 | 에이전트 노이즈 평활화 |
| 정맥 능선 범위 | STEP | STEP×2 | 넓은 수송 채널 감지 |
| ridgeStrength | clamp | smoothstep(0.2, 0.5) | 선명한 라인 |

## 위험 요소

- **색상 튜닝**: 수치만으로 예측 어려움 → 브라우저 시각 확인 필수
- **정맥 블러**: 텍스처 샘플 증가 → GPU 성능 확인 필요 (13 샘플은 문제 없을 것)
- **MAX_VALUE 과도 상향**: 본체가 전부 투명해질 수 있음 → 단계적 조정
