# 정맥 렌더링 개선 -- Spec/Plan 작성 및 감수 (2차 회의)

## 참가자 (1차 토론과 동일)
- **최로드맵** -- 기획자 (spec/plan 주도)
- **박코드** -- WebGL2/셰이더 개발자 (공동 작성)
- **이헤시안** -- 이미지 처리 수학자 (감수)
- **Dr. 김점균** -- 균류학 전문가 (최종 리뷰)

## 전제
1차 토론(`vein-discussion.md`)에서 합의된 3단계 로드맵을 기반으로 구체적 spec/plan을 작성한다.

---

## 파트 1: Spec 초안 작성 (기획자 + 개발자)

**최로드맵**: 1차 토론에서 합의된 로드맵을 이제 실제 구현 가능한 spec으로 구체화하겠습니다. 각 Phase별로 **변경 파일, 정확한 코드 위치, 파라미터, 성공 기준, 위험 요소**를 빠짐없이 명세합니다. 코드 님, 같이 채워주시죠.

### Phase 1 Spec: Additive Blend + 파라미터 조정

**최로드맵**: Phase 1의 핵심 목표는 "정맥이 본체 위에 떠 보이는 효과". 형태 개선은 기대하지 않습니다. 성공 기준을 먼저 정의해야 Phase 완료 판단이 가능합니다.

**박코드**: 현재 코드를 기준으로 정확한 변경 지점을 짚겠습니다. `SceneRenderer.ts` 270~271행이 핵심이에요:

```typescript
// 현재 (270~271행)
if (this.viewMode !== 'density') {
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
```

이걸 additive로 바꾸면:

```typescript
// 변경 후
if (this.viewMode !== 'density') {
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);  // additive blend
```

그리고 `config.ts`의 VEINS 파라미터 조정이 필요합니다. Additive blend에서는 같은 alpha 값이 더 밝게 나오기 때문에:

```typescript
// 현재 → 변경
MAJOR_ALPHA: 0.85 → 0.40   // additive 보정: 0.85면 화이트아웃
MINOR_ALPHA: 0.15 → 0.08   // 모세정맥 노이즈 추가 억제
```

이것만으로도 정맥이 본체 색 위에 "더해져" 밝아지는 효과가 나옵니다.

**최로드맵**: 변경 파일 목록과 정확한 위치를 확인합니다:

| 파일 | 위치 | 변경 내용 |
|------|------|----------|
| `src/gpu/SceneRenderer.ts` | 271행 | `ONE_MINUS_SRC_ALPHA` -> `ONE` |
| `src/config.ts` | VEINS.MAJOR_ALPHA | 0.85 -> 0.40 |
| `src/config.ts` | VEINS.MINOR_ALPHA | 0.15 -> 0.08 |

성공 기준은:

1. **밝기**: 정맥이 본체(올리브) 위에서 확실히 밝은 노란색으로 보임
2. **포화 없음**: RGB 중 어떤 채널도 1.0 클램프로 인한 화이트아웃 없음
3. **구조 유지**: 기존 능선 검출 구조가 깨지지 않음 (형태는 동일해도 됨)
4. **돌출감**: 본체 가장자리에서 정맥이 배경(어두운 초록) 위에 빛남
5. **큐빅 글로우 무충돌**: 큐빅 글로우(이미 additive)와 시각적 간섭 없음

위험 요소: **매우 낮음**. 블렌딩 함수 1행 + config 2값 변경. `git revert` 한 커밋으로 완전 롤백 가능.

**박코드**: 한 가지 추가 고려 사항이 있어요. Additive blend 후 정맥 색상 자체도 조정이 필요할 수 있습니다. 현재 `MAJOR_COLOR: (0.95, 0.88, 0.35)`인데, 본체 색상 `(0.86, 0.78, 0.24)` 위에 additive로 더해지면:

```
결과 = 본체(0.86, 0.78, 0.24) + 정맥(0.95, 0.88, 0.35) * 0.40
     = (0.86 + 0.38, 0.78 + 0.35, 0.24 + 0.14)
     = (1.24, 1.13, 0.38) → 클램프 → (1.0, 1.0, 0.38)
```

RG 채널이 1.0 클램프됩니다. alpha를 0.40까지 낮추는 건 조금 과했네요. 0.30 정도가 안전할 수 있어요:

```
0.30일 때: (0.86 + 0.29, 0.78 + 0.26, 0.24 + 0.11) = (1.15, 1.04, 0.35)
```

아직도 클램프가 발생해요. 하지만 실제로는 본체의 BODY_MAX_ALPHA가 0.85이고 배경이 (8/255, 20/255, 10/255)이라, 본체가 그려진 후의 실제 프레임버퍼 값은 정확히 `(0.86, 0.78, 0.24)`가 아닙니다. 배경과 알파 블렌딩된 결과죠.

```
실제 본체 = 배경(0.031, 0.078, 0.039) * (1-0.85) + 본체(0.86, 0.78, 0.24) * 0.85
         = (0.005 + 0.73, 0.012 + 0.66, 0.006 + 0.20)
         = (0.74, 0.67, 0.21)
```

이 위에 정맥 alpha 0.30:

```
결과 = (0.74 + 0.29, 0.67 + 0.26, 0.21 + 0.11) = (1.03, 0.93, 0.32)
```

R만 약간 클램프. 이 정도면 수용 가능해요. 하지만 alpha는 시각 확인하며 0.25~0.40 범위에서 튜닝하는 게 맞습니다.

**최로드맵**: 그러면 spec의 alpha 초기값을 0.30으로 조정하고, "0.25~0.40 범위에서 시각 튜닝" 항목을 추가합니다.

---

### Phase 2 Spec: 미확산 트레일맵 분리

**최로드맵**: Phase 2가 핵심이죠. 코드 님, 1차 토론에서 `blendDeposits()` 후 복사한다고 했는데, 실제 GPU 경로를 보면 `blendDeposits()`가 사용되지 않더군요?

**박코드**: 맞아요, 중요한 정정입니다. 1차 토론에서 `blendDeposits()` 기반으로 설명했는데, 실제 전체 GPU 경로(`PhysarumSimulation.ts` 309~350행)를 보면:

```
매 프레임 GPU 경로:
1. agentGPU.runOccupancy()      -- occupancy map 업데이트
2. agentGPU.runUpdate(trailTex) -- 에이전트 이동/회전
3. agentGPU.runDeposit(currentFbo, ...) -- 현재 trail FBO에 직접 가산 기록
4. gpu.runDiffuseDecay(decay, 4) -- 확산+감쇠 (핑퐁 4패스)
```

