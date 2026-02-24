# Blob 희미한 점막 렌더링

## 현재 상태

`blob_body.frag.glsl` — `avgVal < FADE_START`이면 완전 투명 (early return).
trail이 0.3~2 구간(희미한 흔적)은 아무것도 보이지 않음.

## 문제 정의

실제 Physarum처럼 촉수 끝단/경계에 아주 희미한 노란 점막이 보여야 함.

## 요구사항

- [ ] `NOISE_FLOOR(0.3)` 미만: 완전 투명 유지 (배경 노이즈 제거)
- [ ] `NOISE_FLOOR ~ FADE_START` 구간: 아주 희미한 노란색 (alpha 0~MEMBRANE_ALPHA)
- [ ] `FADE_START` 이상 본체 로직: **완전히 기존 그대로** (손대지 않음)
- [ ] `npm run build` 통과

## 핵심 원칙

점막 영역을 **별도 early return**으로 처리 → 본체 렌더링에 절대 영향 없음.
