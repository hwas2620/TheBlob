import React, { useState } from 'react';
import { useGameStore } from '../store/gameStore';
import { spawnWaterEffect } from '../hooks/useGameLoop';

export const WaterButton: React.FC = () => {
  const { addWater, moisture, maxMoisture, blobState, nucleus } = useGameStore();
  const [isAnimating, setIsAnimating] = useState(false);

  const handleClick = () => {
    if (moisture >= maxMoisture) return;

    addWater();
    setIsAnimating(true);
    setTimeout(() => setIsAnimating(false), 300);

    // 캔버스 물방울 이펙트 (핵 위치에서 생성)
    spawnWaterEffect(nucleus.position.x, nucleus.position.y);
  };

  const isDormant = blobState === 'dormant';
  const isFull = moisture >= maxMoisture;

  return (
    <button
      onClick={handleClick}
      disabled={isFull}
      className={`
        relative w-full py-4 px-6 rounded-xl font-bold text-lg
        transition-all duration-200 transform
        ${isAnimating ? 'scale-95' : 'scale-100'}
        ${isFull
          ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
          : isDormant
            ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/30 animate-pulse'
            : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20'
        }
      `}
    >
      <span className="flex items-center justify-center gap-2">
        💧
        {isFull ? '습도 충분' : '물 주기'}
      </span>

      {/* 물방울 효과 */}
      {isAnimating && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="absolute w-full h-full bg-blue-400/30 rounded-xl animate-ping" />
        </div>
      )}
    </button>
  );
};
