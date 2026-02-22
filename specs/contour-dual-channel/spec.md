# 등고선 이중 채널 분리 렌더링

## 문제

현재 등고선(페로몬 필드)은 **u_trailMap 하나만** 샘플링하여 녹색 등고선으로 표시.
커밋 `cb94f42`에서 먹이 전용 채널(`foodMap`)을 추가했으나,
**foodMap의 등고선은 렌더링되지 않고 있음.**

사용자는 페로몬과 먹이의 등고선을 **색을 달리하여 별개로** 볼 수 있기를 원함.

## 핵심 설계 원칙

**trailMap과 foodMap은 완전 분리** — 먹이 deposit은 foodMap에만 주입.
trailMap은 순수 에이전트 자기 페로몬만 포함하여, 렌더링 시 색 겹침 없이 독립 표시.

## 현재 상태

### 데이터 채널
| 채널 | 텍스처 | 내용물 | 등고선 색상 |
|------|--------|--------|-------------|
| 자기 페로몬 | `trailTexA/B` (R32F) | 에이전트 분비물만 | 녹색 |
| 먹이 화학물질 | `foodTexA/B` (R32F) | 먹이 deposit만 | 주황색 |

### 렌더링 파이프라인
```
SceneRenderer.render()
  1. 페로몬 등고선 ← u_trailMap + u_foodMap (이중 채널)
     - trailmap: pheromone_field_trailmap.frag.glsl
       - A. 자기 페로몬 → 녹색 등고선/필드
       - B. 먹이 화학물질 → 주황색 등고선/필드 (위에 합성)
     - inverse-square: pheromone_field.frag.glsl (어트랙터 기반, food 미지원)
  2. 블롭 본체
  3. 정맥
  4. 큐빅 글로우
  5. 에이전트 표시
```

### 관련 파일
| 파일 | 역할 |
|------|------|
| `src/gpu/SceneRenderer.ts` | 렌더링 조율, foodTexture 바인딩 (TEXTURE3) |
| `src/gpu/shaders/glsl/pheromone_field_trailmap.frag.glsl` | 이중 채널 등고선 셰이더 |
| `src/gpu/shaders/pheromone_field_trailmap.ts` | 셰이더 플레이스홀더 치환 (trail + food) |
| `src/gpu/TrailMapGPU.ts` | food 핑퐁 텍스처 소유 (`getCurrentFoodTexture()`) |
| `src/config.ts` | `FOOD_CONTOUR` 설정 (색상, 레벨, 선 두께) |
| `src/simulation/PhysarumSimulation.ts` | food deposit → foodMap만 (trailMap 분리) |

## 요구사항

1. **페로몬 등고선** (자기 트레일): 기존 녹색 계열 유지
2. **먹이 등고선** (food 채널): 별도 색상 (주황/노랑 등 따뜻한 계열)
3. 두 등고선은 **독립적으로** 그려져야 함 (겹칠 때 서로 간섭 없이 합성)
4. 동일한 SDF 등고선 알고리즘 사용 (코드 재활용)
5. **trailMap에는 food deposit을 넣지 않는다** (데이터 레이어 분리)

## 구현: 단일 셰이더에서 두 채널 동시 처리

- `pheromone_field_trailmap.frag.glsl`에 `u_foodMap` uniform 추가
- 두 채널 각각 독립 등고선 계산 → 색 다르게 → 알파 합성
- trailMap 순수화로 trailMask 등의 해킹 불필요

### 수정 파일 (6개)

| 파일 | 변경 |
|------|------|
| `src/config.ts` | `FOOD_CONTOUR` 설정 추가 |
| `src/gpu/shaders/glsl/pheromone_field_trailmap.frag.glsl` | `u_foodMap` + 주황 등고선 |
| `src/gpu/shaders/pheromone_field_trailmap.ts` | `{{FOOD_*}}` 플레이스홀더 치환 |
| `src/gpu/SceneRenderer.ts` | foodTexture 파라미터 + TEXTURE3 바인딩 |
| `src/hooks/useGameLoop.ts` | foodTex 전달 |
| `src/simulation/PhysarumSimulation.ts` | food deposit → foodMap만 (trailMap 주입 제거) |

## 검증
1. `npm run build` 통과
2. 녹색(페로몬) + 주황색(먹이) 등고선이 별개로 표시
3. 먹이 없을 때: 주황 등고선 없음, 기존 녹색만 표시
4. 두 등고선 겹침 영역: 주황이 녹색 위에 자연스럽게 합성

## 튜닝 가이드
- 먹이 등고선이 너무 넓음: `FOOD_CONTOUR.MAX_VALUE` ↑
- 먹이 등고선이 안 보임: `FOOD_CONTOUR.MIN_THRESHOLD` ↓
- 색상 구분 어려움: `FOOD_CONTOUR.CONTOUR_COLOR` 조정
