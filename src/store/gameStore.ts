import { create } from 'zustand';
import type {
  GameState,
  Tendril,
  Nutrient,
  Spore,
  BlobFragment,
  Upgrades,
  StageInfo,
  BlobState,
  GamePhase,
} from '../types/game';
import { UPGRADE_COSTS, UPGRADE_MAX_LEVEL, GAME_CONFIG } from '../types/game';
import { UI, FRAGMENT, SPORULATION } from '../config';
import { TEXT } from '../text';
import { recordSessionStats } from '../utils/gameStats';

const SAVE_KEY = 'the_blob_save_v2';

interface GameStore extends GameState {
  // 수분 관련
  addWater: () => void;
  updateMoisture: (delta: number) => void;

  // 자원 관련
  addAtp: (amount: number) => void;
  spendAtp: (amount: number) => boolean;
  addBiomass: (amount: number) => void;

  // 게임 오브젝트
  setTendrils: (tendrils: Tendril[]) => void;
  setNutrients: (nutrients: Nutrient[]) => void;
  setSpores: (spores: Spore[]) => void;
  setFragments: (fragments: BlobFragment[]) => void;
  updateNucleus: (pulsePhase: number) => void;

  // 상태 관리
  setBlobState: (state: BlobState) => void;
  setGamePhase: (phase: GamePhase) => void;

  // 스테이지 시스템
  updateStageNutrients: (consumed: number) => void;
  startSporulation: () => void;
  completeSporulation: () => void;
  startNewStage: () => void;
  collectFragment: (id: string) => void;
  mergeAllFragments: () => boolean;

  // 업그레이드
  purchaseUpgrade: (type: keyof Upgrades) => boolean;
  getUpgradeCost: (type: keyof Upgrades) => number;
  getUpgradeMultiplier: (type: keyof Upgrades) => number;

  // 저장/로드
  saveGame: () => void;
  loadGame: () => number;
  calculateOfflineEarnings: () => number;
  setGameTime: (time: number) => void;
  resetGame: () => void;
}

const createInitialStage = (stageNumber: number): StageInfo => {
  const totalNutrients =
    GAME_CONFIG.BASE_STAGE_NUTRIENTS +
    (stageNumber - 1) * GAME_CONFIG.NUTRIENTS_PER_STAGE_INCREASE;
  // 난이도 배율: 스테이지가 올라갈수록 영양분 간격 증가, 흡수 속도 감소
  const difficultyMultiplier = 1 + (stageNumber - 1) * GAME_CONFIG.DIFFICULTY_NUTRIENT_SPACING_SCALE;
  return {
    stageNumber,
    totalNutrients,
    remainingNutrients: totalNutrients,
    nutrientPositions: [],
    difficultyMultiplier,
  };
};

const getInitialState = (): GameState => ({
  // 핵심 자원
  moisture: UI.INITIAL_MOISTURE,
  maxMoisture: UI.MAX_MOISTURE,
  biomass: 0,
  atp: UI.INITIAL_ATP,

  // 스테이지
  stage: createInitialStage(1),
  gamePhase: 'growing',
  blobState: 'active',

  // 유전 시스템
  genetics: {
    points: 0,
    permanentBiomassBoost: 0,
    permanentMoistureBoost: 0,
    permanentATPBoost: 0,
  },
  totalSporulations: 0,

  // 게임 오브젝트
  nucleus: {
    position: { x: 0, y: 0 },
    radius: 25,
    pulsePhase: 0,
  },
  tendrils: [],
  nutrients: [],
  spores: [],
  fragments: [],

  // 업그레이드
  upgrades: {
    moistureRetention: 1,
    expansionSpeed: 1,
    digestiveEnzyme: 1,
    autoWatering: 0,
    sporeQuality: 1,
  },

  // 메타
  lastSaveTime: Date.now(),
  gameTime: 0,
  lastWaterTime: Date.now(),
});

