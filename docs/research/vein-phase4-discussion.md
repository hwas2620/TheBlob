# Phase 4 정맥 튜닝 논의 (3차 역할극)

## 참여자
- Dr. 김점균 (Physarum 전문가/의뢰인)
- 박코드 (개발자)
- 이헤시안 (수학자/감수)
- 최로드맵 (기획자)
- 한빛나 (Technical Artist / VFX 전문가) — **신규 합류**

---

## 1. Phase 4-1 결과 리뷰 (THRESHOLD/ALPHA 조정)

### 변경 내용
| 파라미터 | Phase 3 값 | Phase 4 값 |
|---------|-----------|-----------|
| RIDGE_THRESHOLD | 0.1 | 0.02 |
| RIDGE_SATURATE | 0.3 | 0.10 |
| MAJOR_ALPHA | 0.4 | 0.65 |
| HESSIAN_STEP | 1 | 2 |
| VEIN_MIN | 25 | 35 |

### 브라우저 결과
- 정맥 강도 증가했으나 **경계부 점 노이즈도 증폭**
- 밝은 노란 사각형 픽셀들이 경계에서 반짝반짝 깜빡임
- 원인: THRESHOLD/ALPHA만 바꾸면 신호와 노이즈를 동시에 증폭

### Dr. 김점균
> 이건 오히려 후퇴. 경계에서 금가루를 흘리는 것 같다. 본체 내부에 희미한 곡선 2~3가닥이 보이긴 하지만, 노이즈가 압도한다. 원인은 미확산 맵의 점 노이즈 평활화 부족.

### 이헤시안
> Hessian 2차 미분 연산자는 입력의 불연속점에 극도로 민감. δ(x)의 2차 미분은 이론적으로 무한대. box blur 1패스(σ≈0.8px)로는 점 입력을 연속화하기에 절대적으로 부족. 최소 σ≈1.5~2.0px (3패스) 필요. blur 3패스 + HESSIAN_STEP 3~4를 동시 적용 권고.

### 박코드
> captureRawTrail()에서 blur 루프 1→3으로 반복하면 됨. 성능 영향 미미. HESSIAN_STEP 4면 8×8px 영역 커버, 개별 agent(1px)는 안 보임.

### 최로드맵
> 교훈: THRESHOLD/ALPHA만 바꾸는 건 신호와 노이즈를 동시에 증폭. 노이즈를 먼저 제거한 뒤에 증폭해야 한다.

---

## 2. 한빛나 합류 — 접근 재고 제안

### 한빛나의 핵심 관찰
> 노이즈 가득한 원본 데이터에서 정밀한 구조를 검출하려고 하고 있다. blur를 많이 하면 구름 문제로 회귀. blur를 적게 하면 반짝반짝. 이건 blur 패스 수의 문제가 아니라, **어디서 ridge를 찾느냐**의 문제.

### Option A: 확산 맵 + 큰 HESSIAN_STEP (한빛나 제안)
- 확산 맵은 이미 완벽하게 평활화됨 → 점 노이즈 제로
- 정맥 구조의 **위치**는 확산 후에도 보존됨 (Lindeberg 스케일 스페이스 이론)
- 폭만 넓어짐 → HESSIAN_STEP을 6~8로 올리면 넓어진 ridge를 깨끗하게 잡음
- rawTrail 파이프라인 전체 제거 가능 (메모리 절약, 코드 단순화)

### Option B: 미확산 맵 + temporal smoothing
- rawTrail 유지, mix(prevRaw, currentRaw, 0.3) IIR 로우패스
- 한 프레임만 존재하는 점은 희석, 지속되는 정맥은 누적
- 코드는 mix 한 줄 추가

### 이헤시안 감수
> 한빛나 제안이 수학적으로 타당. 가우시안 컨볼루션 후 ridge의 영교차점(위치)은 보존. HESSIAN_STEP은 σ_diffuse × 2~3 = 3~5 범위가 이론적 최적.

### 전원 합의
> Option A를 먼저 시도. 가장 단순하고 노이즈가 원천 차단. 결과가 너무 둔하면 Option B로 전환.

---

## 3. Phase 4-2 Spec/Plan 드래프트 + 감수

### 박코드 + 최로드맵 초안
- 셰이더: u_rawTrailMap → u_trailMap 전환
- config: HESSIAN_STEP 2→7
- rawTrail 파이프라인 전체 제거 (확인 후)

### Dr. 김점균 감수
> HESSIAN_STEP 7은 14×14px 커버. 모세정맥(확산 후 ~6px)은 해상도 부족 우려. **5~6으로 시작** 권고.

### 이헤시안 감수
> STEP은 σ_diffuse × 2~3 = 3~5 범위가 최적. 5~6이 적절, 7 이상은 과도. ridgeness가 σ²만큼 감소하므로 RIDGE_THRESHOLD 추가 하향 필요할 수 있음. **승인.**

### 한빛나 감수
> rawTrail 삭제 전에 결과 확인 먼저. Step 순서: 셰이더 전환 + 파라미터 → 확인 → 삭제. **승인.**

