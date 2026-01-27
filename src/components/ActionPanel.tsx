import React from 'react';
import { useGameStore } from '../store/gameStore';
import { GAME_CONFIG } from '../types/game';
import { WaterButton } from './WaterButton';
import { MoistureBar } from './MoistureBar';

export const ActionPanel: React.FC = () => {
  const {
    biomass,
    gamePhase,
    blobState,
    startSporulation,
    stage,
    saveGame,
    resetGame,
  } = useGameStore();

  const canSporulate = biomass >= GAME_CONFIG.MIN_BIOMASS_FOR_SPORULATION;
  const allNutrientsGone = stage.remainingNutrients <= 0;
  const showSporulateButton = gamePhase === 'growing' && blobState !== 'sporulating';

  const handleSporulate = () => {
    if (canSporulate) {
      startSporulation();
    }
  };

  const handleSave = () => {
    saveGame();
    alert('게임이 저장되었습니다!');
  };

  const handleReset = () => {
    if (confirm('정말로 게임을 초기화하시겠습니까? 모든 진행 상황이 삭제됩니다.')) {
      resetGame();
      window.location.reload();
    }
  };

  return (
    <div className="bg-black/80 backdrop-blur-sm border border-yellow-900/50 rounded-xl p-4 space-y-4">
      {/* 수분 바 */}
      <MoistureBar />

      {/* 물 주기 버튼 */}
      <WaterButton />

      {/* 포자화 버튼 */}
      {showSporulateButton && (
        <button
          onClick={handleSporulate}
          disabled={!canSporulate}
          className={`
            w-full py-3 px-4 rounded-xl font-bold transition-all
            ${canSporulate
              ? allNutrientsGone
                ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-500/30 animate-pulse'
                : 'bg-purple-700 hover:bg-purple-600 text-white'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }
          `}
        >
          <span className="flex items-center justify-center gap-2">
            ✨ 포자화
            {!canSporulate && (
              <span className="text-xs">
                (질량 {GAME_CONFIG.MIN_BIOMASS_FOR_SPORULATION} 필요)
              </span>
            )}
          </span>
        </button>
      )}

      {/* 포자화 중 안내 */}
      {blobState === 'sporulating' && (
        <div className="text-center py-4">
          <div className="text-orange-400 animate-pulse text-lg">
            ✨ 포자화 진행 중...
          </div>
          <p className="text-xs text-gray-500 mt-2">
            새로운 생명으로 환생합니다
          </p>
        </div>
      )}

      {/* 조각 수집 안내 */}
      {gamePhase === 'sporeCollection' && (
        <div className="text-center py-4 bg-yellow-900/20 rounded-lg">
          <div className="text-yellow-400 text-lg">
            🔗 조각을 모으세요!
          </div>
          <p className="text-xs text-gray-400 mt-2">
            흩어진 블롭 조각을 클릭하거나 가까이 가세요
          </p>
        </div>
      )}

      {/* 저장/초기화 버튼 */}
      <div className="flex gap-2 pt-2 border-t border-gray-800">
        <button
          onClick={handleSave}
          className="flex-1 py-2 px-3 rounded-lg bg-blue-900/50 hover:bg-blue-800/50 text-blue-300 text-sm transition-colors"
        >
          💾 저장
        </button>
        <button
          onClick={handleReset}
          className="flex-1 py-2 px-3 rounded-lg bg-red-900/30 hover:bg-red-800/30 text-red-400 text-sm transition-colors"
        >
          🔄 초기화
        </button>
      </div>
    </div>
  );
};
