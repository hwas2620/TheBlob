import { useEffect, useRef } from 'react';
import { useGameStore } from '../store/gameStore';
import type { Vector2, WaterDrop, WaterRipple } from '../types/game';
import { GAME_CONFIG } from '../types/game';
import { PhysarumSimulation, MAP_WIDTH, MAP_HEIGHT } from '../simulation/PhysarumSimulation';
import { SceneRenderer } from '../gpu/SceneRenderer';
import { ZOOM, GAME, WATER_EFFECT, SPORULATION, UI, FRAGMENT } from '../config';
import { TEXT, formatText } from '../text';

// Utility functions
const generateId = () => Math.random().toString(36).substr(2, 9);

const distance = (a: Vector2, b: Vector2): number => {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
};

interface UseGameLoopProps {
  glCanvasRef: React.RefObject<HTMLCanvasElement | null>;
  overlayCanvasRef: React.RefObject<HTMLCanvasElement | null>;
  width: number;
  height: number;
}

// Module-level state
let sporulationTimer = 0;
let sporulationPhase: 'retract' | 'form' | 'explode' = 'retract';
let waterDrops: WaterDrop[] = [];
let waterRipples: WaterRipple[] = [];
let sporangiaPositions: Array<{ x: number; y: number; size: number; alpha: number }> = [];

// Jeff Jones 파티클 시뮬레이션
let simulation: PhysarumSimulation | null = null;

// GPU 가속
let sceneRenderer: SceneRenderer | null = null;
let showBlobGraphics = true;

// 큐빅 표시 토글
export function toggleCubicVisibility(show: boolean) {
  if (simulation) {
    simulation.setShowCubic(show);
  }
}

export function getCubicVisibility(): boolean {
  return simulation?.getShowCubic() ?? false;
}

// 파티클 표시 토글
export function toggleParticleVisibility(show: boolean) {
  if (simulation) {
    simulation.setShowParticles(show);
  }
}

export function getParticleVisibility(): boolean {
  return simulation?.getShowParticles() ?? false;
}

// 블롭 그래픽 표시 토글
export function toggleBlobGraphics(show: boolean) {
  showBlobGraphics = show;
}

export function getBlobGraphics(): boolean {
  return showBlobGraphics;
}

// 페로몬 모드 토글 (역제곱 ↔ 트레일맵)
export function setPheromoneMode(mode: 'inverse-square' | 'trailmap') {
  if (sceneRenderer) {
    sceneRenderer.setPheromoneMode(mode);
  }
}

export function getPheromoneMode(): 'inverse-square' | 'trailmap' {
  return sceneRenderer?.getPheromoneMode() ?? 'inverse-square';
}

// 뷰 모드 토글 (페로몬 ↔ 밀집도)
export function toggleViewMode(): 'pheromone' | 'density' {
  if (sceneRenderer) {
    return sceneRenderer.toggleViewMode();
  }
  return 'pheromone';
}

export function getViewMode(): 'pheromone' | 'density' {
  return sceneRenderer?.getViewMode() ?? 'pheromone';
}

// 미니맵용 시뮬레이션 접근
export function getSimulation() {
  return simulation;
}

// 물방울 효과 생성
export function spawnWaterEffect(x: number, y: number) {
  const W = WATER_EFFECT;
  for (let i = 0; i < W.DROP_COUNT; i++) {
    const angle = (i / W.DROP_COUNT) * Math.PI * 2 + Math.random() * 0.5;
    const speed = W.DROP_SPEED_MIN + Math.random() * W.DROP_SPEED_RANGE;
    waterDrops.push({
      id: generateId(),
      position: { x, y },
      velocity: {
        x: Math.cos(angle) * speed,
        y: Math.sin(angle) * speed + W.DROP_GRAVITY_OFFSET,
      },
      size: W.DROP_SIZE_MIN + Math.random() * W.DROP_SIZE_RANGE,
      alpha: W.DROP_INITIAL_ALPHA,
      age: 0,
    });
  }

  waterRipples.push({
    id: generateId(),
    position: { x, y },
    radius: W.RIPPLE_INITIAL_RADIUS,
    maxRadius: W.RIPPLE_MAX_RADIUS_MIN + Math.random() * W.RIPPLE_MAX_RADIUS_RANGE,
    alpha: W.RIPPLE_INITIAL_ALPHA,
  });

  setTimeout(() => {
    waterRipples.push({
      id: generateId(),
      position: { x, y },
      radius: W.RIPPLE_INITIAL_RADIUS,
      maxRadius: W.SECONDARY_MAX_RADIUS_MIN + Math.random() * W.SECONDARY_MAX_RADIUS_RANGE,
      alpha: W.SECONDARY_ALPHA,
    });
  }, W.SECONDARY_DELAY);
}