`blendDeposits()`는 CPU/하이브리드 경로용이고, 전체 GPU 경로에서는 `agentGPU.runDeposit()`이 **직접 현재 trail FBO에 additive blending으로 deposit을 씁니다**. 이 점이 1차 토론과 다릅니다.

따라서 미확산 맵 캡처 타이밍은:

```
3. agentGPU.runDeposit(currentFbo, ...) -- deposit 완료
   ★ captureRawTrail() -- 여기서 복사!
4. gpu.runDiffuseDecay(decay, 4) -- 확산 시작
```

`runDeposit()` 직후, `runDiffuseDecay()` 직전입니다.

**최로드맵**: 좋습니다. 그러면 캡처 메서드는 `TrailMapGPU`에 추가하되, 호출은 `PhysarumSimulation.ts`에서?

**박코드**: 네. 구체적인 변경 사항을 파일별로 정리합니다.

#### 2-1. `src/gpu/TrailMapGPU.ts` 변경

**추가 멤버:**
```typescript
// 미확산 트레일 텍스처 (정맥 렌더링 전용)
private rawTrailTex: WebGLTexture;
private rawTrailFbo: WebGLFramebuffer;
```

**생성자 변경 (constructor, 83~97행 부근):**
```typescript
// 기존 텍스처 생성 이후에 추가
this.rawTrailTex = this.createR32FTexture(width, height);
this.rawTrailFbo = this.createFBO(this.rawTrailTex);
```

**새 메서드 추가:**
```typescript
// 현재 trail 상태를 미확산 텍스처로 복사 (확산 전 캡처)
captureRawTrail() {
    const gl = this.gl;
    const srcFbo = this.currentIsA ? this.fboA : this.fboB;
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, srcFbo);
    gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, this.rawTrailFbo);
    gl.blitFramebuffer(
        0, 0, this.width, this.height,
        0, 0, this.width, this.height,
        gl.COLOR_BUFFER_BIT, gl.NEAREST,
    );
    gl.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
    gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, null);
}

// 미확산 트레일 텍스처 반환 (정맥 셰이더용)
getRawTrailTexture(): WebGLTexture {
    return this.rawTrailTex;
}
```

**dispose() 변경:**
```typescript
// 추가
gl.deleteTexture(this.rawTrailTex);
gl.deleteFramebuffer(this.rawTrailFbo);
```

메모리 비용: R32F 1500x1500 = 1500 * 1500 * 4bytes = **9MB**. 기존 핑퐁 18MB 대비 50% 증가지만 절대량은 미미.

#### 2-2. `src/simulation/PhysarumSimulation.ts` 변경

**GPU 경로 (343~350행 사이):**
```typescript
// 2. GPU 분비: 에이전트 자기 페로몬 → trail FBO
const currentFbo = this.gpu.getCurrentFBO();
this.agentGPU.runDeposit(currentFbo, ...);

// ★ 미확산 트레일 캡처 (확산 전)
this.gpu.captureRawTrail();

// 3. 자기 트레일 확산+감쇠
this.gpu.runDiffuseDecay(this.config.decayFactor, AGENT.DIFFUSE_PASSES);
```

CPU/하이브리드 경로와 휴면 경로에서는 미확산 맵 불필요 (정맥 렌더링은 GPU 경로에서만 의미 있음).

#### 2-3. `src/gpu/SceneRenderer.ts` 변경

**render() 시그니처 변경:**
```typescript
render(
    trailTexture: WebGLTexture,
    foodTexture: WebGLTexture | null,
    rawTrailTexture: WebGLTexture | null,  // ★ 추가
    camera: { x: number; y: number },
    // ... 나머지 동일
)
```

**renderPass() 변경:**
```typescript
private renderPass(
    program: WebGLProgram,
    uniforms: SceneUniforms,
    trailTexture: WebGLTexture,
    // ... 기존 파라미터 ...
    rawTrailTexture?: WebGLTexture | null,  // ★ 추가
)
```

**정맥 renderPass 호출 변경 (269~281행):**
```typescript
if (this.viewMode !== 'density') {
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE);  // Phase 1에서 변경됨
    this.renderPass(
        this.veinsProgram,
        this.veinsUniforms,
        trailTexture,
        camera, mapSize, logicalWidth, logicalHeight,
        isDormant,
        undefined,
        time,
        undefined,
        rawTrailTexture,  // ★ 미확산 텍스처 전달
    );
}
```

**renderPass() 내부에서 TEXTURE4에 바인딩:**
```typescript
// 미확산 트레일맵 (정맥 셰이더용)
if (rawTrailTexture && uniforms.rawTrailMap) {
    gl.activeTexture(gl.TEXTURE4);
    gl.bindTexture(gl.TEXTURE_2D, rawTrailTexture);
    gl.uniform1i(uniforms.rawTrailMap!, 4);
}
```

**SceneUniforms 인터페이스:**
```typescript
interface SceneUniforms {
    // ... 기존 ...
    rawTrailMap?: WebGLUniformLocation | null;  // ★ 추가
}
```

**veinsUniforms 초기화 변경 (101~104행):**
```typescript
this.veinsUniforms = {
    ...this.getUniforms(this.veinsProgram, true),
    time: gl.getUniformLocation(this.veinsProgram, 'u_time'),
    rawTrailMap: gl.getUniformLocation(this.veinsProgram, 'u_rawTrailMap'),  // ★
};
```

#### 2-4. `src/gpu/shaders/glsl/veins.frag.glsl` 변경

