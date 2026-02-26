# 본체 렌더링 품질 개선 — 결과 보고서

## 요약

**목표**: Physarum 본체의 시각적 품질 개선 (구름→덩어리, 잉크→질량감, 확산→촉수)
**결과**: 중간 수준 개선. 덩어리감과 엣지 선명도는 향상되었으나, 내부 텍스처와 촉수 형태에는 구조적 한계.

## 이터레이션 기록

| Iter | 변경 | 파일 | 결과 |
|------|------|------|------|
| 0 | 기준점 | - | `screenshots/body-iter0-baseline.png` |
| 1 | NOISE_FLOOR=1.0, FADE_START=5, MEM_ALPHA=0.3 | config | 엣지 선명화 but 내부 검은 구멍 발생 |
| 2 | NOISE_FLOOR=0.5, MEM_ALPHA=0.25 | config | 구멍 해결, 하지만 내부 어두운 패치 |
| 3 | smoothstep→pow(densityT, 0.35) | shader | 내부 구멍 해결, 질량감 향상, 엣지 아직 구름 |
| 4 | NOISE_FLOOR=0.8, FADE_START=8, MEM_ALPHA=0.18 | config | 좋아졌으나 하단 돌출부 구름 잔존 |
| 5 | **NOISE_FLOOR=2.0, MEM_ALPHA=0.06, GAMMA=0.3** | config | **최선 결과** — 구름 대폭 감소, 엣지 선명 |
| 6 | OccupancyMap 혼합 (OCC_SAT=5, MIN=0.4) | shader | 격자 노이즈 — 실패 |
| 7 | OCC_SAT=1, MIN=0.85 (미묘한 효과) | config | 여전히 점 텍스처 — 철회 |

## 최종 채택: Iter 5

### 변경된 파라미터

| 파라미터 | Before | After | 변경 이유 |
|---------|--------|-------|----------|
| NOISE_FLOOR | 0.3 | 2.0 | 확산 노이즈 공격적 제거 |
| FADE_START | 2 | 8 | 점막→본체 임계값 상향 |
| MEMBRANE_ALPHA | 0.15 | 0.06 | 점막 극소화 (구름 제거) |
| BODY_MAX_ALPHA | 0.85 | 0.92 | 중심부 불투명도 증가 |
| ALPHA_GAMMA | (없음) | 0.3 | pow 커브 감마 (신규) |

### 셰이더 변경

```glsl
// Before: smoothstep (조기 포화)
float alphaT = smoothstep(0.1, 0.5, densityT);

// After: pow 커브 (빠른 상승 + 내부 차이 유지)
float alphaT = pow(densityT, {{ALPHA_GAMMA}});
```

## 개선된 점

1. **구름 효과 대폭 감소**: NOISE_FLOOR 2.0 + MEMBRANE_ALPHA 0.06으로 본체 주변 헤일로 최소화
2. **덩어리감 향상**: BODY_MAX_ALPHA 0.92 + pow 커브로 중심부가 단단한 질량체처럼 보임
3. **엣지 선명도**: FADE_START 8로 점막→본체 전환이 더 빠르게 일어남

## 남은 한계

1. **가장자리 구름 잔존**: 트레일맵 확산의 본질적 한계 — 에이전트 이동 후 남은 트레일이 퍼지면서 가장자리에 약간의 반투명 영역 형성
2. **내부 텍스처 부족**: 본체 내부가 균일한 노란색 — 실물 physarum의 정맥/네트워크 구조가 본체 렌더링에서는 보이지 않음 (별도 vein 레이어로 처리해야 함)
3. **촉수 형태 미흡**: 가장자리 돌출부가 촉수라기보다 "뭉툭한 팔"에 가까움 — 에이전트 이동 패턴 자체의 한계

## 스크린샷

- `screenshots/body-iter0-baseline.png` — 기준점 (변경 전)
- `screenshots/body-iter3-pow-curve.png` — pow 커브 적용
- `screenshots/body-iter5-minimal-membrane.png` — **최종 채택** (Iter 5)
- `screenshots/body-iter6-occmap.png` — OccupancyMap 시도 (실패)
- `screenshots/body-final.png` — 최종 확인
