import React from 'react';
import { useGameStore } from '../store/gameStore';
import type { Upgrades } from '../types/game';
import { UPGRADE_MAX_LEVEL } from '../types/game';
import { TEXT } from '../text';

interface UpgradeItemProps {
  type: keyof Upgrades;
  name: string;
  description: string;
  icon: string;
}

const UpgradeItem: React.FC<UpgradeItemProps> = ({ type, name, description, icon }) => {
  const { upgrades, atp, purchaseUpgrade, getUpgradeCost, getUpgradeMultiplier } = useGameStore();

  const level = upgrades[type];
  const cost = getUpgradeCost(type);
  const multiplier = getUpgradeMultiplier(type);
  const canAfford = atp >= cost;
  const isMaxed = level >= UPGRADE_MAX_LEVEL;

  const handleClick = () => {
    if (!isMaxed && canAfford) {
      purchaseUpgrade(type);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={isMaxed || !canAfford}
      className={`
        w-full p-3 rounded-lg border transition-all duration-200 text-left
        ${isMaxed
          ? 'bg-green-900/20 border-green-600/30 cursor-default'
          : canAfford
            ? 'bg-yellow-900/30 border-yellow-600/50 hover:bg-yellow-800/40 hover:border-yellow-500 cursor-pointer'
            : 'bg-gray-900/30 border-gray-700/50 cursor-not-allowed opacity-50'
        }
      `}
    >
      <div className="flex items-start gap-3">
        <div className="text-xl">{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-center">
            <span className="font-medium text-yellow-200 text-sm truncate">{name}</span>
            <span className="text-xs text-yellow-500 ml-2">
              Lv.{level}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5 truncate">{description}</p>
          <div className="flex justify-between items-center mt-1.5">
            <span className="text-xs text-green-400">
              {type === 'autoWatering'
                ? TEXT.UPGRADE_CHANCE.replace('{0}', (multiplier * 10).toFixed(0))
                : TEXT.UPGRADE_MULTIPLIER.replace('{0}', multiplier.toFixed(2))}
            </span>
            {!isMaxed ? (
              <span className={`text-xs font-mono ${canAfford ? 'text-yellow-300' : 'text-red-400'}`}>
                {cost.toFixed(0)} {TEXT.UNIT_ATP}
              </span>
            ) : (
              <span className="text-xs text-green-400 font-bold">{TEXT.UPGRADE_MAX}</span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
};

export const UpgradePanel: React.FC = () => {
  return (
    <div className="bg-black/80 backdrop-blur-sm border border-yellow-900/50 rounded-xl p-3">
      <h2 className="text-sm font-bold text-yellow-400 mb-3 flex items-center gap-2">
        {TEXT.PANEL_UPGRADE}
      </h2>

      <div className="space-y-2">
        <UpgradeItem
          type="moistureRetention"
          name={TEXT.UPGRADE_MOISTURE}
          description={TEXT.UPGRADE_MOISTURE_DESC}
          icon="💧"
        />
        <UpgradeItem
          type="expansionSpeed"
          name={TEXT.UPGRADE_EXPANSION}
          description={TEXT.UPGRADE_EXPANSION_DESC}
          icon="🌿"
        />
        <UpgradeItem
          type="digestiveEnzyme"
          name={TEXT.UPGRADE_ENZYME}
          description={TEXT.UPGRADE_ENZYME_DESC}
          icon="🧪"
        />
        <UpgradeItem
          type="autoWatering"
          name={TEXT.UPGRADE_AUTO_WATER}
          description={TEXT.UPGRADE_AUTO_WATER_DESC}
          icon="🚿"
        />
        <UpgradeItem
          type="sporeQuality"
          name={TEXT.UPGRADE_SPORE_QUALITY}
          description={TEXT.UPGRADE_SPORE_QUALITY_DESC}
          icon="✨"
        />
      </div>
    </div>
  );
};
