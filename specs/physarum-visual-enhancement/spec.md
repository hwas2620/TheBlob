# Physarum 비주얼 개선 — 리얼리스틱 색상/정맥/맥동

## 현재 상태

Jeff Jones 알고리즘은 논문 100% 준수 상태. 렌더링만 개선하면 실제 점균류에 가까워짐.

### 관련 파일
- `src/config.ts` — 모든 렌더링 파라미터
- `src/gpu/shaders/glsl/blob_body.frag.glsl` — 본체 셰이더
- `src/gpu/shaders/glsl/veins.frag.glsl` — 정맥 셰이더
- `src/hooks/useGameLoop.ts` — clearColor 설정 (L769)
- `src/index.css` — CSS 배경색

### 현재 색상 값
| 항목 | 현재 값 | 비고 |
|------|---------|------|
| clearColor | `rgb(10, 10, 10)` = `#0a0a0a` | 거의 검정 |
| CSS background | `#000` | 순수 검정 |
| ACTIVE_BASE | `(255, 240, 100)` | 밝은 황금 |
| ACTIVE_DARK | `(240, 200, 60)` | 저밀도 황금 |
| VEINS ACTIVE_COLOR | `(0.95, 0.85, 0.3)` | 황금 하이라이트 |
| 맥동 범위 | `0.85 + 0.15 * sin(...)` | 85~100% (15% 변동) |

## 문제 정의

1. **배경+색상 톤**: 현재 황금색 + 검정 배경은 "네온 게임" 느낌. 실제 Physarum은 크림~연황색 본체 + 어두운 한천(agar) 배경
2. **정맥 단일 레이어**: 모든 정맥이 동일 색상/두께. 실제 Physarum은 주정맥(굵고 밝음)과 모세정맥(가늘고 희미)이 뚜렷이 구분됨
3. **맥동 미약**: 15% 변동은 거의 인지 불가. 실제 Physarum의 원형질 유동(cytoplasmic streaming)은 육안으로 보일 정도로 뚜렷

## 요구사항

### 1. 배경색 + 색상 톤 (임팩트 ⭐⭐⭐⭐⭐)
- [ ] clearColor를 어두운 한천색으로 변경 (검정 → 어두운 갈색/올리브 계열)
- [ ] 본체 색상을 크림~연황색 계열로 조정 (네온 황금 → 자연스러운 노란색)
- [ ] 정맥 색상도 본체 톤에 맞춰 조정

### 2. 정맥 계층화 (임팩트 ⭐⭐⭐⭐)
- [ ] 트레일 값 기준으로 주정맥/모세정맥 2단계 분리
- [ ] 주정맥: 높은 트레일 값 → 더 밝고 불투명
- [ ] 모세정맥: 낮은 트레일 값 → 가늘고 희미
- [ ] 두 계층 간 자연스러운 그라데이션

### 3. 맥동 진폭 증대 (임팩트 ⭐⭐⭐)
- [ ] 맥동 범위 확대: 현재 85~100% → 더 넓은 범위
- [ ] 주정맥에서 더 강한 맥동, 모세정맥에서 약한 맥동 (계층화와 연동)

## 접근 방식

모든 변경은 config.ts 파라미터 + 셰이더 수정만으로 구현.
알고리즘(AgentGPU, TrailMapGPU) 변경 없음.

| 항목 | 수정 파일 | 방식 |
|------|-----------|------|
| 배경색 | config.ts, useGameLoop.ts, index.css | clearColor + CSS 값 변경 |
| 본체 색상 | config.ts | ACTIVE_BASE/DARK 값 조정 |
| 정맥 계층화 | config.ts, veins.frag.glsl | 트레일 임계값 분기 + 색상/알파 차등 |
| 맥동 증대 | config.ts, veins.frag.glsl | pulseIntensity 범위 파라미터화 |
