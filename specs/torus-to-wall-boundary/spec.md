# 토러스 제거 → 벽 경계

## 게임 방향

인크리멘탈 성장 게임. 블롭이 중심에서 시작해 방사형으로 확장하며 성장.
업그레이드가 시뮬레이션 파라미터를 직접 조작 → 화면에서 다른 성장 패턴으로 나타남.

> 근거: `docs/research/game-direction-roleplay.md` (역할극 결론)
> 외부 리뷰: `docs/research/game-direction-external-review.md` (Gemini/Claude 피드백)

## 현재 상태

### 관련 파일
- `src/config.ts` — `MAP.WIDTH/HEIGHT: 1500`
- `src/gpu/TrailMapGPU.ts` — `createR32FTexture`: `GL_REPEAT`
- `src/gpu/AgentGPU.ts` — Occupancy Map `createR32FTexture`: `GL_REPEAT`
- `src/gpu/shaders/glsl/diffuse_decay.frag.glsl` — `fract(v_uv + offset)` 확산
- `src/gpu/shaders/glsl/agent_update.frag.glsl` — `mod(pos, u_mapSize)` 래핑 (7곳)
- `src/gpu/shaders/glsl/agent_display.vert.glsl` — 토러스 3×3 반복 렌더링
- `src/gpu/SceneRenderer.ts` — `renderAgents`: 9× 반복 루프
- 렌더링 셰이더 5종 — `mod(u_camera + screenPos, u_mapSize)` + `fract(trailUV + ...)` 다수
- `src/hooks/useGameLoop.ts` — 카메라 `((x % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH` 토러스 래핑
- `src/components/GameCanvas.tsx` — 줌/드래그 카메라 토러스 래핑
- `src/components/Minimap.tsx` — 클릭 카메라 토러스 래핑

### 현재 동작
- 맵이 **토러스(도넛)** 구조 — 오른쪽 끝 → 왼쪽 처음 연결
- 에이전트가 방사형 확산 → 맵 반대편에서 돌아와 자기 자신과 합쳐짐
- 블롭이 작은 맵(1500×1500)을 금방 채워 네트워크 구분 불가

## 문제 정의

1. **자가 접합**: 블롭이 방사형 확산 → 맵 반대편에서 자기 촉수와 만남 → 단일 연결 덩어리
2. **좁은 맵**: 1500×1500에서 촉수가 금방 한 바퀴 돌아 자신과 이어짐
3. **경계 비직관성**: 실제 Physarum은 용기(페트리 디쉬) 벽에 부딪히면 멈춤
4. **성장 한계**: 맵 크기가 아닌 게임 깊이(업그레이드/콘텐츠) 문제 — 시뮬레이션-게임 연결 강화로 해결

## 방법론 분석 (무한 필드)

> **결론: 보류** — 역할극 + 외부 리뷰에서 "고정 맵 내 밀도를 높이는 것이 현 단계에서 100배 효율적" 합의.
> 게임 방향(인크리멘탈) 확정 후 필요 시 재검토.

| 접근법 | 메모리 | 무한 느낌 | Physarum 적합성 | 판정 |
|--------|--------|---------|---------------|------|
| 큰 고정맵 (3000²) | 324 MB | 보통 | 좋음 | 모바일 VRAM 초과 위험 |
| 동적 확장 | 가변 | 높음 | 최적 | **보류** (게임 방향 확정 후) |
| 스크롤 버퍼 | 고정 | 높음 | 부적합 | 블롭 내부 네트워크 유실 |
| 청크/타일 | 가변 | 최고 | 비현실적 | WebGL2 확산 경계 처리 불가 |

---

## Phase 1: 토러스 → 벽 경계 전환

### 접근 방식: 경계 막힘(Wall/Clamp)

**막힘 (반사 없음)**

에이전트가 맵 경계에 도달하면:
- 이동 시도 차단 (이전 위치 유지)
- 각도 랜덤화 (벽에서 랜덤 방향 전환)

