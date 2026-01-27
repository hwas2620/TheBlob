import { useEffect, useRef } from 'react';
import { useGameStore } from '../store/gameStore';
import type { Vector2, WaterDrop, WaterRipple } from '../types/game';
import { GAME_CONFIG } from '../types/game';
import { PhysarumSimulation, MAP_WIDTH, MAP_HEIGHT } from '../simulation/PhysarumSimulation';

// Utility functions
const generateId = () => Math.random().toString(36).substr(2, 9);

const distance = (a: Vector2, b: Vector2): number => {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
};

interface UseGameLoopProps {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
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

// 큐빅 표시 토글
export function toggleCubicVisibility(show: boolean) {
  if (simulation) {
    simulation.setShowCubic(show);
  }
}

export function getCubicVisibility(): boolean {
  return simulation?.getShowCubic() ?? true;
}

// 미니맵용 시뮬레이션 접근
export function getSimulation() {
  return simulation;
}

// 물방울 효과 생성
export function spawnWaterEffect(x: number, y: number) {
  for (let i = 0; i < 12; i++) {
    const angle = (i / 12) * Math.PI * 2 + Math.random() * 0.5;
    const speed = 30 + Math.random() * 60;
    waterDrops.push({
      id: generateId(),
      position: { x, y },
      velocity: {
        x: Math.cos(angle) * speed,
        y: Math.sin(angle) * speed - 20,
      },
      size: 2 + Math.random() * 4,
      alpha: 0.8,
      age: 0,
    });
  }

  waterRipples.push({
    id: generateId(),
    position: { x, y },
    radius: 5,
    maxRadius: 50 + Math.random() * 30,
    alpha: 0.6,
  });

  setTimeout(() => {
    waterRipples.push({
      id: generateId(),
      position: { x, y },
      radius: 5,
      maxRadius: 30 + Math.random() * 20,
      alpha: 0.4,
    });
  }, 100);
}

// 물 이펙트 업데이트
function updateWaterEffects(deltaTime: number) {
  waterDrops = waterDrops.filter((drop) => {
    drop.position.x += drop.velocity.x * deltaTime;
    drop.position.y += drop.velocity.y * deltaTime;
    drop.velocity.y += 150 * deltaTime;
    drop.alpha -= deltaTime * 1.5;
    drop.age += deltaTime;
    return drop.alpha > 0;
  });

  waterRipples = waterRipples.filter((ripple) => {
    ripple.radius += 80 * deltaTime;
    ripple.alpha -= deltaTime * 1.2;
    return ripple.alpha > 0 && ripple.radius < ripple.maxRadius;
  });
}

// 물 이펙트 렌더링 (화면 좌표로 생성되므로 변환 불필요)
function renderWaterEffects(ctx: CanvasRenderingContext2D) {
  for (const ripple of waterRipples) {
    const { x, y } = ripple.position;
    ctx.strokeStyle = `rgba(100, 180, 255, ${ripple.alpha})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y, ripple.radius, 0, Math.PI * 2);
    ctx.stroke();

    ctx.strokeStyle = `rgba(150, 200, 255, ${ripple.alpha * 0.5})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(x, y, ripple.radius * 0.6, 0, Math.PI * 2);
    ctx.stroke();
  }

  for (const drop of waterDrops) {
    const { x, y } = drop.position;
    ctx.save();
    ctx.shadowColor = '#6Bf';
    ctx.shadowBlur = 5;
    ctx.fillStyle = `rgba(100, 180, 255, ${drop.alpha})`;
    ctx.beginPath();
    ctx.arc(x, y, drop.size, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

export const useGameLoop = ({ canvasRef, width, height }: UseGameLoopProps) => {
  const animationFrameRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);
  const lastAutoSaveRef = useRef<number>(0);
  const initializedRef = useRef<boolean>(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || width === 0 || height === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 핵 위치는 맵 중앙 (고정)
    const nucleusPos = { x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 };

    // Initialize
    const store = useGameStore.getState();
    useGameStore.setState({
      nucleus: { ...store.nucleus, position: nucleusPos },
    });

    if (!initializedRef.current) {
      initializedRef.current = true;

      // Jeff Jones 시뮬레이션 초기화 (고정 2000x2000 맵)
      simulation = new PhysarumSimulation();

      // 영양분 초기화 (맵 좌표 기준)
      initializeNutrients(MAP_WIDTH, MAP_HEIGHT, nucleusPos);

      console.log('Jeff Jones 시뮬레이션 초기화 완료 (맵: 5000x5000)');
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
      simulation.setViewport(cameraX, cameraY, width, height);
    }

    const gameLoop = (timestamp: number) => {
      if (!lastTimeRef.current) {
        lastTimeRef.current = timestamp;
        lastAutoSaveRef.current = timestamp;
      }

      const deltaTime = Math.min((timestamp - lastTimeRef.current) / 1000, 0.1);
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
      render(ctx, width, height);

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
    };
  }, [canvasRef, width, height]);

  return {};
};

// 영양분 초기화
function initializeNutrients(width: number, height: number, nucleusPos: Vector2) {
  const state = useGameStore.getState();
  const count = GAME_CONFIG.NUTRIENTS_COUNT_BASE + state.stage.stageNumber * 5;
  const nutrients: import('../types/game').Nutrient[] = [];

  const minRadius = 80;

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

    // 티어 결정: 60% 소, 30% 중, 10% 대
    const roll = Math.random();
    const tier: 1 | 2 | 3 = roll < 0.6 ? 1 : roll < 0.9 ? 2 : 3;
    // 티어별 영양 배율: 소=0.5x, 중=1.5x, 대=4x
    const tierMultiplier = tier === 1 ? 0.5 : tier === 2 ? 1.5 : 4;
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
    }

    const newPulse = (state.nucleus.pulsePhase + deltaTime * 0.5) % (Math.PI * 2);
    useGameStore.setState({
      nucleus: { ...state.nucleus, pulsePhase: newPulse },
      gameTime: state.gameTime + deltaTime,
    });
    return;
  }

