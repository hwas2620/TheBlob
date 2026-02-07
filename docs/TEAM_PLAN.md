# TheBlob 팀 협업 및 MCP 활용 계획

## 목표

Claude 팀 기능으로 2개 팀을 병렬 운영하여 미완성 기능 구현 + MCP 서버 통합 + GPU 성능 최적화를 동시에 진행한다.

---

## 팀 구성 (2팀)

### 팀 A: MCP 통합 & 기능 완성

| 항목 | 내용 |
|------|------|
| 역할 | 미완성 기능 구현, MCP 서버 활용 기능 개발 |
| Agent Type | `general-purpose` |

**담당 파일:**
- `src/simulation/PhysarumSimulation.ts` — 밀집도 회피 로직
- `src/store/gameStore.ts` — 스테이지 스케일링, Memory MCP 통합
- `src/hooks/useGameLoop.ts` — 통계 수집
- `src/components/StatsPanel.tsx` — 통계 UI

**작업 목록:**

| # | 작업 | 의존성 |
|---|------|--------|
| 1 | 밀집도 회피 알고리즘 완성 | 없음 |
| 2 | 스테이지 난이도 스케일링 | 없음 |
| 3 | Memory MCP 통계 수집 시스템 | 없음 |
| 4 | Puppeteer MCP 벤치마크 스크립트 | 작업 6, 7 완료 후 |
| 5 | Fetch MCP 리더보드 (선택) | 작업 2 완료 후 |

---

### 팀 B: GPU 성능 최적화

| 항목 | 내용 |
|------|------|
| 역할 | GPU 병목 제거, 렌더링 최적화 |
| Agent Type | `general-purpose` |

**담당 파일:**
- `src/gpu/TrailMapGPU.ts` — 비동기 리드백
- `src/gpu/AgentGPU.ts` — Occupancy Map 최적화
- `src/gpu/SceneRenderer.ts` — 큐빅 글로우 통합
- `src/gpu/shaders/glsl/cubic_glow.frag.glsl` — 셰이더 최적화
- `src/config.ts` — 성능 파라미터 튜닝

**작업 목록:**

| # | 작업 | 의존성 |
|---|------|--------|
| 6 | GPU 리드백 비동기화 (PBO) | 없음 |
| 7 | 큐빅 글로우 셰이더 최적화 | 없음 |
| 8 | Occupancy Map 계산 최적화 | 없음 |

---

## MCP 서버 활용 계획

### Memory MCP — 게임 통계 수집

게임 세션 데이터를 지속적으로 수집하여 밸런싱 데이터로 활용한다.

**데이터 스키마:**
```typescript
interface GameStats {
  sessionId: string;
  timestamp: number;
  totalPlaytime: number;        // ms
  stagesCleared: number;
  avgClearTime: number;
  upgradeUsage: Record<string, number>;
  avgFPS: number;
  peakAgents: number;
}
```

**저장 시점:** 세션 종료, 스테이지 클리어, 오프라인 전환

---

### Puppeteer MCP — 자동 벤치마크

성능 회귀를 방지하기 위한 자동화 벤치마크를 실행한다.

**벤치마크 설정:**
```
Config 1: 50k 에이전트, 센서거리 9  → 기준 FPS 확인
Config 2: 100k 에이전트, 센서거리 9 → 기본 설정 벤치마크
Config 3: 150k 에이전트, 센서거리 15 → 스트레스 테스트
```

**측정 지표:** 평균/최소/최대 FPS, 렌더 시간, GPU 리드백 시간, 메모리 사용량

---

### Fetch MCP — 온라인 리더보드 (선택)

스테이지 클리어 시간을 API로 전송하여 글로벌 랭킹을 표시한다.
백엔드 서버가 필요하므로 선택적으로 진행.

---

## 팀 간 협업

### 병렬 작업 (동시 진행 가능)
- 작업 1, 2, 3 (팀 A) ↔ 작업 6, 7, 8 (팀 B)

### 순차 작업 (의존성 있음)
- 작업 4 (벤치마크) → 작업 6, 7 완료 후 (최적화 효과 측정)
- 작업 5 (리더보드) → 작업 2 완료 후 (스테이지 시스템 필요)

### 파일 충돌 방지
- 동일 파일은 한 팀만 작업 (작업 목록으로 관리)
- `config.ts`는 팀 B가 성능 파라미터만 수정

---

## 미완성 기능 상세

### 1. 밀집도 회피 (작업 1)

**현황:** `AGENT.OCCUPANCY_THRESHOLD = 5` 설정은 있으나 GPU 셰이더에서 하드코딩된 `currentDensity > 1.0`으로만 동작 중.

**구현 필요사항:**
- `u_occupancyThreshold` 유니폼을 셰이더에서 실제 활용
- 밀도 구배에 따른 회피 강도 조절
- config 값 변경 시 즉시 반영

### 2. 스테이지 난이도 스케일링 (작업 2)

**현황:** `createInitialStage()` 함수가 영양분 수만 조정하고 난이도는 고정.

**구현 필요사항:**
- 스테이지별 에이전트 파라미터 동적 조정 (SENSOR_DISTANCE, TURN_SPEED 등)
- 난이도 곡선 밸런싱
- 스테이지 정보에 난이도 메타데이터 추가

### 3. GPU 리드백 비동기화 (작업 6)

**현황:** `syncTrailMapFromGPU()` 함수가 매 프레임 동기 리드백 (512KB).

**구현 필요사항:**
- Pixel Buffer Object (PBO) 사용
- 3프레임 버퍼링으로 GPU 파이프라인 동기화 제거
- 리드백 주기 조정 (매 프레임 → 매 N프레임)

---

## 검증 방법

### 팀 A
- [ ] 밀집도 회피: 에이전트가 밀집 영역 회피하는지 시각적 확인
- [ ] 스테이지 스케일링: 스테이지 1-5 난이도 체감
- [ ] Memory MCP: 세션 종료 후 데이터 저장 확인
- [ ] Puppeteer 벤치마크: `npm run benchmark` 실행 성공

### 팀 B
- [ ] GPU 리드백: FPS 10-20% 개선 (60→66-72 FPS)
- [ ] 큐빅 글로우: 프레임 드롭 제거, 60 FPS 안정
- [ ] Occupancy Map: 계산 시간 축소, 밀도 맵 정확성 유지

### 통합
- [ ] 전체 FPS 20% 개선 달성
- [ ] 모든 기능 E2E 동작 확인

---

## 실행 명령

```bash
# 팀 생성
TeamCreate: theblob-improvement

# 팀원 생성 (Task 도구)
팀 A: mcp-integration-lead (general-purpose)
팀 B: gpu-optimization-lead (general-purpose)

# 작업 할당 후 병렬 진행
```