```glsl
#version 300 es
precision highp float;

uniform sampler2D u_trailMap;      // 확산된 텍스처 (본체 영역 마스킹용)
uniform sampler2D u_rawTrailMap;   // ★ 미확산 텍스처 (정맥 검출용)
uniform vec2 u_mapSize, u_viewportSize, u_camera;
uniform bool u_isDormant;
uniform float u_time;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 screenPos = vec2(v_uv.x, 1.0 - v_uv.y) * u_viewportSize;
    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);
    vec2 trailUV = worldPos / u_mapSize;

    // 본체 영역 마스킹 (확산 맵 기반 -- 확산 맵이 영역 판단에 적합)
    float bodyValue = texture(u_trailMap, trailUV).r;
    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x, u_viewportSize.y / u_mapSize.y));
    float veinMin = {{VEIN_MIN}} / zoomFactor;

    if (bodyValue < veinMin) {
        fragColor = vec4(0.0);
        return;
    }

    // ★ 미확산 맵에서 직접 샘플링 (3x3 블러 제거!)
    vec2 texel = ({{STEP}} * zoomFactor) / u_mapSize;
    float value = texture(u_rawTrailMap, trailUV).r;

    // 능선 검출: STEP=2로 축소된 범위에서 center-avg 비교
    vec2 farTexel = texel * 2.0;
    float right = texture(u_rawTrailMap, fract(trailUV + vec2(farTexel.x, 0.0))).r;
    float up    = texture(u_rawTrailMap, fract(trailUV + vec2(0.0, farTexel.y))).r;
    float left  = texture(u_rawTrailMap, fract(trailUV - vec2(farTexel.x, 0.0))).r;
    float down  = texture(u_rawTrailMap, fract(trailUV - vec2(0.0, farTexel.y))).r;
    float avg = (right + left + up + down) * 0.25;
    float ridge = value - avg;

    if (ridge < -0.5) { fragColor = vec4(0.0); return; }
    ridge = max(ridge, 0.0);

    // 이하 기존 로직 유지 (densityT, relRidge, ridgeStrength, 맥동, 색상)
    // ...
}
```

#### 2-5. `src/gpu/shaders/veins.ts` 변경

변경 없음 -- `u_rawTrailMap`은 uniform location으로 `SceneRenderer.ts`에서 직접 관리. placeholder 추가 불필요.

#### 2-6. `src/config.ts` 변경

```typescript
STEP: 8 → 2   // 미확산 맵에서는 2~5px 폭 검출에 적합
```

#### 2-7. `src/hooks/useGameLoop.ts` 변경

**render() 호출부 (799~814행):**
```typescript
const rawTrailTex = simulation.getGPU()?.getRawTrailTexture() ?? null;

sceneRenderer.render(
    trailTex,
    foodTex,
    rawTrailTex,  // ★ 추가
    { x: cameraX, y: cameraY },
    // ... 나머지 동일
);
```

`PhysarumSimulation`에 `getGPU()` 접근자가 없으면 추가가 필요합니다.

**박코드**: 확인해 봅시다... `PhysarumSimulation`에 `this.gpu`는 private이에요. 접근자를 추가하거나, `getRawTrailTexture()` 메서드를 PhysarumSimulation 자체에 추가하는 게 낫겠습니다:

```typescript
// PhysarumSimulation에 추가
getRawTrailTexture(): WebGLTexture | null {
    return this.gpu?.getRawTrailTexture() ?? null;
}
```

이러면 useGameLoop에서:
```typescript
const rawTrailTex = simulation.getRawTrailTexture();
```

**최로드맵**: Phase 2 성공 기준을 정리합니다:

1. **정맥 폭 감소**: 확산 맵 대비 정맥 렌더링 폭이 눈에 띄게 좁아짐
2. **경계 선명화**: 이전의 부드러운 그라데이션 -> 더 뚜렷한 전환
3. **시뮬레이션 무영향**: 에이전트 행동 동일 (미확산 맵은 읽기 전용)
4. **성능 유지**: FPS 하락 없음 (blit 1회/프레임 추가)
5. **본체 마스킹 정상**: 확산 맵 기반 마스킹으로 본체 외부에 정맥 누출 없음

위험 요소:
- **중간**: FBO 관리 복잡도 증가. 텍스처 바인딩 순서 주의 (TEXTURE0~4)
- **낮음**: 메모리 9MB 추가
- **주의**: `glBlitFramebuffer` 호출 전후의 FBO 바인딩 상태 복원 필수

---

### Phase 3 Spec: Hessian Ridge Detection

**최로드맵**: Phase 3은 셰이더 전면 재작성입니다. 가장 복잡한 Phase이니 상세하게 가겠습니다.

**박코드**: `veins.frag.glsl`을 Hessian 기반으로 전면 교체합니다. 핵심 변경점:

1. 3x3 블러 **제거** (Phase 2에서 이미 제거됨)
2. center-avg 능선 검출 **제거**
3. Hessian 행렬 고유값 기반 ridgeness 검출 **추가**
4. 멀티스케일 선택적 적용

#### 3-1. `src/gpu/shaders/glsl/veins.frag.glsl` 전면 재작성

