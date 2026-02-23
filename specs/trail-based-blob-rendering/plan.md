# Blob 본체 Trail 기반 렌더링 구현 계획

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/gpu/shaders/glsl/blob_body.frag.glsl` | 페로몬 뷰: occupancy 체크 제거, trail smoothstep 알파로 교체 |

그 외 모든 파일 변경 없음 (`blob_body.ts`, `SceneRenderer.ts`, `config.ts` 등)

---

## 구현 단계

### Step 1: blob_body.frag.glsl 페로몬 뷰 수정

**파일:** `src/gpu/shaders/glsl/blob_body.frag.glsl`

**제거 (6줄, 52~59):**
```glsl
// 에이전트 밀집도 체크 (단일 픽셀 - 밀집도 뷰와 동일 방식)
float occupancy = texture(u_occupancyMap, trailUV).r;
if (occupancy < 1.0) {
    fragColor = vec4(0.0);
    return;
}

// 에이전트 수에 비례한 알파 (1~30 → 0.1~1.0)
float occupancyAlpha = clamp(occupancy / 30.0, 0.1, 1.0);
```

**수정 (마지막 2줄, 97~98):**
```glsl
// Before
vec3 bodyColor = mix(darkColor, baseColor, sqrt(densityT));
fragColor = vec4(bodyColor, occupancyAlpha);

// After
vec3 bodyColor = mix(darkColor, baseColor, sqrt(densityT));
float alpha = smoothstep(adjustedThreshold, adjustedThreshold * 3.0, avgVal);
fragColor = vec4(bodyColor, alpha);
```

**변경 후 페로몬 뷰 흐름:**
```
trailUV 계산
→ 9-tap 평균 (avgVal)
→ avgVal < adjustedThreshold → 투명 (기존 노이즈 제거 유지)
→ densityT = clamp((avgVal - adjustedThreshold) / (maxValue - adjustedThreshold))
→ bodyColor = mix(darkColor, baseColor, sqrt(densityT))  [기존 그대로]
→ alpha = smoothstep(adjustedThreshold, adjustedThreshold*3, avgVal)  [신규]
→ fragColor = vec4(bodyColor, alpha)
```

`u_occupancyMap` uniform 선언과 밀집도 뷰 분기(`u_viewMode == 1`)는 **그대로 유지** — 키4 밀집도 뷰 기능 보존.

---

### Step 2: 검증

```bash
npm run build   # TypeScript + Vite 빌드 통과 확인
```

브라우저 확인:
- 기본 모드: trail이 쌓인 네트워크 형태가 부드럽게 보임
- 키4 밀집도 뷰: 기존과 동일하게 히트맵 동작
- 키2 에이전트 토글: 여전히 정상 동작

---

## 의존성

Step 1 → Step 2 (순차)

---

## 위험 요소

| 항목 | 설명 | 대응 |
|------|------|------|
| alpha 너무 연함 | `adjustedThreshold * 3.0`이 너무 높으면 전체적으로 흐릿 | `config.ts` `BLOB_BODY.FADE_START` 낮추거나 multiplier 조정 |
| alpha 너무 진함 | 촉수/엣지까지 불투명해져 형태 구분 안 됨 | multiplier를 높이거나 `MAX_VALUE` 조정 |
| 빌드 오류 없음 | GLSL 변경이므로 TypeScript 에러는 없음 | 런타임 셰이더 컴파일 오류만 주의 |

파라미터 튜닝이 필요할 경우 `config.ts`의 `BLOB_BODY` 값만 조정하면 됨 (셰이더 재컴파일 자동):
- `FADE_START: 2` → trail 2 이상이면 표시 시작 (현재 적절)
- `MAX_VALUE: 60` → trail 60에서 최대 밝기 (정상 상태 평균 ~133이므로 일찍 포화 → 더 밝게 보임)
