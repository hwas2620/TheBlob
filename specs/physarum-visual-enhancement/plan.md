# Physarum 비주얼 개선 — 구현 계획

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/gpu/SceneRenderer.ts` | 정맥 additive blend + rawTrailMap 바인딩 |
| `src/gpu/TrailMapGPU.ts` | 미확산 텍스처/FBO + captureRawTrail() |
| `src/gpu/shaders/glsl/veins.frag.glsl` | Hessian ridge detection 전면 재작성 |
| `src/gpu/shaders/veins.ts` | 신규 플레이스홀더 치환 |
| `src/simulation/PhysarumSimulation.ts` | 미확산 캡처 호출 + 접근자 |
| `src/hooks/useGameLoop.ts` | rawTrailTexture 전달 |
| `src/config.ts` | VEINS 파라미터 재구성 |

## Phase 1: 구조 개선 ✅ (커밋 882870b)
## Phase 2: 색상 매칭 ✅ (커밋 51fac4b)

## Phase 3: 정맥 렌더링 개선 ✅ (커밋 622de50)

### Step 1: Additive Blend 전환

**SceneRenderer.ts** 271행
- 정맥 블렌딩: `ONE_MINUS_SRC_ALPHA` → `ONE`

**config.ts** VEINS 파라미터 (additive 보정)
- `MAJOR_ALPHA`: 0.85 → 0.4
- `MINOR_ALPHA`: 0.15 → 0.08
- `MAJOR_COLOR`: (0.95,0.88,0.35) → (0.6,0.5,0.2) 명도 하향
- `MINOR_COLOR`: (0.80,0.72,0.25) → (0.45,0.38,0.15)

### Step 2: 미확산 트레일맵 분리

**TrailMapGPU.ts**
- `rawTrailTex` + `rawTrailFbo` 추가 (R32F, 1500×1500)
- `captureRawTrail()`: 현재 트레일 → rawTrail에 blit
- box blur 1패스 적용 (기존 diffuseDecay 셰이더 재사용, decay=1.0)
- `getCurrentRawTrailTexture()` 접근자

타이밍 (PhysarumSimulation.ts GPU 경로):
```
agentGPU.runDeposit()     // 에이전트 deposit → trail FBO
★ gpu.captureRawTrail()    // 확산 전 상태 캡처 + 1패스 블러
gpu.runDiffuseDecay(4)     // 확산 + 감쇠 (기존)
```

**SceneRenderer.ts**
- `render()` 파라미터에 `rawTrailTexture` 추가
- 정맥 패스에서 TEXTURE1에 rawTrailMap 바인딩
- `veinsUniforms`에 `rawTrailMap` 추가

**useGameLoop.ts**
- `simulation.getCurrentRawTrailTexture()` 호출 → 렌더러 전달

### Step 3: Hessian Ridge Detection

**veins.frag.glsl** 전면 재작성:
- `u_rawTrailMap`에서 Hessian 2차 미분 계산 (h=1px)
- 9 texture fetches (center + 상하좌우 4 + 대각 4)
- 고유값: `lambda2 = 0.5*trace - sqrt(discriminant)`
- `ridgeness = max(-lambda2, 0.0)` (직접 사용, 감수 반영)
- 정규화: `ridgeness / max(center, 1.0)`
- 강도: `smoothstep(THRESHOLD, SATURATE, normalizedRidgeness)`
- 계층화, 맥동, 색상은 기존 구조 유지

**config.ts** VEINS 재구성:
- `STEP` 제거
- `HESSIAN_STEP`: 1 (샘플 간격 px)
- `RIDGE_THRESHOLD`: 0.1 (ridgeness 최소)
- `RIDGE_SATURATE`: 0.3 (ridgeness 포화)
- 나머지 (MAJOR_THRESHOLD, PULSE, 색상 등) 유지

**veins.ts**
- 신규 플레이스홀더: HESSIAN_STEP, RIDGE_THRESHOLD, RIDGE_SATURATE

### Step 4: 검증
- [ ] `npm run build` 통과
- [ ] 브라우저 시각 확인
  - [ ] 정맥이 가느다란 선 (구름 아님)
  - [ ] 경계 날카로움
  - [ ] 본체 위에 밝게 떠 보임
  - [ ] 포화(white-out) 없음
  - [ ] 시뮬레이션 동역학 영향 없음

## Phase 4: 파라미터 튜닝 (진행 중)

### Step 1: config.ts VEINS 파라미터 조정

| 파라미터 | 변경 |
|---------|------|
| `RIDGE_THRESHOLD` | 0.1 → 0.02 |
| `RIDGE_SATURATE` | 0.3 → 0.10 |
| `MAJOR_ALPHA` | 0.4 → 0.65 |
| `HESSIAN_STEP` | 1 → 2 |
| `VEIN_MIN` (= MIN) | 25 → 35 |

### Step 2: 검증
- [ ] `npm run build` 통과
- [ ] 브라우저 시각 확인
  - [ ] 정맥 강도 충분 (본체 대비 눈에 띔)
  - [ ] 경계 반짝임 감소/제거
  - [ ] 포화(white-out) 없음

## 위험 요소

- **Hessian 파라미터**: THRESHOLD/SATURATE 수치를 브라우저에서 반복 튜닝 필요
- **점 노이즈**: box blur 1패스 부족 시 2패스로 확대
- **Additive 포화**: 정맥 색상/alpha를 충분히 낮춰야 함
- **captureRawTrail 타이밍**: deposit 후, diffuse 전 필수
