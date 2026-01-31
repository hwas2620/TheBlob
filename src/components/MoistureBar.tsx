import React from 'react';
import { useGameStore } from '../store/gameStore';
import { TEXT } from '../text';

export const MoistureBar: React.FC = () => {
  const { moisture, maxMoisture, blobState } = useGameStore();

  const percentage = (moisture / maxMoisture) * 100;
  const isDormant = blobState === 'dormant';

  const getBarColor = () => {
    if (isDormant) return 'bg-gray-500';
    if (percentage > 60) return 'bg-blue-500';
    if (percentage > 30) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-blue-400 flex items-center gap-1">
          {TEXT.LABEL_MOISTURE}
        </span>
        <span className="text-xs text-blue-300 font-mono">
          {moisture.toFixed(0)}%
        </span>
      </div>
      <div className="h-3 bg-gray-800 rounded-full overflow-hidden border border-gray-700">
        <div
          className={`h-full transition-all duration-300 ${getBarColor()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {isDormant && (
        <p className="text-xs text-red-400 mt-1 animate-pulse">
          {TEXT.WARNING_DORMANT}
        </p>
      )}
    </div>
  );
};
