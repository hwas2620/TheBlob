# Physarum 본체 렌더링 품질 개선 — 구현 계획

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/config.ts` | BLOB_BODY 파라미터 조정 |
| `src/gpu/shaders/glsl/blob_body.frag.glsl` | 알파 커브 수정 + occupancyMap 활용 |
| `src/gpu/shaders/blob_body.ts` | 새 플레이스홀더 추가 (필요시) |

파이프라인 구조 변경 없음. SceneRenderer, TrailMapGPU 변경 없음.

## 구현 전략

shader-dev.md 규칙에 따라 **자율 반복 루프**로 진행:
```
변경 → 스크린샷 → 자체 평가 → 결과보고서 → 불만족시 반복
```

단순한 것부터 시작, 효과 부족시 단계적으로 확대.

## 구현 단계

### Step 1: 알파 커브 조정 (config.ts만 변경)

가장 단순한 변경으로 효과 측정. 셰이더 코드 수정 없이 파라미터만.

**변경 대상 — `src/config.ts` BLOB_BODY:**

| 파라미터 | 현재 | 변경 | 근거 |
|---------|------|------|------|
| NOISE_FLOOR | 0.3 | 1.0 | 점막 헤일로 범위 축소 (구름 감소) |
| FADE_START | 2 | 5~8 | 점막→본체 전환 임계값 올려서 엣지 선명화 |
| MEMBRANE_ALPHA | 0.15 | 0.25~0.35 | 좁아진 점막이 더 뚜렷해야 경계 인식 |
| BODY_MAX_ALPHA | 0.85 | 0.92 | 중심부 더 불투명하게 (질량감) |

**검증**: 스크린샷 → 레퍼런스 비교. 구름 감소, 엣지 선명도 향상 확인.

### Step 2: S커브 완화 — 내부 밀도 차이 표현 (셰이더 변경)

현재 `smoothstep(0.1, 0.5, densityT)`는 densityT 0.5 (avgVal≈76)에서 포화.
본체 내부 대부분이 avgVal>76이므로 전부 같은 알파 → 평탄.

**변경 — `blob_body.frag.glsl` 3단계 알파 계산:**

```glsl
// 현재: 조기 포화
float alphaT = smoothstep(0.1, 0.5, densityT);

// 변경: 더 넓은 범위에서 밀도 차이 반영
float alphaT = smoothstep({{ALPHA_EDGE}}, {{ALPHA_FULL}}, densityT);
```

새 파라미터 `ALPHA_EDGE`, `ALPHA_FULL`을 config.ts에 추가:
- `ALPHA_EDGE`: 0.02~0.05 (더 빨리 불투명 시작 = 엣지 선명)
- `ALPHA_FULL`: 0.85~0.95 (더 늦게 포화 = 내부 밀도 차이 유지)

**검증**: 본체 내부에서 밀도 차이가 보이는지. 중심↔주변 알파 차이 확인.

### Step 3: OccupancyMap 혼합 — 엣지 강화 + 질감 (셰이더 변경)

Step 1-2로 부족할 경우. OccupancyMap은 이미 셰이더에 바인딩됨 (TEXTURE2).

**활용 방식**: trailMap 알파에 occupancy 밀도를 곱해서 보정.

```glsl
float occ = texture(u_occupancyMap, trailUV).r;
float occFactor = smoothstep(0.0, {{OCC_SATURATE}}, occ);

// trailMap 알파 × occupancy 보정 (에이전트 없는 곳 = 더 투명)
float finalAlpha = alpha * mix({{OCC_MIN_BLEND}}, 1.0, occFactor);
```

- `OCC_SATURATE`: occupancy 몇 이상이면 "충분히 밀집" (5~10)
- `OCC_MIN_BLEND`: 에이전트 없는 영역의 알파 배율 (0.3~0.6)

**효과**:
- 에이전트 밀집 영역 = 불투명 (질량감)
- 에이전트 희박 영역 = 반투명 (정맥 사이 투명 → 레퍼런스와 일치)
- 엣지가 occupancy 기준으로 더 날카로워짐

**주의**: occupancy는 프레임별 갱신 → 잠재적 깜빡임. 필요시 trailMap과 가중 평균으로 안정화.

### Step 4: 검증

- `npm run build` 통과
- 브라우저에서 시각 확인 (자율 반복 루프 결과보고서)
- 레퍼런스 이미지(physarum-real/03, 06)와 비교

## 의존성

```
Step 1 (config만) → 평가
  ↓ 부족하면
Step 2 (S커브) → 평가
  ↓ 부족하면
Step 3 (occupancy) → 평가
```

각 Step은 독립적으로 커밋 가능. Step 1만으로 충분하면 2-3 생략.

## 위험 요소

- **occupancy 깜빡임**: 에이전트가 매 프레임 이동 → occupancy 변동. `mix(trail, occ, weight)`로 완화 가능
- **기존 코드 주석의 경고**: `NOISE_FLOOR` 주석에 "높이면 내부 검은 구멍 발생" → Step 1에서 주의깊게 관찰
- **줌 레벨 영향**: zoomFactor에 따라 adjustedNoise/Threshold 변경됨 → 줌인/줌아웃 모두 테스트