```glsl
#version 300 es
precision highp float;

uniform sampler2D u_trailMap;      // 확산된 텍스처 (본체 마스킹)
uniform sampler2D u_rawTrailMap;   // 미확산 텍스처 (Hessian 입력)
uniform vec2 u_mapSize, u_viewportSize, u_camera;
uniform bool u_isDormant;
uniform float u_time;

in vec2 v_uv;
out vec4 fragColor;

// Hessian ridge 검출 함수
float computeHessianRidge(vec2 uv, float h) {
    vec2 dx = vec2(h / u_mapSize.x, 0.0);
    vec2 dy = vec2(0.0, h / u_mapSize.y);

    float c  = texture(u_rawTrailMap, uv).r;
    float l  = texture(u_rawTrailMap, fract(uv - dx)).r;
    float r  = texture(u_rawTrailMap, fract(uv + dx)).r;
    float u_ = texture(u_rawTrailMap, fract(uv + dy)).r;
    float d  = texture(u_rawTrailMap, fract(uv - dy)).r;
    float tr = texture(u_rawTrailMap, fract(uv + dx + dy)).r;
    float tl = texture(u_rawTrailMap, fract(uv - dx + dy)).r;
    float br = texture(u_rawTrailMap, fract(uv + dx - dy)).r;
    float bl = texture(u_rawTrailMap, fract(uv - dx - dy)).r;

    float h2 = h * h;
    float fxx = (l + r - 2.0 * c) / h2;
    float fyy = (u_ + d - 2.0 * c) / h2;
    float fxy = (tr + bl - tl - br) / (4.0 * h2);

    float trace = fxx + fyy;
    float det = fxx * fyy - fxy * fxy;
    float disc = max(trace * trace * 0.25 - det, 0.0);
    float sqrtDisc = sqrt(disc);

    float lambda1 = 0.5 * trace + sqrtDisc;
    float lambda2 = 0.5 * trace - sqrtDisc;

    // 큰 음의 고유값 = 능선 (능선에서 횡방향 곡률이 크게 음)
    return max(-min(lambda1, lambda2), 0.0);
}

void main() {
    vec2 screenPos = vec2(v_uv.x, 1.0 - v_uv.y) * u_viewportSize;
    vec2 worldPos = mod(u_camera + screenPos, u_mapSize);
    vec2 trailUV = worldPos / u_mapSize;

    // 본체 영역 마스킹 (확산 맵)
    float bodyValue = texture(u_trailMap, trailUV).r;
    float zoomFactor = max(1.0, max(u_viewportSize.x / u_mapSize.x,
                                     u_viewportSize.y / u_mapSize.y));
    float veinMin = {{VEIN_MIN}} / zoomFactor;

    if (bodyValue < veinMin) {
        fragColor = vec4(0.0);
        return;
    }

    // Hessian ridge detection (단일 스케일 h=1 먼저, h=2는 후속 추가)
    float ridgeness = computeHessianRidge(trailUV, {{HESSIAN_H}});

    // ridgeness -> 강도 매핑
    float intensity = smoothstep({{RIDGE_THRESHOLD}}, {{RIDGE_SATURATE}}, ridgeness);

    // 맥동
    float pulsePeriod = 120.0;
    float pulsePhase = mod(u_time, pulsePeriod) / pulsePeriod * 2.0 * 3.14159;
    float pulseBase = {{PULSE_MIN}} + ({{PULSE_MAX}} - {{PULSE_MIN}})
                      * (0.5 + 0.5 * sin(pulsePhase));

    // 계층화: 미확산 맵의 원본 값 기준
    float rawValue = texture(u_rawTrailMap, trailUV).r;
    float majorT = smoothstep({{MAJOR_THRESHOLD}} * 0.7, {{MAJOR_THRESHOLD}} * 1.3, rawValue);

    float majorPulse = pulseBase;
    float minorPulse = mix(1.0, pulseBase, 0.3);
    float layerAlpha = mix({{MINOR_ALPHA}}, {{MAJOR_ALPHA}}, majorT);
    float layerPulse = mix(minorPulse, majorPulse, majorT);

    float alpha = intensity * layerAlpha * layerPulse;

    // 색상
    vec3 majorColor = u_isDormant
        ? vec3({{DORMANT_R}}, {{DORMANT_G}}, {{DORMANT_B}})
        : vec3({{MAJOR_R}}, {{MAJOR_G}}, {{MAJOR_B}});
    vec3 minorColor = u_isDormant
        ? vec3({{DORMANT_R}}, {{DORMANT_G}}, {{DORMANT_B}})
        : vec3({{MINOR_R}}, {{MINOR_G}}, {{MINOR_B}});
    vec3 veinColor = mix(minorColor, majorColor, majorT);

    fragColor = vec4(veinColor, alpha);
}
```

텍스처 fetch 수: 1 (bodyValue) + 9 (Hessian) + 1 (rawValue) = **11**. 현재 13보다 적습니다. 멀티스케일(h=2 추가) 시에도 11 + 8 = 19 (center 공유), 성능 문제 없음.

#### 3-2. `src/config.ts` 변경

```typescript
export const VEINS = {
    MIN: 25,
    MAX: 120,
    // STEP: 제거 (Hessian에서는 HESSIAN_H로 대체)
    HESSIAN_H: 1.0,              // ★ Hessian 스케일 (픽셀 단위)
    MAX_ALPHA: 0.8,
    RIDGE_THRESHOLD: 0.5,        // ★ ridgeness smoothstep 시작
    RIDGE_SATURATE: 3.0,         // ★ ridgeness smoothstep 포화
    MAJOR_THRESHOLD: 40,
    MAJOR_ALPHA: 0.30,           // additive 기준 (Phase 1에서 조정됨)
    MINOR_ALPHA: 0.08,           // additive 기준
    PULSE_MIN: 0.5,
    PULSE_MAX: 1.0,
    MAJOR_COLOR: { r: 0.95, g: 0.88, b: 0.35 },
    MINOR_COLOR: { r: 0.80, g: 0.72, b: 0.25 },
    DORMANT_COLOR: { r: 0.45, g: 0.38, b: 0.22 },
};
```

#### 3-3. `src/gpu/shaders/veins.ts` 변경

```typescript
export const VEINS_FRAG = resolveShader(veinsFragSrc, {
    VEIN_MIN: V.MIN.toFixed(1),
    VEIN_MAX: V.MAX.toFixed(1),
    HESSIAN_H: V.HESSIAN_H.toFixed(1),           // ★ 신규
    RIDGE_THRESHOLD: V.RIDGE_THRESHOLD.toFixed(2), // ★ 신규
    RIDGE_SATURATE: V.RIDGE_SATURATE.toFixed(2),   // ★ 신규
    MAJOR_THRESHOLD: V.MAJOR_THRESHOLD.toFixed(1),
    MAJOR_ALPHA: V.MAJOR_ALPHA.toFixed(2),
    MINOR_ALPHA: V.MINOR_ALPHA.toFixed(2),
    PULSE_MIN: V.PULSE_MIN.toFixed(2),
    PULSE_MAX: V.PULSE_MAX.toFixed(2),
    MAJOR_R: V.MAJOR_COLOR.r.toFixed(3),
    MAJOR_G: V.MAJOR_COLOR.g.toFixed(3),
    MAJOR_B: V.MAJOR_COLOR.b.toFixed(3),
    MINOR_R: V.MINOR_COLOR.r.toFixed(3),
    MINOR_G: V.MINOR_COLOR.g.toFixed(3),
    MINOR_B: V.MINOR_COLOR.b.toFixed(3),
    DORMANT_R: V.DORMANT_COLOR.r.toFixed(3),
    DORMANT_G: V.DORMANT_COLOR.g.toFixed(3),
    DORMANT_B: V.DORMANT_COLOR.b.toFixed(3),
});
```

기존의 `STEP`, `RIDGE_SCALE`은 제거되고 `HESSIAN_H`, `RIDGE_THRESHOLD`, `RIDGE_SATURATE`로 대체.

**최로드맵**: Phase 3 성공 기준:

1. **정맥 폭**: 2~5px 범위 유지 (줌인 스크린샷으로 측정)
2. **경계 전환**: 1~2px 이내에서 alpha가 0.8 -> 0으로 전환
3. **면 vs 선 구분**: 본체 중심의 넓은 고밀도 영역이 정맥으로 오검출 안 됨
4. **분기 구조**: 주정맥에서 모세정맥이 분기하는 패턴이 시각적으로 확인됨
5. **밝기 대비**: 정맥이 본체 대비 2~4배 밝음 (additive + intensity)