// 물 이펙트 업데이트
function updateWaterEffects(deltaTime: number) {
  waterDrops = waterDrops.filter((drop) => {
    drop.position.x += drop.velocity.x * deltaTime;
    drop.position.y += drop.velocity.y * deltaTime;
    drop.velocity.y += WATER_EFFECT.DROP_GRAVITY * deltaTime;
    drop.alpha -= deltaTime * WATER_EFFECT.DROP_ALPHA_DECAY;
    drop.age += deltaTime;
    return drop.alpha > 0;
  });

  waterRipples = waterRipples.filter((ripple) => {
    ripple.radius += WATER_EFFECT.RIPPLE_EXPANSION_RATE * deltaTime;
    ripple.alpha -= deltaTime * WATER_EFFECT.RIPPLE_ALPHA_DECAY;
    return ripple.alpha > 0 && ripple.radius < ripple.maxRadius;
  });
}

// 물 이펙트 렌더링 (화면 좌표로 생성되므로 변환 불필요)
function renderWaterEffects(ctx: CanvasRenderingContext2D) {
  for (const ripple of waterRipples) {
    const { x, y } = ripple.position;
    ctx.strokeStyle = `rgba(100, 180, 255, ${ripple.alpha})`;
    ctx.lineWidth = UI.WATER_RIPPLE_THICKNESS;
    ctx.beginPath();
    ctx.arc(x, y, ripple.radius, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = `rgba(150, 200, 255, ${ripple.alpha * 0.5})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(x, y, ripple.radius * UI.WATER_RIPPLE_SECONDARY_SCALE, 0, Math.PI * 2);
    ctx.stroke();
  }

  for (const drop of waterDrops) {
    const { x, y } = drop.position;
    ctx.save();
    ctx.shadowColor = '#6Bf';
    ctx.shadowBlur = UI.WATER_DROP_SHADOW_BLUR;
    ctx.fillStyle = `rgba(100, 180, 255, ${drop.alpha})`;
    ctx.beginPath();
    ctx.arc(x, y, drop.size, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

export const useGameLoop = ({ glCanvasRef, overlayCanvasRef, width, height }: UseGameLoopProps) => {
  const animationFrameRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);
  const lastAutoSaveRef = useRef<number>(0);
  const initializedRef = useRef<boolean>(false);

  useEffect(() => {
    const glCanvas = glCanvasRef.current;
    const overlayCanvas = overlayCanvasRef.current;
    if (!glCanvas || !overlayCanvas || width === 0 || height === 0) return;

    // WebGL2 컨텍스트 (메인 렌더링)
    const gl = glCanvas.getContext('webgl2', {
      antialias: false,
      depth: false,
      stencil: false,
      premultipliedAlpha: false,
      alpha: true,
    });

    // Canvas2D 오버레이 컨텍스트
    const ctx = overlayCanvas.getContext('2d');
    if (!ctx) return;

    // 핵 위치는 맵 중앙 (고정)
    const nucleusPos = { x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 };

    // Initialize
    const store = useGameStore.getState();
    useGameStore.setState({
      nucleus: { ...store.nucleus, position: nucleusPos },
    });

    // HMR 감지: 모듈 변수가 null이면 재초기화 필요
    if (simulation === null) {
      initializedRef.current = false;
    }

    if (!initializedRef.current) {
      initializedRef.current = true;

      // Jeff Jones 시뮬레이션 초기화 (고정 1500x1500 맵)
      simulation = new PhysarumSimulation();

      // GPU 가속 초기화
      if (gl) {
        // Phase 1: 트레일맵 GPU 처리
        simulation.initGPU(gl);
        // Phase 2: GPU 씬 렌더링
        try {
          sceneRenderer = new SceneRenderer(gl);
          console.log(TEXT.LOG_GPU_SCENE_ACTIVE);
        } catch (e) {
          console.warn(TEXT.LOG_GPU_SCENE_FAILED, e);
          sceneRenderer = null;
        }
      } else {
        console.warn(TEXT.LOG_WEBGL2_FALLBACK);
      }

      // 영양분 초기화 (맵 좌표 기준)
      initializeNutrients(MAP_WIDTH, MAP_HEIGHT, nucleusPos);

      console.log(formatText(
        TEXT.LOG_INIT_COMPLETE,
        MAP_WIDTH,
        MAP_HEIGHT,
        simulation?.isGPUEnabled() ? TEXT.LOG_GPU_STATUS_ON : TEXT.LOG_GPU_STATUS_OFF
      ));
    }

    // 카메라 초기화 (핵이 화면 중앙에 오도록, 항상 [0, MAP) 범위)
    if (!cameraInitialized) {
      const rawX = nucleusPos.x - width / 2;
      const rawY = nucleusPos.y - height / 2;
      cameraX = ((rawX % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH;
      cameraY = ((rawY % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT;
      cameraInitialized = true;
    }
    if (simulation) {
      simulation.setViewport(cameraX, cameraY, width / zoomLevel, height / zoomLevel);
    }

    // 탭 복귀 시 타이머 리셋 (거대 deltaTime 방지)
    let tabHidden = false;
    const onVisibilityChange = () => {
      tabHidden = document.hidden;
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    const gameLoop = (timestamp: number) => {
      if (!lastTimeRef.current) {
        lastTimeRef.current = timestamp;
        lastAutoSaveRef.current = timestamp;
      }

      // 탭 복귀: 타이머만 리셋 (GPU 동기 캐치업은 스톨 유발)
      if (tabHidden) {
        lastTimeRef.current = timestamp;
        animationFrameRef.current = requestAnimationFrame(gameLoop);
        return;
      }
      if (timestamp - lastTimeRef.current > 1000) {
        // 1초 이상 갭 → 탭 복귀로 간주, 타이머 리셋
        lastTimeRef.current = timestamp;
      }

      const deltaTime = Math.min((timestamp - lastTimeRef.current) / 1000, GAME.MAX_DELTA_TIME);
      lastTimeRef.current = timestamp;

      const state = useGameStore.getState();

      // 게임 페이즈별 업데이트
      switch (state.gamePhase) {
        case 'growing':
          updateGrowingPhase(deltaTime, width, height, nucleusPos);
          break;
        case 'sporulating':
          updateSporulatingPhase(deltaTime);
          break;
        case 'sporeCollection':
          updateSporeCollectionPhase(deltaTime, nucleusPos);
          break;
      }

      // 물 이펙트 업데이트
      updateWaterEffects(deltaTime);

      // 렌더링
      renderGPU(gl, width, height);
      renderOverlay(ctx, width, height);

      // 자동 저장
      if (timestamp - lastAutoSaveRef.current > GAME_CONFIG.AUTO_SAVE_INTERVAL) {
        useGameStore.getState().saveGame();
        lastAutoSaveRef.current = timestamp;
      }

      animationFrameRef.current = requestAnimationFrame(gameLoop);
    };

    animationFrameRef.current = requestAnimationFrame(gameLoop);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [glCanvasRef, overlayCanvasRef, width, height]);

  return {};
};

// 영양분 초기화
function initializeNutrients(width: number, height: number, nucleusPos: Vector2) {
  const state = useGameStore.getState();
  const count = GAME_CONFIG.NUTRIENTS_COUNT_BASE + state.stage.stageNumber * 5;
  const nutrients: import('../types/game').Nutrient[] = [];

  // 난이도 스케일링: 스테이지가 올라갈수록 영양분이 핵에서 더 멀리 스폰
  const minRadius = GAME.NUTRIENT_MIN_RADIUS * state.stage.difficultyMultiplier;

  for (let i = 0; i < count; i++) {
    // 맵 전체에 고르게 분포 (핵에서 최소 거리만 유지)
    let position: Vector2;
    let attempts = 0;
    do {
      position = {
        x: Math.random() * width,
        y: Math.random() * height,
      };
      const dx = Math.abs(position.x - nucleusPos.x);
      const dy = Math.abs(position.y - nucleusPos.y);
      const wrapDx = Math.min(dx, width - dx);
      const wrapDy = Math.min(dy, height - dy);
      const dist = Math.sqrt(wrapDx * wrapDx + wrapDy * wrapDy);
      if (dist >= minRadius) break;
      attempts++;
    } while (attempts < 20);

    const roll = Math.random();
    const tier: 1 | 2 | 3 = roll < GAME.TIER_DISTRIBUTION[0] ? 1 : roll < GAME.TIER_DISTRIBUTION[1] ? 2 : 3;
    const tierMultiplier = GAME.TIER_NUTRIENT_MULT[tier - 1];
    const value = (state.stage.totalNutrients / count) * tierMultiplier * (0.8 + Math.random() * 0.4);
    const id = generateId();

    nutrients.push({
      id,
      position,
      value,
      maxValue: value,
      harvested: false,
      connected: false,
      glowIntensity: 0,
      tier,
    });
  }

  useGameStore.setState({ nutrients });
}

// 성장 페이즈 업데이트
function updateGrowingPhase(
  deltaTime: number,
  _width: number,
  _height: number,
  nucleusPos: Vector2
) {
  const state = useGameStore.getState();

  // 수분 감소
  state.updateMoisture(deltaTime);

  // 시뮬레이션 휴면 상태 설정
  if (simulation) {
    simulation.setDormant(state.blobState === 'dormant');
    simulation.setNucleusPosition(nucleusPos.x, nucleusPos.y);
  }

  // 휴면 상태면 시뮬레이션만 느리게
  if (state.blobState === 'dormant') {
    if (simulation) {
      simulation.update();
      // GPU 모드: 동기화
      if (simulation.isGPUEnabled()) {
        simulation.syncTrailMapFromGPU();
      }
    }

    const newPulse = (state.nucleus.pulsePhase + deltaTime * 0.5) % (Math.PI * 2);
    useGameStore.setState({
      nucleus: { ...state.nucleus, pulsePhase: newPulse },
      gameTime: state.gameTime + deltaTime,
    });
    return;
  }

  // === 유인점 설정 + 페로몬 주입 ===
  if (simulation) {
    const attractors: Array<{ x: number; y: number; strength: number }> = [];
    const unharvested: typeof state.nutrients = [];
    for (const nutrient of state.nutrients) {
      if (!nutrient.harvested) {
        const tierStrength = GAME.TIER_SMELL_STRENGTH[nutrient.tier - 1];
        const strength = (nutrient.value / nutrient.maxValue) * tierStrength;
        attractors.push({
          x: nutrient.position.x,
          y: nutrient.position.y,
          strength,
        });
        unharvested.push(nutrient);
      }
    }
    simulation.setAttractors(attractors);
    simulation.syncAttractorsToAgentGPU();

    // 먹이 페로몬 분비: 모든 영양분에서 강한 페로몬 방출 (에이전트가 감지 가능)
    // 논문: "fixing concentration at food sources"
    for (const n of unharvested) {
      const tierStrength = GAME.TIER_SMELL_STRENGTH[n.tier - 1];
      const ratio = n.value / n.maxValue;
      // 먹이 잔량에 비례하는 페로몬 (다 먹히면 냄새 감소)
      const amount = GAME.FOOD_DEPOSIT_AMOUNT * ratio * tierStrength;
      simulation.depositAtPosition(n.position.x, n.position.y, amount, GAME.FOOD_DEPOSIT_RADIUS);
    }

    // 시뮬레이션 업데이트 (매 프레임 여러 번 = 더 빠른 시뮬레이션)
    const steps = UI.SIMULATION_STEPS;
    for (let i = 0; i < steps; i++) {
      simulation.update();
    }
    // GPU 모드: 3스텝 완료 후 트레일맵+에이전트 CPU 동기화 (프레임당 1회)
    if (simulation.isGPUEnabled()) {
      simulation.syncTrailMapFromGPU();
    }
  }

  // === 연결 감지: 파티클 밀도 기반 ===
  const DENSITY_THRESHOLD = GAME.DENSITY_THRESHOLD;
  let nutrientsConsumed = 0;

  const updatedNutrients = state.nutrients.map((nutrient) => {
    if (nutrient.harvested) return nutrient;

    const updated = { ...nutrient };

    // 파티클 밀도 체크
    if (simulation) {
      const density = simulation.getParticleDensity(nutrient.position.x, nutrient.position.y, UI.DENSITY_CHECK_RADIUS);

      if (density >= DENSITY_THRESHOLD) {
        updated.connected = true;
        updated.glowIntensity = Math.min(1, density / GAME.DENSITY_GLOW_NORM);

        const tierATPBonus = GAME.TIER_ATP_BONUS[nutrient.tier - 1];
        // 난이도 스케일링: 스테이지가 올라갈수록 흡수 속도 감소
        const difficultyAbsorbRate = 1 / (1 + (state.stage.difficultyMultiplier - 1) * GAME_CONFIG.DIFFICULTY_ABSORB_RATE_SCALE / GAME_CONFIG.DIFFICULTY_NUTRIENT_SPACING_SCALE);
        const absorb = deltaTime * GAME.NUTRIENT_ABSORB_RATE * state.getUpgradeMultiplier('digestiveEnzyme') * difficultyAbsorbRate;
        updated.value -= absorb;
        nutrientsConsumed += absorb * tierATPBonus;

        // 바이오매스(파티클) 증가: 흡수량에 비례
        const spawnCount = Math.floor(absorb * GAME.AGENT_SPAWN_CHANCE);
        const spawnFrac = absorb * GAME.AGENT_SPAWN_CHANCE - spawnCount;
        const totalSpawn = spawnCount + (Math.random() < spawnFrac ? 1 : 0);
        if (totalSpawn > 0) {
          simulation.addAgents(totalSpawn, nutrient.position.x, nutrient.position.y);
        }

        if (updated.value <= 0) {
          updated.harvested = true;
          updated.value = 0;
        }
      } else {
        updated.connected = false;
        updated.glowIntensity = Math.max(0, updated.glowIntensity - deltaTime);
      }
    }

    return updated;
  });

  // 핵 펄스
  const newPulse = (state.nucleus.pulsePhase + deltaTime * 2) % (Math.PI * 2);

  useGameStore.setState({
    nutrients: updatedNutrients,
    nucleus: { ...state.nucleus, pulsePhase: newPulse },
    gameTime: state.gameTime + deltaTime,
    stage: {
      ...state.stage,
      remainingNutrients: Math.max(0, state.stage.remainingNutrients - nutrientsConsumed),
    },
  });

  // 스테이지 완료 체크
  const allHarvested = updatedNutrients.every((n) => n.harvested);
  if (allHarvested && updatedNutrients.length > 0) {
    console.log(TEXT.INFO_NUTRIENTS_DEPLETED);
  }
}

// 포자화 페이즈 - 3단계 (수축 → 형성 → 폭발)
function updateSporulatingPhase(deltaTime: number) {
  const state = useGameStore.getState();
  const nucleusPos = state.nucleus.position;

  sporulationTimer += deltaTime;

  // Phase 1: 수축 (0~2초)
  if (sporulationPhase === 'retract') {
    if (simulation) {
      simulation.retractToCenter(SPORULATION.RETRACT_BASE_SPEED + sporulationTimer * SPORULATION.RETRACT_ACCEL);
      simulation.update();
    }

    if (sporulationTimer > SPORULATION.RETRACT_DURATION) {
      sporulationPhase = 'form';
      sporulationTimer = 0;

      const count = SPORULATION.SPORANGIUM_COUNT_MIN + Math.floor(Math.random() * SPORULATION.SPORANGIUM_COUNT_RANGE);
      sporangiaPositions = [];
      for (let i = 0; i < count; i++) {
        const angle = (i / count) * Math.PI * 2;
        const dist = SPORULATION.SPORANGIUM_DIST_MIN + Math.random() * SPORULATION.SPORANGIUM_DIST_RANGE;
        sporangiaPositions.push({
          x: nucleusPos.x + Math.cos(angle) * dist,
          y: nucleusPos.y + Math.sin(angle) * dist,
          size: SPORULATION.SPORANGIUM_SIZE_MIN + Math.random() * SPORULATION.SPORANGIUM_SIZE_RANGE,
          alpha: 0,
        });
      }
    }
  }

  // Phase 2: 포자낭 형성 (0~1.5초)
  if (sporulationPhase === 'form') {
    if (simulation) {
      simulation.retractToCenter(SPORULATION.FORM_RETRACT_STRENGTH);
    }

    // 포자낭 페이드인
    sporangiaPositions = sporangiaPositions.map((sp) => ({
      ...sp,
      alpha: Math.min(1, sp.alpha + deltaTime * SPORULATION.SPORANGIUM_FADE_IN),
    }));

    if (sporulationTimer > SPORULATION.FORM_DURATION) {
      sporulationPhase = 'explode';
      sporulationTimer = 0;
      state.completeSporulation();
      if (simulation) {
        simulation.reset();
      }
    }
  }

  // Phase 3: 폭발 (포자 퍼짐)
  if (sporulationPhase === 'explode') {
    // 포자낭 페이드아웃
    sporangiaPositions = sporangiaPositions.map((sp) => ({
      ...sp,
      alpha: Math.max(0, sp.alpha - deltaTime * SPORULATION.SPORANGIUM_FADE_OUT),
    }));

    if (state.spores.length > 0) {
      const updatedSpores = state.spores.map((spore) => {
        const updated = { ...spore };
        // 속도 적용
        updated.position = {
          x: updated.position.x + updated.velocity.x * deltaTime,
          y: updated.position.y + updated.velocity.y * deltaTime,
        };
        // 감속
        updated.velocity = {
          x: updated.velocity.x * SPORULATION.SPORE_FRICTION,
          y: updated.velocity.y * SPORULATION.SPORE_FRICTION,
        };
        updated.bobPhase += deltaTime * SPORULATION.SPORE_BOB_RATE;
        updated.alpha = Math.max(0, updated.alpha - deltaTime * SPORULATION.SPORE_ALPHA_DECAY);
        return updated;
      });

      useGameStore.setState({ spores: updatedSpores });

      // 모든 포자가 사라지면 새 스테이지
      if (updatedSpores.every((s) => s.alpha <= 0)) {
        sporulationTimer = 0;
        sporulationPhase = 'retract';
        sporangiaPositions = [];
        state.startNewStage();
      }
    }
  }

  const newPulse = (state.nucleus.pulsePhase + deltaTime * 5) % (Math.PI * 2);
  useGameStore.setState({
    nucleus: { ...state.nucleus, pulsePhase: newPulse },
    gameTime: state.gameTime + deltaTime,
  });
}

// 포자낭 렌더링 (토러스 래핑, 다중 복제)
function renderSporangia(ctx: CanvasRenderingContext2D, vw: number, vh: number) {
  for (const sp of sporangiaPositions) {
    if (sp.alpha <= 0) continue;

    const positions = worldToScreenAll(sp.x, sp.y, vw, vh, 30);
    for (const { x, y } of positions) {
      ctx.save();

      const gradient = ctx.createRadialGradient(x, y, 0, x, y, sp.size);
      gradient.addColorStop(0, `rgba(80, 50, 30, ${sp.alpha})`);
      gradient.addColorStop(0.6, `rgba(60, 35, 20, ${sp.alpha * 0.8})`);
      gradient.addColorStop(1, `rgba(40, 25, 15, 0)`);

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, sp.size, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(120, 80, 50, ${sp.alpha * 0.5})`;
      ctx.beginPath();
      ctx.arc(x - sp.size * 0.3, y - sp.size * 0.3, sp.size * 0.3, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }
  }
}

// 조각 수집 페이즈
function updateSporeCollectionPhase(deltaTime: number, nucleusPos: Vector2) {
  const state = useGameStore.getState();

  const updatedFragments = state.fragments.map((fragment) => {
    const updated = { ...fragment };
    updated.pulsePhase += deltaTime * 2;

    if (!updated.merged) {
      const dist = distance(updated.position, nucleusPos);
      if (dist < state.nucleus.radius + FRAGMENT.MERGE_RANGE) {
        state.collectFragment(updated.id);
        return { ...updated, merged: true };
      }
    }

    return updated;
  });

  useGameStore.setState({
    fragments: updatedFragments,
    gameTime: state.gameTime + deltaTime,
  });

  // 모든 조각이 합쳐지면 growing 페이즈로 전환 + 영양분 재초기화
  const allMerged = updatedFragments.every((f) => f.merged);
  if (allMerged && updatedFragments.length > 0) {
    state.mergeAllFragments();

    // 시뮬레이션 리셋 + 영양분 재생성
    if (simulation) {
      initializeNutrients(MAP_WIDTH, MAP_HEIGHT, nucleusPos);
    }
  }
}

// 카메라 위치 (외부에서 접근 가능) - 맵 중앙에서 시작
let cameraX = MAP_WIDTH / 2;
let cameraY = MAP_HEIGHT / 2;
let cameraInitialized = false;
let zoomLevel = 1.0;
const MIN_ZOOM = ZOOM.MIN;
const MAX_ZOOM = ZOOM.MAX;

export function getCamera() {
  return { x: cameraX, y: cameraY };
}

export function setCamera(x: number, y: number) {
  cameraX = ((x % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH;
  cameraY = ((y % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT;
  console.log(`[setCamera] New camera: (${cameraX.toFixed(0)}, ${cameraY.toFixed(0)}), sim:`, !!simulation);
  if (simulation) {
    const vp = simulation.getViewport();
    simulation.setViewport(cameraX, cameraY, vp.width, vp.height);
  }
}

export function getZoom() {
  return zoomLevel;
}

export function setZoom(z: number) {
  zoomLevel = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z));
}

// 월드 좌표 → 스크린 좌표 (토러스 래핑)
// 화면이 맵보다 클 수 있으므로 (1920>1500) 여러 위치 반환
function worldToScreenAll(wx: number, wy: number, vw: number, vh: number, margin: number = 30): Array<{ x: number; y: number }> {
  const baseX = ((wx - cameraX) % MAP_WIDTH + MAP_WIDTH) % MAP_WIDTH;
  const baseY = ((wy - cameraY) % MAP_HEIGHT + MAP_HEIGHT) % MAP_HEIGHT;

  const results: Array<{ x: number; y: number }> = [];

  // 뷰포트 크기에 맞춰 필요한 타일 개수 계산
  const tilesX = Math.ceil((vw + 2 * margin) / MAP_WIDTH) + 1;
  const tilesY = Math.ceil((vh + 2 * margin) / MAP_HEIGHT) + 1;

  // 중심 기준으로 타일 배치
  for (let ox = -Math.floor(tilesX / 2); ox <= Math.ceil(tilesX / 2); ox++) {
    for (let oy = -Math.floor(tilesY / 2); oy <= Math.ceil(tilesY / 2); oy++) {
      const sx = baseX + ox * MAP_WIDTH;
      const sy = baseY + oy * MAP_HEIGHT;
      // 마진을 포함한 뷰포트 범위 체크
      if (sx >= -margin && sx <= vw + margin && sy >= -margin && sy <= vh + margin) {
        results.push({ x: sx, y: sy });
      }
    }
  }
  return results;
}

// GPU 렌더링 (WebGL2 캔버스 - 블롭/페로몬/정맥/큐빅)
function renderGPU(
  gl: WebGL2RenderingContext | null,
  _width: number,
  _height: number
) {
  if (!gl) return;

  // 캔버스 실제 크기 사용 (리사이즈 즉시 반영)
  const width = gl.canvas.width;
  const height = gl.canvas.height;

  const state = useGameStore.getState();
  const isDormant = state.blobState === 'dormant';

  // 뷰포트 업데이트 (줌 반영: 월드 공간 크기)
  if (simulation) {
    simulation.setViewport(cameraX, cameraY, width / zoomLevel, height / zoomLevel);
  }

  // 배경 클리어 (#0a0a0a)
  gl.viewport(0, 0, width, height);
  gl.clearColor(10 / 255, 10 / 255, 10 / 255, 1.0);
  gl.clear(gl.COLOR_BUFFER_BIT);

  // GPU 씬 렌더링
  if (sceneRenderer && simulation && simulation.isGPUEnabled()) {
    // 어트랙터 데이터 업데이트
    const attractors: Array<{ x: number; y: number; strength: number }> = [];
    for (const nutrient of state.nutrients) {
      if (!nutrient.harvested) {
        const tierStrength = GAME.TIER_SMELL_STRENGTH[nutrient.tier - 1];
        attractors.push({
          x: nutrient.position.x,
          y: nutrient.position.y,
          strength: (nutrient.value / nutrient.maxValue) * tierStrength,
        });
      }
    }
    sceneRenderer.updateAttractors(attractors);

    const trailTex = simulation.getCurrentTrailTexture();
    const agentGPU = simulation.getAgentGPU();

    // 밀집도 맵 텍스처 전달 (페로몬 ↔ 밀집도 토글용)
    if (agentGPU) {
      sceneRenderer.setOccupancyTexture(agentGPU.getOccupancyTexture());
    }

    if (trailTex) {
      const timeInSeconds = performance.now() / 1000;
      sceneRenderer.render(
        trailTex,
        { x: cameraX, y: cameraY },
        simulation.getMapSize(),
        width, height,
        width / zoomLevel, height / zoomLevel,
        isDormant,
        attractors.length,
        simulation.getShowCubic(),
        simulation.getShowParticles(),
        agentGPU?.getCurrentAgentTexture() ?? null,
        agentGPU?.agentCount ?? 0,
        showBlobGraphics,
        timeInSeconds,
      );
    }
  } else if (simulation) {
    // CPU 폴백: 기존 Canvas2D 렌더링을 위해 2D 컨텍스트가 필요하지만
    // 듀얼 캔버스에서는 WebGL 캔버스에 2D를 그릴 수 없으므로
    // CPU 폴백 시 오버레이 캔버스에서 처리
  }
}

// Canvas2D 오버레이 렌더링 (영양분/핵/포자/물 이펙트/텍스트)
function renderOverlay(
  ctx: CanvasRenderingContext2D,
  _width: number,
  _height: number
) {
  // 캔버스 실제 크기 사용 (리사이즈 즉시 반영)
  const width = ctx.canvas.width;
  const height = ctx.canvas.height;

  const state = useGameStore.getState();
  const isDormant = state.blobState === 'dormant';
  const isSporulating = state.blobState === 'sporulating';

  // 오버레이 클리어 (투명)
  ctx.clearRect(0, 0, width, height);

  // 수분 효과 (화면 좌표 - 줌 무관)
  if (state.moisture > UI.WATER_EFFECT_THRESHOLD) {
    const moistureAlpha = (state.moisture / 100) * 0.1;
    ctx.fillStyle = `rgba(100, 150, 200, ${moistureAlpha})`;
    ctx.fillRect(0, 0, width, height);
  }

  // 줌 적용 (월드 오브젝트에만)
  const zoom = zoomLevel;
  const zoomedW = width / zoom;
  const zoomedH = height / zoom;

  ctx.save();
  ctx.scale(zoom, zoom);

  // CPU 폴백: GPU 씬 렌더러가 없으면 Canvas2D로 시뮬레이션 렌더링
  if (!sceneRenderer && simulation) {
    simulation.render(ctx);
  }

  // === 월드 오브젝트 렌더링 (토러스 래핑 적용) ===

  // 영양분 그리기 (항상 표시)
  renderNutrients(ctx, state.nutrients, zoomedW, zoomedH);

  // 포자낭 그리기 (포자화 중)
  if (isSporulating) {
    renderSporangia(ctx, zoomedW, zoomedH);
  }

  // 포자 그리기
  renderSpores(ctx, state.spores, zoomedW, zoomedH);

  // 조각 그리기
  renderFragments(ctx, state.fragments, zoomedW, zoomedH);

  ctx.restore();

  // 상태 표시 (화면 중앙 - 화면 좌표, 줌 무관)
  if (isDormant) {
    ctx.fillStyle = 'rgba(100, 100, 100, 0.8)';
    ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(TEXT.SCREEN_DORMANT, width / 2, height / 2 + 50);
  }

  if (isSporulating) {
    ctx.fillStyle = 'rgba(255, 200, 100, 0.9)';
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(TEXT.SCREEN_SPORULATING, width / 2, height / 2 + 50);
  }

  // 물 이펙트 렌더링 (화면 좌표 - 줌 적용)
  ctx.save();
  ctx.scale(zoom, zoom);
  renderWaterEffects(ctx);
  ctx.restore();
}

// 영양분 렌더링 - 소비에 따라 축소 (토러스 래핑, 다중 복제)
function renderNutrients(ctx: CanvasRenderingContext2D, nutrients: import('../types/game').Nutrient[], vw: number, vh: number) {
  for (const nutrient of nutrients) {
    if (nutrient.harvested) continue;

    const positions = worldToScreenAll(nutrient.position.x, nutrient.position.y, vw, vh, UI.SPORANGIUM_RENDER_MARGIN);
    const ratio = nutrient.value / nutrient.maxValue;
    const baseSize = GAME.TIER_BASE_SIZE[nutrient.tier - 1];
    const size = baseSize * (0.3 + 0.7 * ratio);
    // 티어별 색상: 소=연한 베이지, 중=진한 베이지, 대=황금빛
    const fillColor = nutrient.tier === 1 ? '#c8b898' : nutrient.tier === 2 ? '#d4c4a8' : '#e8d090';
    const strokeColor = nutrient.tier === 1 ? '#8b7355' : nutrient.tier === 2 ? '#7a6040' : '#a08030';

    for (const { x, y } of positions) {
      ctx.save();

      // 본체 - 소비될수록 반투명
      ctx.globalAlpha = 0.4 + 0.6 * ratio;
      ctx.fillStyle = fillColor;
      ctx.beginPath();
      ctx.ellipse(x, y, size, size * 0.7, 0, 0, Math.PI * 2);
      ctx.fill();

      // 테두리
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = nutrient.tier === 3 ? 1.5 : 1;
      ctx.stroke();

      // 하이라이트
      const s = size / baseSize;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.beginPath();
      ctx.ellipse(x - 1.5 * s, y - 1 * s, 1.5 * s, 1 * s, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }
  }
}

// 포자 렌더링 (토러스 래핑, 다중 복제)
function renderSpores(ctx: CanvasRenderingContext2D, spores: import('../types/game').Spore[], vw: number, vh: number) {
  for (const spore of spores) {
    if (spore.alpha <= 0) continue;

    const positions = worldToScreenAll(spore.position.x, spore.position.y, vw, vh, UI.SPORANGIUM_RENDER_MARGIN);
    for (const { x, y } of positions) {
      const bobOffset = Math.sin(spore.bobPhase) * SPORULATION.SPORE_BOB_OFFSET;

      ctx.save();
      ctx.shadowColor = '#FFD700';
      ctx.shadowBlur = 10;

      ctx.fillStyle = `rgba(255, 220, 100, ${spore.alpha})`;
      ctx.beginPath();
      ctx.arc(x, y + bobOffset, spore.size, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }
  }
}

// 조각 렌더링 (토러스 래핑, 다중 복제)
function renderFragments(ctx: CanvasRenderingContext2D, fragments: import('../types/game').BlobFragment[], vw: number, vh: number) {
  for (const fragment of fragments) {
    if (fragment.merged) continue;

    const positions = worldToScreenAll(fragment.position.x, fragment.position.y, vw, vh, 30);
    for (const { x, y } of positions) {
      const pulseSize = fragment.size + Math.sin(fragment.pulsePhase) * 3;

      ctx.save();
      ctx.shadowColor = '#FFFF00';
      ctx.shadowBlur = 15;

      ctx.fillStyle = `rgba(255, 255, 0, 0.8)`;
      ctx.beginPath();
      ctx.arc(x, y, pulseSize, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.beginPath();
      ctx.arc(x - pulseSize * 0.3, y - pulseSize * 0.3, pulseSize * 0.3, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }
  }
}
