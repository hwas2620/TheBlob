# TheBlob 벤치마크 결과 및 버그 수정 계획

## 벤치마크 결과 (Playwright MCP)

| 항목 | 측정값 | 목표 |
|------|--------|------|
| 평균 FPS | ~11 FPS | 60 FPS |
| 블롭 렌더링 | 빨간색 occupancy 디버그 출력 | 노란색 정상 블롭 렌더링 |
| 콘솔 경고 | PBO performance warning | 경고 없음 |

---

## 발견된 버그 목록

### BUG-1: blob_body.frag.glsl 디버그 코드 잔류 (Critical)

**파일:** `src/gpu/shaders/glsl/blob_body.frag.glsl:51-54`

**증상:** 블롭이 노란색 본체 대신 빨간색 occupancy 값으로 렌더링됨

**원인:** 팀 B가 occupancy map 디버깅 중 넣은 `early return`이 남아있음
```glsl
// 디버그: occupancy 값을 빨간색으로 출력
float occupancy = texture(u_occupancyMap, trailUV).r;
fragColor = vec4(occupancy / 10.0, 0.0, 0.0, 1.0);
return;  // ← 이 return 때문에 아래 정상 렌더링 코드 실행 안됨
```

**수정:**
- 51~54번째 줄(디버그 코드 4줄) 삭제
- 56번째 줄의 `occupancy` 변수 재선언 필요 (디버그 코드 삭제 시 변수 사라짐)

---

### BUG-2: PBO 리드백 성능 경고 (High)

**파일:** `src/gpu/TrailMapGPU.ts:284-309`, `src/gpu/AgentGPU.ts:376-404`

**증상:** 콘솔에 `performance warning: READ-usage buffer was written, then fenced, but written again before being read back` 반복 출력

**원인 분석:**
`syncTrailMapFromGPU()` 메서드 내에서 resolve(PBO→CPU 읽기)와 request(GPU→PBO 쓰기)가 같은 함수 호출 내에서 순차 실행됨:
```typescript
// 1. resolve: PBO → CPU (읽기)
this.gpu.resolveAsyncReadback(this.trailMap);
// 2. request: GPU → PBO (쓰기) ← 같은 프레임에서 바로 재요청
this.gpu.requestAsyncReadback();
```

3프레임 카운터가 있지만, resolve 성공 직후 같은 프레임에서 request가 실행될 수 있어 WebGL 드라이버가 "write → fence → write before read" 패턴으로 감지함.

**수정 방안:**
- **옵션 A (권장):** 더블 PBO 사용 - 2개의 PBO를 교대로 사용하여 읽기/쓰기 충돌 방지
- **옵션 B:** resolve와 request 사이에 1프레임 간격 보장 - resolve 성공한 프레임에서는 request 스킵

---

### BUG-3: AgentGPU 디버그 로그 잔류 (Low)

**파일:** `src/gpu/AgentGPU.ts:363-373`

**증상:** 게임 시작 10프레임 후 에이전트 위치 샘플이 콘솔에 출력됨

**원인:** 팀 B가 디버깅용으로 넣은 `console.log`가 남아있음
```typescript
if (this.frameIndex === 10) {
    console.log('[AgentGPU] 10프레임 후 에이전트 위치 샘플:');
    // ...
}
```

**수정:** 해당 디버그 블록 삭제

---

### BUG-4: 블롭 분열 현상 (Investigation)

**증상:** 시간이 지나면 블롭 혈관이 얇아지면서 연결이 끊기고 두 개체로 분열됨

**분석:**
- 점균류(Physarum)는 실제로도 네트워크 최적화 과정에서 약한 연결을 제거함
- 하지만 현재 구현에서 분열이 과도하게 발생하는 것은 파라미터 밸런싱 이슈일 수 있음

**가능한 원인:**
1. `AGENT.OCCUPANCY_THRESHOLD = 5` (밀집도 회피 임계값)가 너무 낮아 분산 과도
2. `CONNECTIVITY` 파라미터가 약하여 재연결 실패
3. `AGENT.DECAY_FACTOR = 0.99`가 높아 페로몬 잔존이 길어도 에이전트 분산이 더 우세

**수정:** BUG-1~3 해결 후 관찰 필요 (디버그 코드가 렌더링을 막고 있어 정확한 판단 불가)

---

## 수정 우선순위

| 순서 | 버그 | 예상 영향 | 복잡도 |
|------|------|-----------|--------|
| 1 | BUG-1: 디버그 코드 삭제 | FPS 대폭 개선 + 정상 렌더링 복원 | 낮음 |
| 2 | BUG-3: 디버그 로그 삭제 | 콘솔 정리 | 낮음 |
| 3 | BUG-2: PBO 더블 버퍼링 | 성능 경고 제거 + GPU 스톨 감소 | 중간 |
| 4 | BUG-4: 분열 파라미터 튜닝 | 게임플레이 개선 | 높음 (테스트 필요) |

---

## 팀 현황

| 팀 | 상태 | 완료 작업 | 미해결 |
|----|------|-----------|--------|
| 팀 A (mcp-feature-lead) | IDLE | 밀집도 회피, 스테이지 스케일링, 통계 수집 | 없음 |
| 팀 B (gpu-optimization-lead) | 응답 대기 중 | PBO 비동기화, 큐빅 글로우, Occupancy 최적화 | BUG-1, BUG-2, BUG-3 |

팀 B에 BUG-1, BUG-2 수정 요청을 보냈으나 응답이 없는 상태.
→ **팀 리더가 직접 BUG-1, BUG-3을 수정하고, BUG-2는 후속 작업으로 처리**