  // === 유인점만 설정 (injectPheromone 제거 - 논문에 충실) ===
  if (simulation) {
    const attractors: Array<{ x: number; y: number; strength: number }> = [];
    for (const nutrient of state.nutrients) {
      if (!nutrient.harvested) {
        // 티어별 냄새 세기: 소=0.7, 중=1.0, 대=1.8
        const tierStrength = nutrient.tier === 1 ? 0.7 : nutrient.tier === 2 ? 1.0 : 1.8;
        attractors.push({
          x: nutrient.position.x,
          y: nutrient.position.y,
          strength: (nutrient.value / nutrient.maxValue) * tierStrength,
        });
      }
    }
    simulation.setAttractors(attractors);

    // 시뮬레이션 업데이트 (매 프레임 여러 번 = 더 빠른 시뮬레이션)
    const steps = 3;
    for (let i = 0; i < steps; i++) {
      simulation.update();
    }
  }

  // === 연결 감지: 파티클 밀도 기반 ===
  const DENSITY_THRESHOLD = 30; // 이 밀도 이상이면 "연결됨"
  let nutrientsConsumed = 0;

  const updatedNutrients = state.nutrients.map((nutrient) => {
    if (nutrient.harvested) return nutrient;

    const updated = { ...nutrient };

    // 파티클 밀도 체크
    if (simulation) {
      const density = simulation.getParticleDensity(nutrient.position.x, nutrient.position.y, 25);

      if (density >= DENSITY_THRESHOLD) {
        updated.connected = true;
        updated.glowIntensity = Math.min(1, density / 50);

        // ATP 생성 & 영양분 흡수 (티어별 ATP 보너스: 소=1x, 중=1.5x, 대=3x)
        const tierATPBonus = nutrient.tier === 1 ? 1 : nutrient.tier === 2 ? 1.5 : 3;
        const absorb = deltaTime * 2 * state.getUpgradeMultiplier('digestiveEnzyme');
        updated.value -= absorb;
        nutrientsConsumed += absorb * tierATPBonus;

        // 바이오매스(파티클) 증가
        if (Math.random() < deltaTime * 2) {
          simulation.addAgents(1);
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
    console.log('모든 영양분 소진! 포자화를 고려해보세요.');
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
      // 강하게 중심으로 수축
      simulation.retractToCenter(0.05 + sporulationTimer * 0.02);
      simulation.update();
    }

    if (sporulationTimer > 2) {
      sporulationPhase = 'form';
      sporulationTimer = 0;

      // 포자낭 위치 생성 (3~5개)
      const count = 3 + Math.floor(Math.random() * 3);
      sporangiaPositions = [];
      for (let i = 0; i < count; i++) {
        const angle = (i / count) * Math.PI * 2;
        const dist = 30 + Math.random() * 20;
        sporangiaPositions.push({
          x: nucleusPos.x + Math.cos(angle) * dist,
          y: nucleusPos.y + Math.sin(angle) * dist,
          size: 15 + Math.random() * 10,
          alpha: 0,
        });
      }
    }
  }

  // Phase 2: 포자낭 형성 (0~1.5초)
  if (sporulationPhase === 'form') {
    if (simulation) {
      simulation.retractToCenter(0.1); // 더 강하게 수축
    }

    // 포자낭 페이드인
    sporangiaPositions = sporangiaPositions.map((sp) => ({
      ...sp,
      alpha: Math.min(1, sp.alpha + deltaTime * 2),
    }));

    if (sporulationTimer > 1.5) {
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
      alpha: Math.max(0, sp.alpha - deltaTime * 3),
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
          x: updated.velocity.x * 0.97,
          y: updated.velocity.y * 0.97,
        };
        updated.bobPhase += deltaTime * 3;
        updated.alpha = Math.max(0, updated.alpha - deltaTime * 0.15);
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
      if (dist < state.nucleus.radius + 20) {
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

export function getCamera() {
  return { x: cameraX, y: cameraY };
}

export function setCamera(x: number, y: number) {
  cameraX = ((x % MAP_WIDTH) + MAP_WIDTH) % MAP_WIDTH;
  cameraY = ((y % MAP_HEIGHT) + MAP_HEIGHT) % MAP_HEIGHT;
  if (simulation) {
    const vp = simulation.getViewport();
    simulation.setViewport(cameraX, cameraY, vp.width, vp.height);
  }
}

// 월드 좌표 → 스크린 좌표 (토러스 래핑)
// 화면이 맵보다 클 수 있으므로 (1920>1500) 여러 위치 반환
function worldToScreenAll(wx: number, wy: number, vw: number, vh: number, margin: number = 30): Array<{ x: number; y: number }> {
  const baseX = ((wx - cameraX) % MAP_WIDTH + MAP_WIDTH) % MAP_WIDTH;
  const baseY = ((wy - cameraY) % MAP_HEIGHT + MAP_HEIGHT) % MAP_HEIGHT;

  const results: Array<{ x: number; y: number }> = [];
  // 토러스 복제: 기본 위치와 ±MAP 오프셋 (화면이 맵보다 클 때 필요)
  for (const ox of [0, -MAP_WIDTH, MAP_WIDTH]) {
    for (const oy of [0, -MAP_HEIGHT, MAP_HEIGHT]) {
      const sx = baseX + ox;
      const sy = baseY + oy;
      if (sx > -margin && sx < vw + margin && sy > -margin && sy < vh + margin) {
        results.push({ x: sx, y: sy });
      }
    }
  }
  return results;
}

// 렌더링
function render(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
) {
  const state = useGameStore.getState();
  const isDormant = state.blobState === 'dormant';
  const isSporulating = state.blobState === 'sporulating';

  // 뷰포트 업데이트
  if (simulation) {
    simulation.setViewport(cameraX, cameraY, width, height);
  }

  // 배경 (화면 좌표)
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, width, height);

  // 수분 효과 (화면 좌표)
  if (state.moisture > 20) {
    const moistureAlpha = (state.moisture / 100) * 0.1;
    ctx.fillStyle = `rgba(100, 150, 200, ${moistureAlpha})`;
    ctx.fillRect(0, 0, width, height);
  }

  // 파티클 시뮬레이션 렌더링 (내부에서 자체 카메라 적용)
  if (simulation) {
    simulation.render(ctx);
  }

  // === 월드 오브젝트 렌더링 (토러스 래핑 적용) ===

  // 영양분 그리기
  renderNutrients(ctx, state.nutrients, width, height);

  // 포자낭 그리기 (포자화 중)
  if (isSporulating) {
    renderSporangia(ctx, width, height);
  }

  // 포자 그리기
  renderSpores(ctx, state.spores, width, height);

  // 조각 그리기
  renderFragments(ctx, state.fragments, width, height);

  // 상태 표시 (화면 중앙 - 화면 좌표)
  if (isDormant) {
    ctx.fillStyle = 'rgba(100, 100, 100, 0.8)';
    ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('휴면 중 - 물을 주세요!', width / 2, height / 2 + 50);
  }

  if (isSporulating) {
    ctx.fillStyle = 'rgba(255, 200, 100, 0.9)';
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('포자화 중...', width / 2, height / 2 + 50);
  }

  // 물 이펙트 렌더링 (화면 좌표)
  renderWaterEffects(ctx);
}

// 영양분 렌더링 - 소비에 따라 축소 (토러스 래핑, 다중 복제)
function renderNutrients(ctx: CanvasRenderingContext2D, nutrients: import('../types/game').Nutrient[], vw: number, vh: number) {
  for (const nutrient of nutrients) {
    if (nutrient.harvested) continue;

    const positions = worldToScreenAll(nutrient.position.x, nutrient.position.y, vw, vh, 20);
    const ratio = nutrient.value / nutrient.maxValue;
    // 티어별 크기: 소=4, 중=7, 대=12
    const baseSize = nutrient.tier === 1 ? 4 : nutrient.tier === 2 ? 7 : 12;
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

    const positions = worldToScreenAll(spore.position.x, spore.position.y, vw, vh, 30);
    for (const { x, y } of positions) {
      const bobOffset = Math.sin(spore.bobPhase) * 3;

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
