# 등고선 이중 채널 분리 렌더링 — 구현 계획

> spec: [spec.md](./spec.md)

## 변경 파일 순서

총 5개 파일, 의존 순서대로 실행.

---

### Step 1. `src/config.ts` — FOOD_CONTOUR 설정 추가

**위치**: FOOD 블록 아래 (40행 부근)

```typescript
export const FOOD_CONTOUR = {
  MIN_THRESHOLD: 1.0,               // 이 값 미만이면 food 등고선 안 그림
  MAX_VALUE: 500,                    // food 정규화 최대값 (FOOD.MAX_TRAIL=1000이지만 중심부만 높음)
  LOW_COLOR: { r: 120, g: 60, b: 0 },    // 낮은 농도: 갈색
  HIGH_COLOR: { r: 255, g: 160, b: 30 }, // 높은 농도: 밝은 주황
  BASE_ALPHA: 0.25,
  LINE_WIDTH: 2.0,
  CONTOUR_COLOR: { r: 255, g: 180, b: 50 },  // 등고선: 주황
  CONTOUR_ALPHA: 0.7,
  LEVELS: [0.05, 0.15, 0.3, 0.5, 0.7],       // 5단계 레벨
} as const;
```

**이유**: 기존 `TRAILMAP_PHEROMONE`(녹색 계열)과 명확히 구분되는 따뜻한 색상.

---

### Step 2. `src/gpu/shaders/glsl/pheromone_field_trailmap.frag.glsl` — 셰이더 수정

**핵심 변경**: `u_foodMap` uniform 추가, food 등고선을 별도로 계산 후 합성.

#### 2a. uniform 추가 (4행)
```glsl
uniform sampler2D u_foodMap;
```

#### 2b. food 샘플링 + 등고선 (기존 trail 등고선 블록 바로 아래, 66행 부근)

```glsl
// === 먹이 등고선 (별도 채널, 별도 색상) ===
float foodSum = 0.0;
for (int dy = -1; dy <= 1; dy++) {
    for (int dx = -1; dx <= 1; dx++) {
        vec2 offset = vec2(float(dx), float(dy)) * texel;
        foodSum += texture(u_foodMap, fract(trailUV + offset)).r;
    }
}
float foodValue = foodSum / 9.0;

float foodContourLine = 0.0;
if (foodValue > {{FOOD_MIN_THRESHOLD}} / zoomFactor) {
    float foodMaxValue = {{FOOD_MAX_VALUE}};
    float foodIntensity = clamp(foodValue / foodMaxValue, 0.0, 1.0);

    // food 그래디언트
    float foodR = texture(u_foodMap, fract(trailUV + vec2(texel.x, 0.0))).r;
    float foodU = texture(u_foodMap, fract(trailUV + vec2(0.0, texel.y))).r;
    float fIR = clamp(foodR / foodMaxValue, 0.0, 1.0);
    float fIU = clamp(foodU / foodMaxValue, 0.0, 1.0);
    vec2 foodGrad = vec2(fIR - foodIntensity, fIU - foodIntensity);
    float foodGradLen = length(foodGrad);

    // food 등고선 레벨
    float foodLevels[5] = float[5]({{FOOD_LEVELS}});
    for (int i = 0; i < 5; i++) {
        float dist = abs(foodIntensity - foodLevels[i]);
        float pixelDist = foodGradLen > 0.0001 ? dist / foodGradLen : 9999.0;
        float line = 1.0 - smoothstep(0.0, {{FOOD_LINE_WIDTH}}, pixelDist);
        foodContourLine = max(foodContourLine, line);
    }

    // food 배경 필드 (그라데이션)
    vec3 foodLowColor = vec3({{FOOD_LOW_R}}, {{FOOD_LOW_G}}, {{FOOD_LOW_B}});
    vec3 foodHighColor = vec3({{FOOD_HIGH_R}}, {{FOOD_HIGH_G}}, {{FOOD_HIGH_B}});
    vec3 foodFieldColor = mix(foodLowColor, foodHighColor, foodIntensity);
    float foodBaseAlpha = foodIntensity * {{FOOD_BASE_ALPHA}};

    // food 등고선 합성 → finalColor에 추가
    vec3 foodContourRGB = vec3({{FOOD_CONTOUR_R}}, {{FOOD_CONTOUR_G}}, {{FOOD_CONTOUR_B}});
    vec3 foodFinal = mix(foodFieldColor, foodContourRGB, foodContourLine * 0.5);
    float foodFinalAlpha = max(foodBaseAlpha, foodContourLine * {{FOOD_CONTOUR_ALPHA}});

    // trail + food 합성 (food를 위에 덮기)
    finalColor = finalColor * (1.0 - foodFinalAlpha) + foodFinal * foodFinalAlpha;
    finalAlpha = max(finalAlpha, foodFinalAlpha);
}
```

#### 2c. 최종 fragColor 출력
기존 `fragColor = vec4(finalColor, finalAlpha);` 유지.
단, 기존 코드에서 `finalColor`/`finalAlpha` 변수명으로 변경 필요 (현재는 inline 계산).

**리팩터 포인트**: 기존 trail 등고선 결과를 `finalColor`/`finalAlpha` 변수에 저장한 뒤, food 블록이 그 위에 합성.