위험 요소:
- **중간**: `RIDGE_THRESHOLD`, `RIDGE_SATURATE` 튜닝 -- ridgeness 분포를 모르면 blind tuning
- **낮음**: 텍스처 fetch 수 동일/감소 (성능 무관)
- **대안**: ridgeness가 너무 약하면 HESSIAN_H를 2로 올려서 스케일 확대

---

## 파트 2: Plan 초안 작성 (기획자 + 개발자)

**최로드맵**: Spec이 나왔으니 이제 구현 순서와 의존관계를 정리합니다. 각 Step마다 "무엇을 하고 -> 어떻게 검증하는지"를 명시합니다.

### Phase 1 Plan: Additive Blend (예상 0.5일)

**Step 1.1: 블렌딩 변경**
- 파일: `src/gpu/SceneRenderer.ts` 271행
- 변경: `gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)` -> `gl.blendFunc(gl.SRC_ALPHA, gl.ONE)`
- 검증: `npm run build` 통과

**Step 1.2: 파라미터 조정**
- 파일: `src/config.ts`
- 변경: `MAJOR_ALPHA: 0.85 -> 0.30`, `MINOR_ALPHA: 0.15 -> 0.08`
- 검증: `npm run build` 통과

**Step 1.3: 시각 검증**
- `npm run dev` -> 브라우저에서 확인
- 체크리스트:
  - [ ] 정맥이 본체 위에서 밝게 보이는가?
  - [ ] 화이트아웃(순백색 영역)이 없는가?
  - [ ] 큐빅 글로우와 겹쳤을 때 이상 없는가?
  - [ ] 본체 가장자리에서 정맥이 배경 위에 빛나는가?
- alpha 범위(0.25~0.40)에서 최적값 찾기
- 필요시 색상 미세 조정

**Step 1.4: 커밋**
- 커밋 전 diff 확인 (사용자 수정사항 충돌 방지)
- 의존관계: 없음. 단독 실행 가능.

---

### Phase 2 Plan: 미확산 트레일맵 분리 (예상 1~2일)

**Step 2.1: TrailMapGPU에 rawTrail 추가**
- 파일: `src/gpu/TrailMapGPU.ts`
- 변경: `rawTrailTex`, `rawTrailFbo` 추가, `captureRawTrail()`, `getRawTrailTexture()`, dispose() 업데이트
- 검증: `npm run build` 통과
- 의존관계: 없음

**Step 2.2: PhysarumSimulation에서 captureRawTrail() 호출**
- 파일: `src/simulation/PhysarumSimulation.ts`
- 변경: `runDeposit()` 직후 `this.gpu.captureRawTrail()` 추가, `getRawTrailTexture()` 접근자 추가
- 검증: `npm run build` 통과
- 의존관계: Step 2.1 완료

**Step 2.3: SceneRenderer에서 rawTrailTexture 바인딩**
- 파일: `src/gpu/SceneRenderer.ts`
- 변경: `render()` 시그니처에 `rawTrailTexture` 추가, `SceneUniforms`에 `rawTrailMap` 추가, veinsUniforms 초기화 수정, renderPass에서 TEXTURE4 바인딩
- 검증: `npm run build` 통과
- 의존관계: Step 2.1 (rawTrail 텍스처 존재)

**Step 2.4: useGameLoop에서 rawTrailTexture 전달**
- 파일: `src/hooks/useGameLoop.ts`
- 변경: `simulation.getRawTrailTexture()` 호출, `sceneRenderer.render()` 인자 추가
- 검증: `npm run build` 통과
- 의존관계: Step 2.2, 2.3

**Step 2.5: veins.frag.glsl에서 u_rawTrailMap 사용**
- 파일: `src/gpu/shaders/glsl/veins.frag.glsl`
- 변경: `uniform sampler2D u_rawTrailMap` 추가, 3x3 블러 제거, rawTrailMap에서 직접 샘플링
- 검증: `npm run build` 통과
- 의존관계: Step 2.3 (uniform location 등록)

**Step 2.6: config.ts STEP 변경**
- 변경: `VEINS.STEP: 8 -> 2`
- 의존관계: Step 2.5 (미확산 맵이 실제로 사용되어야 의미 있음)

**Step 2.7: 시각 검증**
- `npm run dev` -> 브라우저
- 체크리스트:
  - [ ] 정맥이 이전보다 확실히 좁아졌는가?
  - [ ] 정맥 경계가 더 선명한가?
  - [ ] 시뮬레이션 동역학이 동일한가? (에이전트 이동 패턴 확인)
  - [ ] FPS 하락 없는가?
  - [ ] 본체 외부로 정맥이 누출되지 않는가?
  - [ ] 개별 에이전트 노이즈가 심하지 않은가?
- 노이즈가 문제라면: 미확산 맵에 1패스 블러를 `captureRawTrail()` 후 적용 (대안)

**위험 대안:**
- `glBlitFramebuffer` 실패 시: fullscreen quad + passthrough 셰이더로 복사
- 노이즈 심할 경우: rawTrail에 가벼운 1패스 확산 적용 (sigma=0.8px)

---

### Phase 3 Plan: Hessian Ridge Detection (예상 1~2일)

**Step 3.1: config.ts 파라미터 재구성**
- `STEP`, `RIDGE_SCALE` 제거
- `HESSIAN_H`, `RIDGE_THRESHOLD`, `RIDGE_SATURATE` 추가
- 초기값: H=1.0, THRESHOLD=0.5, SATURATE=3.0 (수학자 검증 후 확정)
- 의존관계: 없음

**Step 3.2: veins.ts placeholder 업데이트**
- `STEP`, `RIDGE_SCALE` 제거 -> `HESSIAN_H`, `RIDGE_THRESHOLD`, `RIDGE_SATURATE` 추가
- 의존관계: Step 3.1

**Step 3.3: veins.frag.glsl 전면 재작성**
- Hessian ridge 함수 추가 (9 fetches)
- main() 로직 교체
- 의존관계: Step 3.1, 3.2, Phase 2 완료

**Step 3.4: 시각 검증 (단일 스케일 h=1)**
- 체크리스트:
  - [ ] 정맥이 선 형태로 보이는가? (면이 아닌 선)
  - [ ] 본체 중심 고밀도 영역이 정맥으로 오검출되지 않는가?
  - [ ] 분기 구조가 보이는가?
  - [ ] 정맥 밝기가 적절한가?
- RIDGE_THRESHOLD / RIDGE_SATURATE 튜닝

