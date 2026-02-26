# 토러스 제거 → 벽 경계 — 구현 계획

## Phase 1: 토러스 → 벽 경계 전환

### Step 1: 텍스처 래핑 변경

**파일**: `src/gpu/TrailMapGPU.ts` (L124-126)

```typescript
// Before
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);

// After
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
```

**파일**: `src/gpu/AgentGPU.ts` (L456-457) — Occupancy Map 동일 변경

→ verify: 텍스처 생성 로그로 CLAMP_TO_EDGE 확인

### Step 2: 확산 셰이더

**파일**: `src/gpu/shaders/glsl/diffuse_decay.frag.glsl` (L18)

```glsl
// Before
vec2 sampleUV = fract(v_uv + offset);

// After
vec2 sampleUV = clamp(v_uv + offset, 0.0, 1.0);
```

경계 아티팩트 방지 — 경계 1px border wipe:
```glsl
// 경계 픽셀이면 0으로 강제 (CLAMP_TO_EDGE 반복 샘플링 누적 방지)
if (v_uv.x < u_texelSize.x || v_uv.x > 1.0 - u_texelSize.x ||
    v_uv.y < u_texelSize.y || v_uv.y > 1.0 - u_texelSize.y) {
    fragColor = vec4(0.0);
    return;
}
```

→ verify: 맵 경계에 밝은 선이 안 생기는지 스크린샷 확인

### Step 3: 에이전트 업데이트 셰이더

**파일**: `src/gpu/shaders/glsl/agent_update.frag.glsl`

7곳의 `mod()` → `clamp()` 교체:

| 함수/위치 | 라인 참고 | 변경 |
|-----------|---------|------|
| `senseTrail()` | ~L46 | `mod(sensorPos, u_mapSize)` → `clamp(sensorPos, vec2(0.0), u_mapSize)` |
| `senseFood()` | ~L53 | 동일 |
| 연결성 `searchPos` | ~L140 | 동일 |
| `spFar` | ~L235 | 동일 |
| `spNear` | ~L236 | 동일 |
| 밀도 dN/dS/dE/dW | ~L267-270 | 동일 |
| ATTEMPT MOVE | ~L332 | 벽 충돌 처리 (아래) |

벽 충돌 로직:
```glsl
vec2 newPos = pos + vec2(cos(angle), sin(angle)) * u_moveSpeed;
bool hitWall = any(lessThan(newPos, vec2(0.0))) || any(greaterThanEqual(newPos, u_mapSize));
if (hitWall) {
    newPos = clamp(newPos, vec2(0.0), u_mapSize - vec2(0.001));
    angle = rnd.y * 6.28318;
}
```

→ verify: 에이전트가 벽에서 반대편으로 안 나타나는지, 벽에서 랜덤 방향 전환하는지

### Step 4: 에이전트 디스플레이 & SceneRenderer

**파일**: `src/gpu/shaders/glsl/agent_display.vert.glsl` (L30-46)
- 토러스 3×3 인스턴스 오프셋 로직 제거
- 단순 좌표 변환만 유지

**파일**: `src/gpu/SceneRenderer.ts` (L388-421)
- 9× 반복 렌더링 → 단일 `gl.drawArrays` 호출

→ verify: 에이전트가 화면에 1번만 표시되는지

### Step 5: 렌더링 셰이더 5종

**파일**: blob_body.frag.glsl, veins.frag.glsl, cubic_glow.frag.glsl, pheromone_field_trailmap.frag.glsl, pheromone_field.frag.glsl

공통 변경:
```glsl
// Before
vec2 worldPos = mod(u_camera + screenPos, u_mapSize);

// After
vec2 worldPos = u_camera + screenPos;
// 맵 밖이면 배경 처리
if (any(lessThan(worldPos, vec2(0.0))) || any(greaterThanEqual(worldPos, u_mapSize))) {
    fragColor = vec4(0.0);  // 또는 배경색
    return;
}
vec2 trailUV = worldPos / u_mapSize;
```

각 셰이더 내부의 `fract(trailUV + offset)` → `clamp(trailUV + offset, 0.0, 1.0)` 교체

→ verify: 맵 경계 밖이 배경색(어두운 초록)으로 렌더링되는지

### Step 6: 카메라 & UI 시스템

**파일**: `src/hooks/useGameLoop.ts`
```typescript
// Before (토러스 래핑)
cameraX = ((x % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH;

// After (클램프 — 뷰포트가 맵을 벗어나지 않도록)
cameraX = Math.max(0, Math.min(x, currentMapWidth - viewportWidth));
cameraY = Math.max(0, Math.min(y, currentMapHeight - viewportHeight));
```

`worldToScreenAll()` — 토러스 타일 반복 제거:
```typescript
// Before: 다중 복제본 반환 (토러스)
// After: 단일 좌표 반환
function worldToScreen(wx, wy, vw, vh) {
    return { x: wx - cameraX, y: wy - cameraY };
}
```

**파일**: `src/components/GameCanvas.tsx` — 줌/드래그 래핑 제거 (동일 패턴)
**파일**: `src/components/Minimap.tsx` — 클릭 래핑 제거, 토러스 거리 계산 제거

→ verify: 카메라가 맵 끝에서 멈추는지, 반대편으로 점프 안 하는지

### Step 7: 맵 크기 변경

**파일**: `src/config.ts`
```typescript
export const MAP = {
  WIDTH: 2000,
  HEIGHT: 2000,
} as const;
```

→ verify: `npm run build` 통과

---

## 구현 순서 요약

```
Step 1 (텍스처 래핑) → Step 2 (확산) → Step 3 (에이전트)
→ Step 4 (디스플레이) → Step 5 (렌더링)
→ Step 6 (카메라/UI) → Step 7 (config)
→ build 확인
```

## 검증 계획

| # | 검증 항목 | 방법 |
|---|---------|------|
| 1 | 에이전트가 경계에서 멈추고 반대편 안 나옴 | Playwright 스크린샷 (90초 대기) |
| 2 | 경계에 밝은 테두리 없음 | 스크린샷 확대 확인 |
| 3 | 카메라가 맵 끝에서 자연스럽게 멈춤 | 수동 드래그 테스트 |
| 4 | `npm run build` 통과 | CI 빌드 |