```glsl
// Before
vec2 newPos = mod(pos + move, u_mapSize);

// After
vec2 newPos = pos + vec2(cos(angle), sin(angle)) * u_moveSpeed;
bool hitWall = any(lessThan(newPos, vec2(0.0))) || any(greaterThanEqual(newPos, u_mapSize));
if (hitWall) {
    newPos = clamp(newPos, vec2(0.0), u_mapSize - vec2(0.001));
    angle = rnd.y * 6.28318; // 벽에서 랜덤 방향
}
```

### 요구사항

- [ ] `MAP.WIDTH/HEIGHT` 1500 → 2000
- [ ] `TrailMapGPU.ts`: 모든 R32F 텍스처 `GL_REPEAT` → `GL_CLAMP_TO_EDGE`
- [ ] `AgentGPU.ts`: Occupancy Map `GL_REPEAT` → `GL_CLAMP_TO_EDGE`
- [ ] `diffuse_decay.frag.glsl`: `fract(v_uv + offset)` → `clamp(v_uv + offset, 0.0, 1.0)`
- [ ] `diffuse_decay.frag.glsl`: 경계 1px border wipe (CLAMP_TO_EDGE 반복 샘플링 아티팩트 방지)
- [ ] `agent_update.frag.glsl`:
  - `senseTrail` / `senseFood`: `mod(sensorPos, u_mapSize)` → `clamp(sensorPos, vec2(0.0), u_mapSize)`
  - 연결성 탐색 `searchPos`: `mod(...)` → `clamp(...)`
  - 장거리 먹이 `spFar/spNear`: `mod(...)` → `clamp(...)`
  - 밀도 그래디언트 dN/dS/dE/dW: `mod(...)` → `clamp(...)`
  - ATTEMPT MOVE: `mod(pos + move, u_mapSize)` → 경계 막힘 처리
- [ ] `agent_display.vert.glsl`: 토러스 반복 로직 제거 → 단순 클리핑
- [ ] `SceneRenderer.ts`: `renderAgents` 9× 반복 → 단일 렌더링
- [ ] 렌더링 셰이더 5종 `worldPos`: `mod(u_camera + screenPos, u_mapSize)` → 맵 밖 픽셀 배경 처리
- [ ] 렌더링 셰이더 `fract(trailUV + offset)` → `clamp(...)` (blob_body, veins, cubic_glow, pheromone_field_trailmap)
- [ ] `useGameLoop.ts`: 카메라 토러스 래핑 `((x % W) + W) % W` 제거 → 클램프
- [ ] `useGameLoop.ts`: `worldToScreenAll()` 토러스 타일 반복 제거 → 단일 좌표
- [ ] `GameCanvas.tsx`: 줌/드래그 카메라 래핑 제거
- [ ] `Minimap.tsx`: 클릭 카메라 래핑 제거, 토러스 거리 계산 제거
- [ ] `npm run build` 통과

---

## Phase 2: 동적 맵 확장 (보류)

> **보류 사유**: 역할극 + 외부 리뷰 결과, 무한 필드의 우선순위가 낮음.
> 인크리멘탈 방향에서는 스테이지별 맵 크기 스케일링으로 충분.
> 시뮬레이션-게임 연결 강화가 선결 과제.
> 게임 디자인 확립 후 재검토. 기술 설계는 참고용으로 보존.

### 개요

블롭이 맵 경계에 가까워지면 자동으로 맵 확장. 새 영역은 빈 공간(미탐험 영토).

### 확장 트리거

- Occupancy Map 경계 200px 대역 내 에이전트 밀도가 임계값 초과
- 또는 가장 바깥 에이전트가 경계 200px 이내에 도달

### 확장 단계

| 단계 | 맵 크기 | 텍스처 메모리 (R32F × 9) | 비고 |
|------|---------|------------------------|------|
| 초기 | 2000×2000 | 144 MB | Phase 1 완료 상태 |
| 1차 확장 | 3000×3000 | 324 MB | 대부분 GPU 지원 |
| 2차 확장 | 4096×4096 | 603 MB | 최대 한계 (MAX_TEXTURE_SIZE 체크) |

### 확장 프로세스