export const useGameStore = create<GameStore>((set, get) => ({
  ...getInitialState(),

  // 물 주기
  addWater: () => {
    const state = get();
    const newMoisture = Math.min(state.maxMoisture, state.moisture + GAME_CONFIG.WATER_AMOUNT);
    const wasInDormant = state.blobState === 'dormant';

    set({
      moisture: newMoisture,
      lastWaterTime: Date.now(),
      blobState: newMoisture > GAME_CONFIG.DORMANT_THRESHOLD ? 'active' : state.blobState,
    });

    // 휴면에서 깨어남
    if (wasInDormant && newMoisture > GAME_CONFIG.DORMANT_THRESHOLD) {
      console.log(TEXT.LOG_WAKE_UP);
    }
  },

  // 수분 업데이트
  updateMoisture: (delta: number) => {
    const state = get();
    if (state.blobState === 'sporulating') return;

    const retentionMult = get().getUpgradeMultiplier('moistureRetention');
    const decayRate = GAME_CONFIG.BASE_MOISTURE_DECAY / retentionMult;

    // 자동 급수 체크
    const autoWaterLevel = state.upgrades.autoWatering;
    if (autoWaterLevel > 0 && state.moisture < UI.AUTO_WATER_THRESHOLD) {
      const autoWaterChance = autoWaterLevel * 0.1; // 레벨당 10% 확률
      if (Math.random() < autoWaterChance * delta) {
        get().addWater();
        return;
      }
    }

    const newMoisture = Math.max(0, state.moisture - decayRate * delta);

    set({
      moisture: newMoisture,
      blobState: newMoisture <= GAME_CONFIG.DORMANT_THRESHOLD ? 'dormant' : 'active',
    });
  },

  addAtp: (amount: number) => {
    const boost = get().genetics.permanentATPBoost;
    set((state) => ({
      atp: state.atp + amount * (1 + boost),
    }));
  },

  spendAtp: (amount: number) => {
    const state = get();
    if (state.atp >= amount) {
      set({ atp: state.atp - amount });
      return true;
    }
    return false;
  },

  addBiomass: (amount: number) => {
    const boost = get().genetics.permanentBiomassBoost;
    set((state) => ({
      biomass: state.biomass + amount * (1 + boost),
    }));
  },

  setTendrils: (tendrils: Tendril[]) => set({ tendrils }),
  setNutrients: (nutrients: Nutrient[]) => set({ nutrients }),
  setSpores: (spores: Spore[]) => set({ spores }),
  setFragments: (fragments: BlobFragment[]) => set({ fragments }),

  updateNucleus: (pulsePhase: number) => {
    set((state) => ({
      nucleus: { ...state.nucleus, pulsePhase },
    }));
  },

  setBlobState: (blobState: BlobState) => set({ blobState }),
  setGamePhase: (gamePhase: GamePhase) => set({ gamePhase }),

  updateStageNutrients: (consumed: number) => {
    set((state) => ({
      stage: {
        ...state.stage,
        remainingNutrients: Math.max(0, state.stage.remainingNutrients - consumed),
      },
    }));
  },

  // 포자화 시작
  startSporulation: () => {
    const state = get();
    if (state.biomass < GAME_CONFIG.MIN_BIOMASS_FOR_SPORULATION) {
      console.log(TEXT.WARNING_LOW_BIOMASS);
      return;
    }

    set({
      blobState: 'sporulating',
      gamePhase: 'sporulating',
    });
  },

  // 포자화 완료 - 포자 생성
  completeSporulation: () => {
    const state = get();
    const sporeCount = Math.floor(state.biomass * GAME_CONFIG.SPORES_PER_BIOMASS);
    const qualityMult = get().getUpgradeMultiplier('sporeQuality');
    const genePointsEarned = sporeCount * GAME_CONFIG.GENE_POINTS_PER_SPORE * qualityMult;

    // 포자 생성 (캔버스 중앙에서 퍼져나감)
    const spores: Spore[] = [];
    const centerX = state.nucleus.position.x;
    const centerY = state.nucleus.position.y;

    for (let i = 0; i < Math.min(sporeCount, SPORULATION.SPORE_MAX_COUNT); i++) {
      const angle = (i / sporeCount) * Math.PI * 2 + Math.random() * 0.5;
      const speed = 50 + Math.random() * 100;
      spores.push({
        id: `spore_${i}_${Date.now()}`,
        position: { x: centerX, y: centerY },
        velocity: {
          x: Math.cos(angle) * speed,
          y: Math.sin(angle) * speed,
        },
        collected: false,
        size: SPORULATION.SPORE_SIZE_MIN + Math.random() * SPORULATION.SPORE_SIZE_RANGE,
        alpha: 1,
        bobPhase: Math.random() * Math.PI * 2,
      });
    }

    // 통계 기록
    recordSessionStats({
      stageNumber: state.stage.stageNumber,
      clearTimeSeconds: state.gameTime,
      nutrientsConsumed: state.stage.totalNutrients - state.stage.remainingNutrients,
      peakBiomass: state.biomass,
      sporulationCount: state.totalSporulations + 1,
      timestamp: Date.now(),
    });

    set({
      spores,
      genetics: {
        ...state.genetics,
        points: state.genetics.points + genePointsEarned,
      },
      totalSporulations: state.totalSporulations + 1,
    });
  },

  // 새 스테이지 시작
  startNewStage: () => {
    const state = get();
    const newStageNumber = state.stage.stageNumber + 1;

    // 블롭 조각 생성 (흩어진 상태로 시작)
    const fragments: BlobFragment[] = [];
    const centerX = state.nucleus.position.x;
    const centerY = state.nucleus.position.y;
    const fragmentCount = 5 + Math.floor(state.genetics.points * FRAGMENT.GENETICS_RATIO);

    for (let i = 0; i < Math.min(fragmentCount, FRAGMENT.MAX_COUNT); i++) {
      const angle = (i / fragmentCount) * Math.PI * 2;
      const distance = FRAGMENT.DISTANCE_MIN + Math.random() * FRAGMENT.DISTANCE_RANGE;
      fragments.push({
        id: `fragment_${i}`,
        position: {
          x: centerX + Math.cos(angle) * distance,
          y: centerY + Math.sin(angle) * distance,
        },
        size: 8 + Math.random() * 8,
        merged: false,
        pulsePhase: Math.random() * Math.PI * 2,
      });
    }

    set({
      stage: createInitialStage(newStageNumber),
      gamePhase: 'sporeCollection',
      blobState: 'active',
      moisture: 50 + state.genetics.permanentMoistureBoost * UI.GENETICS_MOISTURE_BOOST,
      biomass: state.genetics.permanentBiomassBoost * UI.GENETICS_BIOMASS_BOOST,
      tendrils: [],
      nutrients: [],
      spores: [],
      fragments,
      nucleus: {
        ...state.nucleus,
        radius: 15, // 작게 시작
      },
    });
  },

  // 조각 수집
  collectFragment: (id: string) => {
    set((state) => ({
      fragments: state.fragments.map((f) =>
        f.id === id ? { ...f, merged: true } : f
      ),
      nucleus: {
        ...state.nucleus,
        radius: state.nucleus.radius + 2,
      },
      biomass: state.biomass + 5,
    }));
  },

  // 모든 조각 합치기 확인
  mergeAllFragments: () => {
    const state = get();
    const allMerged = state.fragments.every((f) => f.merged);

    if (allMerged && state.fragments.length > 0) {
      set({
        gamePhase: 'growing',
        fragments: [],
        nucleus: {
          ...state.nucleus,
          radius: 25,
        },
      });
      return true;
    }
    return false;
  },

  // 업그레이드 구매
  purchaseUpgrade: (type: keyof Upgrades) => {
    const state = get();
    const currentLevel = state.upgrades[type];

    if (currentLevel >= UPGRADE_MAX_LEVEL) return false;

    const cost = UPGRADE_COSTS[type][currentLevel];

    if (state.atp >= cost) {
      set({
        atp: state.atp - cost,
        upgrades: {
          ...state.upgrades,
          [type]: currentLevel + 1,
        },
      });
      return true;
    }
    return false;
  },

  getUpgradeCost: (type: keyof Upgrades) => {
    const currentLevel = get().upgrades[type];
    if (currentLevel >= UPGRADE_MAX_LEVEL) return Infinity;
    return UPGRADE_COSTS[type][currentLevel] || Infinity;
  },

  getUpgradeMultiplier: (type: keyof Upgrades) => {
    const level = get().upgrades[type];
    switch (type) {
      case 'moistureRetention':
        return 1 + (level - 1) * 0.15;
      case 'expansionSpeed':
        return 1 + (level - 1) * 0.2;
      case 'digestiveEnzyme':
        return 1 + (level - 1) * 0.25;
      case 'autoWatering':
        return level; // 레벨 자체가 확률
      case 'sporeQuality':
        return 1 + (level - 1) * 0.3;
      default:
        return 1;
    }
  },

  saveGame: () => {
    const state = get();
    const saveData = {
      moisture: state.moisture,
      biomass: state.biomass,
      atp: state.atp,
      stage: state.stage,
      genetics: state.genetics,
      totalSporulations: state.totalSporulations,
      upgrades: state.upgrades,
      gameTime: state.gameTime,
      lastSaveTime: Date.now(),
    };
    localStorage.setItem(SAVE_KEY, JSON.stringify(saveData));
    set({ lastSaveTime: Date.now() });
  },

  loadGame: () => {
    const savedData = localStorage.getItem(SAVE_KEY);
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        const offlineEarnings = get().calculateOfflineEarnings();

        set({
          moisture: Math.min(UI.MAX_MOISTURE, parsed.moisture || 50),
          biomass: parsed.biomass || 0,
          atp: (parsed.atp || 0) + offlineEarnings,
          stage: parsed.stage || createInitialStage(1),
          genetics: parsed.genetics || getInitialState().genetics,
          totalSporulations: parsed.totalSporulations || 0,
          upgrades: parsed.upgrades || getInitialState().upgrades,
          gameTime: parsed.gameTime || 0,
          lastSaveTime: Date.now(),
          blobState: parsed.moisture > GAME_CONFIG.DORMANT_THRESHOLD ? 'active' : 'dormant',
        });

        return offlineEarnings;
      } catch (e) {
        console.error(TEXT.LOG_SAVE_FAILED, e);
      }
    }
    return 0;
  },

  calculateOfflineEarnings: () => {
    const savedData = localStorage.getItem(SAVE_KEY);
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        const lastSave = parsed.lastSaveTime || Date.now();
        const offlineSeconds = Math.min((Date.now() - lastSave) / 1000, UI.OFFLINE_MAX_HOURS * 60 * 60);

        // 수분이 있었을 때만 수익 발생
        const hadMoisture = parsed.moisture > GAME_CONFIG.DORMANT_THRESHOLD;
        if (!hadMoisture) return 0;

        return offlineSeconds * GAME_CONFIG.OFFLINE_ATP_RATE;
      } catch {
        return 0;
      }
    }
    return 0;
  },

  setGameTime: (time: number) => set({ gameTime: time }),

  resetGame: () => {
    localStorage.removeItem(SAVE_KEY);
    set(getInitialState());
  },
}));
