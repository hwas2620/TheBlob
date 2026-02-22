# 등고선 이중 채널 분리 렌더링 — 구현 계획

> spec: [spec.md](./spec.md)

## 변경 파일 순서

총 6개 파일, 의존 순서대로 실행.

---

### Step 1. `src/config.ts` — FOOD_CONTOUR 설정 추가

**위치**: FOOD 블록 아래 (40행 부근)

```typescript
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
```

---

### Step 2. `src/gpu/shaders/glsl/pheromone_field_trailmap.frag.glsl` — 셰이더 수정

- `uniform sampler2D u_foodMap;` 추가
- A블록: 자기 페로몬 → 녹색 (기존 로직 유지)
- B블록: 먹이 화학물질 → 주황색 (동일 SDF 알고리즘)
- B를 A 위에 알파 합성

**trailMap이 순수 에이전트 페로몬만 포함하므로 trailMask 등 해킹 불필요.**

---

### Step 3. `src/gpu/shaders/pheromone_field_trailmap.ts` — 플레이스홀더 치환

`FOOD_CONTOUR` config → `{{FOOD_*}}` 계열 15개 플레이스홀더 추가.

---

### Step 4. `src/gpu/SceneRenderer.ts` — food 텍스처 바인딩

- `SceneUniforms`에 `foodMap` 추가
- `render()` 시그니처에 `foodTexture` 파라미터 추가
- `renderPass()`에 `foodTexture` 파라미터 + TEXTURE3 바인딩

---

### Step 5. `src/hooks/useGameLoop.ts` + `src/simulation/PhysarumSimulation.ts`

- PhysarumSimulation에 `getCurrentFoodTexture()` 공개 메서드 추가
- useGameLoop에서 `foodTex` 가져와서 `sceneRenderer.render()`에 전달

---

### Step 6. `src/simulation/PhysarumSimulation.ts` — trailMap 순수화

**핵심 변경**: `depositAtPosition()`에서 food→trailMap 주입 제거.

기존:
```typescript
// 먹이 → food 버퍼 + self-trail 버퍼 (둘 다 주입)
this.foodDepositBuffer[idx] = Math.max(...);
this.depositBuffer[idx] = Math.max(...);
```

변경:
```typescript
// 먹이 → food 전용 버퍼만 (trailMap과 완전 분리)
this.foodDepositBuffer[idx] = Math.max(...);
```

update()에서 `hasTrailDeposits` 관련 블록 제거, 멤버 변수 `hasTrailDeposits` 삭제.

**이유**: trailMap에 food가 섞이면 녹색 등고선이 먹이 영역에도 표시되어 색 분리 불가.
에이전트가 먹이에 도착하면 자기 페로몬을 자연스럽게 축적하므로 Jeff Jones 수렴에 문제 없음.

---

## 의존 관계

```
Step 1 (config) ─────┐
                      ├──→ Step 2 (셰이더 GLSL)
                      ├──→ Step 3 (셰이더 TS 치환)
Step 5 (메서드 공개)  ├──→ Step 4 (SceneRenderer)
Step 6 (trailMap 분리)└──→ 렌더링 정확성 보장
```

## 검증 체크리스트

- [x] `npm run build` 통과 (TS 에러 없음)
- [ ] 먹이 없을 때: 녹색 trail 등고선만 표시 (기존과 동일)
- [ ] 먹이 놓았을 때: 주황색 food 등고선 별도 표시
- [ ] 두 등고선 겹침: 주황이 녹색 위에 자연스럽게 합성
- [ ] 디버그 코드 없음
