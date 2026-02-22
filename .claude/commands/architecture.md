# TheBlob 아키텍처 상세

이 문서는 프로젝트의 GPU 파이프라인, 렌더링, 시뮬레이션 아키텍처를 다룬다.

## WebGL2 GPU 가속 (3 Phase)

1. **Phase 1: TrailMapGPU** (`src/gpu/TrailMapGPU.ts`)
   - 트레일맵 확산 + 감쇠 처리
   - 3x3 box blur + 페로몬 감쇠 (ping-pong 버퍼)
   - CPU 섀도 카피 동기화 (프레임당 1회)

2. **Phase 2: SceneRenderer** (`src/gpu/SceneRenderer.ts`)
   - 블롭 바디, 페로몬 필드, 정맥, 큐빅 글로우 렌더링
   - Fragment shader 시각화
   - Canvas2D getImageData/putImageData 제거

3. **Phase 3: AgentGPU** (`src/gpu/AgentGPU.ts`)
   - 100k 에이전트 병렬 업데이트
   - RGBA32F 텍스처에 에이전트 상태 인코딩 (x, y, angle, flags)
   - Jeff Jones 알고리즘: 3방향 센서 + 연결성 체크

## 듀얼 캔버스 아키텍처

하나의 캔버스에는 하나의 컨텍스트만 가능하므로 분리:

- **WebGL2 Canvas** (하단): 트레일맵 처리 + 블롭/페로몬/정맥/큐빅 렌더링
- **Canvas2D Overlay** (상단, 투명): 영양소, 핵, 포자, 물 이펙트, 텍스트
- CSS absolute positioning으로 레이어링

구현: `src/components/GameCanvas.tsx`

## 메인 게임 루프

`src/hooks/useGameLoop.ts`:

```typescript
// 프레임당 3회 시뮬레이션
for (let i = 0; i < 3; i++) {
  simulation.update();
}
// GPU/CPU 동기화
simulation.syncTrailMapFromGPU();
// 렌더링
renderGPU();      // WebGL2
renderOverlay();  // Canvas2D 오버레이
```

## 상태 관리

Zustand (`src/store/gameStore.ts`):
- 자원: moisture, biomass, ATP
- 게임 페이즈: growing, sporulating, sporeCollection
- 스테이지, 업그레이드, 저장/불러오기 (localStorage)

## WebGL2 셰이더 시스템

`.glsl` 파일 + TypeScript 플레이스홀더 치환:

```
src/gpu/shaders/
├── glsl/           # GLSL 셰이더 소스 ({{PLACEHOLDER}} 포함)
├── agent_update.ts # config.ts 값을 플레이스홀더에 치환
└── ...
```

수정 방법:
1. `.glsl` 파일에 `{{PLACEHOLDER}}` 정의
2. `.ts` 파일에서 `resolveShader()`로 치환
3. config.ts 값 자동 반영

## 토러스 맵 래핑

맵은 토러스 구조 (좌우/상하 연결):
- 에이전트가 경계를 넘으면 반대편에 출현
- 거리 계산은 토러스 최단 경로 사용
- WebGL2 텍스처는 `GL_REPEAT` 래핑으로 자동 처리

## Jeff Jones 2010 논문 파라미터

현재 설정은 논문 기본 파라미터 준수:
- AGENT.MOVE_SPEED = 1, DEPOSIT_AMOUNT = 5, DIFFUSE_PASSES = 1
- CONNECTIVITY.SEARCH_DISTANCES = [30] (8방향 × 1거리)

논문과 차이점:
- 100k 에이전트 (GPU 가속)
- 단순화된 연결성 체크 (8방향 × 1거리, 논문은 16방향 × 2거리)

## 터치 제스처

모바일 지원 (`src/components/GameCanvas.tsx`):
- **1손가락 탭**: 물 분사 + 조각 수집
- **2손가락 핀치**: 줌 (거리 변화)
- **2손가락 팬**: 카메라 이동 (중심점 이동)

## 텍스처 유닛 할당

- TEXTURE0: trailMap (자기 페로몬)
- TEXTURE1: attractors (어트랙터)
- TEXTURE2: occupancyMap (밀도맵)
- TEXTURE3: foodMap (먹이 페로몬)
