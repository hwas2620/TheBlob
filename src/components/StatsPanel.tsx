import React from 'react';
import { useGameStore } from '../store/gameStore';
import { GAME_CONFIG } from '../types/game';
import { TEXT, formatText } from '../text';

const formatNumber = (num: number): string => {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(2) + 'K';
  return num.toFixed(1);
};

export const StatsPanel: React.FC = () => {
  const {
    atp,
    biomass,
    stage,
    genetics,
    totalSporulations,
    blobState,
    gamePhase,
  } = useGameStore();

  const nutrientPercentage = (stage.remainingNutrients / stage.totalNutrients) * 100;
  const canSporulate = biomass >= GAME_CONFIG.MIN_BIOMASS_FOR_SPORULATION;

  return (
    <div className="bg-black/80 backdrop-blur-sm border border-yellow-900/50 rounded-xl p-4 space-y-4">
      {/* 스테이지 정보 */}
      <div className="text-center border-b border-yellow-900/30 pb-3">
        <div className="text-xs text-yellow-600 uppercase tracking-wider">Stage</div>
        <div className="text-2xl font-bold text-yellow-400">{stage.stageNumber}</div>
        {totalSporulations > 0 && (
          <div className="text-xs text-purple-400">
            {formatText(TEXT.STAT_SPORULATIONS, totalSporulations)}
          </div>
        )}
      </div>

      {/* ATP */}
      <div className="bg-yellow-900/20 rounded-lg p-3">
        <div className="flex justify-between items-center">
          <span className="text-yellow-500/80 text-xs">⚡ ATP</span>
          <span className="text-yellow-300 font-mono font-bold text-lg">
            {formatNumber(atp)}
          </span>
        </div>
      </div>

      {/* Biomass */}
      <div className="bg-green-900/20 rounded-lg p-3">
        <div className="flex justify-between items-center">
          <span className="text-green-500/80 text-xs">{TEXT.STAT_BIOMASS}</span>
          <span className="text-green-300 font-mono font-bold">
            {formatNumber(biomass)}
          </span>
        </div>
        {canSporulate && gamePhase === 'growing' && (
          <div className="text-xs text-purple-400 mt-1">
            {TEXT.INFO_SPORULATION_READY}
          </div>
        )}
      </div>

      {/* 영양분 잔량 */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-amber-500/80">{TEXT.STAT_NUTRIENTS}</span>
          <span className="text-amber-300">
            {formatNumber(stage.remainingNutrients)} / {formatNumber(stage.totalNutrients)}
          </span>
        </div>
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-amber-500 transition-all duration-500"
            style={{ width: `${nutrientPercentage}%` }}
          />
        </div>
      </div>

      {/* 유전 포인트 */}
      {genetics.points > 0 && (
        <div className="bg-purple-900/20 rounded-lg p-3">
          <div className="flex justify-between items-center">
            <span className="text-purple-500/80 text-xs">{TEXT.STAT_GENETICS}</span>
            <span className="text-purple-300 font-mono">
              {genetics.points.toFixed(1)} GP
            </span>
          </div>
        </div>
      )}

      {/* 상태 표시 */}
      <div className="text-center text-xs">
        {blobState === 'dormant' && (
          <span className="text-gray-400">{TEXT.STATUS_DORMANT}</span>
        )}
        {blobState === 'active' && gamePhase === 'growing' && (
          <span className="text-yellow-400">{TEXT.STATUS_ACTIVE}</span>
        )}
        {blobState === 'sporulating' && (
          <span className="text-orange-400">{TEXT.STATUS_SPORULATING}</span>
        )}
        {gamePhase === 'sporeCollection' && (
          <span className="text-yellow-400">{TEXT.STATUS_FRAGMENT}</span>
        )}
      </div>
    </div>
  );
};
