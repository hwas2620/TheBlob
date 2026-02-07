# The Blob — 황색망사점균 시뮬레이터

Jeff Jones의 2010년 논문 *"Characteristics of Pattern Formation and Evolution in Approximations of Physarum Transport Networks"* 를 기반으로 한 점균류(Physarum polycephalum) 시뮬레이션 아이들 게임입니다.

100,000개의 에이전트를 WebGL2 GPU로 병렬 처리하여 실시간으로 점균류의 성장, 탐색, 네트워크 형성을 시뮬레이션합니다.

## 주요 기능

- **Jeff Jones 알고리즘** — 3방향 센서 + 회전/이동 + 페로몬 분비의 논문 원본 파라미터 구현
- **WebGL2 GPU 가속** — 100k 에이전트 병렬 업데이트, 페로몬 확산/감쇠, 실시간 렌더링
- **아이들 게임 메커닉** — 수분 관리, 영양분 흡수, 업그레이드, 포자화를 통한 환생
- **토러스 맵** — 좌우/상하가 연결된 1500×1500 무한 맵
- **듀얼 캔버스** — WebGL2(블롭/페로몬/정맥) + Canvas2D(물/핵/포자/UI) 레이어
- **터치 지원** — 핀치 줌, 2손가락 팬, 탭 물주기

## 기술 스택

| 기술 | 용도 |
|------|------|
| React 19 | UI 컴포넌트 |
| TypeScript | 타입 안전성 |
| WebGL2 | GPU 가속 (에이전트 처리 + 렌더링) |
| Zustand | 상태 관리 |
| Vite | 빌드 도구 |
| Tailwind CSS | 스타일링 |

## 시작하기

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 프로덕션 빌드
npm run build

# 빌드 미리보기
npm run preview

# 린트
npm run lint
```

## 아키텍처

### GPU 3단계 파이프라인

```
Phase 1: TrailMapGPU        Phase 2: SceneRenderer       Phase 3: AgentGPU
┌─────────────────┐        ┌──────────────────────┐     ┌───────────────────┐
│ 페로몬 확산/감쇠  │        │ 블롭 본체 렌더링      │     │ 100k 에이전트 병렬  │
│ 핑퐁 버퍼 R32F   │        │ 페로몬 필드           │     │ RGBA32F 텍스처     │
│ 3×3 박스 블러     │        │ 정맥 구조             │     │ 센서→회전→이동→분비  │
│ decay factor     │        │ 큐빅 글로우           │     │ 연결성 체크         │
└─────────────────┘        └──────────────────────┘     └───────────────────┘
```

### 듀얼 캔버스

```
┌──────────────────────────────┐
│  Canvas2D (투명 오버레이)      │ ← 물 이펙트, 핵, 포자, UI 텍스트
├──────────────────────────────┤
│  WebGL2 Canvas               │ ← 블롭 본체, 페로몬, 정맥, 큐빅 글로우
└──────────────────────────────┘
```

### 주요 모듈

```
src/
├── gpu/                        # WebGL2 GPU 가속
│   ├── AgentGPU.ts             # 에이전트 병렬 처리 (Phase 3)
│   ├── TrailMapGPU.ts          # 페로몬 맵 확산/감쇠 (Phase 1)
│   ├── SceneRenderer.ts        # 시각화 렌더링 (Phase 2)
│   └── shaders/glsl/           # GLSL 프래그먼트 셰이더
├── simulation/
│   └── PhysarumSimulation.ts   # Jeff Jones 알고리즘 CPU 로직
├── hooks/
│   └── useGameLoop.ts          # 메인 게임 루프
├── store/
│   └── gameStore.ts            # Zustand 게임 상태 관리
├── components/                 # React UI 컴포넌트
├── config.ts                   # 중앙 설정 파일
└── text.ts                     # UI 텍스트 상수
```

## 조작법

### 마우스
- **클릭** — 물 주기 (블롭에 수분 공급)
- **드래그** — 카메라 이동
- **스크롤** — 줌 인/아웃

### 터치 (모바일)
- **1손가락 탭** — 물 주기 + 조각 수집
- **2손가락 핀치** — 줌
- **2손가락 팬** — 카메라 이동

### 키보드 단축키
| 키 | 기능 |
|----|------|
| `1` | 큐빅 글로우 토글 |
| `2` | 에이전트 입자 표시 토글 |
| `3` | 등고선 모드 전환 (역제곱 ↔ 트레일맵) |
| `4` / `D` | 뷰 모드 전환 (페로몬 ↔ 밀집도) |

## 게임 메커닉

### 생명 주기

```
🌱 성장 (Growing)
 │  물을 주어 블롭 활성화
 │  영양분 흡수로 질량 증가
 │  업그레이드 구매 (ATP 소비)
 ▼
✨ 포자화 (Sporulating)
 │  충분한 질량 도달 시 포자화 가능
 │  블롭이 수축 → 포자낭 형성 → 포자 분산
 ▼
🔗 조각 수집 (Fragment Collection)
 │  흩어진 블롭 조각 수집
 │  유전자 포인트 획득
 ▼
🧬 다음 스테이지
    유전자 부스트 적용
    새로운 영양분으로 재시작
```

### 자원

| 자원 | 설명 |
|------|------|
| 💧 습도 | 블롭 생존에 필수, 시간 경과로 감소 |
| 🧫 질량 | 영양분 흡수로 증가, 포자화 조건 |
| ⚡ ATP | 업그레이드 구매 화폐 |
| 🧬 유전자 | 환생 시 영구 부스트 |

### 업그레이드

| 업그레이드 | 효과 |
|-----------|------|
| 습도 유지 | 습도 감소 속도 감소 |
| 확장 속도 | 촉수 성장 속도 증가 |
| 분해 효소 | 영양분 흡수 속도 증가 |
| 자동 급수 | 자동으로 물 주기 |
| 포자 품질 | 환생 보너스 증가 |

## 설정 커스터마이징

모든 시뮬레이션 파라미터는 `src/config.ts`에서 관리됩니다:

```typescript
// Jeff Jones 에이전트 파라미터 (논문 원본)
AGENT.COUNT = 100000        // 에이전트 수
AGENT.SENSOR_ANGLE = 22.5°  // 센서 각도
AGENT.SENSOR_DISTANCE = 9   // 센서 거리
AGENT.TURN_SPEED = 45°      // 회전 속도
AGENT.MOVE_SPEED = 1        // 이동 속도
AGENT.DEPOSIT_AMOUNT = 5    // 페로몬 분비량
```

셰이더는 `src/gpu/shaders/glsl/` 디렉토리의 `.glsl` 파일을 편집하고, `{{PLACEHOLDER}}` 형식으로 config 값을 참조합니다.

## 참고 문헌

- Jones, J. (2010). *Characteristics of Pattern Formation and Evolution in Approximations of Physarum Transport Networks.* Artificial Life, 16(2), 127-153.
