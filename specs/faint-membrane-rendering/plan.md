# 구현 계획

## 수정 파일
| 파일 | 변경 내용 |
|------|----------|
| `src/config.ts` | `BLOB_BODY`에 `NOISE_FLOOR: 0.3`, `MEMBRANE_ALPHA: 0.06` 추가 |
| `src/gpu/shaders/blob_body.ts` | 플레이스홀더 치환 2개 추가 |
| `src/gpu/shaders/glsl/blob_body.frag.glsl` | 기존 early return을 3단계로 분리 |

## 핵심 전략

기존 `if (avgVal < adjustedThreshold) { return; }` 하나를 3단계로 분리:

```
1. avgVal < adjustedNoise  → 완전 투명 (기존 동일)
2. avgVal < adjustedThreshold → 희미한 점막 + return (새 추가)
3. adjustedThreshold 이상 → 기존 본체 로직 한 줄도 변경 없음
```

본체(densityT, bodyColor, alpha 계산)는 절대 건드리지 않음.
