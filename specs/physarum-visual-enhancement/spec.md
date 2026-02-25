# Physarum 비주얼 개선 — 리얼리스틱 렌더링

## 비주얼 레퍼런스

`docs/reference/` 참고 — 실물 Physarum 타임랩스/접사/포자화 사진 수록.

## 현재 상태

Jeff Jones 알고리즘은 논문 100% 준수 상태. 렌더링만 개선하면 실제 점균류에 가까워짐.

### 관련 파일
- `src/config.ts` — 모든 렌더링 파라미터
- `src/gpu/shaders/glsl/blob_body.frag.glsl` — 본체 셰이더
- `src/gpu/shaders/blob_body.ts` — 본체 플레이스홀더 치환
- `src/gpu/shaders/glsl/veins.frag.glsl` — 정맥 셰이더
- `src/gpu/shaders/veins.ts` — 정맥 플레이스홀더 치환
- `src/gpu/TrailMapGPU.ts` — 트레일맵 GPU 처리 (미확산 맵 추가)
- `src/gpu/SceneRenderer.ts` — 씬 렌더링 (블렌딩, 텍스처 바인딩)
- `src/simulation/PhysarumSimulation.ts` — 시뮬레이션 루프
- `src/hooks/useGameLoop.ts` — 게임 루프 (렌더러 호출)
- `src/index.css` — CSS 배경색

## Phase 1: 구조 개선 ✅ (커밋 882870b)

정맥 계층화, 맥동 파라미터화, 노이즈 억제. 색상은 크림/황색 중간 단계.

## Phase 2: 레퍼런스 색상 매칭 ✅ (커밋 51fac4b)

### 물리 모델 (핵심 인사이트)
- **본체 원형질** = 노란색 반투명 막
- **기질(agar)** = 어두운 초록/검정
- **올리브그린 외관** = 노란 막이 초록 기질 위에 겹쳐서 생기는 착시
- 배경 초록 + 본체 노란 반투명 = 자연스러운 올리브 합성
- 본체 알파: `smoothstep(0.1, 0.5, densityT) * BODY_MAX_ALPHA` (S커브)

## Phase 3: 정맥 렌더링 개선 (진행 중)

### 문제 진단

현재 정맥이 "구름/안개"처럼 렌더링됨. 레퍼런스에서 정맥은 "촉수 같은 가느다란 선".

**근본 원인** (전문가 토론 결론, `docs/research/` 참조):
1. 트레일맵 확산 4패스 (σ≈1.6px) → 2~5px 정맥이 8~13px로 팽창
2. 정맥 셰이더 추가 3x3 블러 (STEP=8) → 더 퍼뜨림
3. 등방성 능선 검출 (STEP×2=16px) → 선 vs 면 구분 불가
4. 알파 블렌딩 → 정맥이 본체에 묻힘

**핵심 인사이트**: 확산은 화학 신호의 전파이지, 원형질 자체가 아님.
정맥 렌더링은 확산 전 데이터(에이전트 실제 위치)를 사용해야 함.

### 3-1. Additive Blend
- [ ] 정맥 블렌딩: `ONE_MINUS_SRC_ALPHA` → `ONE` (additive)
- [ ] 정맥이 본체 위에 "떠 보이는" 효과
- [ ] MAJOR_ALPHA 0.85→0.4 (additive 보정)
- [ ] 정맥 색상 명도 하향 (포화 방지)

### 3-2. 미확산 트레일맵 분리
- [ ] `TrailMapGPU`에 rawTrailTex + rawTrailFbo 추가
- [ ] `runDeposit()` 후, `runDiffuseDecay()` 전에 현재 상태를 복사
- [ ] box blur 1패스 (σ≈0.8px) 적용: 점 노이즈 제거 필수
- [ ] 정맥 셰이더에 `u_rawTrailMap` uniform으로 전달
- [ ] 시뮬레이션 동역학 영향 없음 (렌더링만 변경)

### 3-3. Hessian Ridge Detection
- [ ] 2차 미분 고유값 기반 능선 검출 (Frangi Filter 계열)
- [ ] 미확산 맵에서 STEP=1~2로 2~5px 선 정밀 검출
- [ ] 선형 구조(ridge)만 추출, 둥근 구조(blob) 자동 제거
- [ ] 텍스처 fetch 9개 (현재 13개보다 적음)

### 정맥 시각적 목표 (레퍼런스 기반)

| 속성 | 목표값 |
|------|--------|
| 주정맥 폭 | 2~4px (1500px 맵 기준) |
| 모세정맥 폭 | 1~2px |
| 경계 전환 거리 | 1~2px 이내 (sharp edge) |
| 밝기 (본체 대비) | 2~4배 밝음 |
| 블렌딩 | additive (본체 위에 떠 보여야 함) |
| 분포 | 핵에서 방사상, Y분기, 위계적 |

## 접근 방식

- Phase 1~2: config.ts 파라미터 + 셰이더 수정만으로 구현
- Phase 3: TrailMapGPU에 미확산 텍스처 추가 (유일한 구조 변경)
- 알고리즘(AgentGPU) 변경 없음
