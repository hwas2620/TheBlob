import React from 'react';
import { useGameStore } from '../store/gameStore';

export const GeneticsPanel: React.FC = () => {
  const { genetics, totalSporulations } = useGameStore();

  const upgrades = [
    {
      key: 'permanentBiomassBoost' as const,
      name: '질량 부스트',
      description: '시작 질량 +5',
      cost: 5,
      icon: '🧬',
    },
    {
      key: 'permanentMoistureBoost' as const,
      name: '습도 부스트',
      description: '시작 습도 +10',
      cost: 3,
      icon: '💧',
    },
    {
      key: 'permanentATPBoost' as const,
      name: 'ATP 부스트',
      description: 'ATP 획득량 +10%',
      cost: 8,
      icon: '⚡',
    },
  ];

  const handlePurchase = (key: keyof typeof genetics, cost: number) => {
    if (genetics.points >= cost) {
      useGameStore.setState((state) => ({
        genetics: {
          ...state.genetics,
          points: state.genetics.points - cost,
          [key]: state.genetics[key] + 1,
        },
      }));
    }
  };

  if (genetics.points === 0 && totalSporulations === 0) {
    return null;
  }

  return (
    <div className="bg-black/80 backdrop-blur-sm border border-purple-900/50 rounded-xl p-4">
      <h3 className="text-purple-400 font-bold mb-3 flex items-center gap-2">
        <span>🧬</span>
        유전자 ({genetics.points.toFixed(0)} GP)
      </h3>

      <div className="space-y-2">
        {upgrades.map((upgrade) => {
          const currentLevel = genetics[upgrade.key];
          const canAfford = genetics.points >= upgrade.cost;

          return (
            <button
              key={upgrade.key}
              onClick={() => handlePurchase(upgrade.key, upgrade.cost)}
              disabled={!canAfford}
              className={`
                w-full p-2 rounded-lg text-left transition-all text-sm
                ${canAfford
                  ? 'bg-purple-900/40 hover:bg-purple-800/50 border border-purple-700/50'
                  : 'bg-gray-900/40 border border-gray-800/50 opacity-50'
                }
              `}
            >
              <div className="flex justify-between items-center">
                <span className="flex items-center gap-2">
                  <span>{upgrade.icon}</span>
                  <span className="text-purple-200">{upgrade.name}</span>
                  <span className="text-purple-500 text-xs">Lv.{currentLevel}</span>
                </span>
                <span className="text-purple-400 text-xs">{upgrade.cost} GP</span>
              </div>
              <p className="text-xs text-gray-500 mt-1 ml-6">{upgrade.description}</p>
            </button>
          );
        })}
      </div>

      <div className="mt-3 pt-3 border-t border-purple-900/30 text-xs text-gray-500">
        포자화 횟수: {totalSporulations}
      </div>
    </div>
  );
};