**Step 3.5: 멀티스케일 추가 (선택적)**
- h=2 스케일 추가: `computeHessianRidge(trailUV, 2.0)` 호출
- `ridgeness = max(ridgeness1, ridgeness2)`
- 텍스처 fetch: 11 -> 19
- 이 스텝은 h=1 단독으로 충분하면 건너뜀

**Step 3.6: 최종 파라미터 튜닝**
- RIDGE_THRESHOLD, RIDGE_SATURATE, MAJOR_ALPHA, MINOR_ALPHA
- 레퍼런스 이미지와 나란히 비교
- Dr. 김점균 최종 검수

**의존관계 그래프:**
```
Phase 1 → Phase 2 → Phase 3
  1.1─1.2─1.3   2.1─┬─2.2─┬─2.4─2.5─2.6─2.7   3.1─3.2─3.3─3.4─(3.5)─3.6
                     └─2.3─┘
```

---

## 파트 3: 수학자 감수 (이헤시안)

**이헤시안**: spec/plan 초안을 꼼꼼히 검토했습니다. 전체적으로 잘 구성되어 있지만, 수학적으로 **정정이 필요한 부분이 3건**, **개선 권고가 2건** 있습니다.

### 지적 1 (정정 필수): RIDGE_THRESHOLD / RIDGE_SATURATE 초기값이 근거 없음

spec에서 `RIDGE_THRESHOLD: 0.5`, `RIDGE_SATURATE: 3.0`을 제안했는데, 이 값들이 실제 ridgeness 분포와 맞는지 전혀 검증되지 않았습니다.

ridgeness의 크기는 **입력 데이터의 스케일에 직접 의존**합니다. Hessian은 2차 미분이므로, 트레일 값이 V이고 정맥 폭이 w일 때:

```
ridgeness ~ V / w^2
```

구체적으로:
- 수송 채널 중심 트레일 값 V ~ 167 (AGENT.DEPOSIT_AMOUNT / (1 - DECAY_FACTOR))
- 미확산 맵에서 정맥 폭 w ~ 3px (에이전트 수송 채널)
- h = 1px일 때 (HESSIAN_H=1.0):

```
dxx ~ (V_left + V_right - 2*V_center) / h^2
```

정맥 중심에서 횡단 프로파일을 가우시안으로 근사하면: `V(x) = V_peak * exp(-x^2 / (2*sigma^2))`, sigma ~ w/2.35 ~ 1.3px

```
d^2V/dx^2 |_{x=0} = -V_peak / sigma^2 = -167 / 1.69 = -98.8
```

따라서 ridgeness (= -lambda_min) ~ **99** 정도.

smoothstep(0.5, 3.0, 99) = 1.0으로, 사실상 거의 모든 약한 구조도 ridgeness가 0.5를 넘길 겁니다. RIDGE_THRESHOLD는 **50~100 범위**, RIDGE_SATURATE는 **100~200 범위**가 적절합니다.

**수정 제안:**
```typescript
RIDGE_THRESHOLD: 30.0,     // ridgeness 최소 임계 (노이즈 컷오프)
RIDGE_SATURATE: 120.0,     // 포화 ridgeness (주정맥 수준)
```

이 값들도 추정치이므로 시각 튜닝은 필수이지만, 적어도 **올바른 자릿수(order of magnitude)**에 있어야 합니다. 0.5~3.0은 3~4 자릿수 차이로, 첫 시각 테스트에서 "전부 하얗게"라는 결과만 나올 겁니다.

### 지적 2 (정정 필수): Hessian의 h 파라미터와 ridgeness 정규화

spec에서 `h = 1.0`을 "픽셀 단위"로 사용하면서 `dxx = (l + r - 2*c) / (h*h)`로 나누고 있는데, 이때 h의 단위가 혼재합니다.

현재 셰이더에서 `dx = vec2(h / u_mapSize.x, 0.0)` -- 이건 **UV 좌표계**에서 h 픽셀에 해당하는 오프셋입니다. 하지만 `dxx = (l + r - 2*c) / (h*h)` -- 여기서 h는 **픽셀 단위**입니다.

텍스처 fetch는 UV 좌표로 하고, Hessian 나눗셈은 픽셀 단위로 한다면, 결과의 ridgeness 단위가 "트레일 값 / 픽셀^2"이 됩니다. h=1일 때는 나눗셈이 1이라 문제가 없지만, **h=2로 멀티스케일 할 때** 중요해집니다:

```
h=1: ridgeness = -(l + r - 2c) / 1  = 큰 값
h=2: ridgeness = -(l + r - 2c) / 4  = 작은 값 (같은 구조라도)
```

`max(ridgeness1, ridgeness2)`를 하면 h=1이 항상 이길 수 있습니다. 멀티스케일을 의미 있게 결합하려면 **정규화**가 필요합니다.

하지만 실용적 관점에서, h=1과 h=2는 서로 다른 폭의 정맥을 검출하는 것이므로, 같은 폭의 정맥에 대해 h가 적합할 때 ridgeness가 최대가 됩니다. 넓은 정맥(~5px)은 h=2에서 더 큰 ridgeness를 줄 수 있어요.

**수정 제안:** Phase 3 Step 3.5에서 멀티스케일 결합 시 `h^2`로 나누지 말고, 나눗셈 없이 raw 2차 차분을 사용하는 것을 고려하세요:

```glsl
// 방법 A: 정규화 없이 (h^2 나눗셈 제거)
float fxx = (l + r - 2.0 * c);  // h^2로 안 나눔
float fyy = (u_ + d - 2.0 * c);
float fxy = (tr + bl - tl - br) / 4.0;
```

이렇게 하면 h가 클수록 검출 범위만 넓어지고, ridgeness 크기는 구조의 실제 높이에만 의존합니다. 넓은 정맥은 높이가 높으므로 자동으로 큰 ridgeness를 가집니다.

**주의**: 이 방법은 수학적으로는 "Hessian"이 아닌 "2차 차분"이지만, 멀티스케일 결합의 실용성 면에서는 더 안정적입니다. 단일 스케일(h=1)에서는 차이 없습니다.

### 지적 3 (주의 필요): `fract()` 래핑과 Hessian 정확성

셰이더에서 토러스 래핑을 `fract()`로 구현하고 있는데, 이건 `GL_REPEAT` 텍스처 래핑과 중복입니다. `TrailMapGPU.createR32FTexture()`에서 이미 `gl.REPEAT`를 설정하고 있으므로, `fract()` 호출이 불필요합니다.

