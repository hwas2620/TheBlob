# Physarum polycephalum 실제 움직임 메커니즘

## 1. 핵심 구조

### Plasmodium (원형질체)
- **다핵 단일 세포 구조** (수백~수천 개의 핵)
- 세포막으로 둘러싸인 하나의 거대한 세포
- 내부: 유동적인 원형질(cytoplasm)
- 외부: Actin-myosin 세포골격

### 튜브 네트워크
- 원형질을 수송하는 **관(tube) 네트워크**
- Node(교점): 영양분 위치 또는 핵 중심부
- Edge(간선): 원형질 흐름 경로

---

## 2. 이동 메커니즘

### A. Cytoplasmic Shuttle Streaming (세포질 왕복 흐름)

**원리:**
- 원형질이 튜브 내에서 리듬감 있게 **왕복 운동**
- 한 방향으로 흐르다가 일정 시간 후 **반대 방향**으로 전환

**주기:**
- 60~180초 (평균 100초)
- 매 100초마다 흐름 방향 전환

**목적:**
- 영양분 수송
- 신호 전달
- 네트워크 재배치

### B. Peristaltic Wave (연동파)

**원리:**
- 튜브 벽이 수축하면서 **파동처럼 전파**
- 위장의 연동 운동과 동일한 메커니즘
- Actin-myosin 세포골격이 수축 생성

**특징:**
- 튜브 단면이 수축 → 원형질 밀어냄
- 수축 파동이 한 방향으로 이동
- 여러 튜브가 조율되어 동기화

### C. Ca²⁺ Oscillation (칼슘 진동)

**원리:**
- 세포 내 칼슘 농도가 **파동 형태**로 전파
- Ca²⁺ 농도 상승 → 근육 수축 → 원형질 흐름

**측정값:**
- 진동 주기: **50~200초**
- 전압 진폭: **±5~40 mV**
- 전체 세포에 동기화

**메커니즘:**
1. 영양분 자극 → 신호 분자 방출
2. 신호 분자가 원형질 흐름에 실려 이동
3. 흐름 증가 → 신호 더 빨리 전파 (positive feedback)
4. Ca²⁺ 파동 생성 → 수축 제어

---

## 3. Pseudopodia (촉수) 형성

### 탐색 행동
- **화학 유인물질(chemoattractant)** 기울기 감지
- **습도 기울기** 감지
- 영양분 방향으로 촉수 확장

### 네트워크 형성
1. **영양분 발견** → 촉수 더 확장
2. **영양분 없음** → 촉수 수축 또는 방향 전환
3. 여러 영양분 발견 시 → **모두 연결**하는 네트워크 형성

### 환경 적응
- **영양분 풍부한 기질**: 많은 촉수, 조밀한 네트워크
- **영양분 빈약한 기질**: 적은 촉수, 최소 연결

---

## 4. 네트워크 최적화

### 단계별 과정

**1단계: 초기 탐색**
- 모든 방향으로 촉수 뻗음
- **조밀한 mesh** 형성
- 영양분 위치 파악

**2단계: 강화**
- 영양분 연결 경로 → 원형질 흐름 증가
- 흐름 많은 튜브 → 더 굵어짐 (positive feedback)
- 흐름 적은 튜브 → 약화

**3단계: 최적화**
- 비효율적 경로 제거
- **최단 거리 + 중복 경로** 유지
- 네트워크 이론의 최적 해와 유사

**수학적 특성:**
- Steiner tree 문제의 근사해
- 다중 경로 보장 (robustness)
- 동적 재구성 능력

---

## 5. Jeff Jones 2010 논문과의 차이

| 구분 | Jones 모델 | 실제 Physarum |
|------|-----------|---------------|
| **기본 단위** | 독립 에이전트 (입자) | 연결된 튜브 네트워크 |
| **이동 방식** | 에이전트 자유 이동 | 원형질 흐름 (진동) |
| **통신** | 페로몬 (간접) | Ca²⁺ 파동 (직접) |
| **주기성** | 없음 | 60-180초 진동 |
| **구조** | 분산 (각 입자 독립) | 단일 세포 (다핵) |
| **메커니즘** | 추상화된 행동 규칙 | 물리적 흐름 역학 |

### Jones 모델의 장점
- ✅ **패턴 형성** 정확히 재현
- ✅ 계산 효율적 (GPU 병렬화)
- ✅ 네트워크 최적화 결과 동일

### Jones 모델의 한계
- ❌ 물리적 메커니즘 다름
- ❌ 진동/맥동 없음
- ❌ 중심부 고정 구조 없음

**결론:**
Jones 모델은 **"무엇을"** (패턴)은 재현하지만 **"어떻게"** (메커니즘)는 추상화

---

## 6. 게임 구현 전략

### 현재 구현 (Jones 기반)
```
독립 에이전트 → 페로몬 분비 → 센서로 감지 → 방향 결정
```

### 실제 Physarum
```
중심부 → 튜브 확장 → 원형질 흐름 → 진동 → 영양분 수송
```

### 하이브리드 접근

**시뮬레이션 레이어** (Jones 유지)
- 에이전트 기반 패턴 형성
- 논문 파라미터 유지
- GPU 병렬 처리

**비주얼 레이어** (실제처럼)
- ✅ 정맥 맥동 효과 (60-180초 주기)
- ✅ 본체/흔적 명확한 구분
- ✅ CONNECTIVITY 강화 → 중심부 밀집
- ✅ 촉수 느낌 시각화

**장점:**
- 시뮬레이션 안정성 유지
- 게임 성능 보장
- 생명체 느낌 향상

---

## 7. 구현 완료 사항

### 정맥 맥동 (2026-01-29)
```glsl
// veins.frag.glsl
float pulsePeriod = 120.0; // 초
float pulsePhase = mod(u_time, pulsePeriod) / pulsePeriod * 2.0 * 3.14159;
float pulseIntensity = 0.85 + 0.15 * sin(pulsePhase); // 0.85~1.0 범위
```

### CONNECTIVITY 강화
```typescript
// config.ts
ISOLATION_THRESHOLD: 15,    // 8 → 15 (더 강한 연결성)
STRENGTH_SEVERE: 0.9,       // 0.6 → 0.9
STRENGTH_MILD: 0.7,         // 0.4 → 0.7
```

### 본체/흔적 구분
```glsl
// blob_body.frag.glsl
float bodyThreshold = 25.0;  // 고밀도 = 본체
if (avgVal >= bodyThreshold) {
  // 선명한 본체
} else {
  // 얇은 흔적 (alpha 0.06)
}
```

---

## 참고 문헌

1. [Locomotive Mechanism of Physarum Plasmodia - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2267142/)
2. [Random network peristalsis in Physarum polycephalum - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3746869/)
3. [Mechanism of signal propagation in Physarum polycephalum - PNAS](https://www.pnas.org/doi/10.1073/pnas.1618114114)
4. [Physarum polycephalum - Wikipedia](https://en.wikipedia.org/wiki/Physarum_polycephalum)
5. [Mathematical Model for Rhythmic Protoplasmic Movement - Journal of Mathematical Biology](https://link.springer.com/article/10.1007/s00285-006-0007-0)
6. Jeff Jones (2010) - "Characteristics of Pattern Formation and Evolution in Approximations of Physarum Transport Networks"