### 최종 합의
- HESSIAN_STEP: 5 (시작값)
- Step 순서: 셰이더 전환 → 파라미터 → 브라우저 확인 → rawTrail 삭제
- 전원 승인

---

## 4. Phase 4-2 구현 결과

### 변경 내용
- veins.frag.glsl: u_rawTrailMap → u_trailMap (9개 fetch 전부)
- config.ts: HESSIAN_STEP 2→5

### 브라우저 결과 (Playwright 타임랩스 30프레임)
- 점 노이즈/반짝임: **완전 제거** (확산 맵에는 개별 deposit 없음)
- 경계: **깨끗** (노이즈 없음)
- 정맥 강도: **약함** — 희미한 곡선 몇 가닥만 보임
- 전체 느낌: **잉크/구름** — 아직 "촉수 같은 선"에 못 미침
- 원인: 확산 맵에서는 ridge가 넓고 부드러워져서 Hessian 검출 강도 감소

### 미해결 과제
- 확산 맵 기반에서 정맥을 더 날카롭게 만드는 방법 필요
- 또는 Option B(temporal smoothing)로 전환 검토
- rawTrail 파이프라인 삭제는 보류 (결과 불만족)

---

## 5. Phase 4-3 방향 논의 — Temporal Smoothing

### 배경
- Phase 4-2에서 점 노이즈는 **완전 제거**됐으나 정맥이 **잉크/구름**처럼 뭉개짐
- 확산 맵의 ridge가 넓고 부드러워서 Hessian 검출 강도 부족
- Option A(확산 맵) 한계 확인 → **Option B(temporal smoothing)로 전환** 합의

### 한빛나 핵심 제안
> 확산 맵 단독으로 날카로운 정맥 불가능. ridge **위치**는 보존되지만 **강도**(대비)는 감소.
> rawTrail에 시간축 IIR 필터 적용: `mix(prevRaw, currentRaw, α)`
> - 공간 블러가 아닌 **시간 블러** → ridge 폭을 넓히지 않음
> - 한 프레임짜리 점은 α비율로 희석, 지속적 경로는 누적

### 이헤시안 감수
> IIR `y[n] = (1-α)·y[n-1] + α·x[n]`, α=0.3이면 τ ≈ 2.9프레임.
> ~3프레임 이상 존재하는 구조만 잔존. 개별 deposit은 τ 내 소멸, 정맥 경로는 반복 통과로 누적.
> HESSIAN_STEP은 rawTrail에서 **2~3**으로 복원. α=0.3 시작 추천. **승인.**

### 박코드 구현 방안
> 1. captureRawTrail()에서 blur 대신 **IIR temporal blend** 수행
> 2. 더블 버퍼(rawTrailTexA/B) ping-pong으로 mix 셰이더
> 3. veins.frag.glsl: Hessian 입력을 temporal-smoothed rawTrailMap으로 복원
> 4. 본체 마스킹은 u_trailMap 유지
> 5. HESSIAN_STEP: 5→3, THRESHOLD/SATURATE 재조정

### Dr. 김점균 감수
> 생물학적으로도 타당. 실제 원형질 흐름은 수초~수분 단위로 안정 경로 형성. 프레임 단위 깜빡임은 시뮬레이션 artifact. **승인.**

### 한빛나 감수
> temporal blend 셰이더는 별도 .glsl이 적절. diffuseDecay에 mode 분기는 유지보수 어려움. **승인.**

### 최로드맵 위험 요소
> IIR α에 따라 반응 지연 가능 — blob 빠른 이동 시 정맥 잔상. α=0.3~0.5에서 시작, 시각 조정.

### 전원 합의
- Phase 4-3: rawTrail + temporal smoothing (IIR) 적용
- Hessian 입력을 temporal-smoothed rawTrail로 전환
- HESSIAN_STEP 3, THRESHOLD/SATURATE 재조정
- **미구현 — 다음 세션에서 진행**

---

## 6. 에이전트 추상화 관련 메모

- 에이전트 움직임은 실제 원형질 흐름의 **추상적 표현**
- 트레일맵(확산 후)은 에이전트 반복 경로의 누적 → 실제 Physarum 패턴을 **간접 반영**
- 직접 렌더링 vs 트레일맵 기반 렌더링 결정은 `specs/trail-based-blob-rendering/` 참고

---

## 커밋 이력
| 커밋 | 내용 |
|------|------|
| 622de50 | Phase 3: Hessian ridge + additive blend + rawTrail |
| 8ff57f7 | Phase 4: THRESHOLD/ALPHA 파라미터 튜닝 |
| 6b863bb | Phase 4-2: 확산 맵 기반 Hessian 전환 |

## 다음 세션 TODO
- [ ] Phase 4-3 구현: temporal smoothing IIR 셰이더
- [ ] captureRawTrail() → IIR blend로 교체
- [ ] veins.frag.glsl: Hessian 입력 rawTrailMap 복원
- [ ] HESSIAN_STEP 3, α=0.3 시작
- [ ] 브라우저 시각 확인 → 파라미터 튜닝