하지만 여기서 중요한 건, **맵 경계에서 Hessian이 올바른 값을 내는가**입니다. `GL_REPEAT`가 있으면 UV가 0~1 범위를 벗어나도 자동으로 래핑되므로, 경계에서도 올바른 이웃 값을 참조합니다. `fract()`가 이미 있으니 더블 세이프이긴 한데, 성능 면에서 9개 fract() 호출을 제거할 수 있습니다.

단, `fract()`를 제거하면 코드 의도가 덜 명확해지므로, 이건 정정이 아닌 **개선 권고**입니다.

### 개선 권고 1: densityT 제거

Phase 3 셰이더에서 `densityT`(확산 맵 기반 밀도 가중치)가 alpha 계산에서 빠졌는데, 이건 의도적인가요? 현재 Phase 2 셰이더에는 `alpha = densityT * ridgeStrength * layerAlpha * layerPulse`로 densityT가 포함되어 있습니다.

Hessian ridgeness는 이미 "주변보다 얼마나 뾰족한가"를 측정하므로, 추가로 밀도 가중치를 곱하면 주정맥이 이중으로 강화됩니다. densityT 제거는 수학적으로 합리적이에요. 다만, **저밀도 영역의 약한 구조가 과도하게 보일 수** 있습니다.

대안으로, `bodyValue` 기반 마스킹의 `veinMin` 임계값을 올려서 저밀도 영역을 더 공격적으로 걸러내는 것을 권합니다.

### 개선 권고 2: ridgeness의 부호 처리

```glsl
return max(-min(lambda1, lambda2), 0.0);
```

이 코드에서 `min(lambda1, lambda2)`는 항상 `lambda2` (= 0.5*trace - sqrtDisc)입니다. 왜냐하면 `sqrtDisc >= 0`이므로 `lambda2 <= lambda1`이 항상 성립합니다. 따라서 `min()` 대신 직접 `lambda2`를 사용하면 됩니다:

```glsl
return max(-lambda2, 0.0);
```

이건 기능 변경이 아니라 코드 명확성 개선입니다. 하지만 `lambda2`가 반드시 더 작은 고유값이라는 사실은 수식에서 자명하므로, 의미적으로도 더 정확합니다.

---

### 감수 요약

| # | 유형 | 항목 | 심각도 |
|---|------|------|--------|
| 1 | **정정 필수** | RIDGE_THRESHOLD/SATURATE 초기값: 0.5/3.0 -> 30.0/120.0 | 높음 (3~4 자릿수 오류) |
| 2 | **정정 필수** | 멀티스케일 h^2 나눗셈: 제거 권고 (raw 2차 차분 사용) | 중간 (단일 스케일에서는 무관) |
| 3 | **주의** | fract() 중복 (GL_REPEAT와 이중) | 낮음 |
| 4 | **개선** | densityT 제거 의도 확인, 저밀도 마스킹 강화 | 낮음 |
| 5 | **개선** | `min(lambda1, lambda2)` -> `lambda2` 직접 사용 | 매우 낮음 |

**이헤시안**: 지적 1번은 반드시 반영해야 합니다. smoothstep 범위가 3~4 자릿수 틀리면 첫 테스트에서 "전부 하얗게" 또는 "전부 검게" 중 하나가 나와서, 버그인지 파라미터 문제인지 구분이 안 됩니다. 올바른 자릿수에서 시작해야 시각 튜닝이 의미 있어요.

지적 2번은 Phase 3 Step 3.5(멀티스케일)에서만 관련되므로, 단일 스케일 먼저 완성한 후에 적용해도 됩니다.

---

## 파트 4: 전문가 최종 리뷰 (Dr. 김점균)

**Dr. 김점균**: (spec/plan과 감수 결과를 꼼꼼히 읽은 후)

전체적으로 인상적인 수준의 기술 명세입니다. 수학자의 감수가 특히 날카로웠고, 지적 1번의 3~4 자릿수 오류는 개발 중에 상당한 시간을 낭비할 뻔했습니다. 반영이 필수예요.

### 생물학적/시각적 관점 검토

**Phase 1 (Additive Blend)에 대해:**

Additive blend의 물리적 근거는 타당합니다. Dark-field 현미경에서 농축 원형질은 실제로 "빛을 더하는" 방식으로 밝아집니다. 다만 한 가지 우려가 있어요:

additive blend에서 정맥이 본체 바깥 -- 즉 배경(어두운 초록) 위에 있을 때와 본체(올리브) 위에 있을 때의 시각적 차이가 큽니다. 배경 위에서는 `(0.03, 0.08, 0.04) + 정맥` = 거의 정맥 색 그대로, 본체 위에서는 훨씬 밝아지죠. 이 차이가 **너무 크면** 정맥이 본체 경계에서 "끊긴 것처럼" 보일 수 있어요.

실물에서는 정맥이 본체 내부에서 가장자리를 거쳐 의사족(pseudopod) 끝까지 연속적으로 이어집니다. 색조 변화는 있지만 "끊김"은 없어요.

**요구사항 추가**: Phase 1 시각 검증에서 **본체 경계를 가로지르는 정맥의 연속성**을 확인 항목으로 추가해 주세요.

**Phase 2 (미확산 맵)에 대해:**

이 Phase가 가장 기대됩니다. 생물학적으로 정확한 접근이에요 -- 확산된 페로몬이 아닌 원형질 자체의 위치를 보여주는 것이니까요.

한 가지 추가 코멘트: 미확산 맵에서 에이전트가 "한 줄로 서서 이동"하는 수송 채널과, "넓게 퍼져 있는" 본체 중심부의 차이가 명확히 나타날 겁니다. 이게 정확히 실물의 구조와 일치해요:

- **수송 채널**: 좁고, 빠른 셔틀 흐름, 높은 에이전트 밀도/단위 폭
- **본체 중심**: 넓고, 느린 아메바 흐름, 낮은 에이전트 밀도/단위 면적

Hessian이 이 차이를 자동으로 잡아낼 겁니다 -- 좁은 채널은 큰 횡방향 곡률, 넓은 중심부는 작은 곡률.

**Phase 3 (Hessian)에 대해:**

수학자의 ridgeness 추정치(~99)가 맞다면, smoothstep(30, 120, ridgeness)로:
- 주정맥 (ridgeness ~100): intensity ~ 0.8~1.0
- 모세정맥 (ridgeness ~50): intensity ~ 0.2~0.4
- 본체 중심 (ridgeness ~5): intensity ~ 0

