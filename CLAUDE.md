# CLAUDE.md

## Language Preference

**Always respond in Korean (한글).** All conversations for this project must be conducted in Korean.

## Project Overview

TheBlob — Physarum polycephalum 점균류 시뮬레이션 게임. Jeff Jones 2010 논문 기반.
WebGL2 GPU 가속, React 19, TypeScript, Zustand, Vite.

## Development Commands

```bash
npm run dev      # Vite dev server
npm run build    # tsc -b && vite build
npm run lint     # ESLint
npm run preview  # Production preview
```

## Architecture (요약)

- **3-Phase GPU 파이프라인**: TrailMapGPU → SceneRenderer → AgentGPU
- **듀얼 캔버스**: WebGL2 (하단) + Canvas2D 오버레이 (상단)
- **100k 에이전트**: RGBA32F 텍스처 (512×256)에 상태 인코딩
- **토러스 맵**: 1500×1500, `GL_REPEAT` 래핑
- **셰이더**: `.glsl` + `{{PLACEHOLDER}}` → TypeScript `resolveShader()` 치환

상세 아키텍처는 `/architecture` 스킬 참고.

## Key Configuration

`src/config.ts` — 모든 시뮬레이션 파라미터 중앙 관리:
- `AGENT.*`, `ATTRACTION.*`, `CONNECTIVITY.*`, `MAP.*`, `ZOOM.*`, `UI.*`
- 셰이더 플레이스홀더에 자동 치환됨

## Playwright MCP Screenshots

스크린샷은 항상 `screenshots/` 폴더에 저장 (gitignore 등록됨).

## Development Workflow

기능/버그 수정은 단계별 스킬로 진행:

1. `/spec` → 코드베이스 분석 + spec.md 작성 → 사용자 확인
2. `/plan` → spec 기반 plan.md 작성 → 사용자 확인
3. `/implement` → branch 생성 → 문서 커밋 → 구현 → build 검증 → `--no-ff` 병합

각 단계는 사용자 확인 후 다음으로 넘어간다.

## Available Skills

- `/architecture` — GPU 파이프라인, 듀얼 캔버스, 셰이더 시스템, Jeff Jones 파라미터 상세
- `/spec` — 요청 분석 → spec.md 작성
- `/plan` — spec 기반 → plan.md 작성
- `/implement` — branch 생성 → 구현 → 검증 → 병합

## Important Notes

- **하나의 캔버스에 WebGL2 + Canvas2D 동시 생성 금지**
- **GPU fallback**: `gpu: TrailMapGPU | null` — GPU 초기화 실패 시 CPU 경로
- **HMR 지원**: `useGameLoop.ts` 모듈 변수 재초기화 로직
- **Agent texture**: 512×256 (100k of 131072 pixels)
