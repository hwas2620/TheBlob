# Physarum 본체 렌더링 품질 개선 — 구현 계획

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/config.ts` | BLOB_BODY 파라미터 조정 (NOISE_FLOOR, FADE_START, MEMBRANE_ALPHA, BODY_MAX_ALPHA, ALPHA_GAMMA 추가) |
| `src/gpu/shaders/glsl/blob_body.frag.glsl` | smoothstep → pow 커브 전환 |
| `src/gpu/shaders/blob_body.ts` | ALPHA_GAMMA 플레이스홀더 추가 |

파이프라인 구조 변경 없음. SceneRenderer, TrailMapGPU 변경 없음.

## 구현 전략

shader-dev.md 규칙에 따라 **자율 반복 루프**로 진행:
```
변경 → 스크린샷 → 자체 평가 → 결과보고서 → 불만족시 반복
```

단순한 것부터 시작, 효과 부족시 단계적으로 확대.

## 구현 결과

### Step 1: 알파 커브 조정 (config.ts만 변경) ✅

| 파라미터 | 원래 | 최종 | 근거 |
|---------|------|------|------|
| NOISE_FLOOR | 0.3 | 2.0 | 확산 노이즈 공격적 제거 (구름 감소) |
| FADE_START | 2 | 8 | 점막→본체 전환 임계값 올려서 엣지 선명화 |
| MEMBRANE_ALPHA | 0.15 | 0.06 | 점막 거의 안 보이게 (구름 효과 제거) |
| BODY_MAX_ALPHA | 0.85 | 0.92 | 중심부 더 불투명하게 (질량감) |

**이터레이션**: 5회 (Iter 1~5). NOISE_FLOOR 1.0→0.5→0.8→2.0, MEMBRANE_ALPHA 0.3→0.25→0.18→0.06 등 점진적 조정.

### Step 2: pow 커브 — 내부 밀도 차이 표현 (셰이더 변경) ✅

원래 계획은 `smoothstep(ALPHA_EDGE, ALPHA_FULL, densityT)` 이었으나,
`pow(densityT, ALPHA_GAMMA)` 방식이 더 적합하다고 판단.

```glsl
// 변경 전: 조기 포화
float alphaT = smoothstep(0.1, 0.5, densityT);

// 변경 후: pow 커브 — 빠른 엣지 상승 + 내부 차이 유지
float alphaT = pow(densityT, {{ALPHA_GAMMA}});  // ALPHA_GAMMA = 0.3
```

**근거**: smoothstep은 파라미터 2개(edge, full)가 필요하고 곡선 형태가 제한적.
pow(x, γ<1)은 γ 하나로 엣지 경사도와 내부 변화를 동시 제어 가능.

### Step 3: OccupancyMap 혼합 — 시도 후 철회 ❌

occupancyMap 해상도가 1:1 (1500×1500)이라 개별 에이전트 위치가 격자 노이즈로 드러남.
OCC_SATURATE=5→1, OCC_MIN_BLEND=0.4→0.85 조정에도 근본적 해상도 문제 해결 불가.
**블러된 occupancy map이 필요하지만 별도 GPU 패스 필요 → 이번 스코프 밖.**

## 최종 파라미터

```typescript
BLOB_BODY = {
  FADE_START: 8,
  NOISE_FLOOR: 2.0,
  MEMBRANE_ALPHA: 0.06,
  BODY_MAX_ALPHA: 0.92,
  ALPHA_GAMMA: 0.3,      // 신규
  // 나머지 기존 값 유지
}
```

## 교훈

- **점막(membrane) 영역이 구름의 주범**: 트레일맵 확산으로 본체 주변에 항상 기울기(gradient) 존재 → 점막 렌더링 → 구름. MEMBRANE_ALPHA 극소화로 해결.
- **pow(x, γ) > smoothstep**: 셰이더 알파 커브에서 파라미터 1개로 엣지 경사도+내부 변화 동시 제어 가능.
- **OccupancyMap 직접 사용 한계**: 1:1 해상도는 본체 렌더링용으로 너무 세밀. 밀집도 뷰 모드(히트맵)에는 적합하지만, 알파 블렌딩에 사용하면 격자 노이즈 발생.

## 미래 개선 가능성

- **블러된 Occupancy Map**: 별도 GPU 패스로 occupancy를 가우시안 블러 후 본체 알파에 곱하면 엣지 날카로움 개선 가능
- **Temporal Smoothing**: Phase 4-3에서 예정된 IIR 필터 적용 시 추가적인 노이즈 감소 기대