이 분포가 실물과 잘 맞아요! 주정맥은 선명하고, 모세정맥은 약간 보이고, 본체 중심은 매끈한 게 정확합니다.

### 추가 요구사항

1. **맥동의 위상 다양성**: 현재 모든 정맥이 같은 위상으로 맥동합니다(`u_time` 기반 단일 sine). 실물에서는 주정맥과 모세정맥의 맥동 위상이 다르고, 심지어 같은 정맥 내에서도 위치에 따라 위상이 달라요 ("역류 현상" -- cytoplasmic shuttle streaming). 이건 Phase 3 이후의 추가 개선으로 남겨두면 되지만, spec에 "미래 개선 항목"으로 언급해 주세요.

2. **정맥 너비의 맥동**: 실물에서 정맥은 맥동할 때 **폭도 변합니다**. 수축기에는 좁아지고 이완기에는 넓어져요. 이것도 현재 구현에서는 alpha만 변하고 폭은 고정인데, Hessian threshold를 맥동과 연동하면 구현 가능합니다. 이것도 미래 개선 항목.

### 최종 판정

**조건부 승인**

승인 조건:
1. (**필수**) 수학자 지적 1번 반영 -- RIDGE_THRESHOLD/SATURATE 초기값을 올바른 자릿수로 수정 (30.0/120.0 또는 유사 범위)
2. (**필수**) Phase 1 시각 검증 항목에 "본체 경계 연속성" 추가
3. (**권고**) 수학자 지적 2번 -- 멀티스케일 시 h^2 나눗셈 처리 방침 결정 (단일 스케일 우선이면 후순위 가능)
4. (**참고**) 맥동 위상 다양성, 정맥 너비 맥동은 미래 개선 항목으로 기록

사유: 기술적 접근이 생물학적으로 정확하고, 3단계 점진적 개선이 현실적입니다. 수학자의 감수가 치명적 파라미터 오류를 사전에 잡아냈으므로, 이를 반영하면 첫 시각 테스트에서 의미 있는 결과를 볼 수 있을 것입니다.

Phase 2 완료 시점에서 중간 리뷰를 요청합니다. 그때 "내 점균류"가 보이기 시작하면, Phase 3의 세부 파라미터 튜닝에 대해 더 구체적인 피드백을 드릴 수 있습니다.

---

## 감수 반영 최종 Spec/Plan 요약

### 수정 사항 (감수 + 리뷰 반영)

| # | 원래 | 수정 후 | 근거 |
|---|------|---------|------|
| 1 | RIDGE_THRESHOLD: 0.5 | **30.0** | ridgeness ~ V/w^2 ~ 99, smoothstep 범위 맞춤 |
| 2 | RIDGE_SATURATE: 3.0 | **120.0** | 주정맥 ridgeness가 이 범위에서 포화 |
| 3 | Phase 1 검증 항목 5개 | **6개** (+본체 경계 연속성) | 전문가 요구 |
| 4 | 멀티스케일 h^2 나눗셈 | **raw 2차 차분 (h^2 제거)** 또는 단일 스케일 우선 | 수학자 지적 |
| 5 | `min(lambda1, lambda2)` | `lambda2` 직접 사용 | 코드 명확성 |

### 최종 파라미터 정리 (Phase 3 기준)

```typescript
export const VEINS = {
    MIN: 25,
    MAX: 120,
    HESSIAN_H: 1.0,
    MAX_ALPHA: 0.8,
    RIDGE_THRESHOLD: 30.0,    // ★ 수학자 검증 반영
    RIDGE_SATURATE: 120.0,    // ★ 수학자 검증 반영
    MAJOR_THRESHOLD: 40,
    MAJOR_ALPHA: 0.30,        // Phase 1에서 additive 기준 조정
    MINOR_ALPHA: 0.08,
    PULSE_MIN: 0.5,
    PULSE_MAX: 1.0,
    MAJOR_COLOR: { r: 0.95, g: 0.88, b: 0.35 },
    MINOR_COLOR: { r: 0.80, g: 0.72, b: 0.25 },
    DORMANT_COLOR: { r: 0.45, g: 0.38, b: 0.22 },
};
```

### 최종 변경 파일 요약 (전체 Phase)

| Phase | 파일 | 변경 유형 |
|-------|------|----------|
| 1 | `src/gpu/SceneRenderer.ts` | 블렌딩 함수 1행 |
| 1 | `src/config.ts` | VEINS 2~3 파라미터 |
| 2 | `src/gpu/TrailMapGPU.ts` | rawTrailTex/FBO 추가, captureRawTrail(), getRawTrailTexture(), dispose() |
| 2 | `src/simulation/PhysarumSimulation.ts` | captureRawTrail() 호출, getRawTrailTexture() 접근자 |
| 2 | `src/gpu/SceneRenderer.ts` | render() 시그니처, SceneUniforms, veinsUniforms, TEXTURE4 바인딩 |
| 2 | `src/hooks/useGameLoop.ts` | rawTrailTexture 전달 |
| 2 | `src/gpu/shaders/glsl/veins.frag.glsl` | u_rawTrailMap 추가, 3x3 블러 제거, rawTrailMap 사용 |
| 2 | `src/config.ts` | VEINS.STEP: 8 -> 2 |
| 3 | `src/gpu/shaders/glsl/veins.frag.glsl` | 전면 재작성 (Hessian) |
| 3 | `src/gpu/shaders/veins.ts` | placeholder 교체 |
| 3 | `src/config.ts` | VEINS 파라미터 재구성 |

### 미래 개선 항목 (Phase 3 이후)

1. 맥동 위상 다양성 (위치 기반 위상 오프셋)
2. 정맥 너비 맥동 (threshold 연동)
3. ridgeness 히스토그램 시각화 도구 (디버그용)

### 총 예상 공수

- Phase 1: 0.5일
- Phase 2: 1~2일
- Phase 3: 1~2일
- **합계: 3~5일**

---

**최로드맵**: 감수와 리뷰가 모두 반영되었습니다. 조건부 승인 조건 4개 중 필수 2건을 반영했고, 권고 2건은 각각 "단일 스케일 우선 후 반영"과 "미래 개선 항목 기록"으로 처리했습니다.

이 문서를 기반으로 `/spec`과 `/plan`을 정식 작성하면 됩니다. Phase 1부터 시작하시죠.

**전원**: 동의합니다.
