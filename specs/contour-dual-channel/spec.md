# 등고선 이중 채널 분리 렌더링

## 문제

현재 등고선(페로몬 필드)은 **u_trailMap 하나만** 샘플링하여 녹색 등고선으로 표시.
커밋 `cb94f42`에서 먹이 전용 채널(`foodMap`)을 추가했으나,
**foodMap의 등고선은 렌더링되지 않고 있음.**

사용자는 페로몬과 먹이의 등고선을 **색을 달리하여 별개로** 볼 수 있기를 원함.

## 현재 상태

### 데이터 채널
| 채널 | 텍스처 | 용도 | 등고선 렌더링 |
|------|--------|------|---------------|
| 자기 페로몬 | `trailTexA/B` (R32F) | Jeff Jones 에이전트 분비물 | O (녹색) |
| 먹이 화학물질 | `foodTexA/B` (R32F) | 먹이원 그래디언트 | X (미구현) |

### 렌더링 파이프라인
```
SceneRenderer.render()
  1. 페로몬 등고선 ← u_trailMap만 사용
     - inverse-square: pheromone_field.frag.glsl (어트랙터 기반)
     - trailmap: pheromone_field_trailmap.frag.glsl (트레일맵 직접)
  2. 블롭 본체
  3. 정맥
  4. 큐빅 글로우
  5. 에이전트 표시
```

### 관련 파일
| 파일 | 역할 |
|------|------|
| `src/gpu/SceneRenderer.ts` | 렌더링 조율, 셰이더 프로그램 관리 |
| `src/gpu/shaders/glsl/pheromone_field_trailmap.frag.glsl` | trailmap 모드 등고선 셰이더 |
| `src/gpu/shaders/pheromone_field_trailmap.ts` | 셰이더 플레이스홀더 치환 |
| `src/gpu/TrailMapGPU.ts` | food 핑퐁 텍스처 소유 (`getCurrentFoodTexture()`) |
| `src/config.ts` | PHEROMONE 설정 (색상, 레벨, 선 두께) |

## 요구사항

1. **페로몬 등고선** (자기 트레일): 기존 녹색 계열 유지
2. **먹이 등고선** (food 채널): 별도 색상 (주황/노랑 등 따뜻한 계열)
3. 두 등고선은 **독립적으로** 그려져야 함 (겹칠 때 서로 간섭 없이 합성)
4. 동일한 SDF 등고선 알고리즘 사용 (코드 재활용)

## 구현 계획

### 접근 A: 단일 셰이더에서 두 채널 동시 처리 (선택)
- `pheromone_field_trailmap.frag.glsl`에 `u_foodMap` 추가
- 두 채널 각각 등고선 계산 → 색 다르게 → 알파 합성
- **장점**: 드로콜 1회, 텍스처 읽기 최적
- **단점**: 셰이더 복잡도 약간 증가

### 접근 B: 별도 셰이더 + 별도 렌더패스
- food 전용 등고선 셰이더 새로 만듦
- SceneRenderer에서 2번째 렌더패스 추가
- **장점**: 분리 깔끔
- **단점**: 드로콜 추가, 보일러플레이트 증가

→ **접근 A 채택**: 풀스크린 셰이더라 드로콜 비용이 크고, 두 채널이 같은 좌표계를 공유하므로 단일 셰이더가 효율적.

### 수정 파일 (4개)

#### 1. `src/config.ts`
```typescript
export const FOOD_CONTOUR = {
  COLOR: { r: 255, g: 180, b: 50 },    // 주황 (먹이 = 따뜻한 색)
  ALPHA: 0.7,
  LINE_WIDTH: 2.0,
  LEVELS: [0.05, 0.15, 0.3, 0.5, 0.7], // food 정규화 기준 레벨
  MAX_VALUE: 500,                        // food 정규화 최대값
  MIN_THRESHOLD: 1.0,                    // 최소 표시 임계값
} as const;
```

#### 2. `src/gpu/shaders/glsl/pheromone_field_trailmap.frag.glsl`
- `uniform sampler2D u_foodMap;` 추가
- food 채널 샘플링 → 별도 등고선 계산 (주황색)
- 최종 합성: `mix(trailContour, foodContour, foodContourAlpha)`

#### 3. `src/gpu/shaders/pheromone_field_trailmap.ts`
- `FOOD_CONTOUR` config에서 플레이스홀더 값 생성
- `{{FOOD_*}}` 계열 플레이스홀더 추가

#### 4. `src/gpu/SceneRenderer.ts`
- `render()` 메서드: foodTexture 파라미터 추가
- `renderPass()`: food 텍스처 바인딩 (TEXTURE1 또는 TEXTURE2)
- `pheromoneTrailmapUniforms`에 `foodMap` 유니폼 추가

### 변경 불필요
- `TrailMapGPU.ts` — `getCurrentFoodTexture()` 이미 존재
- `PhysarumSimulation.ts` — food 파이프라인 이미 완성
- `AgentGPU.ts` — 에이전트 셰이더 무관

## 검증
1. `npm run build` 통과
2. Playwright 스크린샷: 녹색(페로몬) + 주황색(먹이) 등고선이 별개로 표시
3. 먹이 없을 때: 주황 등고선 없음, 기존 녹색만 표시
4. 두 등고선 겹침 영역: 자연스러운 알파 합성

## 튜닝 가이드
- 먹이 등고선이 너무 넓음: `FOOD_CONTOUR.MAX_VALUE` ↑
- 먹이 등고선이 안 보임: `FOOD_CONTOUR.MIN_THRESHOLD` ↓
- 색상 구분 어려움: `FOOD_CONTOUR.COLOR` 조정 (빨강/노랑 등)
