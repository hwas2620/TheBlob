import React from 'react';
import { useGameStore } from '../store/gameStore';
import { GAME_CONFIG } from '../types/game';
import { MoistureBar } from './MoistureBar';
import { TEXT, formatText } from '../text';

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
    alert(TEXT.TOAST_SAVE_SUCCESS);
  };

  const handleReset = () => {
    if (confirm(TEXT.CONFIRM_RESET)) {
      resetGame();
      window.location.reload();
    }
  };

  return (
    <div className="bg-black/80 backdrop-blur-sm border border-yellow-900/50 rounded-xl p-4 space-y-4">
      {/* 수분 바 */}
      <MoistureBar />

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
            {TEXT.BTN_SPORULATE}
            {!canSporulate && (
              <span className="text-xs">
                ({formatText(TEXT.INFO_SPORULATION_CONDITION, GAME_CONFIG.MIN_BIOMASS_FOR_SPORULATION)})
              </span>
            )}
          </span>
        </button>
      )}

      {/* 포자화 중 안내 */}
      {blobState === 'sporulating' && (
        <div className="text-center py-4">
          <div className="text-orange-400 animate-pulse text-lg">
            {TEXT.BTN_SPORULATE_IN_PROGRESS}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {TEXT.INFO_SPORULATION_DESCRIPTION}
          </p>
        </div>
      )}

      {/* 조각 수집 안내 */}
      {gamePhase === 'sporeCollection' && (
        <div className="text-center py-4 bg-yellow-900/20 rounded-lg">
          <div className="text-yellow-400 text-lg">
            {TEXT.INFO_FRAGMENTS}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            {TEXT.INFO_FRAGMENTS_HELP}
          </p>
        </div>
      )}

      {/* 저장/초기화 버튼 */}
      <div className="flex gap-2 pt-2 border-t border-gray-800">
        <button
          onClick={handleSave}
          className="flex-1 py-2 px-3 rounded-lg bg-blue-900/50 hover:bg-blue-800/50 text-blue-300 text-sm transition-colors"
        >
          {TEXT.BTN_SAVE}
        </button>
        <button
          onClick={handleReset}
          className="flex-1 py-2 px-3 rounded-lg bg-red-900/30 hover:bg-red-800/30 text-red-400 text-sm transition-colors"
        >
          {TEXT.BTN_RESET}
        </button>
      </div>
    </div>
  );
};