---

### Step 3. `src/gpu/shaders/pheromone_field_trailmap.ts` — 플레이스홀더 치환

**추가할 치환 항목** (FOOD_CONTOUR config에서):

```typescript
import { FOOD_CONTOUR } from '../../config';

const F = FOOD_CONTOUR;

// 기존 resolveShader 호출에 추가:
FOOD_MIN_THRESHOLD: F.MIN_THRESHOLD.toFixed(1),
FOOD_MAX_VALUE: F.MAX_VALUE.toFixed(1),
FOOD_LOW_R: (F.LOW_COLOR.r / 255).toFixed(3),
FOOD_LOW_G: (F.LOW_COLOR.g / 255).toFixed(3),
FOOD_LOW_B: (F.LOW_COLOR.b / 255).toFixed(3),
FOOD_HIGH_R: (F.HIGH_COLOR.r / 255).toFixed(3),
FOOD_HIGH_G: (F.HIGH_COLOR.g / 255).toFixed(3),
FOOD_HIGH_B: (F.HIGH_COLOR.b / 255).toFixed(3),
FOOD_BASE_ALPHA: F.BASE_ALPHA.toFixed(2),
FOOD_LINE_WIDTH: F.LINE_WIDTH.toFixed(1),
FOOD_CONTOUR_R: (F.CONTOUR_COLOR.r / 255).toFixed(3),
FOOD_CONTOUR_G: (F.CONTOUR_COLOR.g / 255).toFixed(3),
FOOD_CONTOUR_B: (F.CONTOUR_COLOR.b / 255).toFixed(3),
FOOD_CONTOUR_ALPHA: F.CONTOUR_ALPHA.toFixed(2),
FOOD_LEVELS: F.LEVELS.map(l => l.toFixed(2)).join(', '),
```

---

### Step 4. `src/gpu/SceneRenderer.ts` — food 텍스처 바인딩

#### 4a. render() 시그니처에 foodTexture 추가

```typescript
render(
  trailTexture: WebGLTexture,
  foodTexture: WebGLTexture | null,  // 추가
  camera: ...,
  ...
)
```

#### 4b. pheromoneTrailmapUniforms에 foodMap 유니폼 추가

생성자에서:
```typescript
this.pheromoneTrailmapUniforms = {
  ...this.getUniforms(this.pheromoneTrailmapProgram, false),
  foodMap: gl.getUniformLocation(this.pheromoneTrailmapProgram, 'u_foodMap'),
};
```

`SceneUniforms` 인터페이스에 `foodMap?: WebGLUniformLocation | null` 추가.

#### 4c. renderPass()에서 food 텍스처 바인딩

trailmap 모드 렌더링 시:
```typescript
if (this.pheromoneMode === 'trailmap') {
  this.renderPass(
    this.pheromoneTrailmapProgram,
    this.pheromoneTrailmapUniforms,
    trailTexture,
    camera, mapSize, logicalWidth, logicalHeight,
    isDormant,
    undefined,  // attractorCount
    undefined,  // time
    foodTexture, // 추가
  );
}
```

`renderPass()` 메서드에 `foodTexture?: WebGLTexture | null` 파라미터 추가:
```typescript
if (foodTexture && uniforms.foodMap) {
  gl.activeTexture(gl.TEXTURE3);
  gl.bindTexture(gl.TEXTURE_2D, foodTexture);
  gl.uniform1i(uniforms.foodMap, 3);
}
```

---

### Step 5. `src/hooks/useGameLoop.ts` — foodTexture 전달

#### 5a. PhysarumSimulation에 getCurrentFoodTexture() 공개 메서드 추가

`src/simulation/PhysarumSimulation.ts`에:
```typescript
getCurrentFoodTexture(): WebGLTexture | null {
  return this.gpu ? this.gpu.getCurrentFoodTexture() : null;
}
```

#### 5b. useGameLoop에서 render 호출 수정

```typescript
const trailTex = simulation.getCurrentTrailTexture();
const foodTex = simulation.getCurrentFoodTexture();  // 추가
// ...
sceneRenderer.render(
  trailTex,
  foodTex,   // 추가
  { x: cameraX, y: cameraY },
  ...
);
```

---

## 의존 관계

```
Step 1 (config) ─────┐
                      ├──→ Step 2 (셰이더 GLSL)
                      ├──→ Step 3 (셰이더 TS 치환)
Step 5a (메서드 공개) ├──→ Step 4 (SceneRenderer)
                      └──→ Step 5b (useGameLoop 호출)
```

Step 1은 독립 → Step 2, 3은 Step 1 이후 → Step 4는 Step 2, 3 이후 → Step 5는 Step 4 이후.

## 검증 체크리스트

- [ ] `npm run build` 통과 (TS 에러 없음)
- [ ] 먹이 없을 때: 녹색 trail 등고선만 표시 (기존과 동일)
- [ ] 먹이 놓았을 때: 주황색 food 등고선 추가 표시
- [ ] 두 등고선 겹침: 자연스러운 합성 (서로 간섭 없음)
- [ ] 디버그 코드 없음 (console.log 등)
- [ ] Playwright 스크린샷: `screenshots/contour-dual-before.png`, `screenshots/contour-dual-after.png`
