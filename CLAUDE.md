# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**Always respond in Korean (한글).** All conversations for this project must be conducted in Korean.

## Project Overview

TheBlob is a Physarum polycephalum slime mold simulation game based on Jeff Jones' 2010 paper "Characteristics of Pattern Formation and Evolution in Approximations of Physarum Transport Networks".

## Development Commands

```bash
npm run dev      # Start Vite dev server
npm run build    # Production build (TypeScript compile + Vite build)
npm run lint     # Run ESLint
npm run preview  # Preview production build
```

## Architecture Overview

### WebGL2 GPU Acceleration (3 Phases)

Performance optimization through 3-phase WebGL2 GPU acceleration:

1. **Phase 1: TrailMapGPU** (`src/gpu/TrailMapGPU.ts`)
   - Trail map diffusion + decay processing
   - 3x3 box blur + pheromone decay via ping-pong buffers
   - CPU shadow copy sync (once per frame)

2. **Phase 2: SceneRenderer** (`src/gpu/SceneRenderer.ts`)
   - Renders blob body, pheromone field, veins, cubic glow
   - Fragment shader visualization
   - Eliminates Canvas2D getImageData/putImageData

3. **Phase 3: AgentGPU** (`src/gpu/AgentGPU.ts`)
   - Parallel update of 100k agents
   - Agent state encoded in RGBA32F texture (x, y, angle, flags)
   - Jeff Jones algorithm: 3-way sensors + connectivity check

### Dual Canvas Architecture

Since one canvas can only have one context, split into two:

- **WebGL2 Canvas** (bottom): Trail map processing + blob/pheromone/veins/cubic rendering
- **Canvas2D Overlay Canvas** (top, transparent): Nutrients, nucleus, spores, water effects, text
- Layered via CSS absolute positioning

Implementation: `src/components/GameCanvas.tsx`

### Main Game Loop

`src/hooks/useGameLoop.ts` handles all simulation and rendering:

```typescript
// Run 3 simulation steps per frame
for (let i = 0; i < 3; i++) {
  simulation.update();
}

// GPU/CPU sync
simulation.syncTrailMapFromGPU();

// Rendering
renderGPU();      // WebGL2 rendering
renderOverlay();  // Canvas2D overlay
```

### State Management

Zustand for game state (`src/store/gameStore.ts`):

- Resources: moisture, biomass, ATP
- Game phases: growing, sporulating, sporeCollection
- Stage system
- Upgrades
- Save/Load (localStorage)

## Key Configuration Files

### `src/config.ts`

**All simulation parameters centralized here:**

- `AGENT.*` - Agent settings (count, sensor angle, move speed, etc.)
- `ATTRACTION.*` - Attractor (food) attraction force
- `CONNECTIVITY.*` - Connectivity check parameters
- `MAP.*` - Map size (fixed 1500x1500)
- `ZOOM.*` - Camera zoom settings
- `UI.*` - UI constants

To modify parameters, only edit this file. Shaders auto-substitute placeholders via `src/gpu/shaders/agent_update.ts`.

## WebGL2 Shader System

Shaders consist of `.glsl` files + TypeScript placeholder substitution:

```
src/gpu/shaders/
├── glsl/                    # GLSL shader sources
│   ├── agent_update.frag.glsl
│   ├── blob_body.frag.glsl
│   └── ...
├── agent_update.ts          # Substitutes config.ts values into placeholders
├── blob_body.ts
└── ...
```

To modify shaders:
1. Define placeholders as `{{PLACEHOLDER}}` in `.glsl` files
2. Substitute via `resolveShader()` in corresponding `.ts` file
3. config.ts values automatically reflected

## Torus (Toroidal) Map Wrapping

Map has torus structure (left-right / top-bottom connected):

- Agents crossing boundaries appear on opposite side
- Distance calculations use torus shortest path
- Camera coordinates also use torus wrapping (`% MAP_WIDTH`, `% MAP_HEIGHT`)

WebGL2 textures auto-handled via `GL_REPEAT` wrap mode.

## Touch Gesture Handling

Mobile support touch gestures (`src/components/GameCanvas.tsx`):

- **1-finger tap**: Water spray + fragment collection
- **2-finger pinch**: Zoom (distance change)
- **2-finger pan**: Camera movement (center point movement)

Implementation: Like Google Maps, handles pinch and pan simultaneously (center point movement + distance ratio).

## Jeff Jones 2010 Paper Parameters

Current settings follow paper's base parameters:

- AGENT.MOVE_SPEED = 1
- AGENT.DEPOSIT_AMOUNT = 5
- AGENT.DIFFUSE_PASSES = 1
- CONNECTIVITY.SEARCH_DISTANCES = [30]  # 8 directions × 1 distance

Differences from paper:
- 100k agents (possible via GPU acceleration)
- Simplified connectivity check (8 directions × 1 distance, paper uses 16 directions × 2 distances)

## Playwright MCP Screenshots

스크린샷은 항상 `screenshots/` 폴더에 저장할 것 (gitignore 등록됨):
```
filename: "screenshots/파일명.png"
```

## Development Workflow

### Spec → Plan → Implementation

각 기능/버그 수정 작업 시 다음 워크플로우를 따른다:

1. **Spec 작성**: `specs/[feature-name]/spec.md` — 문제 정의, 현재 상태, 요구사항
2. **Plan 작성**: `specs/[feature-name]/plan.md` — 구현 단계, 수정 파일, 의존성, 검증 방법
3. **Feature branch 생성**: `feat/[feature-name]` (main에서 분기)
4. **Spec/Plan 커밋**: 문서만 먼저 커밋 (코드 변경 전)
5. **구현 + 검증**: `npm run build` 통과 확인
6. **구현 커밋**: 코드 변경사항 커밋
7. **Main 병합**: `git merge --no-ff` 사용 (merge commit으로 브랜치 히스토리 보존)

### Git Branch Strategy

```
main ─────────────────────────────●── merge commit
       \                         /
        feat/feature-name ──●──●
                          spec  impl
```

- **`--no-ff` 필수**: fast-forward 방지, 브랜치 흔적 보존
- Spec/Plan 커밋과 구현 커밋을 분리하여 리뷰 용이성 확보

## Important Notes

- **Never create both WebGL2 and Canvas2D contexts on the same canvas**
- **GPU fallback**: `gpu: TrailMapGPU | null` - Uses CPU path if GPU init fails
- **HMR support**: Module variable re-initialization logic in `useGameLoop.ts`
- **Agent texture**: 512×256 size stores 100k agents (uses 100000 of 8192 pixels)
