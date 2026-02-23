# Blob 본체 렌더링 — Trailmap 직접 렌더링으로 교체

## 현재 상태

### 관련 파일
- `src/gpu/shaders/glsl/blob_body.frag.glsl` — 블롭 본체 프래그먼트 셰이더
- `src/gpu/shaders/blob_body.ts` — 셰이더 플레이스홀더 치환
- `src/config.ts` — `BLOB_BODY` 파라미터

### 현재 동작
`blob_body.frag.glsl`의 페로몬 뷰 분기:

```glsl
float occupancy = texture(u_occupancyMap, trailUV).r;
if (occupancy < 1.0) {
    fragColor = vec4(0.0);  // 에이전트 없으면 무조건 투명
    return;
}
float occupancyAlpha = clamp(occupancy / 30.0, 0.1, 1.0);
// ...trail 값으로 색상 계산 후 occupancyAlpha로 알파 결정
```

렌더링 파이프라인에서 `blob_body`는 `showBlobGraphics=true`일 때만 그려지며,
`showBlobGraphics`는 키2(에이전트 표시)와 반대로 토글된다.

## 문제 정의

**occupancy 기반 렌더링의 구조적 한계:**

| 문제 | 설명 |
|------|------|
| 에이전트 없는 픽셀 무시 | 100k 에이전트가 1500×1500 맵에 4.4% 밀도 → 픽셀 대부분이 투명 |
| trail이 쌓여도 무시됨 | 에이전트가 지나간 흔적(trailmap)이 있어도, 현재 에이전트가 없으면 안 보임 |
| 거친 점 뭉치 형태 | occupancy 픽셀만 보이므로 부드러운 슬라임 형태가 불가 |
| 에이전트 모드와 역할 중복 | 키2(에이전트 점 표시)가 더 자연스럽게 보여서 사용자가 blob_body를 끄게 됨 |

**Physarum의 핵심은 트레일 네트워크다.** 에이전트는 트레일을 남기고, 그 트레일에 다시 모인다. 시각적으로 보여야 할 것은 에이전트 위치가 아니라 **트레일이 쌓인 패턴**이다.

## 요구사항

- [ ] `blob_body` 셰이더에서 `occupancy` 기반 렌더링 제거
- [ ] `trail` 값을 직접 사용하여 블롭 본체 렌더링
- [ ] 낮은 trail 값 → 희미한 촉수 / 높은 trail 값 → 밝은 본체 (연속 그라데이션)
- [ ] 기존 `u_occupancyMap` uniform은 `u_viewMode == 1` (밀집도 뷰)에서만 사용 유지
- [ ] 줌 레벨 보정 유지 (현재 `zoomFactor` 로직 그대로)
- [ ] 휴면(dormant) 색상 분기 유지
- [ ] `BLOB_BODY` config 파라미터 활용 (FADE_START, MAX_VALUE, 색상 등)
- [ ] build(`npm run build`) 통과

## 접근 방식

| 방식 | 설명 | 장점 | 단점 |
|------|------|------|------|
| A. trail 단순 임계값 | avgVal >= threshold면 렌더링 | 구현 간단 | 부드럽지 않음 |
| B. trail smoothstep 그라데이션 | trail → smoothstep → alpha | 부드러운 페이드인/아웃 | 파라미터 튜닝 필요 |
| C. trail + 다단계 색상 | trail 구간별 색상 혼합 | 깊이감 표현 | 복잡도 증가 |

→ **선택: B (smoothstep 그라데이션)** — 에이전트 모드의 자연스러움과 유사한 부드러운 형태를 trail 기반으로 재현

## 데이터 흐름

```
TrailMapGPU (diffuse/decay)
    ↓ trailTexture (RGBA32F, .r 채널 = 페로몬 강도)
blob_body.frag.glsl
    ├── 9-tap 평균 샘플링 (3×3 이웃, zoomFactor 보정)
    ├── avgVal < FADE_START → 투명 (배경 노이즈 제거)
    ├── smoothstep(FADE_START, MAX_VALUE, avgVal) → intensity
    ├── mix(darkColor, baseColor, sqrt(intensity)) → 색상
    └── alpha = smoothstep(FADE_START, FADE_START*3, avgVal) → 페이드인
```

## 셰이더 변경 요약

**제거:**
```glsl
float occupancy = texture(u_occupancyMap, trailUV).r;
if (occupancy < 1.0) { fragColor = vec4(0.0); return; }
float occupancyAlpha = clamp(occupancy / 30.0, 0.1, 1.0);
```

**교체:**
```glsl
// trail 값 기반 직접 렌더링
// avgVal 계산 (기존 9-tap 유지)
float intensity = smoothstep(adjustedThreshold, maxValue, avgVal);
float alpha = smoothstep(adjustedThreshold, adjustedThreshold * 3.0, avgVal);
vec3 bodyColor = mix(darkColor, baseColor, sqrt(intensity));
fragColor = vec4(bodyColor, alpha);
```

## 기대 효과

- 트레일이 쌓인 경로 = 밝게, 엣지 = 희미하게 → 자연스러운 슬라임 네트워크
- 에이전트가 없어도 흔적이 보임 → Physarum 확산 패턴 시각화
- 기존 에이전트 모드(키2)와 상호보완적: 에이전트 ON = 실시간 위치, OFF = 트레일 네트워크