```
1. 새 크기 텍스처 할당 (trail×2, rawTrail×2, food×2, deposit×2, occupancy = 9개)
2. "copy-to-center" 셰이더 실행:
   - 기존 텍스처 → 새 텍스처 중앙에 렌더링
   - 새 영역 = 0 (빈 공간)
3. 에이전트 위치 시프트:
   - 모든 에이전트 (x, y) += (newSize - oldSize) / 2
   - agent_update 셰이더에 u_positionOffset uniform (확장 프레임만 적용)
4. 카메라 위치 조정: camera += (newSize - oldSize) / 2
5. 이전 텍스처 해제 (gl.deleteTexture)
6. mapSize uniform 전역 업데이트
```

### 새 셰이더

```glsl
// copy_to_center.frag.glsl — 기존 텍스처를 새 크기 텍스처 중앙에 복사
uniform sampler2D u_source;
uniform vec2 u_srcSize;
uniform vec2 u_dstSize;
void main() {
    vec2 offset = (u_dstSize - u_srcSize) / (2.0 * u_dstSize);
    vec2 srcUV = (v_uv - offset) * (u_dstSize / u_srcSize);
    if (any(lessThan(srcUV, vec2(0.0))) || any(greaterThan(srcUV, vec2(1.0)))) {
        fragColor = vec4(0.0);
    } else {
        fragColor = texture(u_source, srcUV);
    }
}
```

### 요구사항

- [ ] `copy_to_center.frag.glsl` 신규 생성
- [ ] `TrailMapGPU.ts`: `resize(newW, newH)` 메서드 — 9개 텍스처 재할당 + copy-to-center
- [ ] `AgentGPU.ts`: `shiftAgents(dx, dy)` 메서드 + occupancy 텍스처 재할당
- [ ] `agent_update.frag.glsl`: `u_positionOffset` uniform 추가 (평소 vec2(0), 확장 시 오프셋)
- [ ] `config.ts`: MAP을 런타임 변경 가능하도록 구조 변경
- [ ] `PhysarumSimulation.ts`: 확장 트리거 로직 (매 N프레임 경계 밀도 체크)
- [ ] `useGameLoop.ts`: 확장 시 카메라 오프셋 반영
- [ ] 확장 시 `MAX_TEXTURE_SIZE` 체크 — 한계 도달 시 확장 중단 (벽 유지)
- [ ] `npm run build` 통과

---

## 데이터 흐름

```
Phase 1: 토러스 제거

config.ts (MAP 2000)
    ↓
TrailMapGPU.ts (GL_CLAMP_TO_EDGE)
    ↓
diffuse_decay.frag.glsl (fract → clamp + border wipe)
    ↓
agent_update.frag.glsl (mod → clamp + 벽 충돌)
    ↓
agent_display.vert.glsl (9× → 단일)
SceneRenderer.ts (반복 제거)
    ↓
렌더링 셰이더 5종 (mod → clamp, 맵 밖 = 배경)
    ↓
useGameLoop.ts + GameCanvas.tsx + Minimap.tsx (카메라 래핑 → 클램프)
```

## 메모리 분석

| 맵 크기 | 텍스처 메모리 (R32F × 9) | 변경 |
|---------|------------------------|------|
| 1500×1500 | 81 MB | 현재 |
| 2000×2000 | 144 MB | Phase 1 초기 |
| 3000×3000 | 324 MB | 1차 확장 |
| 4096×4096 | 603 MB | 최대 한계 |

## 위험 요소

| 위험 | 완화 |
|------|------|
| 경계 트레일 밝은 테두리 (CLAMP_TO_EDGE 반복 샘플링) | diffuse 패스에서 경계 1px 강제 0 클리어 |
| 에이전트 벽 밀집 | 각도 랜덤화 + occupancy threshold 벽 근처 강화 |
| 확장 시 1프레임 끊김 | 텍스처 할당/복사 모두 GPU 내부 → ms 단위 |
| 4096² 모바일 VRAM 초과 | `MAX_TEXTURE_SIZE` 체크, 미달 시 확장 중단 |
| 확장 중 에이전트 위치 불일치 | offset을 agent_update와 같은 프레임에 원자적 적용 |
| 렌더링 셰이더 맵 밖 좌표 | worldPos 범위 초과 시 discard 또는 배경색 |
